"""Hermetic Package C integration demonstrations.

The CQC consumer is deliberately mechanical.  This module supplies explicit
post-handoff MAFS artifacts so the integration can be exercised without
putting route cognition, selection, resolution, or adjudication in the
adapter itself.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
from typing import Any

from .cqc_integration import (
    CQC_UPSTREAM_FREEZE_SHA,
    M5_ACCEPTED_SHA,
    attach_elp_integration_provenance,
    consume_cqc_artifacts,
)
from .epistemic_route import EpistemicRoute, RequirementRouteFidelityReview
from .evidence_landscape import EvidenceLandscapePackage
from .evidence_resolution import (
    EvidenceResolutionSession,
    InMemorySourceAdapter,
    PropositionRequest,
    SourceMaterial,
)
from .package_a import PreparedRouteExecution
from .research_state import ResearchState, RouteStatusRecord
from .search_portfolio import SearchPortfolio, SelectionArtifact


FIXED_TIME = "2026-09-06T00:00:00Z"


def _write_json(path: Path, value: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_hermetic_cqc_fixture(root: Path) -> dict[str, Path]:
    """Create a synthetic frozen-format CQC chain for local integration demos.

    These records are Package C fixtures, not a copy or vendor of the CQC
    repository.  They exercise the public artifact protocol only.
    """

    root.mkdir(parents=True, exist_ok=True)
    narrative = (
        "Compare a primary mechanism and an adjacent evidence source under a "
        "bounded search budget."
    )
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
                "resolution_condition": (
                    "A source-grounded result identifies the operative mechanism."
                ),
                "uncertainty": "The relevant level of mechanism remains open.",
            },
            {
                "question_id": "CQ-02",
                "statement": "Does an adjacent evidence source alter the conclusion?",
                "source_trace": [{"exact_quote": "adjacent evidence source"}],
                "question_type": "boundary",
                "dependencies": ["CQ-01"],
                "resolution_condition": (
                    "Independent adjacent evidence supports or narrows the conclusion."
                ),
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
                        "condition": (
                            "Activate only after an explicit collision or unresolved boundary."
                        ),
                    },
                ],
                "source_requirements": ["scholarly source", "citable result span"],
                "stopping_condition": (
                    "Stop after the obligation is grounded or remains explicitly unresolved."
                ),
                "uncertainty_binding": (
                    "Preserve uncertainty about mechanism level and adjacent transfer."
                ),
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
                {
                    "trigger": "required route cannot complete",
                    "action": "RETURN_INSUFFICIENT",
                }
            ]
        },
        "feasibility": {
            "status": "FEASIBLE",
            "unfunded_obligations": [],
            "constraint_note": "No known constraint.",
        },
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
            "commit_sha": "cd09699fc8cc160ab5cfff00a41e714961dd2109",
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
    return {
        "cqs": cqs_path,
        "srp": srp_path,
        "budget": budget_path,
        "binding": binding_path,
    }


def consume(paths: dict[str, Path]):
    return consume_cqc_artifacts(
        cqs_path=paths["cqs"],
        srp_path=paths["srp"],
        budget_path=paths["budget"],
        integration_binding_path=paths["binding"],
        source_cqc_freeze_sha=CQC_UPSTREAM_FREEZE_SHA,
        runtime_mafs_accepted_sha=M5_ACCEPTED_SHA,
        created_at=FIXED_TIME,
    )


def _active_requirement(result) -> dict[str, Any]:
    for requirement in result.mafs_requirements:
        if any(
            item["execution_authorization"] == "ACTIVE_AUTHORIZED"
            for item in requirement["route_authorizations"]
        ):
            return requirement
    raise ValueError("fixture contains no ACTIVE_AUTHORIZED CQC requirement")


def build_positive_demo(paths: dict[str, Path]) -> dict[str, Any]:
    """Build one complete, hermetic CQC -> ELP vertical slice."""

    result = consume(paths)
    if result.integration_status != "INTEGRATION_ACCEPTED":
        raise ValueError(result.to_dict())
    requirement = _active_requirement(result)
    requirement_id = requirement["consumer_requirement_id"]

    route = EpistemicRoute(
        route_id="ER-901",
        origin_requirement_id=requirement_id,
        semantic_intent=(
            "Find cell-type-resolved primary evidence about mechanisms of "
            "vasomotor symptoms."
        ),
        independence_rationale=(
            "The route is defined by an evidence obligation and mechanism vocabulary, "
            "not by a known paper identity."
        ),
        framing_consequence=(
            "Cell-resolved evidence can establish, narrow, or reject a proposed mechanism."
        ),
        search_vocabulary=(
            "vasomotor symptoms",
            "cell-type-specific mechanism",
            "single-cell evidence",
        ),
        disciplinary_neighborhood=("neuroendocrinology", "cell biology"),
        evidence_need=requirement["evidence_obligation"]["evidence_need"],
        source_requirement={
            "preferred_source_classes": ["primary study", "authoritative review"],
            "mechanism_terms": ["cell type", "mechanistic evidence"],
        },
        search_intent="Open discovery of cell-resolution mechanism evidence.",
        uncertainty=requirement["evidence_obligation"]["uncertainty_binding"],
        status="ADMITTED",
        created_at=FIXED_TIME,
    )
    review = RequirementRouteFidelityReview(
        review_id="RFR-901",
        requirement_id=requirement_id,
        route_id=route.route_id,
        status="PRESERVED",
        preserved_obligations=(requirement["evidence_obligation"]["evidence_need"],),
        omitted_obligations=(),
        added_scope=(),
        rationale="The route retains the cell-resolution mechanism evidence obligation.",
        review_authority="package-c-hermetic-semantic-review",
        created_at=FIXED_TIME,
    )
    portfolio = replace(
        SearchPortfolio.admit(
            portfolio_id="SP-901",
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
    search_order = replace(execution.search_order, created_at=FIXED_TIME)

    candidate = {
        "schema_version": "3.0-p1",
        "candidate_pointer_id": "CP-PACKAGE-C-001",
        "provider": "hermetic_package_c_provider",
        "provider_result_id": "fixture-result-001",
        "title_hint": "Cell-resolved evidence for a vasomotor mechanism",
        "identifier_hints": {"doi": "10.5555/package.c.fixture", "pmid": None},
        "rank": 1,
        "retrieval_invocation_id": "RIV-PACKAGE-C-001",
    }
    discovery = {
        "status": "discovered",
        "search_order_id": search_order.search_order_id,
        "route_id": route.route_id,
        "portfolio_id": portfolio.portfolio_id,
        "execution_boundary": "STOP_AWAITING_SELECTION_ARTIFACT",
        "rung_candidate_sets": [
            {
                "rendering_path": "package_c_hermetic_open_discovery",
                "candidate_count": 1,
                "candidate_pointers": [candidate],
            }
        ],
    }
    selection = replace(
        SelectionArtifact.from_discovery(
            selection_id="SEL-901",
            discovery=discovery,
            rendering_path="package_c_hermetic_open_discovery",
            selected_candidate_pointer_id=candidate["candidate_pointer_id"],
            selection_authority="package-c-hermetic-external-selector",
            selection_reason="The candidate directly addresses the admitted route intent.",
            provenance={"decision_record": "demo_positive/selection_artifact.json"},
        ),
        timestamp=FIXED_TIME,
    )
    canonical_evidence = {
        "schema_version": "3.0-p1",
        "evidence_id": "CE-PACKAGE-C-001",
        "candidate_pointer_id": candidate["candidate_pointer_id"],
        "canonical": {
            "title": candidate["title_hint"],
            "authors": ["Fixture Researcher"],
            "year": 2026,
            "venue": "Hermetic Evidence Journal",
            "doi": candidate["identifier_hints"]["doi"],
            "source_locator": "memory://package-c/canonical/001",
            "resolver_identity": "hermetic_package_c_resolver",
        },
        "provenance": {
            "retrieval_invocation_id": candidate["retrieval_invocation_id"],
            "resolver_invocation_id": "RIVR-PACKAGE-C-001",
            "selection_artifact_id": selection.selection_id,
        },
        "created_at": FIXED_TIME,
    }

    result_sentence = (
        "Cell-type-specific perturbation reduced the measured vasomotor response "
        "relative to the control condition (p = 0.004)."
    )
    material = SourceMaterial(
        canonical_identity={
            "doi": candidate["identifier_hints"]["doi"],
            "title": candidate["title_hint"],
            "year": 2026,
        },
        representation_type="FULL_TEXT",
        locator="memory://package-c/source/001",
        content=(
            "Introduction. The mechanism is uncertain. Results. "
            + result_sentence
            + " Discussion. The finding is limited to the studied model."
        ),
        access_provenance={
            "adapter": "package_c_hermetic_full_text",
            "lawful_access": "test_fixture",
            "network_access": False,
        },
    )
    session = EvidenceResolutionSession(
        (InMemorySourceAdapter({"doi:10.5555/package.c.fixture": material}),)
    )
    document = replace(session.resolve_source(canonical_evidence), created_at=FIXED_TIME)
    span = session.create_span(
        source_document=document,
        text=result_sentence,
        evidence_role="STATISTICAL_RESULT",
    )
    proposition_request = PropositionRequest(
        proposition_id="PROP-PACKAGE-C-001",
        text="Did a cell-type-specific perturbation reduce the vasomotor response?",
        expected_source_document_id=document.source_document_id,
        required_evidence_roles=("STATISTICAL_RESULT",),
        requires_statistical_result=True,
    )
    proposition_evidence = replace(
        session.adjudicate(
            request=proposition_request,
            source_document=document,
            spans=(span,),
            relation="SUPPORTS",
            sufficiency_rationale=(
                "The full-text statistical result explicitly reports the perturbation, "
                "comparator, outcome direction, and p-value."
            ),
            uncertainty="Bounded to the fixture model and measured response.",
            adjudication_authority="package-c-hermetic-semantic-adjudicator",
        ),
        created_at=FIXED_TIME,
    )
    executed_portfolio = portfolio.with_execution(
        cost=1, covered_obligations=(requirement_id,)
    )
    state = ResearchState.initial(
        research_state_id="RS-901",
        requirements=(requirement_id,),
        active_route_ids=(route.route_id,),
        proposition_evidence_ids=(proposition_evidence.proposition_evidence_id,),
        route_status=(
            RouteStatusRecord(
                route.route_id,
                "COVERED",
                "The admitted route produced span-grounded proposition evidence.",
            ),
        ),
        provenance={
            "stage": "package_c_positive_vertical_slice",
            "consumer_binding_id": result.consumer_binding["binding_id"],
        },
    )
    landscape = EvidenceLandscapePackage.from_research_state(
        package_id="ELP-901",
        state=state,
        route_history=(
            {
                "route_id": route.route_id,
                "history_kind": "ORIGINAL",
                "parent_route_ids": [],
                "execution_state": "COVERED",
                "origin_requirement_id": requirement_id,
            },
        ),
        search_portfolio_history=(executed_portfolio.to_dict(),),
        budget_history=(
            {
                "source_budget_id": requirement["budget_authority"]["source_budget_id"],
                "source_budget_sha256": requirement["budget_authority"]["source_budget_sha256"],
                "consumer_authorized_units": 1,
                "consumer_used_units": 1,
            },
        ),
        candidate_pointer_lineage=(
            {
                "candidate_pointer_id": candidate["candidate_pointer_id"],
                "route_id": route.route_id,
                "artifact_type": "CandidatePointer",
            },
        ),
        selection_lineage=(selection.to_dict(),),
        source_document_ids=(document.source_document_id,),
        evidence_span_ids=(span.span_id,),
        proposition_evidence_ids=(proposition_evidence.proposition_evidence_id,),
        collisions=(),
        coverage_summary={
            "requirements_covered": [requirement_id],
            "requirements_partially_covered": [],
            "requirements_uncovered": [],
            "routes_executed": [route.route_id],
            "routes_underexplored": [],
            "routes_exhausted": [],
            "evidence_inaccessible": 0,
            "propositions_grounded": 1,
            "propositions_unresolved": 0,
        },
        provenance_manifest={
            "typed_evidence_layers_preserved": [
                "CandidatePointer",
                "SourceDocument",
                "EvidenceSpan",
                "PropositionEvidence",
            ],
            "research_state_id": state.research_state_id,
        },
        created_at=FIXED_TIME,
    )
    integrated_landscape = attach_elp_integration_provenance(
        landscape.to_dict(), result.consumer_binding
    )
    return {
        "consumer_result": result.to_dict(),
        "consumer_binding": result.consumer_binding,
        "mafs_requirement": requirement,
        "route": route.to_dict(),
        "fidelity_review": review.to_dict(),
        "search_portfolio": executed_portfolio.to_dict(),
        "search_order": search_order.to_dict(),
        "discovery": discovery,
        "selection": selection.to_dict(),
        "canonical_evidence": canonical_evidence,
        "source_document": document.to_dict(),
        "evidence_span": span.to_dict(),
        "proposition_evidence": proposition_evidence.to_dict(),
        "research_state": state.to_dict(),
        "evidence_landscape_package": integrated_landscape,
    }


def build_held_demo(paths: dict[str, Path]) -> dict[str, Any]:
    result = consume(paths)
    held = [
        requirement
        for requirement in result.mafs_requirements
        if any(
            item["execution_authorization"] == "HELD_CONDITIONAL"
            for item in requirement["route_authorizations"]
        )
    ]
    return {
        "consumer_result": result.to_dict(),
        "held_requirements": held,
        "activated_route_ids": [],
        "search_orders": [],
        "status": "HELD_CONDITIONAL_NOT_ACTIVATED",
    }
