"""Post-P1.5 R2 governed search and explicit selection artifacts."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Any

from .epistemic_route import (
    SCHEMA_VERSION,
    EpistemicRoute,
    RequirementRouteFidelityReview,
    SemanticBoundaryError,
    assert_open_discovery_pure,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class SearchPortfolio:
    portfolio_id: str
    active_routes: tuple[str, ...]
    budget_authorization: int
    budget_used: int
    coverage_obligations: tuple[str, ...]
    uncovered_obligations: tuple[str, ...]
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not re.fullmatch(r"SP-[0-9]{3,6}", self.portfolio_id):
            raise SemanticBoundaryError(f"invalid portfolio_id: {self.portfolio_id!r}")
        if not self.active_routes:
            raise SemanticBoundaryError("SearchPortfolio requires at least one active route")
        if len(set(self.active_routes)) != len(self.active_routes):
            raise SemanticBoundaryError("SearchPortfolio active routes must be unique")
        if self.budget_authorization < 0 or self.budget_used < 0:
            raise SemanticBoundaryError("search budgets cannot be negative")
        if self.budget_used > self.budget_authorization:
            raise SemanticBoundaryError("budget_used exceeds budget_authorization")
        assert_open_discovery_pure(self.to_dict())

    @classmethod
    def admit(
        cls,
        *,
        portfolio_id: str,
        routes_and_reviews: tuple[
            tuple[EpistemicRoute, RequirementRouteFidelityReview], ...
        ],
        budget_authorization: int,
        coverage_obligations: tuple[str, ...],
    ) -> "SearchPortfolio":
        routes: list[str] = []
        for route, review in routes_and_reviews:
            review.require_execution_allowed(route)
            routes.append(route.route_id)
        return cls(
            portfolio_id=portfolio_id,
            active_routes=tuple(routes),
            budget_authorization=budget_authorization,
            budget_used=0,
            coverage_obligations=coverage_obligations,
            uncovered_obligations=coverage_obligations,
        )

    def with_execution(self, *, cost: int, covered_obligations: tuple[str, ...]) -> "SearchPortfolio":
        unknown = set(covered_obligations) - set(self.coverage_obligations)
        if unknown:
            raise SemanticBoundaryError(f"unknown covered obligations: {sorted(unknown)}")
        covered = (set(self.coverage_obligations) - set(self.uncovered_obligations)) | set(covered_obligations)
        return SearchPortfolio(
            portfolio_id=self.portfolio_id,
            active_routes=self.active_routes,
            budget_authorization=self.budget_authorization,
            budget_used=self.budget_used + cost,
            coverage_obligations=self.coverage_obligations,
            uncovered_obligations=tuple(
                obligation
                for obligation in self.coverage_obligations
                if obligation not in covered
            ),
            created_at=self.created_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "portfolio_id": self.portfolio_id,
            "active_routes": list(self.active_routes),
            "budget_authorization": self.budget_authorization,
            "budget_used": self.budget_used,
            "coverage_obligations": list(self.coverage_obligations),
            "uncovered_obligations": list(self.uncovered_obligations),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class RouteSearchOrder:
    search_order_id: str
    route_id: str
    semantic_vocabulary: tuple[str, ...]
    disciplinary_vocabulary: tuple[str, ...]
    mechanism_terms: tuple[str, ...]
    measurement_terms: tuple[str, ...]
    evidence_type_intent: str
    source_classes: tuple[str, ...]
    required_capabilities: tuple[str, ...] = ("search.query",)
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not re.fullmatch(r"SO-R[0-9]{3,6}-[0-9]{1,3}", self.search_order_id):
            raise SemanticBoundaryError(f"invalid route search_order_id: {self.search_order_id!r}")
        if not re.fullmatch(r"ER-[0-9]{3,6}", self.route_id):
            raise SemanticBoundaryError(f"invalid route_id: {self.route_id!r}")
        if not self.semantic_vocabulary:
            raise SemanticBoundaryError("RouteSearchOrder requires semantic vocabulary")
        if not self.evidence_type_intent.strip():
            raise SemanticBoundaryError("evidence_type_intent must not be empty")
        if not self.required_capabilities:
            raise SemanticBoundaryError("required_capabilities must not be empty")
        assert_open_discovery_pure(self.to_dict())

    @classmethod
    def from_route(cls, route: EpistemicRoute, *, order_number: int = 1) -> "RouteSearchOrder":
        source_classes = tuple(route.source_requirement.get("preferred_source_classes", []))
        return cls(
            search_order_id=f"SO-R{route.route_id.split('-')[1]}-{order_number}",
            route_id=route.route_id,
            semantic_vocabulary=route.search_vocabulary,
            disciplinary_vocabulary=route.disciplinary_neighborhood,
            mechanism_terms=tuple(route.source_requirement.get("mechanism_terms", [])),
            measurement_terms=tuple(route.source_requirement.get("measurement_terms", [])),
            evidence_type_intent=route.evidence_need,
            source_classes=source_classes,
        )

    @property
    def compiled_query(self) -> str:
        ordered = (
            self.semantic_vocabulary
            + self.disciplinary_vocabulary
            + self.mechanism_terms
            + self.measurement_terms
        )
        seen: set[str] = set()
        terms: list[str] = []
        for term in ordered:
            normalized = term.strip()
            if normalized and normalized.casefold() not in seen:
                terms.append(normalized)
                seen.add(normalized.casefold())
        return " ".join(terms)

    def to_live_chain_dict(self) -> dict[str, Any]:
        """Return the minimal interface consumed by the preserved LiveChain."""
        return {
            "schema_version": SCHEMA_VERSION,
            "search_order_id": self.search_order_id,
            "route_id": self.route_id,
            "operation_type": "discovery_search",
            "required_capabilities": list(self.required_capabilities),
            "query_representation": {
                "kind": "semantic_route_terms",
                "terms": self.compiled_query.split(),
            },
            "expected_output": "candidate_pointer_set",
        }

    def to_dict(self) -> dict[str, Any]:
        out = self.to_live_chain_dict()
        out.update(
            {
                "semantic_vocabulary": list(self.semantic_vocabulary),
                "disciplinary_vocabulary": list(self.disciplinary_vocabulary),
                "mechanism_terms": list(self.mechanism_terms),
                "measurement_terms": list(self.measurement_terms),
                "evidence_type_intent": self.evidence_type_intent,
                "source_classes": list(self.source_classes),
                "compiled_query": self.compiled_query,
                "created_at": self.created_at,
            }
        )
        assert_open_discovery_pure(out)
        return out


def candidate_pointers_from_discovery(discovery: dict[str, Any]) -> list[dict[str, Any]]:
    pointers: list[dict[str, Any]] = []
    for candidate_set in discovery.get("rung_candidate_sets") or []:
        pointers.extend(candidate_set.get("candidate_pointers") or [])
    return pointers


@dataclass(frozen=True)
class SelectionArtifact:
    selection_id: str
    search_order_id: str
    rendering_path: str
    candidate_pointer_ids: tuple[str, ...]
    selected_candidate_pointer_ids: tuple[str, ...]
    selection_authority: str
    selection_reason: str
    provenance: dict[str, Any]
    timestamp: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not re.fullmatch(r"SEL-[0-9]{3,6}", self.selection_id):
            raise SemanticBoundaryError(f"invalid selection_id: {self.selection_id!r}")
        if not self.selection_authority.strip() or not self.selection_reason.strip():
            raise SemanticBoundaryError("selection requires authority and reason")
        if len(self.selected_candidate_pointer_ids) != 1:
            raise SemanticBoundaryError(
                "Package A resolver depth requires exactly one selected CandidatePointer"
            )
        if not set(self.selected_candidate_pointer_ids).issubset(self.candidate_pointer_ids):
            raise SemanticBoundaryError("selected CandidatePointer is not in the observed set")
        if not self.provenance:
            raise SemanticBoundaryError("selection provenance must not be empty")

    @classmethod
    def from_discovery(
        cls,
        *,
        selection_id: str,
        discovery: dict[str, Any],
        rendering_path: str,
        selected_candidate_pointer_id: str,
        selection_authority: str,
        selection_reason: str,
        provenance: dict[str, Any],
    ) -> "SelectionArtifact":
        if discovery.get("status") != "discovered":
            raise SemanticBoundaryError("cannot select from a non-discovered result")
        rung = next(
            (
                item
                for item in discovery.get("rung_candidate_sets") or []
                if item.get("rendering_path") == rendering_path
            ),
            None,
        )
        if rung is None:
            raise SemanticBoundaryError("selection rendering_path is not in discovery")
        ids = tuple(
            pointer["candidate_pointer_id"]
            for pointer in rung.get("candidate_pointers") or []
        )
        return cls(
            selection_id=selection_id,
            search_order_id=discovery["search_order_id"],
            rendering_path=rendering_path,
            candidate_pointer_ids=ids,
            selected_candidate_pointer_ids=(selected_candidate_pointer_id,),
            selection_authority=selection_authority,
            selection_reason=selection_reason,
            provenance=provenance,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SelectionArtifact":
        return cls(
            selection_id=data["selection_id"],
            search_order_id=data["search_order_id"],
            rendering_path=data["rendering_path"],
            candidate_pointer_ids=tuple(data["candidate_pointer_ids"]),
            selected_candidate_pointer_ids=tuple(data["selected_candidate_pointer_ids"]),
            selection_authority=data["selection_authority"],
            selection_reason=data["selection_reason"],
            provenance=dict(data["provenance"]),
            timestamp=data.get("timestamp", _now_iso()),
        )

    def to_live_chain_selection(self) -> dict[str, str]:
        return {
            "rendering_path": self.rendering_path,
            "candidate_pointer_id": self.selected_candidate_pointer_ids[0],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "selection_id": self.selection_id,
            "search_order_id": self.search_order_id,
            "rendering_path": self.rendering_path,
            "candidate_pointer_ids": list(self.candidate_pointer_ids),
            "selected_candidate_pointer_ids": list(self.selected_candidate_pointer_ids),
            "selection_authority": self.selection_authority,
            "selection_reason": self.selection_reason,
            "timestamp": self.timestamp,
            "provenance": dict(self.provenance),
        }
