from __future__ import annotations

import pytest

from mafs_p0.evidence_resolution import (
    EvidenceResolutionSession,
    InMemorySourceAdapter,
    PropositionRequest,
    SourceMaterial,
)
from mafs_p0.epistemic_route import SemanticBoundaryError
from mafs_p0.validator import validate_against_schema


def canonical(doi: str = "10.5555/test.paper", title: str = "A Test Paper") -> dict:
    return {
        "schema_version": "3.0-p1",
        "evidence_id": "CE-001",
        "candidate_pointer_id": "CP-001",
        "canonical": {
            "title": title,
            "authors": ["Test Author"],
            "year": 2025,
            "venue": "Test Journal",
            "doi": doi,
            "source_locator": f"https://doi.org/{doi}",
            "resolver_identity": "test_resolver",
        },
        "provenance": {
            "retrieval_invocation_id": "RIV-001",
            "resolver_invocation_id": "RIVR-001",
            "retrieval_snapshot_sha256": "a" * 64,
            "resolver_snapshot_sha256": "b" * 64,
        },
        "created_at": "2026-09-05T00:00:00Z",
    }


def session_with_content(content: str) -> tuple[EvidenceResolutionSession, InMemorySourceAdapter]:
    material = SourceMaterial(
        canonical_identity={"doi": "10.5555/test.paper", "title": "A Test Paper", "year": 2025},
        representation_type="ABSTRACT",
        locator="https://example.invalid/abstract",
        content=content,
        access_provenance={"adapter": "fixture", "lawful_access": "test_fixture"},
    )
    adapter = InMemorySourceAdapter({"doi:10.5555/test.paper": material})
    return EvidenceResolutionSession((adapter,)), adapter


def test_source_document_is_reused_at_paper_level():
    session, adapter = session_with_content("The experiment reported a significant improvement.")
    first = session.resolve_source(canonical())
    second = session.resolve_source(canonical())
    assert first is second
    assert adapter.fetch_count == 1
    assert session.source_fetches == 1
    assert session.source_cache_hits == 1
    assert validate_against_schema(first.to_dict(), "post_p1p5/source_document.schema.json") == []


def test_source_identity_mismatch_is_rejected():
    wrong = SourceMaterial(
        canonical_identity={"doi": "10.5555/wrong.paper"},
        representation_type="ABSTRACT",
        locator="https://example.invalid/wrong",
        content="Wrong source content.",
        access_provenance={"adapter": "fixture"},
    )
    session = EvidenceResolutionSession(
        (InMemorySourceAdapter({"doi:10.5555/test.paper": wrong}),)
    )
    with pytest.raises(SemanticBoundaryError, match="identity mismatch"):
        session.resolve_source(canonical())


def test_abstract_source_can_produce_citable_span_without_full_text():
    sentence = "The experiment reported a significant improvement in retrieval accuracy."
    session, _ = session_with_content(f"Background. {sentence} Limitations follow.")
    document = session.resolve_source(canonical())
    span = session.create_span(
        source_document=document, text=sentence, evidence_role="STATISTICAL_RESULT"
    )
    request = PropositionRequest(
        proposition_id="PROP-1",
        text="Did the experiment report a significant improvement?",
        expected_source_document_id=document.source_document_id,
        required_evidence_roles=("RESULT", "STATISTICAL_RESULT"),
        requires_statistical_result=True,
    )
    evidence = session.adjudicate(
        request=request,
        source_document=document,
        spans=(span,),
        relation="SUPPORTS",
        sufficiency_rationale="The abstract explicitly reports the requested significant result.",
        uncertainty="Low; the span states the result directly.",
    )
    assert document.source_representation_type == "ABSTRACT"
    assert evidence.grounding_status == "CITABLE_SPAN"
    assert validate_against_schema(span.to_dict(), "post_p1p5/evidence_span.schema.json") == []
    assert validate_against_schema(
        evidence.to_dict(), "post_p1p5/proposition_evidence.schema.json"
    ) == []


def test_full_text_to_evidence_span_to_proposition_evidence_hermetic_checkpoint():
    result_sentence = (
        "The intervention increased retrieval accuracy by 12.4 percentage points "
        "(p = 0.003)."
    )
    material = SourceMaterial(
        canonical_identity={
            "doi": "10.5555/test.paper",
            "title": "A Test Paper",
            "year": 2025,
        },
        representation_type="FULL_TEXT",
        locator="memory://fixtures/test-paper/full-text",
        content=(
            "Introduction. Prior work motivates the intervention. "
            "Results. " + result_sentence + " Discussion. The result is limited to this dataset."
        ),
        access_provenance={
            "adapter": "hermetic_full_text_fixture",
            "lawful_access": "test_fixture",
            "network_access": False,
        },
    )
    adapter = InMemorySourceAdapter({"doi:10.5555/test.paper": material})
    session = EvidenceResolutionSession((adapter,))

    document = session.resolve_source(canonical())
    span = session.create_span(
        source_document=document,
        text=result_sentence,
        evidence_role="STATISTICAL_RESULT",
    )
    request = PropositionRequest(
        proposition_id="PROP-FULL-TEXT-1",
        text="Did the intervention significantly improve retrieval accuracy?",
        expected_source_document_id=document.source_document_id,
        required_evidence_roles=("STATISTICAL_RESULT",),
        requires_statistical_result=True,
    )
    evidence = session.adjudicate(
        request=request,
        source_document=document,
        spans=(span,),
        relation="SUPPORTS",
        sufficiency_rationale=(
            "The full-text result states the improvement magnitude and p-value explicitly."
        ),
        uncertainty="Low; the exact result sentence directly answers the proposition.",
        adjudication_authority="hermetic_test_checkpoint",
    )

    assert adapter.fetch_count == 1
    assert session.source_fetches == 1
    assert document.source_representation_type == "FULL_TEXT"
    assert document.source_integrity_status == "VERIFIED_IDENTITY_MATCH"
    assert span.text == result_sentence
    assert span.span_integrity_status == "VERIFIED_EXACT_SUBSTRING"
    assert evidence.relation == "SUPPORTS"
    assert evidence.grounding_status == "CITABLE_SPAN"
    assert evidence.span_ids == (span.span_id,)
    assert evidence.provenance["model_prior_used_as_evidence"] is False
    assert validate_against_schema(
        document.to_dict(), "post_p1p5/source_document.schema.json"
    ) == []
    assert validate_against_schema(
        span.to_dict(), "post_p1p5/evidence_span.schema.json"
    ) == []
    assert validate_against_schema(
        evidence.to_dict(), "post_p1p5/proposition_evidence.schema.json"
    ) == []


def test_background_statement_cannot_satisfy_result_requirement():
    session, _ = session_with_content("Prior work generally assumes the effect exists.")
    document = session.resolve_source(canonical())
    span = session.create_span(
        source_document=document,
        text="Prior work generally assumes the effect exists.",
        evidence_role="BACKGROUND",
    )
    request = PropositionRequest(
        proposition_id="PROP-2",
        text="Did this experiment demonstrate the effect?",
        required_evidence_roles=("RESULT", "STATISTICAL_RESULT"),
    )
    with pytest.raises(SemanticBoundaryError, match="role is insufficient"):
        session.adjudicate(
            request=request,
            source_document=document,
            spans=(span,),
            relation="SUPPORTS",
            sufficiency_rationale="Invalid background-only reasoning.",
            uncertainty="High.",
        )


def test_raw_counts_cannot_establish_statistical_significance():
    session, _ = session_with_content("There were 84 events in one group and 91 in another.")
    document = session.resolve_source(canonical())
    span = session.create_span(
        source_document=document,
        text="There were 84 events in one group and 91 in another.",
        evidence_role="RESULT",
    )
    request = PropositionRequest(
        proposition_id="PROP-3",
        text="Was the difference statistically significant?",
        requires_statistical_result=True,
    )
    with pytest.raises(SemanticBoundaryError, match="statistical significance"):
        session.adjudicate(
            request=request,
            source_document=document,
            spans=(span,),
            relation="SUPPORTS",
            sufficiency_rationale="Counts alone are insufficient.",
            uncertainty="High.",
        )


def test_indirect_implication_cannot_establish_explicit_result():
    session, _ = session_with_content("A related measurement changed after treatment.")
    document = session.resolve_source(canonical())
    span = session.create_span(
        source_document=document,
        text="A related measurement changed after treatment.",
        evidence_role="RESULT",
    )
    request = PropositionRequest(
        proposition_id="PROP-4",
        text="Did the paper explicitly report the target mechanism?",
        explicit_only=True,
    )
    with pytest.raises(SemanticBoundaryError, match="indirect implication"):
        session.adjudicate(
            request=request,
            source_document=document,
            spans=(span,),
            relation="SUPPORTS",
            sufficiency_rationale="Only an indirect implication is available.",
            uncertainty="High.",
            inference_mode="INDIRECT",
        )


def test_model_prior_without_span_is_not_grounded():
    session, _ = session_with_content("No relevant result appears here.")
    document = session.resolve_source(canonical())
    request = PropositionRequest(proposition_id="PROP-5", text="Is the claim supported?")
    with pytest.raises(SemanticBoundaryError, match="model prior"):
        session.adjudicate(
            request=request,
            source_document=document,
            spans=(),
            relation="SUPPORTS",
            sufficiency_rationale="The model remembers the answer.",
            uncertainty="Unknown.",
        )


@pytest.mark.parametrize("state", ["NOT_ADDRESSED", "AMBIGUOUS"])
def test_negative_or_uncertain_grounding_states_remain_first_class(state: str):
    session, _ = session_with_content("The source does not resolve the proposition.")
    document = session.resolve_source(canonical())
    request = PropositionRequest(proposition_id="PROP-6", text="Is claim Z established?")
    evidence = session.ungrounded(
        request=request,
        source_document=document,
        grounding_status=state,
        rationale="No minimally sufficient source span establishes the relation.",
        uncertainty="The paper may address a nearby but different question.",
    )
    assert evidence.relation == "NOT_GROUNDED"
    assert evidence.span_ids == ()
    assert validate_against_schema(
        evidence.to_dict(), "post_p1p5/proposition_evidence.schema.json"
    ) == []


def test_inaccessible_source_is_honest_terminal_state():
    session = EvidenceResolutionSession(())
    document = session.resolve_source(canonical())
    request = PropositionRequest(proposition_id="PROP-7", text="Is claim Z established?")
    evidence = session.ungrounded(
        request=request,
        source_document=document,
        grounding_status="SOURCE_CONTENT_NOT_ACCESSIBLE",
        rationale="No lawful accessible representation was located.",
        uncertainty="The source content was not inspected.",
    )
    assert document.source_representation_type == "INACCESSIBLE"
    assert evidence.relation == "NOT_GROUNDED"
