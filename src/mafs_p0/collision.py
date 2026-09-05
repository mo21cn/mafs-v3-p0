"""R4 scope-aware collision artifacts.

Scientific interpretation remains externalized: a human or model adjudicator
declares the relationship, while this module validates traceability, grounding,
scope comparability, evidence roles, and the contract's fail-closed boundaries.
It deliberately contains no embedding, voting, or lexical-similarity classifier.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Any

from .epistemic_route import SemanticBoundaryError
from .evidence_resolution import EVIDENCE_ROLES, PropositionEvidence


SCHEMA_VERSION_B = "3.0-post-p1p5-b"
COLLISION_TYPES = (
    "SUPPORTING_CONVERGENCE",
    "DIRECT_CONTRADICTION",
    "BOUNDARY_CONDITION",
    "MEASUREMENT_CONFLICT",
    "POPULATION_OR_CONTEXT_DEPENDENCE",
    "INSUFFICIENT_EVIDENCE",
    "UNRESOLVED",
)
COMPARABILITY_STATUSES = (
    "COMPARABLE",
    "PARTIALLY_COMPARABLE",
    "NOT_COMPARABLE",
    "UNRESOLVED",
)
CLAIM_RELATIONS = (
    "SUPPORTS_SCOPE_CLAIM",
    "OPPOSES_SCOPE_CLAIM",
    "MIXED",
    "UNRESOLVED",
)
SCOPE_DIMENSIONS = (
    "population_or_system",
    "intervention_or_exposure",
    "comparator",
    "outcome",
    "measurement_modality",
    "time_scale",
    "context_or_environment",
    "direction",
    "certainty_or_statistical_status",
)
_CONTEXT_DIMENSIONS = {
    "population_or_system",
    "intervention_or_exposure",
    "comparator",
    "outcome",
    "time_scale",
    "context_or_environment",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class ClaimScope:
    population_or_system: str
    intervention_or_exposure: str
    comparator: str
    outcome: str
    measurement_modality: str
    time_scale: str
    context_or_environment: str
    direction: str
    certainty_or_statistical_status: str

    def __post_init__(self) -> None:
        empty = [name for name in SCOPE_DIMENSIONS if not getattr(self, name).strip()]
        if empty:
            raise SemanticBoundaryError(f"claim scope has empty dimensions: {empty}")

    def to_dict(self) -> dict[str, str]:
        return {name: getattr(self, name) for name in SCOPE_DIMENSIONS}


@dataclass(frozen=True)
class ScopedPropositionEvidence:
    evidence: PropositionEvidence
    requirement_ids: tuple[str, ...]
    route_ids: tuple[str, ...]
    claim_text: str
    claim_scope: ClaimScope
    claim_relation: str
    evidence_roles: tuple[str, ...]
    source_limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, PropositionEvidence):
            raise SemanticBoundaryError(
                "collision input must be PropositionEvidence, not bibliographic identity"
            )
        if not self.requirement_ids or not self.route_ids or not self.claim_text.strip():
            raise SemanticBoundaryError(
                "scoped proposition requires requirement, route, and claim lineage"
            )
        if self.claim_relation not in CLAIM_RELATIONS:
            raise SemanticBoundaryError(f"invalid claim relation: {self.claim_relation!r}")
        unknown_roles = set(self.evidence_roles) - set(EVIDENCE_ROLES)
        if unknown_roles:
            raise SemanticBoundaryError(f"unknown evidence roles: {sorted(unknown_roles)}")
        if self.evidence.grounding_status == "CITABLE_SPAN" and not self.evidence_roles:
            raise SemanticBoundaryError("grounded collision input must preserve evidence roles")

    @property
    def grounded(self) -> bool:
        return (
            self.evidence.grounding_status == "CITABLE_SPAN"
            and self.evidence.relation != "NOT_GROUNDED"
            and bool(self.evidence.span_ids)
        )

    def to_scope_record(self) -> dict[str, Any]:
        return {
            "proposition_evidence_id": self.evidence.proposition_evidence_id,
            "claim_text": self.claim_text,
            "claim_scope": self.claim_scope.to_dict(),
            "claim_relation": self.claim_relation,
        }


def _scope_alignment(
    evidence: tuple[ScopedPropositionEvidence, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    aligned: list[str] = []
    differing: list[str] = []
    for dimension in SCOPE_DIMENSIONS:
        values = {getattr(item.claim_scope, dimension).casefold() for item in evidence}
        (aligned if len(values) == 1 else differing).append(dimension)
    return tuple(aligned), tuple(differing)


@dataclass(frozen=True)
class CollisionAssessment:
    collision_id: str
    proposition_evidence_ids: tuple[str, ...]
    requirement_ids: tuple[str, ...]
    route_ids: tuple[str, ...]
    claim_scope: tuple[dict[str, Any], ...]
    comparability: dict[str, Any]
    collision_type: str
    rationale: str
    supporting_span_ids: tuple[str, ...]
    evidence_roles_by_proposition: dict[str, tuple[str, ...]]
    source_limitations_by_proposition: dict[str, tuple[str, ...]]
    uncertainty: str
    status: str
    provenance: dict[str, Any]
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not re.fullmatch(r"CA-[0-9]{3,6}", self.collision_id):
            raise SemanticBoundaryError(f"invalid collision_id: {self.collision_id!r}")
        if len(self.proposition_evidence_ids) < 2:
            raise SemanticBoundaryError("CollisionAssessment requires at least two propositions")
        if len(set(self.proposition_evidence_ids)) != len(self.proposition_evidence_ids):
            raise SemanticBoundaryError("collision proposition evidence must be unique")
        if self.collision_type not in COLLISION_TYPES:
            raise SemanticBoundaryError(f"invalid collision type: {self.collision_type!r}")
        if self.comparability.get("status") not in COMPARABILITY_STATUSES:
            raise SemanticBoundaryError("invalid collision comparability status")
        if self.status not in {"ASSESSED", "UNRESOLVED", "INSUFFICIENT"}:
            raise SemanticBoundaryError(f"invalid collision status: {self.status!r}")
        if not self.rationale.strip() or not self.uncertainty.strip() or not self.provenance:
            raise SemanticBoundaryError("collision requires rationale, uncertainty, and provenance")

    @classmethod
    def assess(
        cls,
        *,
        collision_id: str,
        evidence: tuple[ScopedPropositionEvidence, ...],
        collision_type: str,
        comparability_status: str,
        comparability_rationale: str,
        rationale: str,
        uncertainty: str,
        adjudication_authority: str,
        requires_statistical_evidence: bool = False,
    ) -> "CollisionAssessment":
        if len(evidence) < 2:
            raise SemanticBoundaryError("collision assessment requires multiple evidence inputs")
        if collision_type not in COLLISION_TYPES:
            raise SemanticBoundaryError(f"invalid collision type: {collision_type!r}")
        if comparability_status not in COMPARABILITY_STATUSES:
            raise SemanticBoundaryError(
                f"invalid comparability status: {comparability_status!r}"
            )
        if not comparability_rationale.strip() or not adjudication_authority.strip():
            raise SemanticBoundaryError(
                "comparability and collision adjudication require externalized rationale/authority"
            )

        grounded = tuple(item for item in evidence if item.grounded)
        if len(grounded) != len(evidence) and collision_type != "INSUFFICIENT_EVIDENCE":
            raise SemanticBoundaryError(
                "ungrounded, inaccessible, or not-addressed evidence cannot create a collision"
            )

        aligned, differing = _scope_alignment(evidence)
        substantive_differences = set(differing) - {"direction"}
        relations = {item.claim_relation for item in evidence}

        if collision_type == "DIRECT_CONTRADICTION":
            if comparability_status != "COMPARABLE" or substantive_differences:
                raise SemanticBoundaryError(
                    "direct contradiction requires aligned substantive claim scope"
                )
            if not {
                "SUPPORTS_SCOPE_CLAIM",
                "OPPOSES_SCOPE_CLAIM",
            }.issubset(relations):
                raise SemanticBoundaryError(
                    "direct contradiction requires opposing scoped claim relations"
                )
        elif collision_type == "BOUNDARY_CONDITION":
            if not (substantive_differences & _CONTEXT_DIMENSIONS):
                raise SemanticBoundaryError(
                    "boundary condition requires an explicit contextual scope difference"
                )
        elif collision_type == "POPULATION_OR_CONTEXT_DEPENDENCE":
            if not (
                substantive_differences
                & {"population_or_system", "context_or_environment", "time_scale"}
            ):
                raise SemanticBoundaryError(
                    "population/context dependence requires a population, context, or time difference"
                )
        elif collision_type == "MEASUREMENT_CONFLICT":
            if "measurement_modality" not in differing:
                raise SemanticBoundaryError(
                    "measurement conflict requires differing measurement modalities"
                )
        elif collision_type == "SUPPORTING_CONVERGENCE":
            if "OPPOSES_SCOPE_CLAIM" in relations or not grounded:
                raise SemanticBoundaryError(
                    "supporting convergence requires grounded, non-opposing evidence"
                )

        if requires_statistical_evidence:
            missing = [
                item.evidence.proposition_evidence_id
                for item in grounded
                if "STATISTICAL_RESULT" not in item.evidence_roles
            ]
            if missing:
                raise SemanticBoundaryError(
                    "statistical collision requires STATISTICAL_RESULT evidence roles: "
                    f"{missing}"
                )

        proposition_ids = tuple(item.evidence.proposition_evidence_id for item in evidence)
        requirements = tuple(
            dict.fromkeys(req for item in evidence for req in item.requirement_ids)
        )
        routes = tuple(dict.fromkeys(route for item in evidence for route in item.route_ids))
        span_ids = tuple(
            dict.fromkeys(span for item in grounded for span in item.evidence.span_ids)
        )
        status = "ASSESSED"
        if collision_type == "INSUFFICIENT_EVIDENCE":
            status = "INSUFFICIENT"
        elif collision_type == "UNRESOLVED":
            status = "UNRESOLVED"

        return cls(
            collision_id=collision_id,
            proposition_evidence_ids=proposition_ids,
            requirement_ids=requirements,
            route_ids=routes,
            claim_scope=tuple(item.to_scope_record() for item in evidence),
            comparability={
                "status": comparability_status,
                "aligned_dimensions": list(aligned),
                "differing_dimensions": list(differing),
                "rationale": comparability_rationale,
            },
            collision_type=collision_type,
            rationale=rationale,
            supporting_span_ids=span_ids,
            evidence_roles_by_proposition={
                item.evidence.proposition_evidence_id: item.evidence_roles
                for item in evidence
            },
            source_limitations_by_proposition={
                item.evidence.proposition_evidence_id: item.source_limitations
                for item in evidence
            },
            uncertainty=uncertainty,
            status=status,
            provenance={
                "adjudication_authority": adjudication_authority,
                "mechanical_similarity_determined_type": False,
                "scope_dimensions_inspected": list(SCOPE_DIMENSIONS),
                "requires_statistical_evidence": requires_statistical_evidence,
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION_B,
            "collision_id": self.collision_id,
            "proposition_evidence_ids": list(self.proposition_evidence_ids),
            "requirement_ids": list(self.requirement_ids),
            "route_ids": list(self.route_ids),
            "claim_scope": list(self.claim_scope),
            "comparability": dict(self.comparability),
            "collision_type": self.collision_type,
            "rationale": self.rationale,
            "supporting_span_ids": list(self.supporting_span_ids),
            "evidence_roles_by_proposition": {
                key: list(value) for key, value in self.evidence_roles_by_proposition.items()
            },
            "source_limitations_by_proposition": {
                key: list(value)
                for key, value in self.source_limitations_by_proposition.items()
            },
            "uncertainty": self.uncertainty,
            "status": self.status,
            "provenance": dict(self.provenance),
            "created_at": self.created_at,
        }
