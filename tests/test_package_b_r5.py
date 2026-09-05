from __future__ import annotations

import json

import pytest

from mafs_p0.epistemic_route import SemanticBoundaryError
from mafs_p0.evidence_landscape import AUTHORITY_BOUNDARY, EvidenceLandscapePackage
from mafs_p0.package_b_demo import build_negative_demo, build_positive_demo
from mafs_p0.validator import validate_against_schema


def test_elp_schema_state_collision_and_unresolved_linkage():
    demo = build_positive_demo()
    elp = demo["landscape"]
    state = demo["research_state"]
    assert elp.source_research_state_id == state.research_state_id
    assert elp.collision_ids == state.collision_ids
    assert elp.proposition_evidence_ids == state.proposition_evidence_ids
    assert elp.unresolved_obligations == tuple(
        item.to_dict() for item in state.unresolved_obligations
    )
    assert not validate_against_schema(
        elp.to_dict(), "post_p1p5/evidence_landscape_package.schema.json"
    )


def test_elp_route_history_preserves_original_and_redigested_lineage():
    history = build_positive_demo()["landscape"].route_history
    assert [item["history_kind"] for item in history] == ["ORIGINAL", "REDIGESTED"]
    assert history[1]["parent_route_ids"] == ["ER-101"]
    assert history[1]["redigestion_request_id"] == "RDR-001"


def test_elp_preserves_typed_evidence_authority_layers():
    elp = build_positive_demo()["landscape"]
    assert elp.candidate_pointer_lineage[0]["artifact_type"] == "CandidatePointer"
    assert all(item.startswith("SD-") for item in elp.source_document_ids)
    assert all(item.startswith("ES-") for item in elp.evidence_span_ids)
    assert all(item.startswith("PE-") for item in elp.proposition_evidence_ids)
    assert elp.provenance_manifest["typed_evidence_layers_preserved"] == [
        "CandidatePointer", "SourceDocument", "EvidenceSpan", "PropositionEvidence"
    ]


def test_elp_coverage_is_complete_and_does_not_claim_comprehensiveness():
    positive = build_positive_demo()["landscape"]
    negative = build_negative_demo()["landscape"]
    assert positive.coverage_summary["propositions_grounded"] == 2
    assert negative.coverage_summary["propositions_unresolved"] == 1
    assert negative.coverage_summary["requirements_partially_covered"] == ["REQ-001"]
    assert negative.coverage_summary["routes_underexplored"] == ["ER-101"]


def test_elp_requires_provenance_and_exact_state_references():
    demo = build_positive_demo()
    common = dict(
        package_id="ELP-099",
        state=demo["research_state"],
        route_history=demo["landscape"].route_history,
        search_portfolio_history=demo["landscape"].search_portfolio_history,
        budget_history=demo["landscape"].budget_history,
        candidate_pointer_lineage=demo["landscape"].candidate_pointer_lineage,
        selection_lineage=demo["landscape"].selection_lineage,
        source_document_ids=demo["landscape"].source_document_ids,
        evidence_span_ids=demo["landscape"].evidence_span_ids,
        collisions=(demo["collision"],),
        coverage_summary=demo["landscape"].coverage_summary,
        provenance_manifest={"test": True},
    )
    with pytest.raises(SemanticBoundaryError, match="proposition references"):
        EvidenceLandscapePackage.from_research_state(
            **common, proposition_evidence_ids=("PE-ffffffffffff",)
        )
    with pytest.raises(SemanticBoundaryError, match="provenance"):
        EvidenceLandscapePackage.from_research_state(
            **{**common, "provenance_manifest": {}},
            proposition_evidence_ids=demo["research_state"].proposition_evidence_ids,
        )


def test_elp_authority_boundary_is_hard():
    demo = build_positive_demo()
    elp = demo["landscape"]
    assert elp.authority_boundary == AUTHORITY_BOUNDARY
    data = elp.to_dict()
    data["authority_boundary"] = "OPPORTUNITY_RANKING"
    with pytest.raises(SemanticBoundaryError, match="downstream decision"):
        EvidenceLandscapePackage(
            **{
                key: tuple(value) if key in {
                    "requirement_ids", "route_history", "search_portfolio_history",
                    "budget_history", "candidate_pointer_lineage", "selection_lineage",
                    "source_document_ids", "evidence_span_ids", "proposition_evidence_ids",
                    "collision_ids", "supported_scoped_claims", "contested_scoped_claims",
                    "unresolved_obligations", "new_evidence_obligations",
                } else value
                for key, value in data.items() if key != "schema_version"
            }
        )


def test_elp_canonical_serialization_is_deterministic():
    elp = build_positive_demo()["landscape"]
    first = elp.to_canonical_json()
    second = elp.to_canonical_json()
    assert first == second
    assert json.loads(first) == elp.to_dict()

