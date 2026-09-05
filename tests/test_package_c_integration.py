from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from mafs_p0.cqc_integration import (
    ADAPTER_VERSION,
    AUTHORITY_MAPPING_INVALID,
    COMPATIBLE,
    CQC_UPSTREAM_FREEZE_SHA,
    HASH_MISMATCH,
    HISTORICAL_PRODUCER_MAFS_SHA,
    INCOMPATIBLE,
    INTEGRATION_ACCEPTED,
    INTEGRATION_BLOCKED,
    M5_ACCEPTED_SHA,
    MISSING_REQUIRED_ARTIFACT,
    SCHEMA_INCOMPATIBLE,
    STALE_SOURCE_CHAIN,
    UNSUPPORTED_PRODUCER_BASELINE,
    attach_elp_integration_provenance,
    consume_cqc_artifacts,
    consumer_binding_sha256,
)
from mafs_p0.validator import validate_against_schema


FIXED_TIME = "2026-09-06T00:00:00Z"


def _write_json(path: Path, value: dict) -> str:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_chain(root: Path) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    narrative = "Compare a primary mechanism and an adjacent evidence source under a bounded search budget."
    narrative_sha = hashlib.sha256(narrative.encode("utf-8")).hexdigest()
    cqs = {
        "artifact_id": "CQS-PACKAGE-C-001",
        "schema_version": "0.1",
        "source_narrative_sha256": narrative_sha,
        "source_narrative": narrative,
        "questions": [
            {
                "question_id": "CQ-01",
                "statement": "What evidence establishes the primary mechanism?",
                "source_trace": [{"exact_quote": "primary mechanism"}],
                "question_type": "mechanism",
                "dependencies": [],
                "resolution_condition": "A source-grounded result identifies the operative mechanism.",
                "uncertainty": "The relevant level of mechanism remains open.",
            },
            {
                "question_id": "CQ-02",
                "statement": "Does an adjacent evidence source alter the conclusion?",
                "source_trace": [{"exact_quote": "adjacent evidence source"}],
                "question_type": "boundary",
                "dependencies": ["CQ-01"],
                "resolution_condition": "Independent adjacent evidence supports or narrows the conclusion.",
                "uncertainty": None,
            },
        ],
    }
    cqs_path = root / "source_cqs.json"
    cqs_sha = _write_json(cqs_path, cqs)
    srp = {
        "artifact_id": "SRP-PACKAGE-C-001",
        "schema_version": "0.1",
        "source_cqs_id": cqs["artifact_id"],
        "source_cqs_sha256": cqs_sha,
        "source_narrative_sha256": narrative_sha,
        "source_narrative": narrative,
        "requirements": [
            {
                "requirement_id": "R01",
                "target_question_ids": ["CQ-01", "CQ-02"],
                "evidence_need": "Source-grounded comparative mechanism evidence.",
                "epistemic_routes": [
                    {
                        "route_id": "mechanism_core",
                        "purpose": "Establish the primary mechanism from result evidence.",
                        "status": "REQUIRED",
                        "condition": "Always execute within the authorized envelope.",
                    },
                    {
                        "route_id": "adjacent_check",
                        "purpose": "Test whether adjacent evidence changes the conclusion.",
                        "status": "CONDITIONAL",
                        "condition": "Activate only after an explicit collision or unresolved boundary.",
                    },
                ],
                "source_requirements": ["scholarly source", "citable result span"],
                "stopping_condition": "Stop after the obligation is grounded or remains explicitly unresolved.",
                "uncertainty_binding": "Preserve uncertainty about mechanism level and adjacent transfer.",
            }
        ],
    }
    srp_path = root / "source_srp.json"
    srp_sha = _write_json(srp_path, srp)
    budget = {
        "artifact_id": "BE-PACKAGE-C-001",
        "schema_version": "0.1",
        "source_srp_id": srp["artifact_id"],
        "source_srp_sha256": srp_sha,
        "budget_intent": {"mode": "STANDARD", "operator_goal": "Bounded integration demo"},
        "total_envelope": {
            "wall_clock": {"target_minutes": 10, "hard_ceiling_minutes": 20},
            "model_tokens": {"target_tokens": 4000, "hard_ceiling_tokens": 8000},
        },
        "allocations": [
            {
                "allocation_id": "AL01",
                "requirement_id": "R01",
                "route_id": "mechanism_core",
                "activation": "COMMITTED",
                "wall_clock_target_minutes": 8,
                "model_token_target": 3000,
                "rationale": "Required route receives committed budget.",
            },
            {
                "allocation_id": "AL02",
                "requirement_id": "R01",
                "route_id": "adjacent_check",
                "activation": "RESERVE_CONDITIONAL",
                "wall_clock_target_minutes": 2,
                "model_token_target": 1000,
                "rationale": "Conditional route is held until its condition is met.",
            },
        ],
        "escalation_policy": {
            "triggers": [
                {"trigger": "required route cannot complete", "action": "RETURN_INSUFFICIENT"}
            ]
        },
        "feasibility": {"status": "FEASIBLE", "unfunded_obligations": [], "constraint_note": "No known constraint."},
    }
    budget_path = root / "budget_envelope.json"
    budget_sha = _write_json(budget_path, budget)
    producer_binding = {
        "artifact_id": "BIND-PACKAGE-C-001",
        "schema_version": "0.1",
        "source_chain": {
            "cqs_id": cqs["artifact_id"],
            "cqs_sha256": cqs_sha,
            "srp_id": srp["artifact_id"],
            "srp_sha256": srp_sha,
            "budget_envelope_id": budget["artifact_id"],
            "budget_envelope_sha256": budget_sha,
        },
        "mafs_baseline": {
            "repository": "mo21cn/mafs-v3-p0",
            "commit_sha": HISTORICAL_PRODUCER_MAFS_SHA,
            "interface_state": "MAFS v3.0-P1.5-RA3 closed execution-boundary state",
        },
        "active_routes": [
            {
                "requirement_id": "R01",
                "route_id": "mechanism_core",
                "allocation_id": "AL01",
                "allocation_activation": "COMMITTED",
                "mafs_axis_id": "A1",
                "mafs_search_order_ids": ["SO-A1-1"],
            }
        ],
        "held_conditional_routes": [
            {
                "requirement_id": "R01",
                "route_id": "adjacent_check",
                "allocation_id": "AL02",
                "activation": "RESERVE_CONDITIONAL",
            }
        ],
        "unfunded_required_routes": [],
        "status": "READY_FOR_MAFS_PREFLIGHT",
        "stale_state": "CURRENT",
    }
    binding_path = root / "integration_binding.json"
    _write_json(binding_path, producer_binding)
    return {"cqs": cqs_path, "srp": srp_path, "budget": budget_path, "binding": binding_path}


def _consume(paths: dict[str, Path], **overrides):
    values = {
        "cqs_path": paths["cqs"],
        "srp_path": paths["srp"],
        "budget_path": paths["budget"],
        "integration_binding_path": paths["binding"],
        "source_cqc_freeze_sha": CQC_UPSTREAM_FREEZE_SHA,
        "runtime_mafs_accepted_sha": M5_ACCEPTED_SHA,
        "created_at": FIXED_TIME,
    }
    values.update(overrides)
    return consume_cqc_artifacts(**values)


def _mutate(path: Path, mutate) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    mutate(value)
    _write_json(path, value)


def test_valid_frozen_format_chain_is_accepted(tmp_path: Path):
    result = _consume(_fixture_chain(tmp_path))
    assert result.integration_status == INTEGRATION_ACCEPTED
    assert result.compatibility_status == COMPATIBLE
    assert not result.errors


def test_consumer_binding_is_deterministic_and_schema_valid(tmp_path: Path):
    paths = _fixture_chain(tmp_path)
    first = _consume(paths)
    second = _consume(paths)
    assert first.to_dict() == second.to_dict()
    assert consumer_binding_sha256(first.consumer_binding) == consumer_binding_sha256(second.consumer_binding)
    assert not validate_against_schema(first.consumer_binding, "post_p1p5/cqc_mafs_consumer_binding.schema.json")


def test_cqs_identity_and_wording_are_preserved(tmp_path: Path):
    paths = _fixture_chain(tmp_path)
    source = json.loads(paths["cqs"].read_text(encoding="utf-8"))
    requirement = _consume(paths).mafs_requirements[0]
    assert requirement["target_question_ids"] == ["CQ-01", "CQ-02"]
    assert [item["statement"] for item in requirement["question_bindings"]] == [
        item["statement"] for item in source["questions"]
    ]
    assert all(item["source_admission_status"] is None for item in requirement["question_bindings"])


def test_srp_obligation_identity_is_preserved_and_schema_valid(tmp_path: Path):
    paths = _fixture_chain(tmp_path)
    srp = json.loads(paths["srp"].read_text(encoding="utf-8"))
    requirement = _consume(paths).mafs_requirements[0]
    assert requirement["source_requirement_id"] == "R01"
    assert requirement["evidence_obligation"]["evidence_need"] == srp["requirements"][0]["evidence_need"]
    assert not validate_against_schema(requirement, "post_p1p5/cqc_mafs_requirement.schema.json")


def test_budget_and_conditional_authority_are_preserved(tmp_path: Path):
    result = _consume(_fixture_chain(tmp_path))
    authorizations = {
        item["source_route_id"]: item for item in result.mafs_requirements[0]["route_authorizations"]
    }
    assert authorizations["mechanism_core"]["execution_authorization"] == "ACTIVE_AUTHORIZED"
    assert authorizations["adjacent_check"]["execution_authorization"] == "HELD_CONDITIONAL"
    assert authorizations["adjacent_check"]["budget_activation"] == "RESERVE_CONDITIONAL"


def test_shared_requirement_relationship_is_preserved(tmp_path: Path):
    requirement = _consume(_fixture_chain(tmp_path)).mafs_requirements[0]
    assert requirement["shared_requirement"] is True
    assert requirement["target_question_ids"] == ["CQ-01", "CQ-02"]


def test_historical_and_current_mafs_pins_are_distinct_and_preserved(tmp_path: Path):
    binding = _consume(_fixture_chain(tmp_path)).consumer_binding
    assert binding["producer_mafs_compatibility_baseline"]["commit_sha"] == HISTORICAL_PRODUCER_MAFS_SHA
    assert binding["consumer_mafs_accepted_sha"] == M5_ACCEPTED_SHA
    assert binding["producer_mafs_compatibility_baseline"]["commit_sha"] != binding["consumer_mafs_accepted_sha"]


def test_compatibility_requires_explicit_pass_checks(tmp_path: Path):
    binding = _consume(_fixture_chain(tmp_path)).consumer_binding
    assert binding["compatibility_status"] == COMPATIBLE
    assert {item["status"] for item in binding["compatibility_checks"]} == {"PASS"}
    assert binding["consumer_adapter_version"] == ADAPTER_VERSION


@pytest.mark.parametrize(
    ("target", "mutate", "expected"),
    [
        ("cqs", lambda value: value.__setitem__("source_narrative", value["source_narrative"] + " changed"), HASH_MISMATCH),
        ("srp", lambda value: value.__setitem__("source_cqs_id", "CQS-STALE"), STALE_SOURCE_CHAIN),
        ("budget", lambda value: value.__setitem__("source_srp_id", "SRP-STALE"), STALE_SOURCE_CHAIN),
        ("binding", lambda value: value["source_chain"].__setitem__("srp_sha256", "0" * 64), STALE_SOURCE_CHAIN),
    ],
)
def test_stale_chain_variants_fail_closed(tmp_path: Path, target, mutate, expected):
    paths = _fixture_chain(tmp_path)
    _mutate(paths[target], mutate)
    result = _consume(paths)
    assert result.integration_status == INTEGRATION_BLOCKED
    assert result.compatibility_status == expected
    assert result.consumer_binding is None and not result.mafs_requirements


def test_wrong_cqc_freeze_sha_blocks(tmp_path: Path):
    result = _consume(_fixture_chain(tmp_path), source_cqc_freeze_sha="0" * 40)
    assert result.integration_status == INTEGRATION_BLOCKED
    assert result.compatibility_status == INCOMPATIBLE


def test_wrong_mafs_accepted_sha_blocks(tmp_path: Path):
    result = _consume(_fixture_chain(tmp_path), runtime_mafs_accepted_sha="0" * 40)
    assert result.integration_status == INTEGRATION_BLOCKED
    assert result.compatibility_status == INCOMPATIBLE


def test_schema_incompatibility_blocks_without_guessing(tmp_path: Path):
    paths = _fixture_chain(tmp_path)
    _mutate(paths["srp"], lambda value: value.pop("requirements"))
    result = _consume(paths)
    assert result.integration_status == INTEGRATION_BLOCKED
    assert result.compatibility_status == SCHEMA_INCOMPATIBLE


def test_unknown_producer_baseline_blocks_without_rewriting_history(tmp_path: Path):
    paths = _fixture_chain(tmp_path)
    _mutate(paths["binding"], lambda value: value["mafs_baseline"].__setitem__("commit_sha", "1" * 40))
    result = _consume(paths)
    assert result.compatibility_status == UNSUPPORTED_PRODUCER_BASELINE


def test_invalid_conditional_preactivation_blocks(tmp_path: Path):
    paths = _fixture_chain(tmp_path)
    _mutate(paths["budget"], lambda value: value["allocations"][1].__setitem__("activation", "COMMITTED"))
    result = _consume(paths)
    assert result.compatibility_status == AUTHORITY_MAPPING_INVALID


def test_missing_required_artifact_blocks(tmp_path: Path):
    paths = _fixture_chain(tmp_path)
    paths["binding"].unlink()
    result = _consume(paths)
    assert result.compatibility_status == MISSING_REQUIRED_ARTIFACT


def test_adapter_returns_no_scientific_route_selection_or_resolution(tmp_path: Path):
    payload = _consume(_fixture_chain(tmp_path)).to_dict()

    def all_keys(value):
        if isinstance(value, dict):
            for key, nested in value.items():
                yield key
                yield from all_keys(nested)
        elif isinstance(value, list):
            for nested in value:
                yield from all_keys(nested)

    keys = set(all_keys(payload))
    assert "route_id" not in keys
    assert "selection_artifact" not in keys
    assert "candidate_pointer" not in keys
    assert "resolver_invocation" not in keys
    assert "collision_assessments" not in keys
    assert "research_state" not in keys


def test_elp_provenance_links_back_to_binding_and_frozen_sources(tmp_path: Path):
    binding = _consume(_fixture_chain(tmp_path)).consumer_binding
    elp = {"package_id": "ELP-901", "provenance_manifest": {"existing": "preserved"}}
    integrated = attach_elp_integration_provenance(elp, binding)
    lineage = integrated["provenance_manifest"]["cqc_mafs_integration"]
    assert lineage["consumer_binding_id"] == binding["binding_id"]
    assert lineage["consumer_binding_sha256"] == consumer_binding_sha256(binding)
    assert lineage["source_cqc_freeze_sha"] == CQC_UPSTREAM_FREEZE_SHA
    assert integrated["provenance_manifest"]["existing"] == "preserved"
    assert "cqc_mafs_integration" not in elp["provenance_manifest"]


def test_consumer_binding_links_exact_frozen_artifacts(tmp_path: Path):
    paths = _fixture_chain(tmp_path)
    binding = _consume(paths).consumer_binding
    assert binding["source_cqs_sha256"] == hashlib.sha256(paths["cqs"].read_bytes()).hexdigest()
    assert binding["source_srp_sha256"] == hashlib.sha256(paths["srp"].read_bytes()).hexdigest()
    assert binding["source_budget_sha256"] == hashlib.sha256(paths["budget"].read_bytes()).hexdigest()
    assert binding["source_integration_binding_sha256"] == hashlib.sha256(paths["binding"].read_bytes()).hexdigest()


def test_conflicting_existing_elp_lineage_fails_closed(tmp_path: Path):
    binding = _consume(_fixture_chain(tmp_path)).consumer_binding
    elp = {"provenance_manifest": {"cqc_mafs_integration": {"wrong": "lineage"}}}
    with pytest.raises(Exception, match="conflicting CQC lineage"):
        attach_elp_integration_provenance(elp, binding)
