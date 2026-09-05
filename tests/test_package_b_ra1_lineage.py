from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from mafs_p0.epistemic_route import SemanticBoundaryError
from mafs_p0.evidence_landscape import EvidenceLandscapePackage
from mafs_p0.package_b_demo import build_negative_demo, build_positive_demo


def _rebuild(demo, *, route_history=None, coverage_summary=None):
    elp = demo["landscape"]
    return EvidenceLandscapePackage.from_research_state(
        package_id="ELP-099",
        state=demo["research_state"],
        route_history=route_history or elp.route_history,
        search_portfolio_history=elp.search_portfolio_history,
        budget_history=elp.budget_history,
        candidate_pointer_lineage=elp.candidate_pointer_lineage,
        selection_lineage=elp.selection_lineage,
        source_document_ids=elp.source_document_ids,
        evidence_span_ids=elp.evidence_span_ids,
        proposition_evidence_ids=elp.proposition_evidence_ids,
        collisions=(demo["collision"],),
        coverage_summary=coverage_summary or elp.coverage_summary,
        provenance_manifest={"test": "ra1"},
    )


def test_post_redigestion_research_state_is_created():
    demo = build_positive_demo()
    assert demo["pre_redigestion_state"].research_state_id == "RS-002"
    assert demo["research_state"].research_state_id == "RS-003"


def test_post_redigestion_state_points_to_pre_redigestion_parent():
    demo = build_positive_demo()
    assert demo["research_state"].parent_research_state_id == "RS-002"


def test_new_route_is_current_and_underexplored_in_post_redigestion_state():
    state = build_positive_demo()["research_state"]
    assert state.active_route_ids == ("ER-101", "ER-102")
    assert state.current_route_status() == {
        "ER-101": "REVISION_CANDIDATE",
        "ER-102": "UNDEREXPLORED",
    }


def test_pre_redigestion_state_remains_unchanged():
    state = build_positive_demo()["pre_redigestion_state"]
    assert state.active_route_ids == ("ER-101",)
    assert "ER-102" not in state.current_route_status()
    with pytest.raises(FrozenInstanceError):
        state.research_state_id = "RS-003"  # type: ignore[misc]


def test_elp_cites_post_redigestion_research_state():
    demo = build_positive_demo()
    assert demo["landscape"].source_research_state_id == "RS-003"


def test_elp_rejects_unknown_current_route():
    demo = build_positive_demo()
    history = demo["landscape"].route_history + (
        {
            "route_id": "ER-999",
            "history_kind": "ORIGINAL",
            "parent_route_ids": [],
            "execution_state": "ACTIVE",
            "origin_requirement_id": "REQ-001",
        },
    )
    with pytest.raises(SemanticBoundaryError, match="absent from source ResearchState"):
        _rebuild(demo, route_history=history)


def test_research_state_current_route_cannot_disappear_from_elp():
    demo = build_positive_demo()
    history = tuple(
        record
        for record in demo["landscape"].route_history
        if record["route_id"] != "ER-102"
    )
    with pytest.raises(SemanticBoundaryError, match="omits active routes"):
        _rebuild(demo, route_history=history)


def test_historical_only_route_is_allowed_with_parent_state_lineage():
    demo = build_positive_demo()
    history = demo["landscape"].route_history + (
        {
            "route_id": "ER-099",
            "history_kind": "ANCESTOR",
            "parent_route_ids": [],
            "execution_state": "EXHAUSTED",
            "origin_requirement_id": "REQ-001",
            "lineage_research_state_id": "RS-002",
        },
    )
    assert _rebuild(demo, route_history=history).route_history[-1]["route_id"] == "ER-099"


def test_historical_only_route_requires_proven_lineage():
    demo = build_positive_demo()
    history = demo["landscape"].route_history + (
        {
            "route_id": "ER-099",
            "history_kind": "ANCESTOR",
            "parent_route_ids": [],
            "execution_state": "EXHAUSTED",
            "origin_requirement_id": "REQ-001",
            "lineage_research_state_id": "RS-777",
        },
    )
    with pytest.raises(SemanticBoundaryError, match="not proven"):
        _rebuild(demo, route_history=history)


def test_coverage_summary_matches_underexplored_route_state():
    demo = build_positive_demo()
    coverage = {**demo["landscape"].coverage_summary, "routes_underexplored": []}
    with pytest.raises(SemanticBoundaryError, match="underexplored coverage"):
        _rebuild(demo, coverage_summary=coverage)
    assert demo["landscape"].coverage_summary["routes_executed"] == ["ER-101"]
    assert demo["landscape"].coverage_summary["routes_underexplored"] == ["ER-102"]


def test_elp_route_execution_state_matches_research_state():
    demo = build_positive_demo()
    history = tuple(dict(record) for record in demo["landscape"].route_history)
    history[1]["execution_state"] = "ACTIVE"
    with pytest.raises(SemanticBoundaryError, match="disagrees with source ResearchState"):
        _rebuild(demo, route_history=history)


def test_negative_unresolved_path_remains_valid():
    demo = build_negative_demo()
    assert demo["collision"].collision_type == "INSUFFICIENT_EVIDENCE"
    assert demo["research_state"].redigestion_required is False
    assert demo["landscape"].coverage_summary["routes_underexplored"] == ["ER-101"]
