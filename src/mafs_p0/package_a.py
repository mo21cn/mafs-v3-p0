"""Thin R0-R3 orchestration around the preserved P1.5 execution spine."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .epistemic_route import (
    EpistemicRoute,
    RequirementRouteFidelityReview,
    SemanticBoundaryError,
)
from .live_chain import LiveChain
from .search_portfolio import RouteSearchOrder, SearchPortfolio, SelectionArtifact


@dataclass(frozen=True)
class PreparedRouteExecution:
    route: EpistemicRoute
    fidelity_review: RequirementRouteFidelityReview
    portfolio: SearchPortfolio
    search_order: RouteSearchOrder

    def __post_init__(self) -> None:
        self.fidelity_review.require_execution_allowed(self.route)
        if self.route.route_id not in self.portfolio.active_routes:
            raise SemanticBoundaryError("route is not active in SearchPortfolio")
        if self.search_order.route_id != self.route.route_id:
            raise SemanticBoundaryError("SearchOrder lineage does not match route")

    @classmethod
    def prepare(
        cls,
        *,
        route: EpistemicRoute,
        fidelity_review: RequirementRouteFidelityReview,
        portfolio: SearchPortfolio,
        order_number: int = 1,
    ) -> "PreparedRouteExecution":
        return cls(
            route=route,
            fidelity_review=fidelity_review,
            portfolio=portfolio,
            search_order=RouteSearchOrder.from_route(route, order_number=order_number),
        )

    def new_live_chain(self, *, top_k: int = 5) -> LiveChain:
        return LiveChain(
            search_order=self.search_order.to_live_chain_dict(),
            compiled_query=self.search_order.compiled_query,
            top_k=top_k,
        )

    def discover(self, *, top_k: int = 5) -> tuple[LiveChain, dict[str, Any]]:
        """Execute discovery only and return at the mandatory STOP boundary."""
        chain = self.new_live_chain(top_k=top_k)
        result = chain.discover()
        if result.get("status") == "discovered":
            result["execution_boundary"] = "STOP_AWAITING_SELECTION_ARTIFACT"
            result["route_id"] = self.route.route_id
            result["portfolio_id"] = self.portfolio.portfolio_id
        return chain, result

    def resolve_selected(
        self,
        *,
        chain: LiveChain,
        discovery: dict[str, Any],
        selection: SelectionArtifact,
    ) -> dict[str, Any]:
        if selection.search_order_id != self.search_order.search_order_id:
            raise SemanticBoundaryError("SelectionArtifact search-order lineage mismatch")
        result = chain.resolve(discovery, selection.to_live_chain_selection())
        result["selection_artifact"] = selection.to_dict()
        result["selection_lineage_status"] = (
            "PASS"
            if result.get("selected_candidate_pointer_id")
            == selection.selected_candidate_pointer_ids[0]
            == (result.get("resolver_invocation") or {}).get("candidate_pointer_id")
            else "FAIL"
        )
        return result
