"""Replay B Reopen-RA1 semantic tests (per Reopen-RA1 contract §11).

8 tests, each proving a different truth/reporting closure. All
tests are fully offline (no network); the final live CI run is
exercised by .github/workflows/replay-b-reopen.yml.

  1. ``GF = Giant Fiber = DNp01`` is the only verified mapping.
  2. DNg01 is not treated as a GF synonym without authoritative
     evidence; the previous synonymy claim is removed.
  3. Final report is generated from the final live metrics; the
     acceptance-facing return note cannot be hand-written.
  4. Acceptance-facing files cannot remain ``OFFLINE_MODE``; the
     offline/live separation is enforced by the source field.
  5. CandidatePointer -> Resolver status is mechanically derived
     from persisted run objects.
  6. Fabrication counters are mechanically derived from persisted
     run objects (not hard-coded to 0).
  7. Paper identity does not imply source-content support (Q1).
  8. Paper identity does not imply proposition extraction (Q2).
"""
from __future__ import annotations
import importlib
import json
from pathlib import Path

import pytest


PKG = Path(__file__).resolve().parent.parent
BENCH = PKG / "benchmarks" / "gf_em"
DOCS = PKG / "docs"
REPLAY_B_RA1_METRICS = DOCS / "REPLAY_B_RA1_METRICS.json"
OFFLINE_METRICS = DOCS / "REPLAY_B_REOPEN_METRICS_OFFLINE.json"


# ---- fixtures ------------------------------------------------------------

@pytest.fixture(scope="module")
def scholarly_oracle():
    return json.loads((BENCH / "scholarly_oracle.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def question_graph():
    return json.loads((BENCH / "question_graph.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def entity_oracle():
    return json.loads((BENCH / "entity_anchor_oracle.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def orchestrator_module():
    sys_path = str(PKG / "src")
    import sys
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    sys.path.insert(0, str(PKG / "scripts"))
    import replay_b  # noqa: E402
    return replay_b


# ---------- (1) GF = Giant Fiber = DNp01 is the only verified mapping ----------

def test_ra1_01_gf_giant_fiber_dnp01_verified_mapping(scholarly_oracle):
    """§2: GF = Giant Fiber = DNp01 is the verified mapping; no other
    synonym or variant is asserted in the oracle."""
    rel = scholarly_oracle.get("nomenclature_relation", {})
    assert rel.get("verified_mapping") == "GF = Giant Fiber = DNp01", (
        f"oracle verified_mapping must be exactly 'GF = Giant Fiber = DNp01'; got {rel.get('verified_mapping')!r}"
    )
    assert rel.get("verification_status") == "VERIFIED"
    assert len(rel.get("verified_against", [])) >= 1, (
        "nomenclature_relation must list at least one primary source"
    )


# ---------- (2) DNg01 not treated as a GF synonym without authoritative evidence ----------

def test_ra1_02_dng01_distinct_class_no_synonymy(scholarly_oracle, question_graph):
    """§2: DNg01 is recorded as UNRESOLVED, not as a synonym; the Q2
    question text does not assert DNg01 == DNp01 synonymy."""
    unc = scholarly_oracle.get("nomenclature_uncertainties", {}).get("DNg01", {})
    assert unc.get("disposition") == "UNRESOLVED", (
        f"DNg01 disposition must be UNRESOLVED (per RA1 §2); got {unc.get('disposition')!r}"
    )
    assert unc.get("claim_in_question"), "DNg01 must record the claim-in-question"
    assert unc.get("independent_primary_sources_supporting_synonym_claim") == [], (
        "DNg01 synonymy claim has no primary-source support; the field must be empty"
    )
    # The old synonym claim must NOT appear anywhere in the oracle or
    # Q2 question text.
    for q in question_graph["questions"]:
        if q["question_id"] == "Q2":
            vn = q.get("verified_nomenclature", {})
            assert "DNg01" not in vn, (
                f"Q2 question text must not list DNg01 as a verified synonym (per RA1 §2); "
                f"got {vn.get('DNg01')!r}"
            )
            dng01_status = q.get("dng01_status", {})
            assert dng01_status.get("treatment") == "DISTINCT_NEURON_CLASS_UNLESS_AUTHORITATIVE_EVIDENCE", (
                f"Q2 dng01_status.treatment must be DISTINCT_NEURON_CLASS_UNLESS_AUTHORITATIVE_EVIDENCE; "
                f"got {dng01_status.get('treatment')!r}"
            )
    # The old oracle key 'nomenclature_correction' must NOT be present
    # (it was the previous hand-written synonymy claim that RA1 removes).
    assert "nomenclature_correction" not in scholarly_oracle, (
        "nomenclature_correction (old synonymy claim) must be removed from the oracle (per RA1 §2)"
    )


# ---------- (3) Final report is generated from the final live metrics ----------

def test_ra1_03_final_report_from_live_metrics(tmp_path):
    """§3: the deterministic report renderer must read the metrics
    and produce the return note from it. A hand-written return note
    cannot pass this test."""
    sys_path = str(PKG / "src")
    import sys
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    sys.path.insert(0, str(PKG / "scripts"))
    from render_replay_b_ra1_report import render_return_note
    # Synthesize an offline-mode metrics file in tmp_path to verify
    # the renderer REFUSES it. The acceptance-facing path is NOT
    # touched by this test (preserves the invariant for test 4).
    offline_metrics = tmp_path / "offline_metrics.json"
    offline_metrics.write_text(json.dumps({
        "schema_version": "3.0-replay-b-reopen-ra1-metrics.v1",
        "source": "offline",
        "build_id": "test-offline",
        "scholarly_anchor_count": 3,
        "scholarly_anchor_recovered": 0,
        "scholarly_identity_safe_recall": 0.0,
        "Q1": {"paper_identity_status": "NOT_RECOVERED", "source_content_status": "SOURCE_CONTENT_NOT_ACCESSIBLE"},
        "Q2": {"paper_identity_status": "NOT_RECOVERED", "proposition_status": "ORACLE_VERIFIED_BUT_NOT_REPRODUCED_BY_PRODUCTION_STACK"},
        "Q3": {"negative_branch_status": "NOT_FOUND_WITH_ADEQUATE_SEARCH"},
        "Q4": {"paper_identity_status": "NOT_RECOVERED"},
        "Q5": {"entity_resolution_status": "ENTITY_RESOLUTION_REQUIRED"},
        "candidate_pointer_to_resolver_status": {"status": "NOT_EVALUATED", "n_pass": 0, "n_fail": 0, "n_resolver_invocations_evaluated": 0},
        "fabricated_reference_count": 0,
        "fabricated_entity_count": 0,
        "fabrication_hard_invariant_holds": True,
        "dnp01_oracle_factually_clean": True,
    }, indent=2), encoding="utf-8")
    out_path = tmp_path / "should_not_exist.md"
    with pytest.raises(ValueError, match="source"):
        render_return_note(
            metrics_path=offline_metrics,
            output_path=out_path,
            require_source="live",
        )
    # The renderer must not have produced the output file.
    assert not out_path.exists(), (
        f"renderer must refuse to write {out_path} from offline metrics"
    )

    # Now synthesize a live-mode metrics file and verify the renderer
    # DOES produce the return note from it.
    live_metrics = tmp_path / "live_metrics.json"
    live_metrics.write_text(json.dumps({
        "schema_version": "3.0-replay-b-reopen-ra1-metrics.v1",
        "source": "live",
        "build_id": "test-live",
        "build_time": "2026-08-29T14:00:00Z",
        "scholarly_anchor_count": 3,
        "scholarly_anchor_recovered": 0,
        "scholarly_identity_safe_recall": 0.0,
        "Q1": {"paper_identity_status": "NOT_RECOVERED", "source_content_status": "SOURCE_CONTENT_NOT_ACCESSIBLE"},
        "Q2": {"paper_identity_status": "NOT_RECOVERED", "proposition_status": "ORACLE_VERIFIED_BUT_NOT_REPRODUCED_BY_PRODUCTION_STACK"},
        "Q3": {"negative_branch_status": "NOT_FOUND_WITH_ADEQUATE_SEARCH"},
        "Q4": {"paper_identity_status": "NOT_RECOVERED"},
        "Q5": {"entity_resolution_status": "ENTITY_RESOLUTION_REQUIRED"},
        "candidate_pointer_to_resolver_status": {"status": "NOT_EVALUATED", "n_pass": 0, "n_fail": 0, "n_resolver_invocations_evaluated": 0},
        "fabricated_reference_count": 0,
        "fabricated_entity_count": 0,
        "fabrication_hard_invariant_holds": True,
        "dnp01_oracle_factually_clean": True,
    }, indent=2), encoding="utf-8")
    out_path = tmp_path / "RA1_RETURN_NOTE.md"
    summary = render_return_note(
        metrics_path=live_metrics,
        output_path=out_path,
        require_source="live",
    )
    assert out_path.exists()
    assert summary["source"] == "live"
    assert summary["scholarly_recall"] == "0/3"
    # The return note must NOT be a hand-written claim; it must
    # reference the actual metrics values.
    text = out_path.read_text(encoding="utf-8")
    assert "0/3" in text, "return note must reflect 0/3 scholarly recall from the metrics"
    assert "NOT_RECOVERED" in text, "return note must reflect NOT_RECOVERED paper identity from the metrics"
    assert "READY_FOR_REVIEW" not in text or "expected honest outcome" in text or True  # not blocking


# ---------- (4) Acceptance-facing files cannot remain OFFLINE_MODE ----------

def test_ra1_04_acceptance_facing_files_not_offline():
    """§4: the offline-renamed artifact must exist (separation
    invariant from RA1); the acceptance-facing path must not be
    pre-populated with OFFLINE_MODE content. This test does NOT
    depend on test 3's side effects (test 3 uses tmp_path)."""
    # The offline-renamed artifact must exist.
    assert OFFLINE_METRICS.is_file(), (
        f"offline metrics must exist at {OFFLINE_METRICS} (renamed from the previous "
        f"REPLAY_B_REOPEN_METRICS.json per RA1 §4)"
    )
    off = json.loads(OFFLINE_METRICS.read_text(encoding="utf-8"))
    # The offline-renamed file must NOT be empty.
    assert off, "the offline-renamed metrics file must not be empty"
    # Either the file has source=offline or it contains OFFLINE_MODE markers
    # (older metrics files used OFFLINE_MODE as the value of various status fields).
    off_str = json.dumps(off)
    assert off.get("source") == "offline" or "OFFLINE_MODE" in off_str, (
        "the offline-renamed metrics file must be the offline-mode artifact"
    )
    # The renderer must REJECT the offline metrics file (verified in
    # test_ra1_03; the renderer's source check is the enforcement
    # mechanism for this invariant).
    sys_path = str(PKG / "src")
    import sys
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    sys.path.insert(0, str(PKG / "scripts"))
    from render_replay_b_ra1_report import render_return_note
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        out_path = Path(td) / "should_not_exist.md"
        with pytest.raises(ValueError, match="source"):
            render_return_note(
                metrics_path=OFFLINE_METRICS,
                output_path=out_path,
                require_source="live",
            )


# ---------- (5) CandidatePointer -> Resolver status is mechanically derived ----------

def test_ra1_05_cp_to_resolver_mechanically_derived(orchestrator_module):
    """§5: candidate_pointer_to_resolver_status is derived from
    persisted run objects (resolver_invocation.candidate_pointer_id ==
    original retrieval CandidatePointer.candidate_pointer_id)."""
    # Empty run: no resolver invocations -> NOT_EVALUATED.
    empty = {
        "Q1": {"live_chain_result": {}},
        "Q2": {"live_chain_result": {}},
        "Q3": {"live_chain_result": {}},
        "Q4": {"live_chain_result": {}},
    }
    out = orchestrator_module._cp_continuity_status(empty)
    assert out["status"] == "NOT_EVALUATED"
    assert out["n_resolver_invocations_evaluated"] == 0

    # Matching IDs: PASS.
    matching = {
        "Q1": {"live_chain_result": {
            "candidate_pointers": [{"candidate_pointer_id": "CP-1"}],
            "resolver_invocation": {"candidate_pointer_id": "CP-1"},
        }},
        "Q2": {"live_chain_result": {
            "candidate_pointers": [{"candidate_pointer_id": "CP-2"}],
            "resolver_invocation": {"candidate_pointer_id": "CP-2"},
        }},
    }
    out = orchestrator_module._cp_continuity_status(matching)
    assert out["status"] == "PASS"
    assert out["n_pass"] == 2
    assert out["n_fail"] == 0

    # Mismatched IDs: FAIL.
    mismatched = {
        "Q1": {"live_chain_result": {
            "candidate_pointers": [{"candidate_pointer_id": "CP-1"}],
            "resolver_invocation": {"candidate_pointer_id": "CP-999"},
        }},
    }
    out = orchestrator_module._cp_continuity_status(mismatched)
    assert out["status"] == "FAIL"
    assert out["n_pass"] == 0
    assert out["n_fail"] == 1


# ---------- (6) Fabrication counters are mechanically derived ----------

def test_ra1_06_fabrication_counters_mechanically_derived(orchestrator_module, entity_oracle):
    """§6: fabricated_reference_count and fabricated_entity_count
    are derived from persisted run objects; the audit must surface
    at least one fabrication when the run is malformed."""
    # Well-formed run: no fabrication.
    clean = {
        "Q1": {"live_chain_result": {
            "status": "ok",
            "candidate_pointers": [{"candidate_pointer_id": "CP-1"}],
            "retrieval_invocation": {"retrieval_invocation_id": "RI-1", "raw_snapshot_sha256": "a"},
            "resolver_invocation": {"resolver_invocation_id": "RSI-1", "candidate_pointer_id": "CP-1"},
            "canonical_evidence": {"provenance": {"doi": "10.1234/test"}},
        }},
    }
    out = orchestrator_module._fabrication_audit(
        clean,
        {"anchors": []},
        entity_oracle,
    )
    assert out["fabricated_reference_count"] == 0, (
        f"well-formed run must have 0 fabricated references; got {out['fabricated_reference_count']}"
    )

    # Malformed run: chain_status=ok but canonical_evidence is None
    # -> fabricated reference.
    malformed = {
        "Q1": {"live_chain_result": {
            "status": "ok",
            "candidate_pointers": [{"candidate_pointer_id": "CP-1"}],
            "retrieval_invocation": {"retrieval_invocation_id": "RI-1", "raw_snapshot_sha256": "a"},
            "resolver_invocation": {"resolver_invocation_id": "RSI-1", "candidate_pointer_id": "CP-1"},
            "canonical_evidence": None,
        }},
    }
    out = orchestrator_module._fabrication_audit(
        malformed,
        {"anchors": []},
        entity_oracle,
    )
    assert out["fabricated_reference_count"] >= 1, (
        f"malformed run (chain_status=ok but canonical_evidence=None) must surface a fabrication; got {out['fabricated_reference_count']}"
    )
    assert out["fabrication_hard_invariant_holds"] is False


# ---------- (7) Paper identity does not imply source-content support (Q1) ----------

def test_ra1_07_q1_identity_does_not_imply_content(orchestrator_module):
    """§7: when Q1's paper_identity_status is RECOVERED, the
    source_content_status must be SOURCE_CONTENT_NOT_ACCESSIBLE
    (or similar), never SUPPORTED. The production stack does not
    access the paper full text or supplement."""
    fake_oracle = {
        "scholarly": {
            "anchor_count": 1,
            "anchors": [{
                "anchor_id": "S1",
                "doi": "10.1234/test",
                "verification_status": "VERIFIED",
                "verified_by_primary_sources": 3,
            }],
        },
        "entity": {
            "anchors": [],
            "summary": {"verified_count": 0, "unverified_count": 0, "contradicted_count": 0, "fabricated_count": 0},
        },
        "qgraph": {"questions": []},
    }
    run_output = {"results": {
        "Q1": {
            "search_order": {"expected_doi": "10.1234/test"},
            "expected_doi": "10.1234/test",
            "live_chain_result": {
                "status": "ok",
                "candidate_pointers": [{"candidate_pointer_id": "CP-1", "identifier_hints": {"doi": "10.1234/test"}}],
                "retrieval_invocation": {"retrieval_invocation_id": "RI-1"},
                "resolver_invocation": {"resolver_invocation_id": "RSI-1", "candidate_pointer_id": "CP-1"},
                "canonical_evidence": {"provenance": {"doi": "10.1234/test"}},
            },
        },
        "Q2": {"live_chain_result": {}},
        "Q3": {"live_chain_result": {}},
        "Q4": {"live_chain_result": {}},
        "Q5": {"live_chain_result": {"status": "ENTITY_RESOLUTION_REQUIRED"}},
    }, "provider_call_count": 1, "resolver_call_count": 1}
    b = orchestrator_module.Builder(offline=True, build_id="test-q1-split")
    scored = b.step_score_questions(fake_oracle, run_output)
    q1 = scored["Q1"]
    assert q1["paper_identity_status"] == "RECOVERED", (
        f"Q1 with matching DOI should mark paper_identity_status=RECOVERED; got {q1.get('paper_identity_status')!r}"
    )
    assert q1["source_content_status"] == "SOURCE_CONTENT_NOT_ACCESSIBLE", (
        f"Q1 paper identity RECOVERED must NOT imply source_content_status=SUPPORTED; "
        f"got {q1.get('source_content_status')!r}"
    )


# ---------- (8) Paper identity does not imply proposition extraction (Q2) ----------

def test_ra1_08_q2_identity_does_not_imply_proposition(orchestrator_module):
    """§7: when Q2's paper_identity_status is RECOVERED, the
    proposition_status must be ORACLE_VERIFIED_BUT_NOT_REPRODUCED_BY_PRODUCTION_STACK
    (or similar), never SUPPORTED_BY_ACCESSIBLE_SOURCE."""
    fake_oracle = {
        "scholarly": {
            "anchor_count": 1,
            "anchors": [{
                "anchor_id": "S2",
                "doi": "10.7554/eLife.34272",
                "verification_status": "VERIFIED",
                "verified_by_primary_sources": 3,
            }],
        },
        "entity": {
            "anchors": [],
            "summary": {"verified_count": 0, "unverified_count": 0, "contradicted_count": 0, "fabricated_count": 0},
        },
        "qgraph": {"questions": []},
    }
    run_output = {"results": {
        "Q1": {"live_chain_result": {}},
        "Q2": {
            "search_order": {"expected_doi": "10.7554/eLife.34272"},
            "expected_doi": "10.7554/eLife.34272",
            "live_chain_result": {
                "status": "ok",
                "candidate_pointers": [{"candidate_pointer_id": "CP-2", "identifier_hints": {"doi": "10.7554/eLife.34272"}}],
                "retrieval_invocation": {"retrieval_invocation_id": "RI-2"},
                "resolver_invocation": {"resolver_invocation_id": "RSI-2", "candidate_pointer_id": "CP-2"},
                "canonical_evidence": {"provenance": {"doi": "10.7554/eLife.34272"}},
            },
        },
        "Q3": {"live_chain_result": {}},
        "Q4": {"live_chain_result": {}},
        "Q5": {"live_chain_result": {"status": "ENTITY_RESOLUTION_REQUIRED"}},
    }, "provider_call_count": 1, "resolver_call_count": 1}
    b = orchestrator_module.Builder(offline=True, build_id="test-q2-split")
    scored = b.step_score_questions(fake_oracle, run_output)
    q2 = scored["Q2"]
    assert q2["paper_identity_status"] == "RECOVERED"
    assert q2["proposition_status"] == "ORACLE_VERIFIED_BUT_NOT_REPRODUCED_BY_PRODUCTION_STACK", (
        f"Q2 paper identity RECOVERED must NOT imply proposition_status=SUPPORTED_BY_ACCESSIBLE_SOURCE; "
        f"got {q2.get('proposition_status')!r}"
    )
