from __future__ import annotations

import json
from pathlib import Path

from mafs_p0.validator import validate_against_schema


DEMO = Path("docs/post_p1p5/package_b/B_VERTICAL_SLICE_DEMO")


def read(flow: str, name: str) -> dict:
    return json.loads((DEMO / flow / f"{name}.json").read_text(encoding="utf-8"))


def test_tracked_package_b_demo_artifacts_are_schema_valid():
    for flow in ("positive", "negative"):
        assert not validate_against_schema(
            read(flow, "collision"), "post_p1p5/collision_assessment.schema.json"
        )
        assert not validate_against_schema(
            read(flow, "research_state"), "post_p1p5/research_state.schema.json"
        )
        assert not validate_against_schema(
            read(flow, "landscape"),
            "post_p1p5/evidence_landscape_package.schema.json",
        )


def test_tracked_demo_preserves_m5_and_production_stop_boundary():
    summary = json.loads((DEMO / "demo_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["m5_accepted"] is False
    assert summary["production_migration_authorized"] is False
    assert read("positive", "collision")["collision_type"] == "DIRECT_CONTRADICTION"
    assert read("negative", "collision")["collision_type"] == "INSUFFICIENT_EVIDENCE"


def test_tracked_positive_demo_closes_post_redigestion_state_lineage():
    pre_state = read("positive", "pre_redigestion_state")
    state = read("positive", "research_state")
    landscape = read("positive", "landscape")
    assert pre_state["research_state_id"] == "RS-002"
    assert state["research_state_id"] == "RS-003"
    assert state["parent_research_state_id"] == "RS-002"
    assert state["active_route_ids"] == ["ER-101", "ER-102"]
    assert state["route_status"][-1]["status"] == "UNDEREXPLORED"
    assert landscape["source_research_state_id"] == "RS-003"
    assert landscape["coverage_summary"]["routes_executed"] == ["ER-101"]
    assert landscape["coverage_summary"]["routes_underexplored"] == ["ER-102"]
