"""Package C deterministic CQC -> MAFS consumer integration.

This module validates and translates protocol structure only.  It does not
invent scientific routes, search, select candidates, resolve evidence, assess
collisions, or mutate ResearchState.  CQC remains the authority for admitted
questions, evidence obligations, and resource authorization; MAFS cognition
starts only after the returned mechanical requirement wrappers.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from .util.hashing import sha256_file, sha256_json


ADAPTER_VERSION = "mafs-skill-1.1-package-c.v1"
CONSUMER_BINDING_SCHEMA_VERSION = "mafs-skill-1.1-cqc-mafs-consumer-binding.v1"
CONSUMER_REQUIREMENT_SCHEMA_VERSION = "mafs-skill-1.1-cqc-requirement.v1"

CQC_UPSTREAM_FREEZE_SHA = "c5c00a19f9812058050ba16ad61b717a1c1f1ca2"
M5_ACCEPTED_SHA = "ecfa39e9fdeced45848c643544477e408e872d60"
HISTORICAL_PRODUCER_MAFS_SHA = "cd09699fc8cc160ab5cfff00a41e714961dd2109"
MAFS_REPOSITORY = "mo21cn/mafs-v3-p0"

COMPATIBLE = "COMPATIBLE"
INCOMPATIBLE = "INCOMPATIBLE"
STALE_SOURCE_CHAIN = "STALE_SOURCE_CHAIN"
UNSUPPORTED_PRODUCER_BASELINE = "UNSUPPORTED_PRODUCER_BASELINE"
MISSING_REQUIRED_ARTIFACT = "MISSING_REQUIRED_ARTIFACT"
HASH_MISMATCH = "HASH_MISMATCH"
SCHEMA_INCOMPATIBLE = "SCHEMA_INCOMPATIBLE"
AUTHORITY_MAPPING_INVALID = "AUTHORITY_MAPPING_INVALID"

INTEGRATION_ACCEPTED = "INTEGRATION_ACCEPTED"
INTEGRATION_BLOCKED = "INTEGRATION_BLOCKED"

_EXPECTED_SCHEMA_VERSION = "0.1"
_READY_PRODUCER_STATES = {
    "READY_FOR_MAFS_PLANNING",
    "READY_FOR_MAFS_PREFLIGHT",
}


class PackageCIntegrationError(ValueError):
    """Internal fail-closed error with a stable compatibility state."""

    def __init__(self, compatibility_status: str, detail: str):
        self.compatibility_status = compatibility_status
        self.detail = detail
        super().__init__(f"{compatibility_status}: {detail}")


@dataclass(frozen=True)
class CQCMAFSConsumerResult:
    integration_status: str
    compatibility_status: str
    consumer_binding: dict[str, Any] | None
    mafs_requirements: tuple[dict[str, Any], ...]
    errors: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        return self.integration_status == INTEGRATION_ACCEPTED

    def to_dict(self) -> dict[str, Any]:
        return {
            "integration_status": self.integration_status,
            "compatibility_status": self.compatibility_status,
            "consumer_binding": self.consumer_binding,
            "mafs_requirements": list(self.mafs_requirements),
            "errors": list(self.errors),
        }


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise PackageCIntegrationError(
            MISSING_REQUIRED_ARTIFACT, f"{label} is missing: {path}"
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageCIntegrationError(
            SCHEMA_INCOMPATIBLE, f"{label} is not readable JSON: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise PackageCIntegrationError(
            SCHEMA_INCOMPATIBLE, f"{label} must be a JSON object"
        )
    return value


def _require_keys(value: Mapping[str, Any], keys: set[str], label: str) -> None:
    missing = keys - set(value)
    if missing:
        raise PackageCIntegrationError(
            SCHEMA_INCOMPATIBLE, f"{label} missing required fields: {sorted(missing)}"
        )


def _require_schema(value: Mapping[str, Any], label: str) -> None:
    if value.get("schema_version") != _EXPECTED_SCHEMA_VERSION:
        raise PackageCIntegrationError(
            SCHEMA_INCOMPATIBLE,
            f"{label}.schema_version must be {_EXPECTED_SCHEMA_VERSION!r}",
        )


def _validate_cqs(cqs: dict[str, Any]) -> None:
    _require_keys(
        cqs,
        {
            "artifact_id",
            "schema_version",
            "source_narrative_sha256",
            "source_narrative",
            "questions",
        },
        "CQS",
    )
    _require_schema(cqs, "CQS")
    narrative = cqs.get("source_narrative")
    questions = cqs.get("questions")
    if not isinstance(narrative, str) or not narrative or not isinstance(questions, list) or not questions:
        raise PackageCIntegrationError(
            SCHEMA_INCOMPATIBLE, "CQS requires source_narrative and non-empty questions"
        )
    import hashlib

    observed_narrative_sha = hashlib.sha256(narrative.encode("utf-8")).hexdigest()
    if observed_narrative_sha != cqs.get("source_narrative_sha256"):
        raise PackageCIntegrationError(HASH_MISMATCH, "CQS source narrative hash mismatch")
    seen: set[str] = set()
    for index, question in enumerate(questions):
        if not isinstance(question, dict):
            raise PackageCIntegrationError(SCHEMA_INCOMPATIBLE, f"CQS question {index} is not an object")
        _require_keys(
            question,
            {
                "question_id",
                "statement",
                "source_trace",
                "question_type",
                "dependencies",
                "resolution_condition",
                "uncertainty",
            },
            f"CQS.questions[{index}]",
        )
        question_id = question["question_id"]
        if not isinstance(question_id, str) or question_id in seen:
            raise PackageCIntegrationError(SCHEMA_INCOMPATIBLE, "CQS question ids must be unique strings")
        seen.add(question_id)
        if not isinstance(question["statement"], str) or not question["statement"]:
            raise PackageCIntegrationError(SCHEMA_INCOMPATIBLE, f"{question_id} has empty wording")
        for trace in question["source_trace"]:
            quote = trace.get("exact_quote") if isinstance(trace, dict) else None
            if not isinstance(quote, str) or quote not in narrative:
                raise PackageCIntegrationError(HASH_MISMATCH, f"{question_id} source trace is not verbatim")
        dependencies = question["dependencies"]
        if not isinstance(dependencies, list):
            raise PackageCIntegrationError(SCHEMA_INCOMPATIBLE, f"{question_id} dependencies must be an array")
    unknown_dependencies = {
        dependency
        for question in questions
        for dependency in question["dependencies"]
        if dependency not in seen
    }
    if unknown_dependencies:
        raise PackageCIntegrationError(
            SCHEMA_INCOMPATIBLE, f"CQS has unknown dependencies: {sorted(unknown_dependencies)}"
        )


def _validate_srp(srp: dict[str, Any], cqs: dict[str, Any], cqs_sha: str) -> None:
    _require_keys(
        srp,
        {
            "artifact_id",
            "schema_version",
            "source_cqs_id",
            "source_cqs_sha256",
            "source_narrative_sha256",
            "source_narrative",
            "requirements",
        },
        "SRP",
    )
    _require_schema(srp, "SRP")
    if srp["source_cqs_id"] != cqs["artifact_id"] or srp["source_cqs_sha256"] != cqs_sha:
        raise PackageCIntegrationError(STALE_SOURCE_CHAIN, "SRP does not derive from the supplied CQS")
    if (
        srp["source_narrative_sha256"] != cqs["source_narrative_sha256"]
        or srp["source_narrative"] != cqs["source_narrative"]
    ):
        raise PackageCIntegrationError(STALE_SOURCE_CHAIN, "SRP narrative lineage differs from CQS")
    questions = {item["question_id"] for item in cqs["questions"]}
    requirements = srp.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        raise PackageCIntegrationError(SCHEMA_INCOMPATIBLE, "SRP requirements must be non-empty")
    seen_requirements: set[str] = set()
    seen_routes: set[tuple[str, str]] = set()
    for index, requirement in enumerate(requirements):
        if not isinstance(requirement, dict):
            raise PackageCIntegrationError(SCHEMA_INCOMPATIBLE, f"SRP requirement {index} is not an object")
        _require_keys(
            requirement,
            {
                "requirement_id",
                "target_question_ids",
                "evidence_need",
                "epistemic_routes",
                "source_requirements",
                "stopping_condition",
                "uncertainty_binding",
            },
            f"SRP.requirements[{index}]",
        )
        requirement_id = requirement["requirement_id"]
        if requirement_id in seen_requirements:
            raise PackageCIntegrationError(SCHEMA_INCOMPATIBLE, f"duplicate requirement {requirement_id}")
        seen_requirements.add(requirement_id)
        target_ids = requirement["target_question_ids"]
        if not isinstance(target_ids, list) or not target_ids or not set(target_ids) <= questions:
            raise PackageCIntegrationError(
                SCHEMA_INCOMPATIBLE, f"{requirement_id} has unknown/empty target questions"
            )
        routes = requirement["epistemic_routes"]
        if not isinstance(routes, list) or not routes:
            raise PackageCIntegrationError(SCHEMA_INCOMPATIBLE, f"{requirement_id} has no routes")
        for route in routes:
            if not isinstance(route, dict):
                raise PackageCIntegrationError(SCHEMA_INCOMPATIBLE, f"{requirement_id} route is not an object")
            _require_keys(route, {"route_id", "purpose", "status", "condition"}, "SRP route")
            key = (requirement_id, route["route_id"])
            if key in seen_routes or route["status"] not in {"REQUIRED", "CONDITIONAL"}:
                raise PackageCIntegrationError(SCHEMA_INCOMPATIBLE, f"invalid/duplicate SRP route {key}")
            seen_routes.add(key)


def _validate_budget(budget: dict[str, Any], srp: dict[str, Any], srp_sha: str) -> None:
    _require_keys(
        budget,
        {
            "artifact_id",
            "schema_version",
            "source_srp_id",
            "source_srp_sha256",
            "budget_intent",
            "total_envelope",
            "allocations",
            "escalation_policy",
            "feasibility",
        },
        "BudgetEnvelope",
    )
    _require_schema(budget, "BudgetEnvelope")
    if budget["source_srp_id"] != srp["artifact_id"] or budget["source_srp_sha256"] != srp_sha:
        raise PackageCIntegrationError(
            STALE_SOURCE_CHAIN, "BudgetEnvelope does not derive from the supplied SRP"
        )
    if not isinstance(budget.get("allocations"), list):
        raise PackageCIntegrationError(SCHEMA_INCOMPATIBLE, "BudgetEnvelope.allocations must be an array")
    if not isinstance(budget.get("feasibility"), dict):
        raise PackageCIntegrationError(SCHEMA_INCOMPATIBLE, "BudgetEnvelope.feasibility must be an object")


def _route_authority(
    srp: dict[str, Any], budget: dict[str, Any]
) -> tuple[dict[tuple[str, str], dict[str, Any]], list[dict[str, Any]]]:
    allocation_by_route: dict[tuple[str, str], dict[str, Any]] = {}
    for allocation in budget["allocations"]:
        if not isinstance(allocation, dict):
            raise PackageCIntegrationError(SCHEMA_INCOMPATIBLE, "allocation is not an object")
        _require_keys(
            allocation,
            {
                "allocation_id",
                "requirement_id",
                "route_id",
                "activation",
                "wall_clock_target_minutes",
                "model_token_target",
                "rationale",
            },
            "BudgetEnvelope allocation",
        )
        key = (allocation["requirement_id"], allocation["route_id"])
        if key in allocation_by_route:
            raise PackageCIntegrationError(AUTHORITY_MAPPING_INVALID, f"duplicate allocation for {key}")
        allocation_by_route[key] = allocation

    unfunded = budget["feasibility"].get("unfunded_obligations") or []
    unfunded_by_route = {
        (item["requirement_id"], item["route_id"]): item for item in unfunded
    }
    mapped: dict[tuple[str, str], dict[str, Any]] = {}
    for requirement in srp["requirements"]:
        requirement_id = requirement["requirement_id"]
        for route in requirement["epistemic_routes"]:
            key = (requirement_id, route["route_id"])
            allocation = allocation_by_route.get(key)
            unfunded_item = unfunded_by_route.get(key)
            if allocation is not None and unfunded_item is not None:
                raise PackageCIntegrationError(
                    AUTHORITY_MAPPING_INVALID, f"route {key} is both allocated and unfunded"
                )
            if allocation is None:
                if unfunded_item is None:
                    raise PackageCIntegrationError(
                        AUTHORITY_MAPPING_INVALID, f"route {key} lacks allocation/unfunded authority"
                    )
                execution_status = "UNFUNDED"
            elif allocation["activation"] == "COMMITTED" and route["status"] == "REQUIRED":
                execution_status = "ACTIVE_AUTHORIZED"
            elif allocation["activation"] == "RESERVE_CONDITIONAL" and route["status"] == "CONDITIONAL":
                execution_status = "HELD_CONDITIONAL"
            else:
                raise PackageCIntegrationError(
                    AUTHORITY_MAPPING_INVALID,
                    f"route {key} has invalid SRP/budget activation pair",
                )
            mapped[key] = {
                "source_route_id": route["route_id"],
                "purpose": route["purpose"],
                "srp_status": route["status"],
                "activation_condition": route["condition"],
                "allocation_id": allocation["allocation_id"] if allocation else None,
                "budget_activation": allocation["activation"] if allocation else None,
                "wall_clock_target_minutes": allocation["wall_clock_target_minutes"] if allocation else None,
                "model_token_target": allocation["model_token_target"] if allocation else None,
                "execution_authorization": execution_status,
                "unfunded_reason": unfunded_item["reason"] if unfunded_item else None,
            }
    if set(allocation_by_route) - set(mapped):
        raise PackageCIntegrationError(
            AUTHORITY_MAPPING_INVALID,
            f"budget allocations reference unknown SRP routes: {sorted(set(allocation_by_route) - set(mapped))}",
        )
    return mapped, list(unfunded)


def _validate_producer_binding(
    binding: dict[str, Any],
    *,
    cqs: dict[str, Any],
    srp: dict[str, Any],
    budget: dict[str, Any],
    cqs_sha: str,
    srp_sha: str,
    budget_sha: str,
    route_authority: Mapping[tuple[str, str], dict[str, Any]],
) -> None:
    _require_keys(
        binding,
        {
            "artifact_id",
            "schema_version",
            "source_chain",
            "mafs_baseline",
            "active_routes",
            "held_conditional_routes",
            "unfunded_required_routes",
            "status",
            "stale_state",
        },
        "CQCMAFSIntegrationBinding",
    )
    _require_schema(binding, "CQCMAFSIntegrationBinding")
    chain = binding["source_chain"]
    expected_chain = {
        "cqs_id": cqs["artifact_id"],
        "cqs_sha256": cqs_sha,
        "srp_id": srp["artifact_id"],
        "srp_sha256": srp_sha,
        "budget_envelope_id": budget["artifact_id"],
        "budget_envelope_sha256": budget_sha,
    }
    if chain != expected_chain:
        raise PackageCIntegrationError(STALE_SOURCE_CHAIN, "producer binding source chain is stale")
    if binding["stale_state"] != "CURRENT":
        raise PackageCIntegrationError(STALE_SOURCE_CHAIN, "producer binding declares stale state")
    baseline = binding.get("mafs_baseline") or {}
    if baseline.get("repository") != MAFS_REPOSITORY or baseline.get("commit_sha") != HISTORICAL_PRODUCER_MAFS_SHA:
        raise PackageCIntegrationError(
            UNSUPPORTED_PRODUCER_BASELINE, "producer MAFS compatibility baseline is unsupported"
        )

    expected_active = {
        key: value
        for key, value in route_authority.items()
        if value["execution_authorization"] == "ACTIVE_AUTHORIZED"
    }
    expected_held = {
        key: value
        for key, value in route_authority.items()
        if value["execution_authorization"] == "HELD_CONDITIONAL"
    }
    observed_active = {
        (item.get("requirement_id"), item.get("route_id")): item
        for item in binding["active_routes"]
    }
    observed_held = {
        (item.get("requirement_id"), item.get("route_id")): item
        for item in binding["held_conditional_routes"]
    }
    if set(observed_active) != set(expected_active) or set(observed_held) != set(expected_held):
        raise PackageCIntegrationError(
            AUTHORITY_MAPPING_INVALID, "producer binding route classification differs from SRP/Budget"
        )
    for key, item in observed_active.items():
        if (
            item.get("allocation_id") != expected_active[key]["allocation_id"]
            or item.get("allocation_activation") != "COMMITTED"
        ):
            raise PackageCIntegrationError(AUTHORITY_MAPPING_INVALID, f"active route authority mismatch: {key}")
    for key, item in observed_held.items():
        if (
            item.get("allocation_id") != expected_held[key]["allocation_id"]
            or item.get("activation") != "RESERVE_CONDITIONAL"
        ):
            raise PackageCIntegrationError(AUTHORITY_MAPPING_INVALID, f"held route authority mismatch: {key}")
    if binding["status"] not in _READY_PRODUCER_STATES:
        raise PackageCIntegrationError(
            AUTHORITY_MAPPING_INVALID,
            f"producer binding does not authorize MAFS preflight: {binding['status']}",
        )


def _consumer_requirements(
    *,
    cqs: dict[str, Any],
    srp: dict[str, Any],
    budget: dict[str, Any],
    cqs_sha: str,
    srp_sha: str,
    budget_sha: str,
    producer_binding: dict[str, Any],
    producer_binding_sha: str,
    route_authority: Mapping[tuple[str, str], dict[str, Any]],
) -> tuple[dict[str, Any], ...]:
    questions = {item["question_id"]: item for item in cqs["questions"]}
    translated: list[dict[str, Any]] = []
    for requirement in srp["requirements"]:
        requirement_id = requirement["requirement_id"]
        question_bindings = []
        for question_id in requirement["target_question_ids"]:
            question = questions[question_id]
            question_bindings.append(
                {
                    "source_question_id": question_id,
                    "statement": question["statement"],
                    "question_type": question["question_type"],
                    "dependencies": list(question["dependencies"]),
                    "resolution_condition": question["resolution_condition"],
                    "uncertainty": question["uncertainty"],
                    "source_admission_status": None,
                    "admission_status_note": "CQS v0.1 has no explicit admission-status field; membership is preserved without inventing one.",
                }
            )
        authorizations = [
            route_authority[(requirement_id, route["route_id"])]
            for route in requirement["epistemic_routes"]
        ]
        identity_seed = {
            "source_srp_id": srp["artifact_id"],
            "source_requirement_id": requirement_id,
            "source_srp_sha256": srp_sha,
        }
        translated.append(
            {
                "schema_version": CONSUMER_REQUIREMENT_SCHEMA_VERSION,
                "consumer_requirement_id": f"MR-CQC-{sha256_json(identity_seed)[:12]}",
                "source_requirement_id": requirement_id,
                "source_srp_id": srp["artifact_id"],
                "source_srp_sha256": srp_sha,
                "target_question_ids": list(requirement["target_question_ids"]),
                "question_bindings": question_bindings,
                "shared_requirement": len(requirement["target_question_ids"]) > 1,
                "evidence_obligation": {
                    "evidence_need": requirement["evidence_need"],
                    "source_requirements": list(requirement["source_requirements"]),
                    "stopping_condition": requirement["stopping_condition"],
                    "uncertainty_binding": requirement["uncertainty_binding"],
                },
                "route_authorizations": authorizations,
                "budget_authority": {
                    "source_budget_id": budget["artifact_id"],
                    "source_budget_sha256": budget_sha,
                    "budget_intent": dict(budget["budget_intent"]),
                    "total_envelope": dict(budget["total_envelope"]),
                    "feasibility": dict(budget["feasibility"]),
                },
                "source_lineage": {
                    "source_cqs_id": cqs["artifact_id"],
                    "source_cqs_sha256": cqs_sha,
                    "source_srp_id": srp["artifact_id"],
                    "source_srp_sha256": srp_sha,
                    "source_budget_id": budget["artifact_id"],
                    "source_budget_sha256": budget_sha,
                    "source_integration_binding_id": producer_binding["artifact_id"],
                    "source_integration_binding_sha256": producer_binding_sha,
                },
            }
        )
    return tuple(translated)


def consume_cqc_artifacts(
    *,
    cqs_path: Path,
    srp_path: Path,
    budget_path: Path,
    integration_binding_path: Path,
    source_cqc_freeze_sha: str,
    runtime_mafs_accepted_sha: str,
    created_at: str,
) -> CQCMAFSConsumerResult:
    """Validate a frozen CQC chain and return only mechanical MAFS inputs.

    All unknown, stale, missing, ambiguous, or authority-invalid states return
    ``INTEGRATION_BLOCKED``.  No partial requirement set is returned on failure.
    ``created_at`` is explicit so identical inputs produce identical receipts.
    """

    try:
        if source_cqc_freeze_sha != CQC_UPSTREAM_FREEZE_SHA:
            raise PackageCIntegrationError(
                INCOMPATIBLE,
                f"CQC freeze SHA mismatch: expected {CQC_UPSTREAM_FREEZE_SHA}",
            )
        if runtime_mafs_accepted_sha != M5_ACCEPTED_SHA:
            raise PackageCIntegrationError(
                INCOMPATIBLE,
                f"MAFS accepted SHA mismatch: expected {M5_ACCEPTED_SHA}",
            )
        if not isinstance(created_at, str) or not created_at.strip():
            raise PackageCIntegrationError(SCHEMA_INCOMPATIBLE, "created_at must be explicit")

        cqs = _load_json(Path(cqs_path), "CQS")
        srp = _load_json(Path(srp_path), "SRP")
        budget = _load_json(Path(budget_path), "BudgetEnvelope")
        producer_binding = _load_json(
            Path(integration_binding_path), "CQCMAFSIntegrationBinding"
        )
        cqs_sha = sha256_file(Path(cqs_path))
        srp_sha = sha256_file(Path(srp_path))
        budget_sha = sha256_file(Path(budget_path))
        producer_binding_sha = sha256_file(Path(integration_binding_path))

        _validate_cqs(cqs)
        _validate_srp(srp, cqs, cqs_sha)
        _validate_budget(budget, srp, srp_sha)
        route_authority, _unfunded = _route_authority(srp, budget)
        _validate_producer_binding(
            producer_binding,
            cqs=cqs,
            srp=srp,
            budget=budget,
            cqs_sha=cqs_sha,
            srp_sha=srp_sha,
            budget_sha=budget_sha,
            route_authority=route_authority,
        )
        requirements = _consumer_requirements(
            cqs=cqs,
            srp=srp,
            budget=budget,
            cqs_sha=cqs_sha,
            srp_sha=srp_sha,
            budget_sha=budget_sha,
            producer_binding=producer_binding,
            producer_binding_sha=producer_binding_sha,
            route_authority=route_authority,
        )
        translated_input_ids = [item["consumer_requirement_id"] for item in requirements]
        identity_payload = {
            "source_cqc_freeze_sha": source_cqc_freeze_sha,
            "source_cqs_sha256": cqs_sha,
            "source_srp_sha256": srp_sha,
            "source_budget_sha256": budget_sha,
            "source_integration_binding_sha256": producer_binding_sha,
            "consumer_mafs_accepted_sha": M5_ACCEPTED_SHA,
            "consumer_adapter_version": ADAPTER_VERSION,
        }
        compatibility_checks = [
            {"check_id": "CQC_FREEZE_SHA", "status": "PASS"},
            {"check_id": "CQS_SCHEMA_AND_IDENTITY", "status": "PASS"},
            {"check_id": "SRP_OBLIGATION_LINEAGE", "status": "PASS"},
            {"check_id": "BUDGET_AUTHORITY_LINEAGE", "status": "PASS"},
            {"check_id": "PRODUCER_BINDING_SOURCE_CHAIN", "status": "PASS"},
            {"check_id": "PRODUCER_BASELINE_SUPPORTED", "status": "PASS"},
            {"check_id": "M5_CONSUMER_PIN", "status": "PASS"},
            {"check_id": "AUTHORITY_MAPPING", "status": "PASS"},
        ]
        binding = {
            "binding_id": f"CQCB-{sha256_json(identity_payload)[:16]}",
            "schema_version": CONSUMER_BINDING_SCHEMA_VERSION,
            "source_cqc_freeze_sha": source_cqc_freeze_sha,
            "source_cqs_id": cqs["artifact_id"],
            "source_cqs_sha256": cqs_sha,
            "source_srp_id": srp["artifact_id"],
            "source_srp_sha256": srp_sha,
            "source_budget_id": budget["artifact_id"],
            "source_budget_sha256": budget_sha,
            "source_integration_binding_id": producer_binding["artifact_id"],
            "source_integration_binding_sha256": producer_binding_sha,
            "producer_mafs_compatibility_baseline": dict(producer_binding["mafs_baseline"]),
            "consumer_mafs_accepted_sha": M5_ACCEPTED_SHA,
            "consumer_adapter_version": ADAPTER_VERSION,
            "compatibility_status": COMPATIBLE,
            "compatibility_checks": compatibility_checks,
            "translated_input_ids": translated_input_ids,
            "authority_map": {
                "CQS": "scientific_question_admission_authority",
                "SRP": "evidence_obligation_authority",
                "BudgetEnvelope": "resource_and_route_authorization_authority",
                "CQCMAFSIntegrationBinding": "producer_lineage_and_historical_compatibility",
                "CQCMAFSConsumerBinding": "consumer_validation_and_current_compatibility_receipt",
                "MAFS": "post_handoff_scientific_route_and_evidence_cognition",
            },
            "stale_state_status": "CURRENT",
            "provenance": {
                "producer_semantics": "preserved_verbatim_by_source_hash",
                "consumer_semantics": "mechanical_wrapper_only",
                "integration_semantics": "validated_protocol_handoff",
                "producer_binding_preserved": True,
                "semantic_mutation_count": 0,
            },
            "created_at": created_at,
        }
        return CQCMAFSConsumerResult(
            integration_status=INTEGRATION_ACCEPTED,
            compatibility_status=COMPATIBLE,
            consumer_binding=binding,
            mafs_requirements=requirements,
            errors=(),
        )
    except PackageCIntegrationError as exc:
        return CQCMAFSConsumerResult(
            integration_status=INTEGRATION_BLOCKED,
            compatibility_status=exc.compatibility_status,
            consumer_binding=None,
            mafs_requirements=(),
            errors=(exc.detail,),
        )


def consumer_binding_sha256(binding: Mapping[str, Any]) -> str:
    """Return the canonical content hash carried into downstream provenance."""

    if binding.get("schema_version") != CONSUMER_BINDING_SCHEMA_VERSION:
        raise PackageCIntegrationError(SCHEMA_INCOMPATIBLE, "not a Package C consumer binding")
    return sha256_json(dict(binding))


def attach_elp_integration_provenance(
    elp: Mapping[str, Any], binding: Mapping[str, Any]
) -> dict[str, Any]:
    """Attach deterministic cross-repository lineage without changing ELP science."""

    if binding.get("compatibility_status") != COMPATIBLE:
        raise PackageCIntegrationError(INCOMPATIBLE, "cannot attach an unaccepted binding")
    result = json.loads(_canonical_json(dict(elp)))
    provenance = result.get("provenance_manifest")
    if not isinstance(provenance, dict):
        raise PackageCIntegrationError(SCHEMA_INCOMPATIBLE, "ELP lacks provenance_manifest")
    integration = {
        "source_cqc_freeze_sha": binding["source_cqc_freeze_sha"],
        "source_cqs_ids": [binding["source_cqs_id"]],
        "source_srp_ids": [binding["source_srp_id"]],
        "source_budget_ids": [binding["source_budget_id"]],
        "source_integration_binding_id": binding["source_integration_binding_id"],
        "source_integration_binding_sha256": binding["source_integration_binding_sha256"],
        "consumer_binding_id": binding["binding_id"],
        "consumer_binding_sha256": consumer_binding_sha256(binding),
        "m5_accepted_sha": binding["consumer_mafs_accepted_sha"],
        "package_c_adapter_version": binding["consumer_adapter_version"],
    }
    existing = provenance.get("cqc_mafs_integration")
    if existing is not None and existing != integration:
        raise PackageCIntegrationError(STALE_SOURCE_CHAIN, "ELP carries conflicting CQC lineage")
    provenance["cqc_mafs_integration"] = integration
    return result
