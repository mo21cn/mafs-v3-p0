from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from mafs_p0.validator import validate_against_schema


DEMO = Path("docs/post_p1p5/package_a/A_VERTICAL_SLICE_DEMO")


def _load(name: str):
    return json.loads((DEMO / name).read_text(encoding="utf-8"))


def test_live_demo_preserves_stop_then_explicit_selection_lineage():
    stop = _load("06_stop_boundary.json")
    discovery = _load("05_discovery.json")
    selection = _load("07_selection_artifact.json")
    resolution = _load("08_resolution.json")
    assert stop["status"] == "STOP_AWAITING_SELECTION_ARTIFACT"
    assert stop["resolver_invoked"] is False
    assert selection["provenance"]["discovery_sha256"] == stop["discovery_sha256"]
    selected = selection["selected_candidate_pointer_ids"][0]
    assert selected == resolution["selected_candidate_pointer_id"]
    assert selected == resolution["resolver_invocation"]["candidate_pointer_id"]
    assert resolution["selection_lineage_status"] == "PASS"
    assert validate_against_schema(selection, "post_p1p5/selection_artifact.schema.json") == []
    assert discovery["execution_boundary"] == "STOP_AWAITING_SELECTION_ARTIFACT"


def test_live_demo_retrieval_and_resolution_snapshots_are_real_and_hash_bound():
    resolution = _load("08_resolution.json")
    for invocation, snapshot in zip(
        resolution["retrieval_invocations"], resolution["retrieval_snapshots"]
    ):
        body = base64.b64decode(snapshot["bytes"])
        assert hashlib.sha256(body).hexdigest() == invocation["raw_snapshot_sha256"]
    resolver_body = base64.b64decode(resolution["resolver_snapshot"]["bytes"])
    assert hashlib.sha256(resolver_body).hexdigest() == resolution["resolver_invocation"][
        "raw_snapshot_sha256"
    ]


def test_live_demo_source_span_and_negative_state_are_honest():
    source_document = _load("10_source_document.json")
    spans = _load("11_evidence_spans.json")
    evidence = _load("12_proposition_evidence.json")
    content = (DEMO / "10_source_content.txt").read_text(encoding="utf-8")
    assert source_document["source_integrity_status"] == "VERIFIED_IDENTITY_MATCH"
    assert len(spans) == 1 and spans[0]["text"] in content
    assert validate_against_schema(source_document, "post_p1p5/source_document.schema.json") == []
    assert validate_against_schema(spans[0], "post_p1p5/evidence_span.schema.json") == []
    by_id = {item["proposition_id"]: item for item in evidence}
    assert by_id["PROP-DEMO-001"]["grounding_status"] == "CITABLE_SPAN"
    assert by_id["PROP-DEMO-001"]["relation"] == "SUPPORTS"
    assert by_id["PROP-DEMO-002"]["grounding_status"] == "NOT_ADDRESSED"
    assert by_id["PROP-DEMO-002"]["relation"] == "NOT_GROUNDED"
    for item in evidence:
        assert validate_against_schema(item, "post_p1p5/proposition_evidence.schema.json") == []


def test_live_demo_stops_before_r4():
    summary = _load("14_demo_summary.json")
    assert summary["status"] == "PACKAGE_A_VERTICAL_SLICE_COMPLETE"
    assert summary["negative_or_uncertain_count"] >= 1
    assert summary["r4_entered"] is False
    assert summary["next_gate"] == "M3"
