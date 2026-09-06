#!/usr/bin/env python3
"""Installed-product live smoke that stops before explicit selection."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from mafs_p0.epistemic_route import EpistemicRoute, RequirementRouteFidelityReview
from mafs_p0.package_a import PreparedRouteExecution
from mafs_p0.search_portfolio import SearchPortfolio


def build_execution() -> PreparedRouteExecution:
    """Build the open-discovery execution without performing network I/O."""
    route = EpistemicRoute(
        route_id="ER-9901", origin_requirement_id="REQ-RC1-SMOKE",
        semantic_intent="Discover recent evidence about reproducible scholarly search workflows.",
        independence_rationale="Uses workflow concepts without target paper identity.",
        framing_consequence="Evidence can delimit effective workflow controls.",
        search_vocabulary=("reproducible scholarly search", "workflow provenance", "evidence retrieval"),
        disciplinary_neighborhood=("information retrieval",), evidence_need="scholarly evidence",
        source_requirement={"preferred_source_classes": ["journal", "conference"]},
        search_intent="Open discovery; stop at CandidatePointerSet.",
        uncertainty="Provider results may vary.", status="ADMITTED", created_at="2026-09-06T00:00:00Z")
    review = RequirementRouteFidelityReview(
        review_id="RFR-9901", requirement_id=route.origin_requirement_id,
        route_id=route.route_id, status="PRESERVED",
        preserved_obligations=(route.evidence_need,), omitted_obligations=(), added_scope=(),
        rationale="The route preserves the bounded smoke requirement.",
        review_authority="release-engineering", created_at="2026-09-06T00:00:00Z")
    portfolio = SearchPortfolio.admit(
        portfolio_id="SP-9901", routes_and_reviews=((route, review),),
        budget_authorization=1, coverage_obligations=(route.origin_requirement_id,))
    return PreparedRouteExecution.prepare(route=route, fidelity_review=review, portfolio=portfolio)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    execution = build_execution()
    _, discovery = execution.discover(top_k=args.top_k)
    candidate_count = sum(len(item.get("candidate_pointers") or []) for item in discovery.get("rung_candidate_sets") or [])
    result = {
        "status": discovery.get("status"),
        "execution_boundary": discovery.get("execution_boundary"),
        "candidate_count": candidate_count,
        "target_identity_seeded": False,
        "selection_performed": False,
        "resolve_performed": False,
    }
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if candidate_count > 0 and result["execution_boundary"] == "STOP_AWAITING_SELECTION_ARTIFACT" else 2


if __name__ == "__main__":
    raise SystemExit(main())
