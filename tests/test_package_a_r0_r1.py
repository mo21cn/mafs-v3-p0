from __future__ import annotations

import json
from pathlib import Path

import pytest

from mafs_p0.epistemic_route import (
    EpistemicRoute,
    RequirementRouteFidelityReview,
    SemanticBoundaryError,
    assert_open_discovery_pure,
)
from mafs_p0.search_portfolio import RouteSearchOrder, SearchPortfolio
from mafs_p0.validator import validate_against_schema


ROOT = Path(__file__).resolve().parent.parent


def make_route(**overrides) -> EpistemicRoute:
    values = {
        "route_id": "ER-001",
        "origin_requirement_id": "SRP-1",
        "semantic_intent": "Find empirical evidence about route-grounded retrieval.",
        "independence_rationale": "Targets evidence behavior rather than a familiar paper identity.",
        "framing_consequence": "May distinguish semantic routing from canonical recall.",
        "search_vocabulary": ("semantic routing", "evidence retrieval"),
        "disciplinary_neighborhood": ("information retrieval",),
        "evidence_need": "empirical result",
        "source_requirement": {
            "preferred_source_classes": ["journal", "conference"],
            "mechanism_terms": ["retrieval route"],
        },
        "search_intent": "discover evidence neighborhoods without target identity",
        "uncertainty": "The vocabulary may be shared across several literatures.",
        "status": "ADMITTED",
    }
    values.update(overrides)
    return EpistemicRoute(**values)


def make_review(status: str = "PRESERVED", **overrides) -> RequirementRouteFidelityReview:
    values = {
        "review_id": "RFR-001",
        "requirement_id": "SRP-1",
        "route_id": "ER-001",
        "status": status,
        "preserved_obligations": ("empirical evidence",),
        "omitted_obligations": (),
        "added_scope": (),
        "rationale": "The route preserves the upstream evidence obligation.",
        "review_authority": "package-a-test-reviewer",
    }
    values.update(overrides)
    return RequirementRouteFidelityReview(**values)


def test_r0_ledgers_are_machine_readable_and_do_not_overclaim():
    package = ROOT / "docs" / "post_p1p5" / "package_a"
    claims = json.loads((package / "A_ARCHITECTURE_CLAIMS.json").read_text(encoding="utf-8"))
    by_id = {item["claim_id"]: item for item in claims["claims"]}
    assert by_id["P1_5_SUBSTRATE"]["architecture_status"] == "EARNED"
    assert by_id["HUB_LESION"]["architecture_status"] == "NOT_EARNED"
    assert by_id["E2"]["disposition"] == "PROHIBITED_IN_PACKAGE_A"
    assert by_id["R3_SEMANTIC_SUFFICIENCY"]["disposition"] == "DEVELOPMENT_TARGET"
    assert by_id["AXIS_SEPARATE_OBJECT"]["architecture_status"] == "DEFERRED"


def test_epistemic_route_and_fidelity_schemas_validate():
    route = make_route()
    review = make_review()
    assert validate_against_schema(route.to_dict(), "post_p1p5/epistemic_route.schema.json") == []
    assert validate_against_schema(
        review.to_dict(), "post_p1p5/requirement_route_fidelity_review.schema.json"
    ) == []


@pytest.mark.parametrize("status", ["CONTRACTED", "DRIFTED", "UNRESOLVED"])
def test_non_preserved_fidelity_blocks_execution(status: str):
    route = make_route()
    review = make_review(
        status,
        omitted_obligations=("empirical evidence",) if status == "CONTRACTED" else (),
    )
    with pytest.raises(SemanticBoundaryError, match="execution blocked"):
        review.require_execution_allowed(route)


def test_fidelity_lineage_mismatch_blocks_execution():
    route = make_route()
    review = make_review(route_id="ER-999")
    with pytest.raises(SemanticBoundaryError, match="lineage"):
        review.require_execution_allowed(route)


@pytest.mark.parametrize(
    "payload",
    [
        {"expected_doi": "hidden"},
        {"nested": {"exact_target_title": "Hidden target"}},
        {"search_vocabulary": ["10.1234/hidden.paper"]},
    ],
)
def test_open_discovery_target_identity_is_rejected_recursively(payload):
    with pytest.raises(SemanticBoundaryError):
        assert_open_discovery_pure(payload)


def test_route_search_order_is_semantic_and_schema_valid():
    order = RouteSearchOrder.from_route(make_route())
    artifact = order.to_dict()
    assert artifact["route_id"] == "ER-001"
    assert artifact["search_order_id"] == "SO-R001-1"
    assert "expected_doi" not in json.dumps(artifact).lower()
    assert "axis_id" not in artifact
    assert validate_against_schema(artifact, "post_p1p5/route_search_order.schema.json") == []


def test_search_portfolio_only_admits_preserved_routes_and_tracks_budget():
    portfolio = SearchPortfolio.admit(
        portfolio_id="SP-001",
        routes_and_reviews=((make_route(), make_review()),),
        budget_authorization=2,
        coverage_obligations=("SRP-1", "SRP-2"),
    )
    updated = portfolio.with_execution(cost=1, covered_obligations=("SRP-1",))
    assert updated.budget_used == 1
    assert updated.uncovered_obligations == ("SRP-2",)
    assert validate_against_schema(updated.to_dict(), "post_p1p5/search_portfolio.schema.json") == []


def test_portfolio_rejects_unpreserved_route():
    with pytest.raises(SemanticBoundaryError, match="execution blocked"):
        SearchPortfolio.admit(
            portfolio_id="SP-001",
            routes_and_reviews=((make_route(), make_review("DRIFTED")),),
            budget_authorization=1,
            coverage_obligations=("SRP-1",),
        )
