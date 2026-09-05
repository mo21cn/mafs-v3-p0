from __future__ import annotations

from pathlib import Path

from mafs_p0.cqc_integration import consume_cqc_artifacts
from mafs_p0.package_c_demo import FIXED_TIME, build_held_demo, build_positive_demo
from mafs_p0.validator import validate_against_schema


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "docs" / "mafs_skill_1_1" / "package_c"


def _paths(demo_name: str) -> dict[str, Path]:
    base = PACKAGE_DIR / demo_name / "input"
    return {
        "cqs": base / "source_cqs.json",
        "srp": base / "source_srp.json",
        "budget": base / "budget_envelope.json",
        "binding": base / "integration_binding.json",
    }


def test_positive_demo_closes_cqc_to_proposition_evidence_and_elp():
    demo = build_positive_demo(_paths("C_HERMETIC_POSITIVE_DEMO"))
    binding = demo["consumer_binding"]
    requirement = demo["mafs_requirement"]
    route = demo["route"]
    evidence = demo["proposition_evidence"]
    elp = demo["evidence_landscape_package"]

    assert demo["consumer_result"]["integration_status"] == "INTEGRATION_ACCEPTED"
    assert route["origin_requirement_id"] == requirement["consumer_requirement_id"]
    assert demo["discovery"]["execution_boundary"] == "STOP_AWAITING_SELECTION_ARTIFACT"
    assert demo["selection"]["selected_candidate_pointer_ids"] == ["CP-PACKAGE-C-001"]
    assert demo["source_document"]["source_representation_type"] == "FULL_TEXT"
    assert demo["evidence_span"]["evidence_role"] == "STATISTICAL_RESULT"
    assert evidence["grounding_status"] == "CITABLE_SPAN"
    assert evidence["provenance"]["model_prior_used_as_evidence"] is False
    integration = elp["provenance_manifest"]["cqc_mafs_integration"]
    assert integration["consumer_binding_id"] == binding["binding_id"]
    assert integration["source_cqs_ids"] == [binding["source_cqs_id"]]
    assert integration["source_srp_ids"] == [binding["source_srp_id"]]
    assert integration["source_budget_ids"] == [binding["source_budget_id"]]
    assert integration["source_integration_binding_sha256"] == binding[
        "source_integration_binding_sha256"
    ]


def test_positive_demo_package_c_schemas_validate():
    demo = build_positive_demo(_paths("C_HERMETIC_POSITIVE_DEMO"))
    assert validate_against_schema(
        demo["consumer_binding"],
        "post_p1p5/cqc_mafs_consumer_binding.schema.json",
    ) == []
    assert validate_against_schema(
        demo["mafs_requirement"],
        "post_p1p5/cqc_mafs_requirement.schema.json",
    ) == []
    assert validate_against_schema(
        demo["evidence_landscape_package"],
        "post_p1p5/evidence_landscape_package.schema.json",
    ) == []


def test_negative_stale_demo_blocks_without_partial_downstream_artifacts():
    paths = _paths("C_HERMETIC_NEGATIVE_DEMO")
    result = consume_cqc_artifacts(
        cqs_path=paths["cqs"],
        srp_path=paths["srp"],
        budget_path=paths["budget"],
        integration_binding_path=paths["binding"],
        source_cqc_freeze_sha="c5c00a19f9812058050ba16ad61b717a1c1f1ca2",
        runtime_mafs_accepted_sha="ecfa39e9fdeced45848c643544477e408e872d60",
        created_at=FIXED_TIME,
    )
    assert result.integration_status == "INTEGRATION_BLOCKED"
    assert result.compatibility_status == "STALE_SOURCE_CHAIN"
    assert result.consumer_binding is None
    assert result.mafs_requirements == ()


def test_held_conditional_demo_does_not_preactivate_routes():
    demo = build_held_demo(_paths("C_HELD_CONDITIONAL_DEMO"))
    assert demo["status"] == "HELD_CONDITIONAL_NOT_ACTIVATED"
    assert demo["held_requirements"]
    assert demo["activated_route_ids"] == []
    assert demo["search_orders"] == []
    assert all(
        any(
            route["execution_authorization"] == "HELD_CONDITIONAL"
            for route in requirement["route_authorizations"]
        )
        for requirement in demo["held_requirements"]
    )
