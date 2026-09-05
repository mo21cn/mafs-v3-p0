"""R4 append-only scientific state and governed re-digestion artifacts."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Any

from .collision import CollisionAssessment, SCHEMA_VERSION_B
from .epistemic_route import (
    EpistemicRoute,
    RequirementRouteFidelityReview,
    SemanticBoundaryError,
    assert_open_discovery_pure,
)


CLAIM_STATUSES = (
    "SUPPORTED",
    "CONTESTED",
    "CONTEXT_DEPENDENT",
    "UNRESOLVED",
    "INSUFFICIENT_EVIDENCE",
)
RESEARCH_ROUTE_STATUSES = (
    "ACTIVE",
    "COVERED",
    "UNDEREXPLORED",
    "EXHAUSTED",
    "BLOCKED",
    "REVISION_CANDIDATE",
)
OBLIGATION_AUTHORIZATION_STATUSES = (
    "PROPOSED",
    "AUTHORIZED",
    "DEFERRED",
    "REJECTED",
)
REDIGESTION_STATUSES = ("PROPOSED", "AUTHORIZED", "BLOCKED")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ordered_union(existing: tuple[str, ...], added: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(existing + added))


@dataclass(frozen=True)
class ScopedClaim:
    claim_id: str
    text: str
    scope: dict[str, str]
    status: str
    proposition_evidence_ids: tuple[str, ...]
    collision_ids: tuple[str, ...]
    uncertainty: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"CLM-[0-9]{3,6}", self.claim_id):
            raise SemanticBoundaryError(f"invalid claim_id: {self.claim_id!r}")
        if self.status not in CLAIM_STATUSES:
            raise SemanticBoundaryError(f"invalid scoped claim status: {self.status!r}")
        if not self.text.strip() or not self.scope or not self.uncertainty.strip():
            raise SemanticBoundaryError("scoped claim requires text, scope, and uncertainty")
        if not self.proposition_evidence_ids:
            raise SemanticBoundaryError("scoped claim requires proposition evidence lineage")

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "text": self.text,
            "scope": dict(self.scope),
            "status": self.status,
            "proposition_evidence_ids": list(self.proposition_evidence_ids),
            "collision_ids": list(self.collision_ids),
            "uncertainty": self.uncertainty,
        }


@dataclass(frozen=True)
class RouteStatusRecord:
    route_id: str
    status: str
    rationale: str
    triggering_collision_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not re.fullmatch(r"ER-[0-9]{3,6}", self.route_id):
            raise SemanticBoundaryError(f"invalid route status route_id: {self.route_id!r}")
        if self.status not in RESEARCH_ROUTE_STATUSES:
            raise SemanticBoundaryError(f"invalid research route status: {self.status!r}")
        if not self.rationale.strip():
            raise SemanticBoundaryError("route status requires rationale")

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "status": self.status,
            "rationale": self.rationale,
            "triggering_collision_ids": list(self.triggering_collision_ids),
        }


@dataclass(frozen=True)
class NewEvidenceObligation:
    obligation_id: str
    trigger_collision_ids: tuple[str, ...]
    trigger_research_state_id: str
    scientific_question: str
    why_current_evidence_is_insufficient: str
    required_evidence_type: str
    authorization_status: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"EO-[0-9]{3,6}", self.obligation_id):
            raise SemanticBoundaryError(f"invalid obligation_id: {self.obligation_id!r}")
        if not re.fullmatch(r"RS-[0-9]{3,6}", self.trigger_research_state_id):
            raise SemanticBoundaryError("new evidence obligation requires a ResearchState trigger")
        if self.authorization_status not in OBLIGATION_AUTHORIZATION_STATUSES:
            raise SemanticBoundaryError(
                f"invalid obligation authorization: {self.authorization_status!r}"
            )
        if not self.trigger_collision_ids:
            raise SemanticBoundaryError("new evidence obligation requires a collision trigger")
        if not all(
            value.strip()
            for value in (
                self.scientific_question,
                self.why_current_evidence_is_insufficient,
                self.required_evidence_type,
            )
        ):
            raise SemanticBoundaryError("new evidence obligation has empty semantic fields")

    def to_dict(self) -> dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "trigger_collision_ids": list(self.trigger_collision_ids),
            "trigger_research_state_id": self.trigger_research_state_id,
            "scientific_question": self.scientific_question,
            "why_current_evidence_is_insufficient": self.why_current_evidence_is_insufficient,
            "required_evidence_type": self.required_evidence_type,
            "authorization_status": self.authorization_status,
        }


@dataclass(frozen=True)
class ResearchState:
    research_state_id: str
    parent_research_state_id: str | None
    requirements: tuple[str, ...]
    active_route_ids: tuple[str, ...]
    proposition_evidence_ids: tuple[str, ...]
    collision_ids: tuple[str, ...]
    supported_scoped_claims: tuple[ScopedClaim, ...]
    contested_scoped_claims: tuple[ScopedClaim, ...]
    unresolved_obligations: tuple[NewEvidenceObligation, ...]
    route_status: tuple[RouteStatusRecord, ...]
    new_evidence_obligations: tuple[NewEvidenceObligation, ...]
    redigestion_required: bool
    redigestion_reasons: tuple[str, ...]
    provenance: dict[str, Any]
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not re.fullmatch(r"RS-[0-9]{3,6}", self.research_state_id):
            raise SemanticBoundaryError(
                f"invalid research_state_id: {self.research_state_id!r}"
            )
        if self.parent_research_state_id == self.research_state_id:
            raise SemanticBoundaryError("ResearchState cannot parent itself")
        if not self.requirements or not self.active_route_ids or not self.provenance:
            raise SemanticBoundaryError(
                "ResearchState requires requirements, active routes, and provenance"
            )
        if self.redigestion_required and not self.redigestion_reasons:
            raise SemanticBoundaryError(
                "redigestion_required needs explicit reasons"
            )
        known_collision_ids = set(self.collision_ids)
        for obligation in self.new_evidence_obligations:
            if obligation.trigger_research_state_id != self.research_state_id:
                raise SemanticBoundaryError(
                    "new evidence obligation must identify the state that created it"
                )
            if not set(obligation.trigger_collision_ids).issubset(known_collision_ids):
                raise SemanticBoundaryError(
                    "new evidence obligation references an unknown collision"
                )
        if not set(self.new_evidence_obligations).issubset(
            set(self.unresolved_obligations)
        ):
            raise SemanticBoundaryError(
                "new evidence obligations must remain visible as unresolved obligations"
            )

    @classmethod
    def initial(
        cls,
        *,
        research_state_id: str,
        requirements: tuple[str, ...],
        active_route_ids: tuple[str, ...],
        proposition_evidence_ids: tuple[str, ...],
        route_status: tuple[RouteStatusRecord, ...],
        provenance: dict[str, Any],
        supported_scoped_claims: tuple[ScopedClaim, ...] = (),
    ) -> "ResearchState":
        return cls(
            research_state_id=research_state_id,
            parent_research_state_id=None,
            requirements=requirements,
            active_route_ids=active_route_ids,
            proposition_evidence_ids=proposition_evidence_ids,
            collision_ids=(),
            supported_scoped_claims=supported_scoped_claims,
            contested_scoped_claims=(),
            unresolved_obligations=(),
            route_status=route_status,
            new_evidence_obligations=(),
            redigestion_required=False,
            redigestion_reasons=(),
            provenance=provenance,
        )

    @classmethod
    def evolve(
        cls,
        *,
        research_state_id: str,
        parent: "ResearchState",
        added_proposition_evidence_ids: tuple[str, ...] = (),
        added_collisions: tuple[CollisionAssessment, ...] = (),
        added_supported_claims: tuple[ScopedClaim, ...] = (),
        added_contested_claims: tuple[ScopedClaim, ...] = (),
        added_route_status: tuple[RouteStatusRecord, ...] = (),
        new_evidence_obligations: tuple[NewEvidenceObligation, ...] = (),
        added_active_route_ids: tuple[str, ...] = (),
        redigestion_required: bool = False,
        redigestion_reasons: tuple[str, ...] = (),
        provenance: dict[str, Any],
    ) -> "ResearchState":
        if research_state_id == parent.research_state_id:
            raise SemanticBoundaryError("new evidence must create a new ResearchState")
        collision_ids = tuple(collision.collision_id for collision in added_collisions)
        for obligation in new_evidence_obligations:
            if obligation.trigger_research_state_id != research_state_id:
                raise SemanticBoundaryError(
                    "new obligation trigger must match the evolved ResearchState"
                )
            if not set(obligation.trigger_collision_ids).issubset(
                set(parent.collision_ids) | set(collision_ids)
            ):
                raise SemanticBoundaryError(
                    "new obligation trigger collision is absent from state lineage"
                )
        return cls(
            research_state_id=research_state_id,
            parent_research_state_id=parent.research_state_id,
            requirements=parent.requirements,
            active_route_ids=_ordered_union(
                parent.active_route_ids, added_active_route_ids
            ),
            proposition_evidence_ids=_ordered_union(
                parent.proposition_evidence_ids, added_proposition_evidence_ids
            ),
            collision_ids=_ordered_union(parent.collision_ids, collision_ids),
            supported_scoped_claims=parent.supported_scoped_claims + added_supported_claims,
            contested_scoped_claims=parent.contested_scoped_claims + added_contested_claims,
            unresolved_obligations=(
                parent.unresolved_obligations + new_evidence_obligations
            ),
            route_status=parent.route_status + added_route_status,
            new_evidence_obligations=new_evidence_obligations,
            redigestion_required=redigestion_required,
            redigestion_reasons=redigestion_reasons,
            provenance={**provenance, "parent_research_state_id": parent.research_state_id},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION_B,
            "research_state_id": self.research_state_id,
            "parent_research_state_id": self.parent_research_state_id,
            "requirements": list(self.requirements),
            "active_route_ids": list(self.active_route_ids),
            "proposition_evidence_ids": list(self.proposition_evidence_ids),
            "collision_ids": list(self.collision_ids),
            "supported_scoped_claims": [
                claim.to_dict() for claim in self.supported_scoped_claims
            ],
            "contested_scoped_claims": [
                claim.to_dict() for claim in self.contested_scoped_claims
            ],
            "unresolved_obligations": [
                obligation.to_dict() for obligation in self.unresolved_obligations
            ],
            "route_status": [status.to_dict() for status in self.route_status],
            "new_evidence_obligations": [
                obligation.to_dict() for obligation in self.new_evidence_obligations
            ],
            "redigestion_required": self.redigestion_required,
            "redigestion_reasons": list(self.redigestion_reasons),
            "provenance": dict(self.provenance),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ReDigestionRequest:
    redigestion_request_id: str
    research_state_id: str
    origin_requirement_ids: tuple[str, ...]
    trigger_collision_ids: tuple[str, ...]
    trigger_obligation_ids: tuple[str, ...]
    parent_route_ids: tuple[str, ...]
    reason: str
    budget_authorization: dict[str, Any]
    status: str
    provenance: dict[str, Any]
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not re.fullmatch(r"RDR-[0-9]{3,6}", self.redigestion_request_id):
            raise SemanticBoundaryError(
                f"invalid redigestion_request_id: {self.redigestion_request_id!r}"
            )
        if self.status not in REDIGESTION_STATUSES:
            raise SemanticBoundaryError(f"invalid re-digestion status: {self.status!r}")
        if not all(
            (
                self.origin_requirement_ids,
                self.trigger_collision_ids,
                self.trigger_obligation_ids,
                self.parent_route_ids,
                self.reason.strip(),
                self.provenance,
            )
        ):
            raise SemanticBoundaryError(
                "re-digestion requires requirement, trigger, route, reason, and provenance"
            )
        if self.status == "AUTHORIZED":
            if self.budget_authorization.get("authorized") is not True:
                raise SemanticBoundaryError(
                    "authorized re-digestion requires explicit budget authorization"
                )
            units = self.budget_authorization.get("units")
            if not isinstance(units, int) or isinstance(units, bool) or units <= 0:
                raise SemanticBoundaryError(
                    "authorized re-digestion requires a positive integer budget"
                )
            if not str(self.budget_authorization.get("authority", "")).strip():
                raise SemanticBoundaryError(
                    "authorized re-digestion requires budget authority"
                )

    @classmethod
    def from_state(
        cls,
        *,
        redigestion_request_id: str,
        state: ResearchState,
        origin_requirement_ids: tuple[str, ...],
        trigger_collision_ids: tuple[str, ...],
        trigger_obligation_ids: tuple[str, ...],
        parent_route_ids: tuple[str, ...],
        reason: str,
        budget_authorization: dict[str, Any],
        status: str,
        provenance: dict[str, Any],
    ) -> "ReDigestionRequest":
        if status == "AUTHORIZED" and not state.redigestion_required:
            raise SemanticBoundaryError(
                "ResearchState does not authorize a re-digestion requirement"
            )
        if not set(origin_requirement_ids).issubset(state.requirements):
            raise SemanticBoundaryError("re-digestion references unknown requirements")
        if not set(trigger_collision_ids).issubset(state.collision_ids):
            raise SemanticBoundaryError("re-digestion references unknown collisions")
        obligations = {
            obligation.obligation_id: obligation
            for obligation in state.unresolved_obligations
        }
        if not set(trigger_obligation_ids).issubset(obligations):
            raise SemanticBoundaryError("re-digestion references unknown obligations")
        if status == "AUTHORIZED" and any(
            obligations[obligation_id].authorization_status != "AUTHORIZED"
            for obligation_id in trigger_obligation_ids
        ):
            raise SemanticBoundaryError(
                "re-digestion cannot use an obligation without explicit authorization"
            )
        if not set(parent_route_ids).issubset(state.active_route_ids):
            raise SemanticBoundaryError("re-digestion references unknown parent routes")
        return cls(
            redigestion_request_id=redigestion_request_id,
            research_state_id=state.research_state_id,
            origin_requirement_ids=origin_requirement_ids,
            trigger_collision_ids=trigger_collision_ids,
            trigger_obligation_ids=trigger_obligation_ids,
            parent_route_ids=parent_route_ids,
            reason=reason,
            budget_authorization=dict(budget_authorization),
            status=status,
            provenance=provenance,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION_B,
            "redigestion_request_id": self.redigestion_request_id,
            "research_state_id": self.research_state_id,
            "origin_requirement_ids": list(self.origin_requirement_ids),
            "trigger_collision_ids": list(self.trigger_collision_ids),
            "trigger_obligation_ids": list(self.trigger_obligation_ids),
            "parent_route_ids": list(self.parent_route_ids),
            "reason": self.reason,
            "budget_authorization": dict(self.budget_authorization),
            "status": self.status,
            "provenance": dict(self.provenance),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class RouteRevisionLineage:
    lineage_id: str
    redigestion_request_id: str
    parent_route_ids: tuple[str, ...]
    revised_route_ids: tuple[str, ...]
    fidelity_review_ids: tuple[str, ...]
    status: str
    provenance: dict[str, Any]
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not re.fullmatch(r"RRL-[0-9]{3,6}", self.lineage_id):
            raise SemanticBoundaryError(f"invalid route lineage id: {self.lineage_id!r}")
        if self.status != "VALIDATED":
            raise SemanticBoundaryError("route revision lineage must be VALIDATED")
        if not self.parent_route_ids or not self.revised_route_ids or not self.provenance:
            raise SemanticBoundaryError("route revision lineage is incomplete")
        if set(self.parent_route_ids) & set(self.revised_route_ids):
            raise SemanticBoundaryError("re-digestion cannot overwrite a parent route")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION_B,
            "lineage_id": self.lineage_id,
            "redigestion_request_id": self.redigestion_request_id,
            "parent_route_ids": list(self.parent_route_ids),
            "revised_route_ids": list(self.revised_route_ids),
            "fidelity_review_ids": list(self.fidelity_review_ids),
            "status": self.status,
            "provenance": dict(self.provenance),
            "created_at": self.created_at,
        }


def validate_redigested_routes(
    *,
    lineage_id: str,
    request: ReDigestionRequest,
    routes_and_reviews: tuple[
        tuple[EpistemicRoute, RequirementRouteFidelityReview], ...
    ],
    provenance: dict[str, Any],
) -> RouteRevisionLineage:
    if request.status != "AUTHORIZED":
        raise SemanticBoundaryError("re-digested routes require an AUTHORIZED request")
    if not routes_and_reviews:
        raise SemanticBoundaryError("re-digestion produced no route candidates")
    revised: list[str] = []
    reviews: list[str] = []
    for route, review in routes_and_reviews:
        if route.route_id in request.parent_route_ids:
            raise SemanticBoundaryError("re-digestion attempted to overwrite a parent route")
        if route.origin_requirement_id not in request.origin_requirement_ids:
            raise SemanticBoundaryError(
                "re-digested route does not preserve an origin requirement"
            )
        review.require_execution_allowed(route)
        assert_open_discovery_pure(route.to_dict())
        revised.append(route.route_id)
        reviews.append(review.review_id)
    return RouteRevisionLineage(
        lineage_id=lineage_id,
        redigestion_request_id=request.redigestion_request_id,
        parent_route_ids=request.parent_route_ids,
        revised_route_ids=tuple(revised),
        fidelity_review_ids=tuple(reviews),
        status="VALIDATED",
        provenance=provenance,
    )
