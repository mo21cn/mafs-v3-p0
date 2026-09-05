"""Hermetic Package B fixtures used by the development demo and tests."""
from __future__ import annotations

from typing import Any

from .collision import ClaimScope, CollisionAssessment, ScopedPropositionEvidence
from .epistemic_route import EpistemicRoute, RequirementRouteFidelityReview
from .evidence_landscape import EvidenceLandscapePackage
from .evidence_resolution import PropositionEvidence
from .research_state import (
    NewEvidenceObligation,
    ReDigestionRequest,
    ResearchState,
    RouteStatusRecord,
    ScopedClaim,
    validate_redigested_routes,
)


FIXED_TIME = "2026-09-05T00:00:00Z"


def proposition(
    suffix: str,
    *,
    relation: str = "SUPPORTS",
    grounded: bool = True,
) -> PropositionEvidence:
    return PropositionEvidence(
        proposition_evidence_id=f"PE-{suffix * 12}",
        proposition_id=f"PROP-{suffix.upper()}",
        source_document_id=f"SD-{suffix * 12}",
        span_ids=(f"ES-{suffix * 12}",) if grounded else (),
        relation=relation if grounded else "NOT_GROUNDED",
        sufficiency_rationale=(
            "The cited result span directly addresses the scoped proposition."
            if grounded
            else "The available source does not establish the proposition."
        ),
        uncertainty="Bounded to the reported system and measurement.",
        grounding_status="CITABLE_SPAN" if grounded else "NOT_ADDRESSED",
        provenance={"model_prior_used_as_evidence": False, "fixture": "package_b"},
        created_at=FIXED_TIME,
    )


def scope(**overrides: str) -> ClaimScope:
    values = {
        "population_or_system": "benchmark systems",
        "intervention_or_exposure": "method A",
        "comparator": "method B",
        "outcome": "retrieval accuracy",
        "measurement_modality": "held-out accuracy",
        "time_scale": "single evaluation period",
        "context_or_environment": "controlled benchmark",
        "direction": "higher",
        "certainty_or_statistical_status": "reported point estimate",
    }
    values.update(overrides)
    return ClaimScope(**values)


def scoped(
    evidence: PropositionEvidence,
    *,
    claim_relation: str,
    claim_scope: ClaimScope | None = None,
    evidence_roles: tuple[str, ...] = ("RESULT",),
    limitations: tuple[str, ...] = (),
) -> ScopedPropositionEvidence:
    return ScopedPropositionEvidence(
        evidence=evidence,
        requirement_ids=("REQ-001",),
        route_ids=("ER-101",),
        claim_text="Method A improves retrieval accuracy relative to method B.",
        claim_scope=claim_scope or scope(),
        claim_relation=claim_relation,
        evidence_roles=evidence_roles if evidence.grounding_status == "CITABLE_SPAN" else (),
        source_limitations=limitations,
    )


def route(route_id: str, *, status: str = "ADMITTED") -> EpistemicRoute:
    return EpistemicRoute(
        route_id=route_id,
        origin_requirement_id="REQ-001",
        semantic_intent="Test whether the effect persists under an alternate evaluation context.",
        independence_rationale="The route changes evidence context rather than restating an identity.",
        framing_consequence="A context-bound effect would narrow the original claim.",
        search_vocabulary=("retrieval accuracy", "evaluation context"),
        disciplinary_neighborhood=("information retrieval",),
        evidence_need="comparative result evidence",
        source_requirement={
            "preferred_source_classes": ["conference", "journal"],
            "measurement_terms": ["held-out evaluation"],
        },
        search_intent="Find comparative evaluations in a distinct context.",
        uncertainty="Route quality requires external semantic review.",
        status=status,
        created_at=FIXED_TIME,
    )


def fidelity(route_obj: EpistemicRoute, review_id: str) -> RequirementRouteFidelityReview:
    return RequirementRouteFidelityReview(
        review_id=review_id,
        requirement_id="REQ-001",
        route_id=route_obj.route_id,
        status="PRESERVED",
        preserved_obligations=("Compare the claimed effect across evidence contexts.",),
        omitted_obligations=(),
        added_scope=("alternate evaluation context",),
        rationale="The revised route preserves the comparison and seeks boundary evidence.",
        review_authority="external_semantic_reviewer",
        created_at=FIXED_TIME,
    )


def _lineage_records(revised: bool) -> tuple[dict[str, Any], ...]:
    original = {
        "route_id": "ER-101",
        "history_kind": "ORIGINAL",
        "parent_route_ids": [],
        "execution_state": "REVISION_CANDIDATE" if revised else "UNDEREXPLORED",
        "origin_requirement_id": "REQ-001",
    }
    if not revised:
        return (original,)
    return (
        original,
        {
            "route_id": "ER-102",
            "history_kind": "REDIGESTED",
            "parent_route_ids": ["ER-101"],
            "execution_state": "UNDEREXPLORED",
            "origin_requirement_id": "REQ-001",
            "redigestion_request_id": "RDR-001",
            "route_revision_lineage_id": "RRL-001",
        },
    )


def _elp(
    *,
    package_id: str,
    state: ResearchState,
    collisions: tuple[CollisionAssessment, ...],
    proposition_evidence: tuple[PropositionEvidence, ...],
    revised: bool,
) -> EvidenceLandscapePackage:
    grounded = tuple(
        item for item in proposition_evidence if item.grounding_status == "CITABLE_SPAN"
    )
    unresolved = tuple(
        item for item in proposition_evidence if item.grounding_status != "CITABLE_SPAN"
    )
    return EvidenceLandscapePackage.from_research_state(
        package_id=package_id,
        state=state,
        route_history=_lineage_records(revised),
        search_portfolio_history=(
            {
                "portfolio_id": "SP-001",
                "active_route_ids": list(state.active_route_ids),
                "uncovered_obligations": [
                    obligation.obligation_id for obligation in state.unresolved_obligations
                ],
            },
        ),
        budget_history=(
            {
                "budget_authority": "HO",
                "authorized_units": 2 if revised else 1,
                "used_units": 1,
            },
        ),
        candidate_pointer_lineage=(
            {
                "candidate_pointer_id": "CP-demo-001",
                "route_id": "ER-101",
                "artifact_type": "CandidatePointer",
            },
        ),
        selection_lineage=(
            {
                "selection_id": "SEL-001",
                "candidate_pointer_id": "CP-demo-001",
                "selection_authority": "human_operator",
            },
        ),
        source_document_ids=tuple(item.source_document_id for item in proposition_evidence),
        evidence_span_ids=tuple(span for item in proposition_evidence for span in item.span_ids),
        proposition_evidence_ids=state.proposition_evidence_ids,
        collisions=collisions,
        coverage_summary={
            "requirements_covered": [],
            "requirements_partially_covered": ["REQ-001"],
            "requirements_uncovered": [],
            "routes_executed": ["ER-101"] if revised else [],
            "routes_underexplored": ["ER-102"] if revised else ["ER-101"],
            "routes_exhausted": [],
            "evidence_inaccessible": 0,
            "propositions_grounded": len(grounded),
            "propositions_unresolved": len(unresolved),
        },
        provenance_manifest={
            "research_state_id": state.research_state_id,
            "collision_ids": list(state.collision_ids),
            "typed_evidence_layers_preserved": [
                "CandidatePointer",
                "SourceDocument",
                "EvidenceSpan",
                "PropositionEvidence",
            ],
        },
        created_at=FIXED_TIME,
    )


def build_positive_demo() -> dict[str, Any]:
    supporting = proposition("a", relation="SUPPORTS")
    opposing = proposition("b", relation="CONTRADICTS")
    collision = CollisionAssessment.assess(
        collision_id="CA-001",
        evidence=(
            scoped(supporting, claim_relation="SUPPORTS_SCOPE_CLAIM"),
            scoped(
                opposing,
                claim_relation="OPPOSES_SCOPE_CLAIM",
                claim_scope=scope(direction="lower"),
                limitations=("Single benchmark replication.",),
            ),
        ),
        collision_type="DIRECT_CONTRADICTION",
        comparability_status="COMPARABLE",
        comparability_rationale="All substantive scope dimensions align.",
        rationale="Grounded result spans make opposing claims in the same scope.",
        uncertainty="Replication breadth is limited.",
        adjudication_authority="external_semantic_adjudicator",
    )
    parent = ResearchState.initial(
        research_state_id="RS-001",
        requirements=("REQ-001",),
        active_route_ids=("ER-101",),
        proposition_evidence_ids=(supporting.proposition_evidence_id,),
        route_status=(RouteStatusRecord("ER-101", "ACTIVE", "Initial route executed."),),
        provenance={"stage": "initial", "append_only": True},
    )
    obligation = NewEvidenceObligation(
        obligation_id="EO-001",
        trigger_collision_ids=(collision.collision_id,),
        trigger_research_state_id="RS-002",
        scientific_question="Does the conflict persist in an independent evaluation context?",
        why_current_evidence_is_insufficient="Two grounded results disagree in one benchmark family.",
        required_evidence_type="Independent comparative result evidence",
        authorization_status="AUTHORIZED",
    )
    contested = ScopedClaim(
        claim_id="CLM-001",
        text="Method A improves retrieval accuracy relative to method B.",
        scope=scope().to_dict(),
        status="CONTESTED",
        proposition_evidence_ids=(
            supporting.proposition_evidence_id,
            opposing.proposition_evidence_id,
        ),
        collision_ids=(collision.collision_id,),
        uncertainty="Direct contradiction requires another evidence context.",
    )
    state = ResearchState.evolve(
        research_state_id="RS-002",
        parent=parent,
        added_proposition_evidence_ids=(opposing.proposition_evidence_id,),
        added_collisions=(collision,),
        added_contested_claims=(contested,),
        added_route_status=(
            RouteStatusRecord(
                "ER-101", "REVISION_CANDIDATE", "Collision requires bounded re-digestion.",
                (collision.collision_id,),
            ),
        ),
        new_evidence_obligations=(obligation,),
        redigestion_required=True,
        redigestion_reasons=("Resolve CA-001 with an independent evidence context.",),
        provenance={"stage": "collision_update", "append_only": True},
    )
    request = ReDigestionRequest.from_state(
        redigestion_request_id="RDR-001",
        state=state,
        origin_requirement_ids=("REQ-001",),
        trigger_collision_ids=("CA-001",),
        trigger_obligation_ids=("EO-001",),
        parent_route_ids=("ER-101",),
        reason="Search one bounded alternate evidence context.",
        budget_authorization={"authorized": True, "units": 1, "authority": "HO"},
        status="AUTHORIZED",
        provenance={"authorization_record": "demo-explicit"},
    )
    revised_route = route("ER-102")
    review = fidelity(revised_route, "RFR-102")
    lineage = validate_redigested_routes(
        lineage_id="RRL-001",
        request=request,
        routes_and_reviews=((revised_route, review),),
        provenance={"validator": "package_b"},
    )
    post_redigestion_state = ResearchState.evolve(
        research_state_id="RS-003",
        parent=state,
        added_active_route_ids=(revised_route.route_id,),
        added_route_status=(
            RouteStatusRecord(
                revised_route.route_id,
                "UNDEREXPLORED",
                "Re-digested route is generated and fidelity-validated but not searched.",
                (collision.collision_id,),
            ),
        ),
        redigestion_required=False,
        provenance={
            "stage": "post_redigestion_route_commit",
            "append_only": True,
            "redigestion_request_id": request.redigestion_request_id,
            "route_revision_lineage_id": lineage.lineage_id,
        },
    )
    landscape = _elp(
        package_id="ELP-001",
        state=post_redigestion_state,
        collisions=(collision,),
        proposition_evidence=(supporting, opposing),
        revised=True,
    )
    return {
        "proposition_evidence": (supporting, opposing),
        "collision": collision,
        "parent_state": parent,
        "pre_redigestion_state": state,
        "research_state": post_redigestion_state,
        "obligation": obligation,
        "redigestion_request": request,
        "revised_route": revised_route,
        "fidelity_review": review,
        "route_revision_lineage": lineage,
        "landscape": landscape,
    }


def build_negative_demo() -> dict[str, Any]:
    grounded = proposition("c", relation="SUPPORTS")
    ungrounded = proposition("d", grounded=False)
    collision = CollisionAssessment.assess(
        collision_id="CA-002",
        evidence=(
            scoped(grounded, claim_relation="SUPPORTS_SCOPE_CLAIM"),
            scoped(ungrounded, claim_relation="UNRESOLVED"),
        ),
        collision_type="INSUFFICIENT_EVIDENCE",
        comparability_status="UNRESOLVED",
        comparability_rationale="One source does not address the proposition.",
        rationale="No opposing grounded proposition exists.",
        uncertainty="The claim remains unresolved.",
        adjudication_authority="external_semantic_adjudicator",
    )
    parent = ResearchState.initial(
        research_state_id="RS-010",
        requirements=("REQ-001",),
        active_route_ids=("ER-101",),
        proposition_evidence_ids=(grounded.proposition_evidence_id,),
        route_status=(RouteStatusRecord("ER-101", "UNDEREXPLORED", "One source is silent."),),
        provenance={"stage": "initial", "append_only": True},
    )
    obligation = NewEvidenceObligation(
        obligation_id="EO-010",
        trigger_collision_ids=(collision.collision_id,),
        trigger_research_state_id="RS-011",
        scientific_question="Can an accessible source address the unresolved proposition?",
        why_current_evidence_is_insufficient="The second proposition is not grounded.",
        required_evidence_type="Grounded result evidence",
        authorization_status="PROPOSED",
    )
    state = ResearchState.evolve(
        research_state_id="RS-011",
        parent=parent,
        added_proposition_evidence_ids=(ungrounded.proposition_evidence_id,),
        added_collisions=(collision,),
        new_evidence_obligations=(obligation,),
        redigestion_required=False,
        provenance={"stage": "unresolved_update", "append_only": True},
    )
    landscape = _elp(
        package_id="ELP-002",
        state=state,
        collisions=(collision,),
        proposition_evidence=(grounded, ungrounded),
        revised=False,
    )
    return {
        "proposition_evidence": (grounded, ungrounded),
        "collision": collision,
        "parent_state": parent,
        "research_state": state,
        "obligation": obligation,
        "landscape": landscape,
    }
