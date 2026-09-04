from __future__ import annotations

import hashlib

import pytest

from mafs_p0 import live_chain as live_chain_module
from mafs_p0.epistemic_route import EpistemicRoute, RequirementRouteFidelityReview, SemanticBoundaryError
from mafs_p0.package_a import PreparedRouteExecution
from mafs_p0.search_portfolio import SearchPortfolio, SelectionArtifact
from mafs_p0.validator import validate_against_schema


def prepared() -> PreparedRouteExecution:
    route = EpistemicRoute(
        route_id="ER-002",
        origin_requirement_id="SRP-2",
        semantic_intent="Find empirical studies of route diversity.",
        independence_rationale="Uses mechanism and measurement vocabulary, not paper identity.",
        framing_consequence="Tests whether route diversity changes retrieved evidence.",
        search_vocabulary=("route diversity", "evidence retrieval"),
        disciplinary_neighborhood=("information retrieval",),
        evidence_need="reported empirical result",
        source_requirement={"preferred_source_classes": ["conference"]},
        search_intent="open discovery of route diversity evidence",
        uncertainty="Terminology is not standardized.",
        status="ADMITTED",
    )
    review = RequirementRouteFidelityReview(
        review_id="RFR-002",
        requirement_id="SRP-2",
        route_id="ER-002",
        status="PRESERVED",
        preserved_obligations=("route diversity", "empirical result"),
        omitted_obligations=(),
        added_scope=(),
        rationale="The route retains both requested concepts.",
        review_authority="package-a-test-reviewer",
    )
    portfolio = SearchPortfolio.admit(
        portfolio_id="SP-002",
        routes_and_reviews=((route, review),),
        budget_authorization=1,
        coverage_obligations=("SRP-2",),
    )
    return PreparedRouteExecution.prepare(
        route=route, fidelity_review=review, portfolio=portfolio
    )


def _install_fake_crossref(monkeypatch):
    body = b'{"message":{"items":[]}}'
    sha = hashlib.sha256(body).hexdigest()
    candidates = [
        {
            "schema_version": "3.0-p1",
            "candidate_pointer_id": "CP-001",
            "provider": "crossref_works_v1",
            "provider_result_id": "10.1111/first",
            "title_hint": "First candidate",
            "identifier_hints": {"doi": "10.1111/first", "pmid": None},
            "rank": 1,
            "retrieval_invocation_id": "RIV-001",
        },
        {
            "schema_version": "3.0-p1",
            "candidate_pointer_id": "CP-002",
            "provider": "crossref_works_v1",
            "provider_result_id": "10.1111/second",
            "title_hint": "Second candidate",
            "identifier_hints": {"doi": "10.1111/second", "pmid": None},
            "rank": 2,
            "retrieval_invocation_id": "RIV-001",
        },
    ]

    def fake_discover(self, *args, **kwargs):
        return candidates, {
            "retrieval_invocation_id": "RIV-001",
            "raw_snapshot_sha256": sha,
            "response": {"http_status": 200},
            "status": "ok",
        }, {"sha256": sha, "bytes": "", "content_type": "application/json"}

    def fake_resolve(self, *, candidate_pointer, retrieval_invocation_id, **kwargs):
        resolver_sha = hashlib.sha256(b"resolved").hexdigest()
        evidence = {
            "schema_version": "3.0-p1",
            "evidence_id": "",
            "candidate_pointer_id": candidate_pointer["candidate_pointer_id"],
            "canonical": {
                "title": candidate_pointer["title_hint"],
                "authors": ["A Researcher"],
                "year": 2025,
                "venue": "Test Venue",
                "doi": candidate_pointer["identifier_hints"]["doi"],
                "source_locator": "https://doi.org/10.1111/second",
                "resolver_identity": "crossref_reference_resolver_v1",
            },
            "provenance": {
                "retrieval_invocation_id": retrieval_invocation_id,
                "resolver_invocation_id": "RIVR-001",
                "retrieval_snapshot_sha256": sha,
                "resolver_snapshot_sha256": resolver_sha,
            },
            "created_at": "2026-09-05T00:00:00Z",
        }
        invocation = {
            "resolver_invocation_id": "RIVR-001",
            "candidate_pointer_id": candidate_pointer["candidate_pointer_id"],
        }
        return evidence, invocation, {"sha256": resolver_sha, "bytes": ""}

    monkeypatch.setattr(live_chain_module.CrossrefRetrievalProvider, "discover", fake_discover)
    monkeypatch.setattr(live_chain_module.CrossrefReferenceResolver, "resolve", fake_resolve)


def test_discovery_stops_before_selection_and_resolution(monkeypatch):
    _install_fake_crossref(monkeypatch)
    execution = prepared()
    _, discovery = execution.discover()
    assert discovery["execution_boundary"] == "STOP_AWAITING_SELECTION_ARTIFACT"
    assert discovery["rung_candidate_sets"][0]["candidate_count"] == 2
    assert "canonical_evidence" not in discovery


def test_explicit_rank_two_selection_preserves_resolver_continuity(monkeypatch):
    _install_fake_crossref(monkeypatch)
    execution = prepared()
    chain, discovery = execution.discover()
    selection = SelectionArtifact.from_discovery(
        selection_id="SEL-002",
        discovery=discovery,
        rendering_path="legacy_pubmed_ebsco_query",
        selected_candidate_pointer_id="CP-002",
        selection_authority="external-test-operator",
        selection_reason="Candidate title is semantically aligned with the route.",
        provenance={"decision_record": "unit-test"},
    )
    result = execution.resolve_selected(
        chain=chain, discovery=discovery, selection=selection
    )
    assert result["status"] == "ok"
    assert result["selected_candidate_pointer_id"] == "CP-002"
    assert result["selected_candidate_rank"] == 2
    assert result["resolver_invocation"]["candidate_pointer_id"] == "CP-002"
    assert result["selection_lineage_status"] == "PASS"
    assert validate_against_schema(
        selection.to_dict(), "post_p1p5/selection_artifact.schema.json"
    ) == []


def test_selection_rejects_candidate_not_observed(monkeypatch):
    _install_fake_crossref(monkeypatch)
    _, discovery = prepared().discover()
    with pytest.raises(SemanticBoundaryError, match="not in the observed set"):
        SelectionArtifact.from_discovery(
            selection_id="SEL-003",
            discovery=discovery,
            rendering_path="legacy_pubmed_ebsco_query",
            selected_candidate_pointer_id="CP-999",
            selection_authority="external-test-operator",
            selection_reason="Invalid test selection.",
            provenance={"decision_record": "unit-test"},
        )
