#!/usr/bin/env python3
"""Canonical installed CQC -> Package C -> MAFS -> STOP release smoke."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
sys.path.insert(0, str(RUNTIME))

from mafs_p0.cqc_integration import INTEGRATION_ACCEPTED
from mafs_p0.epistemic_route import EpistemicRoute, RequirementRouteFidelityReview
from mafs_p0.package_a import PreparedRouteExecution
from mafs_p0.package_c_demo import consume, write_hermetic_cqc_fixture
from mafs_p0.search_portfolio import SearchPortfolio


FIXED_TIME = "2026-09-06T00:00:00Z"


def _installed_origin(module_file: str) -> bool:
    return Path(module_file).resolve().is_relative_to(RUNTIME.resolve())


def build_execution() -> tuple[PreparedRouteExecution, dict, dict]:
    """Consume a hermetic CQC artifact chain and construct one governed route."""

    with tempfile.TemporaryDirectory(prefix="mafs-ra2-smoke-") as temp_name:
        paths = write_hermetic_cqc_fixture(Path(temp_name))
        consumer = consume(paths)
    if consumer.integration_status != INTEGRATION_ACCEPTED:
        raise RuntimeError(consumer.to_dict())
    requirement = next(
        item
        for item in consumer.mafs_requirements
        if any(
            route["execution_authorization"] == "ACTIVE_AUTHORIZED"
            for route in item["route_authorizations"]
        )
    )
    requirement_id = requirement["consumer_requirement_id"]
    route = EpistemicRoute(
        route_id="ER-9911",
        origin_requirement_id=requirement_id,
        semantic_intent="Discover evidence that can establish or narrow the admitted mechanism obligation.",
        independence_rationale="The route is derived from the frozen obligation and contains no target identity.",
        framing_consequence="Retrieved evidence can establish, narrow, or leave the mechanism unresolved.",
        search_vocabulary=("primary mechanism evidence", "adjacent evidence source", "bounded evidence retrieval"),
        disciplinary_neighborhood=("scientific evidence synthesis",),
        evidence_need=requirement["evidence_obligation"]["evidence_need"],
        source_requirement={"preferred_source_classes": ["journal", "conference"]},
        search_intent="Open discovery; stop at CandidatePointerSet.",
        uncertainty=requirement["evidence_obligation"]["uncertainty_binding"],
        status="ADMITTED",
        created_at=FIXED_TIME,
    )
    review = RequirementRouteFidelityReview(
        review_id="RFR-9911",
        requirement_id=requirement_id,
        route_id=route.route_id,
        status="PRESERVED",
        preserved_obligations=(requirement["evidence_obligation"]["evidence_need"],),
        omitted_obligations=(),
        added_scope=(),
        rationale="The route preserves the CQC evidence obligation without adding a target identity.",
        review_authority="release-engineering-smoke",
        created_at=FIXED_TIME,
    )
    portfolio = replace(
        SearchPortfolio.admit(
            portfolio_id="SP-9911",
            routes_and_reviews=((route, review),),
            budget_authorization=1,
            coverage_obligations=(requirement_id,),
        ),
        created_at=FIXED_TIME,
    )
    execution = PreparedRouteExecution.prepare(
        route=route,
        fidelity_review=review,
        portfolio=portfolio,
    )
    return execution, consumer.to_dict(), requirement


def hermetic_discovery(execution: PreparedRouteExecution) -> dict:
    candidate = {
        "schema_version": "3.0-p1",
        "candidate_pointer_id": "CP-RA2-SMOKE-001",
        "provider": "hermetic_release_smoke_provider",
        "provider_result_id": "ra2-smoke-001",
        "title_hint": "Open-discovery release smoke candidate",
        "identifier_hints": {"doi": None, "pmid": None},
        "rank": 1,
        "retrieval_invocation_id": "RIV-RA2-SMOKE-001",
    }
    return {
        "status": "discovered",
        "search_order_id": execution.search_order.search_order_id,
        "route_id": execution.route.route_id,
        "portfolio_id": execution.portfolio.portfolio_id,
        "execution_boundary": "STOP_AWAITING_SELECTION_ARTIFACT",
        "rung_candidate_sets": [
            {
                "rendering_path": "hermetic_release_smoke",
                "candidate_count": 1,
                "candidate_pointers": [candidate],
            }
        ],
    }


def run(*, discovery_mode: str, top_k: int) -> dict:
    execution, consumer, requirement = build_execution()
    discovery = (
        hermetic_discovery(execution)
        if discovery_mode == "hermetic"
        else execution.discover(top_k=top_k)[1]
    )
    candidate_count = sum(
        len(item.get("candidate_pointers") or [])
        for item in discovery.get("rung_candidate_sets") or []
    )
    import mafs_p0.cqc_integration as cqc_integration
    import mafs_p0.epistemic_route as epistemic_route
    import mafs_p0.package_a as package_a

    origin_checks = {
        "package_c_consumer": _installed_origin(cqc_integration.__file__),
        "mafs_requirement": _installed_origin(cqc_integration.__file__),
        "route_generation": _installed_origin(epistemic_route.__file__),
        "discovery_spine": _installed_origin(package_a.__file__),
    }
    stop_reached = discovery.get("execution_boundary") == "STOP_AWAITING_SELECTION_ARTIFACT"
    return {
        "status": "PASS_STOP_REACHED" if candidate_count >= 1 and stop_reached and all(origin_checks.values()) else "FAIL",
        "execution_origin": "INSTALLED_RC" if all(origin_checks.values()) else "REPOSITORY_OR_OTHER",
        "installed_origin_checks": origin_checks,
        "cqc_handoff_status": consumer["integration_status"],
        "package_c_consumer_status": consumer["compatibility_status"],
        "mafs_requirement_constructed": bool(requirement),
        "route_constructed": execution.route.status == "ADMITTED",
        "discovery_mode": discovery_mode,
        "live_discovery_attempted": discovery_mode == "live",
        "discovery_status": discovery.get("status"),
        "candidate_count": candidate_count,
        "stop_status": discovery.get("execution_boundary"),
        "target_identity_seeded": False,
        "selection_performed": False,
        "resolve_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--discovery-mode", choices=("hermetic", "live"), default="live")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    result = run(discovery_mode=args.discovery_mode, top_k=args.top_k)
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS_STOP_REACHED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
