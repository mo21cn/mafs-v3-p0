#!/usr/bin/env python3
"""Generate Package C demos, execute the bounded live smoke, and hash artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mafs_p0.cqc_integration import (  # noqa: E402
    CQC_UPSTREAM_FREEZE_SHA,
    M5_ACCEPTED_SHA,
    consume_cqc_artifacts,
)
from mafs_p0.epistemic_route import EpistemicRoute, RequirementRouteFidelityReview  # noqa: E402
from mafs_p0.package_a import PreparedRouteExecution  # noqa: E402
from mafs_p0.package_c_demo import (  # noqa: E402
    FIXED_TIME,
    build_held_demo,
    build_positive_demo,
    write_hermetic_cqc_fixture,
)
from mafs_p0.search_portfolio import SearchPortfolio  # noqa: E402


INPUT_NAMES = {
    "cqs": "source_cqs.json",
    "srp": "source_srp.json",
    "budget": "budget_envelope.json",
    "binding": "integration_binding.json",
}


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def case_paths(case_dir: Path) -> dict[str, Path]:
    paths = {key: case_dir / name for key, name in INPUT_NAMES.items()}
    for path in paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    return paths


def write_positive(output_dir: Path, payload: dict) -> None:
    names = {
        "consumer_result": "consumer_result.json",
        "consumer_binding": "cqc_mafs_consumer_binding.json",
        "mafs_requirement": "mafs_requirement.json",
        "route": "epistemic_route.json",
        "fidelity_review": "requirement_route_fidelity_review.json",
        "search_portfolio": "search_portfolio.json",
        "search_order": "search_order.json",
        "discovery": "discovery_stop.json",
        "selection": "selection_artifact.json",
        "canonical_evidence": "canonical_evidence.json",
        "source_document": "source_document.json",
        "evidence_span": "evidence_span.json",
        "proposition_evidence": "proposition_evidence.json",
        "research_state": "research_state.json",
        "evidence_landscape_package": "evidence_landscape_package.json",
    }
    for key, name in names.items():
        write_json(output_dir / name, payload[key])


def demos(package_dir: Path) -> None:
    positive_dir = package_dir / "C_HERMETIC_POSITIVE_DEMO"
    positive_paths = write_hermetic_cqc_fixture(positive_dir / "input")
    write_positive(positive_dir, build_positive_demo(positive_paths))

    held_dir = package_dir / "C_HELD_CONDITIONAL_DEMO"
    held_paths = write_hermetic_cqc_fixture(held_dir / "input")
    write_json(held_dir / "held_result.json", build_held_demo(held_paths))

    negative_dir = package_dir / "C_HERMETIC_NEGATIVE_DEMO"
    negative_paths = write_hermetic_cqc_fixture(negative_dir / "input")
    srp = json.loads(negative_paths["srp"].read_text(encoding="utf-8"))
    srp["source_cqs_sha256"] = "f" * 64
    write_json(negative_paths["srp"], srp)
    negative = consume_cqc_artifacts(
        cqs_path=negative_paths["cqs"],
        srp_path=negative_paths["srp"],
        budget_path=negative_paths["budget"],
        integration_binding_path=negative_paths["binding"],
        source_cqc_freeze_sha=CQC_UPSTREAM_FREEZE_SHA,
        runtime_mafs_accepted_sha=M5_ACCEPTED_SHA,
        created_at=FIXED_TIME,
    )
    if negative.integration_status != "INTEGRATION_BLOCKED":
        raise RuntimeError("stale-chain demo did not fail closed")
    write_json(negative_dir / "blocked_result.json", negative.to_dict())
    write_json(
        negative_dir / "no_downstream_execution.json",
        {
            "epistemic_routes": [],
            "search_orders": [],
            "candidate_pointers": [],
            "status": "NO_PARTIAL_EXECUTION_AFTER_BLOCK",
        },
    )


def live_smoke(case_dir: Path, output_dir: Path, top_k: int) -> None:
    paths = case_paths(case_dir)
    result = consume_cqc_artifacts(
        cqs_path=paths["cqs"],
        srp_path=paths["srp"],
        budget_path=paths["budget"],
        integration_binding_path=paths["binding"],
        source_cqc_freeze_sha=CQC_UPSTREAM_FREEZE_SHA,
        runtime_mafs_accepted_sha=M5_ACCEPTED_SHA,
        created_at=FIXED_TIME,
    )
    if result.integration_status != "INTEGRATION_ACCEPTED":
        write_json(output_dir / "live_smoke_result.json", result.to_dict())
        raise RuntimeError("CQC integration was blocked")
    requirement = next(
        item
        for item in result.mafs_requirements
        if any(
            route["execution_authorization"] == "ACTIVE_AUTHORIZED"
            for route in item["route_authorizations"]
        )
    )
    requirement_id = requirement["consumer_requirement_id"]
    route = EpistemicRoute(
        route_id="ER-902",
        origin_requirement_id=requirement_id,
        semantic_intent="Find cell-type-resolved evidence for vasomotor symptom mechanisms.",
        independence_rationale="Uses mechanism and evidence vocabulary without a target identity.",
        framing_consequence="Cell-resolved findings can establish or narrow the mechanism.",
        search_vocabulary=(
            "vasomotor symptoms",
            "cell-type-specific mechanism",
            "single-cell evidence",
        ),
        disciplinary_neighborhood=("neuroendocrinology",),
        evidence_need=requirement["evidence_obligation"]["evidence_need"],
        source_requirement={"preferred_source_classes": ["journal", "conference"]},
        search_intent="Open scholarly discovery; stop at CandidatePointerSet.",
        uncertainty=requirement["evidence_obligation"]["uncertainty_binding"],
        status="ADMITTED",
        created_at=FIXED_TIME,
    )
    review = RequirementRouteFidelityReview(
        review_id="RFR-902",
        requirement_id=requirement_id,
        route_id=route.route_id,
        status="PRESERVED",
        preserved_obligations=(requirement["evidence_obligation"]["evidence_need"],),
        omitted_obligations=(),
        added_scope=(),
        rationale="The route preserves the active CQC evidence obligation.",
        review_authority="package-c-live-smoke-semantic-review",
        created_at=FIXED_TIME,
    )
    portfolio = SearchPortfolio.admit(
        portfolio_id="SP-902",
        routes_and_reviews=((route, review),),
        budget_authorization=1,
        coverage_obligations=(requirement_id,),
    )
    execution = PreparedRouteExecution.prepare(
        route=route, fidelity_review=review, portfolio=portfolio
    )
    _, discovery = execution.discover(top_k=top_k)
    write_json(output_dir / "consumer_result.json", result.to_dict())
    write_json(output_dir / "epistemic_route.json", route.to_dict())
    write_json(output_dir / "fidelity_review.json", review.to_dict())
    write_json(output_dir / "search_portfolio.json", portfolio.to_dict())
    write_json(output_dir / "search_order.json", execution.search_order.to_dict())
    write_json(output_dir / "live_smoke_result.json", discovery)
    if discovery.get("status") != "discovered":
        raise RuntimeError(f"live discovery failed: {discovery.get('status')}")
    if discovery.get("execution_boundary") != "STOP_AWAITING_SELECTION_ARTIFACT":
        raise RuntimeError("live smoke crossed the mandatory STOP boundary")
    if "canonical_evidence" in discovery or "selection_artifact" in discovery:
        raise RuntimeError("live smoke performed unauthorized downstream execution")
    candidate_count = sum(
        len(item.get("candidate_pointers") or [])
        for item in discovery.get("rung_candidate_sets") or []
    )
    if candidate_count < 1:
        raise RuntimeError("live smoke did not reach a CandidatePointer")


def validate_cqc_cases(contextual_dir: Path, output: Path) -> None:
    cases: list[dict[str, object]] = []
    for case_dir in sorted(path for path in contextual_dir.iterdir() if path.is_dir()):
        paths = case_paths(case_dir)
        result = consume_cqc_artifacts(
            cqs_path=paths["cqs"],
            srp_path=paths["srp"],
            budget_path=paths["budget"],
            integration_binding_path=paths["binding"],
            source_cqc_freeze_sha=CQC_UPSTREAM_FREEZE_SHA,
            runtime_mafs_accepted_sha=M5_ACCEPTED_SHA,
            created_at=FIXED_TIME,
        )
        cases.append(
            {
                "case_id": case_dir.name,
                "integration_status": result.integration_status,
                "compatibility_status": result.compatibility_status,
                "consumer_requirement_count": len(result.mafs_requirements),
                "errors": list(result.errors),
            }
        )
    all_compatible = bool(cases) and all(
        item["integration_status"] == "INTEGRATION_ACCEPTED"
        and item["compatibility_status"] == "COMPATIBLE"
        for item in cases
    )
    write_json(
        output,
        {
            "source_cqc_freeze_sha": CQC_UPSTREAM_FREEZE_SHA,
            "runtime_mafs_accepted_sha": M5_ACCEPTED_SHA,
            "case_count": len(cases),
            "all_compatible": all_compatible,
            "cases": cases,
        },
    )
    if not all_compatible:
        raise RuntimeError("one or more frozen CQC contextual cases were rejected")


def manifest(package_dir: Path, output: Path) -> None:
    output = output.resolve()
    rows: list[str] = []
    for path in sorted(package_dir.rglob("*")):
        if not path.is_file() or path.resolve() == output:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(f"{digest}  {path.relative_to(ROOT).as_posix()}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    demo_parser = sub.add_parser("demos")
    demo_parser.add_argument("--package-dir", type=Path, required=True)
    live_parser = sub.add_parser("live")
    live_parser.add_argument("--cqc-case-dir", type=Path, required=True)
    live_parser.add_argument("--output-dir", type=Path, required=True)
    live_parser.add_argument("--top-k", type=int, default=3)
    manifest_parser = sub.add_parser("manifest")
    manifest_parser.add_argument("--package-dir", type=Path, required=True)
    manifest_parser.add_argument("--output", type=Path, required=True)
    cqc_parser = sub.add_parser("validate-cqc")
    cqc_parser.add_argument("--contextual-dir", type=Path, required=True)
    cqc_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "demos":
        demos(args.package_dir)
    elif args.command == "live":
        live_smoke(args.cqc_case_dir, args.output_dir, args.top_k)
    elif args.command == "manifest":
        manifest(args.package_dir, args.output)
    else:
        validate_cqc_cases(args.contextual_dir, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
