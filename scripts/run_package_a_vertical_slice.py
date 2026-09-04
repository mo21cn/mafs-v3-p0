"""Run the governed Package A R0-R3 vertical slice in explicit stages.

The command is intentionally not a one-shot pipeline.  ``discover`` stops
after emitting CandidatePointers.  ``select-resolve`` requires a separately
supplied CandidatePointer identifier and writes a SelectionArtifact before it
invokes the preserved P1.5 resolver.  ``ground`` consumes a separate semantic
adjudication artifact and cannot use model prior in place of source text.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

# Allow execution directly from a clean repository checkout without requiring
# an editable install.  This changes only import lookup, not runtime behavior.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from mafs_p0.epistemic_route import EpistemicRoute, RequirementRouteFidelityReview
from mafs_p0.evidence_resolution import (
    EvidenceResolutionSession,
    InMemorySourceAdapter,
    OpenAlexAbstractAdapter,
    PropositionRequest,
    SourceMaterial,
)
from mafs_p0.package_a import PreparedRouteExecution
from mafs_p0.search_portfolio import SearchPortfolio, SelectionArtifact


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prepare(input_document: dict[str, Any]) -> PreparedRouteExecution:
    route = EpistemicRoute.from_dict(input_document["epistemic_route"])
    review = RequirementRouteFidelityReview.from_dict(
        input_document["requirement_route_fidelity_review"]
    )
    portfolio = SearchPortfolio.admit(
        portfolio_id=input_document["portfolio_id"],
        routes_and_reviews=((route, review),),
        budget_authorization=int(input_document["budget_authorization"]),
        coverage_obligations=tuple(input_document["coverage_obligations"]),
    )
    return PreparedRouteExecution.prepare(
        route=route,
        fidelity_review=review,
        portfolio=portfolio,
    )


def discover(input_path: Path, output_dir: Path, *, top_k: int) -> int:
    input_document = _read_json(input_path)
    prepared = _prepare(input_document)
    _write_json(output_dir / "00_input.json", input_document)
    _write_json(output_dir / "01_epistemic_route.json", prepared.route.to_dict())
    _write_json(
        output_dir / "02_requirement_route_fidelity_review.json",
        prepared.fidelity_review.to_dict(),
    )
    _write_json(output_dir / "03_search_portfolio.json", prepared.portfolio.to_dict())
    _write_json(output_dir / "04_search_order.json", prepared.search_order.to_dict())
    _chain, result = prepared.discover(top_k=top_k)
    _write_json(output_dir / "05_discovery.json", result)
    stop = {
        "status": "STOP_AWAITING_SELECTION_ARTIFACT",
        "selection_present": False,
        "resolver_invoked": False,
        "discovery_sha256": _sha256(output_dir / "05_discovery.json"),
    }
    _write_json(output_dir / "06_stop_boundary.json", stop)
    print(json.dumps(stop, indent=2, sort_keys=True))
    return 0


def select_resolve(
    input_path: Path,
    output_dir: Path,
    *,
    rendering_path: str,
    candidate_pointer_id: str,
    selection_authority: str,
    selection_reason: str,
) -> int:
    input_document = _read_json(input_path)
    prepared = _prepare(input_document)
    discovery_path = output_dir / "05_discovery.json"
    discovery = _read_json(discovery_path)
    selection = SelectionArtifact.from_discovery(
        selection_id="SEL-001",
        discovery=discovery,
        rendering_path=rendering_path,
        selected_candidate_pointer_id=candidate_pointer_id,
        selection_authority=selection_authority,
        selection_reason=selection_reason,
        provenance={
            "discovery_artifact": discovery_path.name,
            "discovery_sha256": _sha256(discovery_path),
            "selection_was_external_to_deterministic_executor": True,
        },
    )
    selection_path = output_dir / "07_selection_artifact.json"
    _write_json(selection_path, selection.to_dict())
    chain = prepared.new_live_chain()
    result = prepared.resolve_selected(
        chain=chain,
        discovery=discovery,
        selection=selection,
    )
    _write_json(output_dir / "08_resolution.json", result)
    if result.get("status") != "ok" or not result.get("canonical_evidence"):
        print(json.dumps({"status": result.get("status"), "source": "NOT_ATTEMPTED"}))
        return 2
    canonical_evidence = result["canonical_evidence"]
    _write_json(output_dir / "09_canonical_evidence.json", canonical_evidence)
    session = EvidenceResolutionSession(adapters=(OpenAlexAbstractAdapter(),))
    source_document = session.resolve_source(canonical_evidence)
    _write_json(output_dir / "10_source_document.json", source_document.to_dict())
    content = session.source_content(source_document.source_document_id)
    if content is not None:
        (output_dir / "10_source_content.txt").write_text(content + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "selection_lineage_status": result["selection_lineage_status"],
                "source_representation_type": source_document.source_representation_type,
                "source_integrity_status": source_document.source_integrity_status,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def ground(input_path: Path, output_dir: Path, adjudication_path: Path) -> int:
    input_document = _read_json(input_path)
    resolution = _read_json(output_dir / "08_resolution.json")
    source_document_data = _read_json(output_dir / "10_source_document.json")
    canonical_evidence = resolution["canonical_evidence"]
    content_path = output_dir / "10_source_content.txt"
    source_materials: dict[str, SourceMaterial] = {}
    if content_path.exists():
        from mafs_p0.evidence_resolution import canonical_identity_key

        source_materials[canonical_identity_key(canonical_evidence)] = SourceMaterial(
            canonical_identity=source_document_data["canonical_identity"],
            representation_type=source_document_data["source_representation_type"],
            locator=source_document_data["source_locator"],
            content=content_path.read_text(encoding="utf-8").strip(),
            access_provenance={
                **source_document_data["access_provenance"],
                "rehydrated_from": content_path.name,
            },
        )
    session = EvidenceResolutionSession(
        adapters=(InMemorySourceAdapter(source_materials),)
    )
    source_document = session.resolve_source(canonical_evidence)
    adjudication = _read_json(adjudication_path)
    expected_ids = {
        item["proposition_id"] for item in input_document["proposition_requests"]
    }
    observed_ids = {item["proposition_id"] for item in adjudication["judgments"]}
    if observed_ids != expected_ids:
        raise ValueError("adjudication proposition ids do not match the frozen input")
    requests = {
        item["proposition_id"]: PropositionRequest(
            proposition_id=item["proposition_id"],
            text=item["text"],
            expected_source_document_id=source_document.source_document_id,
            required_evidence_roles=tuple(item.get("required_evidence_roles", [])),
            requires_statistical_result=bool(item.get("requires_statistical_result", False)),
            explicit_only=bool(item.get("explicit_only", True)),
        )
        for item in input_document["proposition_requests"]
    }
    spans = []
    evidence_records = []
    for item in adjudication["judgments"]:
        request = requests[item["proposition_id"]]
        if item["grounding_status"] == "CITABLE_SPAN":
            span = session.create_span(
                source_document=source_document,
                text=item["span_text"],
                evidence_role=item["evidence_role"],
            )
            spans.append(span)
            evidence = session.adjudicate(
                request=request,
                source_document=source_document,
                spans=(span,),
                relation=item["relation"],
                sufficiency_rationale=item["sufficiency_rationale"],
                uncertainty=item["uncertainty"],
                inference_mode=item.get("inference_mode", "EXPLICIT"),
                adjudication_authority=adjudication["adjudication_authority"],
            )
        else:
            evidence = session.ungrounded(
                request=request,
                source_document=source_document,
                grounding_status=item["grounding_status"],
                rationale=item["sufficiency_rationale"],
                uncertainty=item["uncertainty"],
            )
        evidence_records.append(evidence)
    _write_json(output_dir / "11_evidence_spans.json", [span.to_dict() for span in spans])
    _write_json(
        output_dir / "12_proposition_evidence.json",
        [record.to_dict() for record in evidence_records],
    )
    final_portfolio = _prepare(input_document).portfolio.with_execution(
        cost=1,
        covered_obligations=tuple(input_document["coverage_obligations"]),
    )
    _write_json(output_dir / "13_search_portfolio_final.json", final_portfolio.to_dict())
    summary = {
        "status": "PACKAGE_A_VERTICAL_SLICE_COMPLETE",
        "source_document_count": 1,
        "source_fetches": session.source_fetches,
        "source_cache_hits": session.source_cache_hits,
        "evidence_span_count": len(spans),
        "proposition_evidence_count": len(evidence_records),
        "grounded_count": sum(
            record.grounding_status == "CITABLE_SPAN" for record in evidence_records
        ),
        "negative_or_uncertain_count": sum(
            record.grounding_status != "CITABLE_SPAN" for record in evidence_records
        ),
        "r4_entered": False,
        "next_gate": "M3",
    }
    _write_json(output_dir / "14_demo_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    discover_parser = subparsers.add_parser("discover")
    discover_parser.add_argument("--top-k", type=int, default=5)
    select_parser = subparsers.add_parser("select-resolve")
    select_parser.add_argument("--rendering-path", required=True)
    select_parser.add_argument("--candidate-pointer-id", required=True)
    select_parser.add_argument("--selection-authority", required=True)
    select_parser.add_argument("--selection-reason", required=True)
    ground_parser = subparsers.add_parser("ground")
    ground_parser.add_argument("--adjudication", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "discover":
        return discover(args.input, args.output_dir, top_k=args.top_k)
    if args.command == "select-resolve":
        return select_resolve(
            args.input,
            args.output_dir,
            rendering_path=args.rendering_path,
            candidate_pointer_id=args.candidate_pointer_id,
            selection_authority=args.selection_authority,
            selection_reason=args.selection_reason,
        )
    return ground(args.input, args.output_dir, args.adjudication)


if __name__ == "__main__":
    raise SystemExit(main())
