from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from mafs_p0.collision import CollisionAssessment, ScopedPropositionEvidence
from mafs_p0.epistemic_route import EpistemicRoute, SemanticBoundaryError
from mafs_p0.package_b_demo import (
    build_negative_demo,
    build_positive_demo,
    fidelity,
    proposition,
    route,
    scope,
    scoped,
)
from mafs_p0.research_state import (
    ReDigestionRequest,
    validate_redigested_routes,
)
from mafs_p0.validator import validate_against_schema


def assess(kind: str, left, right, *, status: str = "COMPARABLE"):
    return CollisionAssessment.assess(
        collision_id="CA-100",
        evidence=(left, right),
        collision_type=kind,
        comparability_status=status,
        comparability_rationale="Explicit scope comparison was performed.",
        rationale="The relation is adjudicated from typed source spans.",
        uncertainty="Limited to fixture scope.",
        adjudication_authority="test_semantic_adjudicator",
    )


def test_direct_contradiction_is_scope_aligned_and_traceable():
    a = scoped(proposition("1"), claim_relation="SUPPORTS_SCOPE_CLAIM")
    b = scoped(
        proposition("2", relation="CONTRADICTS"),
        claim_relation="OPPOSES_SCOPE_CLAIM",
        claim_scope=scope(direction="lower"),
    )
    collision = assess("DIRECT_CONTRADICTION", a, b)
    assert collision.comparability["differing_dimensions"] == ["direction"]
    assert collision.supporting_span_ids == ("ES-111111111111", "ES-222222222222")
    assert not validate_against_schema(
        collision.to_dict(), "post_p1p5/collision_assessment.schema.json"
    )


def test_context_difference_becomes_boundary_condition_not_direct_contradiction():
    a = scoped(proposition("1"), claim_relation="SUPPORTS_SCOPE_CLAIM")
    b = scoped(
        proposition("2", relation="CONTRADICTS"),
        claim_relation="OPPOSES_SCOPE_CLAIM",
        claim_scope=scope(context_or_environment="field deployment"),
    )
    with pytest.raises(SemanticBoundaryError, match="aligned substantive"):
        assess("DIRECT_CONTRADICTION", a, b)
    boundary = assess("BOUNDARY_CONDITION", a, b, status="PARTIALLY_COMPARABLE")
    assert boundary.collision_type == "BOUNDARY_CONDITION"


def test_measurement_conflict_requires_measurement_difference():
    a = scoped(proposition("1"), claim_relation="SUPPORTS_SCOPE_CLAIM")
    b = scoped(
        proposition("2", relation="CONTRADICTS"),
        claim_relation="OPPOSES_SCOPE_CLAIM",
        claim_scope=scope(measurement_modality="human relevance judgment"),
    )
    assert assess("MEASUREMENT_CONFLICT", a, b, status="PARTIALLY_COMPARABLE").collision_type == "MEASUREMENT_CONFLICT"
    with pytest.raises(SemanticBoundaryError, match="measurement modalities"):
        assess("MEASUREMENT_CONFLICT", a, a)


def test_population_or_context_dependence_and_supporting_convergence():
    a = scoped(proposition("1"), claim_relation="SUPPORTS_SCOPE_CLAIM")
    b = scoped(
        proposition("2"),
        claim_relation="SUPPORTS_SCOPE_CLAIM",
        claim_scope=scope(population_or_system="multilingual benchmark systems"),
    )
    dependence = assess(
        "POPULATION_OR_CONTEXT_DEPENDENCE", a, b, status="PARTIALLY_COMPARABLE"
    )
    assert dependence.collision_type == "POPULATION_OR_CONTEXT_DEPENDENCE"
    convergent = assess("SUPPORTING_CONVERGENCE", a, scoped(proposition("3"), claim_relation="SUPPORTS_SCOPE_CLAIM"))
    assert convergent.status == "ASSESSED"


def test_ungrounded_evidence_can_only_create_insufficient_evidence():
    grounded = scoped(proposition("1"), claim_relation="SUPPORTS_SCOPE_CLAIM")
    silent = scoped(proposition("2", grounded=False), claim_relation="UNRESOLVED")
    with pytest.raises(SemanticBoundaryError, match="cannot create a collision"):
        assess("DIRECT_CONTRADICTION", grounded, silent)
    insufficient = assess("INSUFFICIENT_EVIDENCE", grounded, silent, status="UNRESOLVED")
    assert insufficient.status == "INSUFFICIENT"
    assert insufficient.supporting_span_ids == ("ES-111111111111",)


def test_identity_only_objects_cannot_enter_collision_plane():
    with pytest.raises(SemanticBoundaryError, match="not bibliographic identity"):
        ScopedPropositionEvidence(
            evidence={"doi": "identity-only"},  # type: ignore[arg-type]
            requirement_ids=("REQ-001",),
            route_ids=("ER-101",),
            claim_text="Identity is not proposition evidence.",
            claim_scope=scope(),
            claim_relation="UNRESOLVED",
            evidence_roles=(),
        )


def test_evidence_roles_and_limitations_remain_visible():
    a = scoped(
        proposition("1"),
        claim_relation="SUPPORTS_SCOPE_CLAIM",
        evidence_roles=("RESULT", "LIMITATION"),
        limitations=("Single benchmark.",),
    )
    b = scoped(
        proposition("2", relation="CONTRADICTS"),
        claim_relation="OPPOSES_SCOPE_CLAIM",
        claim_scope=scope(direction="lower"),
        evidence_roles=("RESULT",),
    )
    collision = assess("DIRECT_CONTRADICTION", a, b)
    assert collision.evidence_roles_by_proposition[a.evidence.proposition_evidence_id] == ("RESULT", "LIMITATION")
    assert collision.source_limitations_by_proposition[a.evidence.proposition_evidence_id] == ("Single benchmark.",)


def test_raw_counts_cannot_become_statistical_collision():
    a = scoped(proposition("1"), claim_relation="SUPPORTS_SCOPE_CLAIM", evidence_roles=("RESULT",))
    b = scoped(
        proposition("2", relation="CONTRADICTS"),
        claim_relation="OPPOSES_SCOPE_CLAIM",
        claim_scope=scope(direction="lower"),
        evidence_roles=("RESULT",),
    )
    with pytest.raises(SemanticBoundaryError, match="STATISTICAL_RESULT"):
        CollisionAssessment.assess(
            collision_id="CA-101",
            evidence=(a, b),
            collision_type="DIRECT_CONTRADICTION",
            comparability_status="COMPARABLE",
            comparability_rationale="Scopes align.",
            rationale="Counts alone are insufficient.",
            uncertainty="No significance test.",
            adjudication_authority="test",
            requires_statistical_evidence=True,
        )


def test_research_state_is_append_only_and_preserves_unresolved_obligations():
    demo = build_positive_demo()
    parent = demo["pre_redigestion_state"]
    state = demo["research_state"]
    assert state.parent_research_state_id == parent.research_state_id
    assert set(parent.proposition_evidence_ids).issubset(state.proposition_evidence_ids)
    assert parent.new_evidence_obligations[0] in state.unresolved_obligations
    assert parent.new_evidence_obligations[0].trigger_research_state_id == parent.research_state_id
    with pytest.raises(FrozenInstanceError):
        state.research_state_id = "RS-999"  # type: ignore[misc]
    assert not validate_against_schema(state.to_dict(), "post_p1p5/research_state.schema.json")
    assert not validate_against_schema(
        parent.new_evidence_obligations[0].to_dict(),
        "post_p1p5/new_evidence_obligation.schema.json",
    )


def test_redigestion_requires_state_trigger_obligation_and_budget_authorization():
    demo = build_positive_demo()
    request = demo["redigestion_request"]
    assert request.status == "AUTHORIZED"
    assert request.budget_authorization["authorized"] is True
    assert not validate_against_schema(
        request.to_dict(), "post_p1p5/redigestion_request.schema.json"
    )
    with pytest.raises(SemanticBoundaryError, match="budget authorization"):
        ReDigestionRequest.from_state(
            redigestion_request_id="RDR-099",
            state=demo["pre_redigestion_state"],
            origin_requirement_ids=("REQ-001",),
            trigger_collision_ids=("CA-001",),
            trigger_obligation_ids=("EO-001",),
            parent_route_ids=("ER-101",),
            reason="No budget should fail.",
            budget_authorization={"authorized": False},
            status="AUTHORIZED",
            provenance={"test": True},
        )


def test_redigested_route_preserves_lineage_fidelity_and_discovery_purity():
    demo = build_positive_demo()
    lineage = demo["route_revision_lineage"]
    assert lineage.parent_route_ids == ("ER-101",)
    assert lineage.revised_route_ids == ("ER-102",)
    assert not validate_against_schema(
        lineage.to_dict(), "post_p1p5/route_revision_lineage.schema.json"
    )
    bad_route = route("ER-103")
    bad_route_data = bad_route.to_dict()
    bad_route_data["source_requirement"]["expected_doi"] = "10.1000/oracle"
    with pytest.raises(SemanticBoundaryError, match="target identity"):
        EpistemicRoute.from_dict(bad_route_data)
    blocked_review = fidelity(bad_route, "RFR-103")
    blocked_data = blocked_review.to_dict()
    blocked_data.update({"status": "DRIFTED", "omitted_obligations": ["comparison"]})
    from mafs_p0.epistemic_route import RequirementRouteFidelityReview

    blocked = RequirementRouteFidelityReview.from_dict(blocked_data)
    with pytest.raises(SemanticBoundaryError, match="blocked by fidelity"):
        validate_redigested_routes(
            lineage_id="RRL-099",
            request=demo["redigestion_request"],
            routes_and_reviews=((bad_route, blocked),),
            provenance={"test": True},
        )


def test_negative_demo_never_fabricates_contradiction_or_authorization():
    demo = build_negative_demo()
    assert demo["collision"].collision_type == "INSUFFICIENT_EVIDENCE"
    assert demo["research_state"].redigestion_required is False
    assert demo["obligation"].authorization_status == "PROPOSED"
