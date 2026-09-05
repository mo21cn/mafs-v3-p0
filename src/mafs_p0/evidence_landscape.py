"""R5 EvidenceLandscapePackage: the terminal MAFS-owned semantic artifact.

The package deliberately preserves typed lineage instead of copying evidence
objects into one untyped reference list.  It is a descriptive evidence
landscape only; downstream opportunity, clinical, policy, investment, and
experiment-authorization decisions remain outside MAFS authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import re
from typing import Any

from .collision import CollisionAssessment, SCHEMA_VERSION_B
from .epistemic_route import SemanticBoundaryError
from .research_state import ResearchState


AUTHORITY_BOUNDARY = "EVIDENCE_LANDSCAPE_ONLY"
COVERAGE_KEYS = (
    "requirements_covered",
    "requirements_partially_covered",
    "requirements_uncovered",
    "routes_executed",
    "routes_underexplored",
    "routes_exhausted",
    "evidence_inaccessible",
    "propositions_grounded",
    "propositions_unresolved",
)
ROUTE_HISTORY_KINDS = ("ORIGINAL", "REVISED", "REDIGESTED")
ROUTE_EXECUTION_STATES = (
    "ACTIVE",
    "COVERED",
    "UNDEREXPLORED",
    "EXHAUSTED",
    "BLOCKED",
    "REVISION_CANDIDATE",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_nonempty_dict_records(records: tuple[dict[str, Any], ...], name: str) -> None:
    if any(not isinstance(record, dict) or not record for record in records):
        raise SemanticBoundaryError(f"{name} must contain non-empty records")


@dataclass(frozen=True)
class EvidenceLandscapePackage:
    package_id: str
    source_research_state_id: str
    requirement_ids: tuple[str, ...]
    route_history: tuple[dict[str, Any], ...]
    search_portfolio_history: tuple[dict[str, Any], ...]
    budget_history: tuple[dict[str, Any], ...]
    candidate_pointer_lineage: tuple[dict[str, Any], ...]
    selection_lineage: tuple[dict[str, Any], ...]
    source_document_ids: tuple[str, ...]
    evidence_span_ids: tuple[str, ...]
    proposition_evidence_ids: tuple[str, ...]
    collision_ids: tuple[str, ...]
    supported_scoped_claims: tuple[dict[str, Any], ...]
    contested_scoped_claims: tuple[dict[str, Any], ...]
    unresolved_obligations: tuple[dict[str, Any], ...]
    new_evidence_obligations: tuple[dict[str, Any], ...]
    coverage_summary: dict[str, Any]
    provenance_manifest: dict[str, Any]
    authority_boundary: str = AUTHORITY_BOUNDARY
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not re.fullmatch(r"ELP-[0-9]{3,6}", self.package_id):
            raise SemanticBoundaryError(f"invalid EvidenceLandscapePackage id: {self.package_id!r}")
        if not re.fullmatch(r"RS-[0-9]{3,6}", self.source_research_state_id):
            raise SemanticBoundaryError("ELP requires a valid source ResearchState")
        if self.authority_boundary != AUTHORITY_BOUNDARY:
            raise SemanticBoundaryError(
                "EvidenceLandscapePackage cannot claim downstream decision authority"
            )
        if not self.requirement_ids or not self.route_history:
            raise SemanticBoundaryError("ELP requires requirements and route history")
        for name, records in (
            ("route_history", self.route_history),
            ("search_portfolio_history", self.search_portfolio_history),
            ("budget_history", self.budget_history),
            ("candidate_pointer_lineage", self.candidate_pointer_lineage),
            ("selection_lineage", self.selection_lineage),
        ):
            _require_nonempty_dict_records(records, name)
        self._validate_route_history()
        missing_coverage = set(COVERAGE_KEYS) - set(self.coverage_summary)
        if missing_coverage:
            raise SemanticBoundaryError(
                f"ELP coverage summary is incomplete: {sorted(missing_coverage)}"
            )
        if not self.provenance_manifest:
            raise SemanticBoundaryError("ELP provenance manifest must not be empty")
        if set(self.collision_ids) & {""}:
            raise SemanticBoundaryError("ELP collision references must be stable ids")

    def _validate_route_history(self) -> None:
        route_ids: set[str] = set()
        for record in self.route_history:
            required = {"route_id", "history_kind", "parent_route_ids", "execution_state"}
            missing = required - set(record)
            if missing:
                raise SemanticBoundaryError(
                    f"route history record is missing fields: {sorted(missing)}"
                )
            route_id = record["route_id"]
            if not isinstance(route_id, str) or not re.fullmatch(r"ER-[0-9]{3,6}", route_id):
                raise SemanticBoundaryError("route history has invalid route_id")
            if route_id in route_ids:
                raise SemanticBoundaryError("route history cannot flatten duplicate route identities")
            route_ids.add(route_id)
            if record["history_kind"] not in ROUTE_HISTORY_KINDS:
                raise SemanticBoundaryError("route history kind must preserve route origin")
            if record["execution_state"] not in ROUTE_EXECUTION_STATES:
                raise SemanticBoundaryError("route history has invalid execution state")
            parents = record["parent_route_ids"]
            if not isinstance(parents, list):
                raise SemanticBoundaryError("route parent lineage must be a list")
            if record["history_kind"] == "ORIGINAL" and parents:
                raise SemanticBoundaryError("original route cannot declare parent routes")
            if record["history_kind"] != "ORIGINAL" and not parents:
                raise SemanticBoundaryError("revised/re-digested route must preserve parent lineage")

    @classmethod
    def from_research_state(
        cls,
        *,
        package_id: str,
        state: ResearchState,
        route_history: tuple[dict[str, Any], ...],
        search_portfolio_history: tuple[dict[str, Any], ...],
        budget_history: tuple[dict[str, Any], ...],
        candidate_pointer_lineage: tuple[dict[str, Any], ...],
        selection_lineage: tuple[dict[str, Any], ...],
        source_document_ids: tuple[str, ...],
        evidence_span_ids: tuple[str, ...],
        proposition_evidence_ids: tuple[str, ...],
        collisions: tuple[CollisionAssessment, ...],
        coverage_summary: dict[str, Any],
        provenance_manifest: dict[str, Any],
        authority_boundary: str = AUTHORITY_BOUNDARY,
        created_at: str | None = None,
    ) -> "EvidenceLandscapePackage":
        collision_ids = tuple(collision.collision_id for collision in collisions)
        if collision_ids != state.collision_ids:
            raise SemanticBoundaryError(
                "ELP collision references must exactly preserve the source ResearchState"
            )
        if tuple(proposition_evidence_ids) != state.proposition_evidence_ids:
            raise SemanticBoundaryError(
                "ELP proposition references must exactly preserve the source ResearchState"
            )
        recorded_routes = {record.get("route_id") for record in route_history}
        missing_routes = set(state.active_route_ids) - recorded_routes
        if missing_routes:
            raise SemanticBoundaryError(
                f"ELP route history omits active routes: {sorted(missing_routes)}"
            )
        state_supported = tuple(claim.to_dict() for claim in state.supported_scoped_claims)
        state_contested = tuple(claim.to_dict() for claim in state.contested_scoped_claims)
        state_unresolved = tuple(
            obligation.to_dict() for obligation in state.unresolved_obligations
        )
        state_new = tuple(
            obligation.to_dict() for obligation in state.new_evidence_obligations
        )
        return cls(
            package_id=package_id,
            source_research_state_id=state.research_state_id,
            requirement_ids=state.requirements,
            route_history=route_history,
            search_portfolio_history=search_portfolio_history,
            budget_history=budget_history,
            candidate_pointer_lineage=candidate_pointer_lineage,
            selection_lineage=selection_lineage,
            source_document_ids=source_document_ids,
            evidence_span_ids=evidence_span_ids,
            proposition_evidence_ids=proposition_evidence_ids,
            collision_ids=collision_ids,
            supported_scoped_claims=state_supported,
            contested_scoped_claims=state_contested,
            unresolved_obligations=state_unresolved,
            new_evidence_obligations=state_new,
            coverage_summary=dict(coverage_summary),
            provenance_manifest=dict(provenance_manifest),
            authority_boundary=authority_boundary,
            created_at=created_at or _now_iso(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION_B,
            "package_id": self.package_id,
            "source_research_state_id": self.source_research_state_id,
            "requirement_ids": list(self.requirement_ids),
            "route_history": list(self.route_history),
            "search_portfolio_history": list(self.search_portfolio_history),
            "budget_history": list(self.budget_history),
            "candidate_pointer_lineage": list(self.candidate_pointer_lineage),
            "selection_lineage": list(self.selection_lineage),
            "source_document_ids": list(self.source_document_ids),
            "evidence_span_ids": list(self.evidence_span_ids),
            "proposition_evidence_ids": list(self.proposition_evidence_ids),
            "collision_ids": list(self.collision_ids),
            "supported_scoped_claims": list(self.supported_scoped_claims),
            "contested_scoped_claims": list(self.contested_scoped_claims),
            "unresolved_obligations": list(self.unresolved_obligations),
            "new_evidence_obligations": list(self.new_evidence_obligations),
            "coverage_summary": dict(self.coverage_summary),
            "provenance_manifest": dict(self.provenance_manifest),
            "authority_boundary": self.authority_boundary,
            "created_at": self.created_at,
        }

    def to_canonical_json(self) -> str:
        """Deterministic serialization for manifests and Gate M5 replay."""
        return json.dumps(
            self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
