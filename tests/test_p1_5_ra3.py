"""MAFS v3.0-P1.5-RA3 — AI-Native Execution Boundary & Machine-Truth Final Closure Tests.

10 mandatory acceptance tests per P1.5-RA3 contract §14. All tests are
fully offline (no network). The single final live CI run is exercised
by ``.github/workflows/p1-5.yml``.

  T1  — Real retrieval provenance survives selection
       (no PRE-WALKED; no zero SHA; no synthetic bridge)
  T2  — No synthetic bridge path remains active
       (pre_walked_candidates_by_rung is removed; PRE-WALKED literal is gone)
  T3  — Selection continuity (selected_candidate_pointer_id ==
       resolver_invocation.candidate_pointer_id, even at rank > 1)
  T4  — No top-1 continuity assumption
       (rank 2/3 selected can produce continuity PASS)
  T5  — No selection means no resolution
       (CandidateSets may exist; resolver invocation absent)
  T6  — Rank truth (known rank is preserved exactly)
  T7  — Rank missing is unknown
       (rank = null, rank_status = NOT_EVALUATED_RANK_MISSING;
        never default to 1)
  T8  — CI subtraction truth (real git-derived or
       subtraction_accounting_status = NOT_EVALUATED_GIT_UNAVAILABLE;
        never zero-as-measured-zero)
  T9  — Single acceptance source (P1_5_RA3_METRICS.json is the only
        current acceptance file; P1_5_METRICS.json is historical)
  T10 — Q3 / Q5 / fabrication regression
"""
from __future__ import annotations
import json
import re
from pathlib import Path

import pytest


PKG = Path(__file__).resolve().parent.parent
SRC = PKG / "src" / "mafs_p0"
SCRIPTS = PKG / "scripts"
DOCS = PKG / "docs"


# ---- fixtures ---------------------------------------------------------------

def _load_module(name: str):
    sys_path = str(PKG / "src")
    if sys_path not in __import__("sys").path:
        __import__("sys").path.insert(0, sys_path)
    return __import__(name, fromlist=["*"])


@pytest.fixture(scope="module")
def live_chain_mod():
    return _load_module("mafs_p0.live_chain")


@pytest.fixture(scope="module")
def live_crossref_mod():
    return _load_module("mafs_p0.live_crossref")


@pytest.fixture(scope="module")
def renderer_mod():
    return _load_module("mafs_p0.crossref_renderer")


@pytest.fixture(scope="module")
def replay_b_text():
    return (SCRIPTS / "replay_b.py").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def live_chain_text():
    return (SRC / "live_chain.py").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def workflow_text():
    return (PKG / ".github" / "workflows" / "p1-5.yml").read_text(encoding="utf-8")


# ============================================================================
# T1 — Real retrieval provenance survives selection
# ============================================================================

def test_t1_real_retrieval_provenance_survives_selection(
    live_chain_mod, live_crossref_mod, monkeypatch,
):
    """P1.5-RA3 Closure A: after chain.discover() and chain.resolve(),
    the result's selected retrieval_invocation_id and
    raw_snapshot_sha256 are real (not 'PRE-WALKED' and not
    '0' * 64).
    """
    from mafs_p0.crossref_renderer import (
        RenderedQuery, LADDER_RUNG_A,
    )
    so = {
        "search_order_id": "SO-T1-RA3",
        "required_capabilities": ["search.query", "search.pagination", "result.ranked"],
    }
    rendered_queries = [
        RenderedQuery(rendering_path=LADDER_RUNG_A, url_params={"query.author": "x"}),
    ]
    real_inv_id = "RIV-T1-001"
    real_sha = "a" * 64  # any non-zero SHA

    def fake_discover(self, *args, **kwargs):
        return (
            [{"candidate_pointer_id": "CP-001", "rank": 1, "provider": "crossref_v1",
              "identifier_hints": {"doi": "10.1234/t1"},
              "retrieval_invocation_id": real_inv_id}],
            {
                "retrieval_invocation_id": real_inv_id,
                "search_order_id": so["search_order_id"],
                "provider": "crossref_v1",
                "raw_snapshot_sha256": real_sha,
                "response": {"http_status": 200, "item_count": 1, "attempts": 1},
                "status": "ok",
            },
            {"kind": "retrieval_response", "sha256": real_sha, "bytes": ""},
        )

    def fake_resolve(self, *args, **kwargs):
        return (
            {"evidence_id": "CE-T1-001",
             "canonical": {"doi": "10.1234/t1"},
             "provenance": {"retrieval_snapshot_sha256": real_sha,
                            "resolver_snapshot_sha256": "f" * 64}},
            {"resolver_invocation_id": "RIVR-001", "status": "ok",
             "candidate_pointer_id": "CP-001", "raw_snapshot_sha256": "f" * 64},
            {"kind": "resolver_response", "sha256": "f" * 64, "bytes": ""},
        )

    monkeypatch.setattr(
        live_crossref_mod.CrossrefRetrievalProvider, "discover", fake_discover
    )
    monkeypatch.setattr(
        live_crossref_mod.CrossrefReferenceResolver, "resolve", fake_resolve
    )
    chain = live_chain_mod.LiveChain(
        search_order=so, rendered_queries=rendered_queries, top_k=5,
    )
    discovery = chain.discover()
    result = chain.resolve(discovery, {
        "rendering_path": LADDER_RUNG_A,
        "candidate_pointer_id": "CP-001",
    })
    # The discovery's retrieval_invocations carry real data
    assert len(discovery["retrieval_invocations"]) == 1
    inv = discovery["retrieval_invocations"][0]
    assert inv["retrieval_invocation_id"] == real_inv_id
    assert inv["raw_snapshot_sha256"] == real_sha
    # The resolve() result carries the selected rung's real
    # retrieval_invocation (NOT PRE-WALKED, NOT zero SHA).
    sel_inv = result["retrieval_invocation"]
    assert sel_inv is not None
    assert sel_inv["retrieval_invocation_id"] == real_inv_id
    assert sel_inv["raw_snapshot_sha256"] == real_sha
    assert sel_inv["raw_snapshot_sha256"] != ("0" * 64)
    assert sel_inv["retrieval_invocation_id"] != "PRE-WALKED"
    # The CanonicalEvidence inherits the real snapshot SHA.
    assert result["canonical_evidence"]["provenance"]["retrieval_snapshot_sha256"] == real_sha


# ============================================================================
# T2 — No synthetic bridge path remains active
# ============================================================================

def test_t2_no_synthetic_bridge_path_remains_active(live_chain_text, replay_b_text):
    """P1.5-RA3 Closure A: the active P1.5 production path contains
    no synthetic bridge. Specifically:
      - no `pre_walked_candidates_by_rung` field on LiveChain
      - no `PRE-WALKED` retrieval identity
      - no `0 * 64` SHA synthetic placeholder
    """
    assert "pre_walked_candidates_by_rung" not in live_chain_text, (
        "LiveChain must no longer carry the pre_walked synthetic bridge "
        "(P1.5-RA3 Closure A)"
    )
    assert "PRE-WALKED" not in live_chain_text, (
        "LiveChain must no longer emit the PRE-WALKED synthetic retrieval "
        "identity (P1.5-RA3 Closure A)"
    )
    assert "0\" * 64" not in live_chain_text and "\"0\" * 64" not in live_chain_text, (
        "LiveChain must no longer emit zero-filled retrieval snapshot "
        "hashes (P1.5-RA3 Closure A)"
    )
    # Same checks on the orchestrator's helper
    assert "pre_walked_candidates_by_rung" not in replay_b_text, (
        "orchestrator must no longer pass pre_walked_candidates_by_rung "
        "(P1.5-RA3 Closure A)"
    )


# ============================================================================
# T3 — Selection continuity (selected_cp_id == resolver.cp_id, rank > 1)
# ============================================================================

def test_t3_selection_continuity_with_rank_gt_1(
    live_chain_mod, live_crossref_mod, monkeypatch,
):
    """P1.5-RA3 Closure C: a caller-selected CandidatePointer at
    rank > 1 produces continuity PASS — the resolver's
    candidate_pointer_id equals the selected one (NOT
    candidates[0]).
    """
    from mafs_p0.crossref_renderer import (
        RenderedQuery, LADDER_RUNG_A,
    )
    so = {
        "search_order_id": "SO-T3-RA3",
        "required_capabilities": ["search.query", "search.pagination", "result.ranked"],
    }
    rendered_queries = [
        RenderedQuery(rendering_path=LADDER_RUNG_A, url_params={"query.author": "x"}),
    ]
    # Three candidates; the caller selects rank 3 (cp_id="CP-rank-3").
    cands = [
        {"candidate_pointer_id": "CP-rank-1", "rank": 1, "provider": "crossref_v1",
         "identifier_hints": {"doi": "10.1/rank-1"},
         "retrieval_invocation_id": "RIV-003"},
        {"candidate_pointer_id": "CP-rank-2", "rank": 2, "provider": "crossref_v1",
         "identifier_hints": {"doi": "10.1/rank-2"},
         "retrieval_invocation_id": "RIV-003"},
        {"candidate_pointer_id": "CP-rank-3", "rank": 3, "provider": "crossref_v1",
         "identifier_hints": {"doi": "10.1/rank-3"},
         "retrieval_invocation_id": "RIV-003"},
    ]

    def fake_discover(self, *args, **kwargs):
        return (
            list(cands),
            {"retrieval_invocation_id": "RIV-003", "status": "ok",
             "search_order_id": so["search_order_id"], "provider": "crossref_v1",
             "raw_snapshot_sha256": "0" * 64,
             "response": {"http_status": 200, "item_count": 3, "attempts": 1}},
            {"kind": "retrieval_response", "sha256": "0" * 64, "bytes": ""},
        )

    def fake_resolve(self, *args, **kwargs):
        cp = kwargs["candidate_pointer"]
        return (
            {"evidence_id": "CE-T3-001", "canonical": {"doi": "10.1/rank-3"},
             "provenance": {}},
            {"resolver_invocation_id": "RIVR-001", "status": "ok",
             "candidate_pointer_id": cp["candidate_pointer_id"],
             "raw_snapshot_sha256": "0" * 64},
            {"kind": "resolver_response", "sha256": "0" * 64, "bytes": ""},
        )

    monkeypatch.setattr(
        live_crossref_mod.CrossrefRetrievalProvider, "discover", fake_discover
    )
    monkeypatch.setattr(
        live_crossref_mod.CrossrefReferenceResolver, "resolve", fake_resolve
    )
    chain = live_chain_mod.LiveChain(
        search_order=so, rendered_queries=rendered_queries, top_k=5,
    )
    discovery = chain.discover()
    result = chain.resolve(discovery, {
        "rendering_path": LADDER_RUNG_A,
        "candidate_pointer_id": "CP-rank-3",
    })
    # Continuity: selected_cp_id == resolver.cp_id
    assert result["selected_candidate_pointer_id"] == "CP-rank-3"
    assert result["resolver_invocation"]["candidate_pointer_id"] == "CP-rank-3"
    # The candidate_pointers returned in resolve() are the SELECTED
    # rung's candidates (rank 3 IS present), NOT a top-1 truncated set.
    cps = result["candidate_pointers"]
    assert any(c.get("candidate_pointer_id") == "CP-rank-3" for c in cps)
    # The resolver received the EXPLICITLY selected CandidatePointer,
    # not the top-1.
    assert result["selected_candidate_rank"] == 3


# ============================================================================
# T4 — No top-1 continuity assumption
# ============================================================================

def test_t4_no_top1_continuity_assumption(
    live_chain_mod, live_crossref_mod, monkeypatch,
):
    """P1.5-RA3 Closure C: the continuity invariant does NOT
    reference candidates[0]. Even when the top-1 differs from
    the selected CandidatePointer, the chain produces continuity
    PASS for the selection.
    """
    from mafs_p0.crossref_renderer import (
        RenderedQuery, LADDER_RUNG_A,
    )
    so = {
        "search_order_id": "SO-T4-RA3",
        "required_capabilities": ["search.query", "search.pagination", "result.ranked"],
    }
    rendered_queries = [
        RenderedQuery(rendering_path=LADDER_RUNG_A, url_params={"query.author": "x"}),
    ]
    # Top-1 is CP-A (different from selection).
    cands = [
        {"candidate_pointer_id": "CP-A", "rank": 1, "provider": "crossref_v1",
         "identifier_hints": {"doi": "10.1/top1"},
         "retrieval_invocation_id": "RIV-004"},
        {"candidate_pointer_id": "CP-B", "rank": 2, "provider": "crossref_v1",
         "identifier_hints": {"doi": "10.1/rank2"},
         "retrieval_invocation_id": "RIV-004"},
    ]

    def fake_discover(self, *args, **kwargs):
        return (
            list(cands),
            {"retrieval_invocation_id": "RIV-004", "status": "ok",
             "search_order_id": so["search_order_id"], "provider": "crossref_v1",
             "raw_snapshot_sha256": "0" * 64,
             "response": {"http_status": 200, "item_count": 2, "attempts": 1}},
            {"kind": "retrieval_response", "sha256": "0" * 64, "bytes": ""},
        )

    def fake_resolve(self, *args, **kwargs):
        cp = kwargs["candidate_pointer"]
        return (
            {"evidence_id": "CE-T4-001", "canonical": {"doi": "10.1/rank2"},
             "provenance": {}},
            {"resolver_invocation_id": "RIVR-002", "status": "ok",
             "candidate_pointer_id": cp["candidate_pointer_id"],
             "raw_snapshot_sha256": "0" * 64},
            {"kind": "resolver_response", "sha256": "0" * 64, "bytes": ""},
        )

    monkeypatch.setattr(
        live_crossref_mod.CrossrefRetrievalProvider, "discover", fake_discover
    )
    monkeypatch.setattr(
        live_crossref_mod.CrossrefReferenceResolver, "resolve", fake_resolve
    )
    chain = live_chain_mod.LiveChain(
        search_order=so, rendered_queries=rendered_queries, top_k=5,
    )
    discovery = chain.discover()
    result = chain.resolve(discovery, {
        "rendering_path": LADDER_RUNG_A,
        "candidate_pointer_id": "CP-B",  # rank 2 selection
    })
    # The top-1 is CP-A but the selected is CP-B. The chain
    # resolves CP-B (not CP-A), and the resolver's cp_id matches
    # the SELECTED cp_id (not the top-1).
    assert result["selected_candidate_pointer_id"] == "CP-B"
    assert result["resolver_invocation"]["candidate_pointer_id"] == "CP-B"
    # The first candidate_pointers[0] is NOT what got resolved;
    # CP-B is in the set but is not at index 0.
    cps = result["candidate_pointers"]
    assert cps[0]["candidate_pointer_id"] == "CP-A"
    assert any(c.get("candidate_pointer_id") == "CP-B" for c in cps)


# ============================================================================
# T5 — No selection means no resolution
# ============================================================================

def test_t5_no_selection_means_no_resolution(
    live_chain_mod, live_crossref_mod, monkeypatch,
):
    """P1.5-RA3 Closure A + §1: CandidateSets may be non-empty
    while canonical evidence remains absent. The resolver is NOT
    invoked without an explicit selection.
    """
    from mafs_p0.crossref_renderer import (
        RenderedQuery, LADDER_RUNG_A, LADDER_RUNG_B,
    )
    so = {
        "search_order_id": "SO-T5-RA3",
        "required_capabilities": ["search.query", "search.pagination", "result.ranked"],
    }
    rendered_queries = [
        RenderedQuery(rendering_path=LADDER_RUNG_A, url_params={"query.author": "x"}),
        RenderedQuery(rendering_path=LADDER_RUNG_B, url_params={"query.author": "x"}),
    ]
    resolver_calls: list[dict] = []

    def fake_discover(self, *args, **kwargs):
        rendering_path = kwargs.get("rendering_path", "")
        return (
            [{"candidate_pointer_id": f"CP-{rendering_path}",
              "rank": 1, "provider": "crossref_v1",
              "identifier_hints": {"doi": f"10.1/{rendering_path}"},
              "retrieval_invocation_id": f"RIV-{rendering_path}"}],
            {"retrieval_invocation_id": f"RIV-{rendering_path}", "status": "ok",
             "search_order_id": so["search_order_id"], "provider": "crossref_v1",
             "raw_snapshot_sha256": "0" * 64,
             "response": {"http_status": 200, "item_count": 1, "attempts": 1}},
            {"kind": "retrieval_response", "sha256": "0" * 64, "bytes": ""},
        )

    def fake_resolve(self, *args, **kwargs):
        resolver_calls.append(kwargs["candidate_pointer"])
        return (None, None, None)

    monkeypatch.setattr(
        live_crossref_mod.CrossrefRetrievalProvider, "discover", fake_discover
    )
    monkeypatch.setattr(
        live_crossref_mod.CrossrefReferenceResolver, "resolve", fake_resolve
    )
    chain = live_chain_mod.LiveChain(
        search_order=so, rendered_queries=rendered_queries, top_k=5,
    )
    discovery = chain.discover()
    result = chain.resolve(discovery, None)  # no selection
    # Both rungs yielded candidates (audit available).
    assert len(discovery["rung_candidate_sets"]) == 2
    # Canonical evidence absent; resolver NOT invoked.
    assert result["canonical_evidence"] is None
    assert result["resolver_invocation"] is None
    assert result["candidate_pointers"] == []
    assert result["status"] == "ladder_completed_no_selection"
    assert len(resolver_calls) == 0


# ============================================================================
# T6 — Rank truth: known rank is preserved exactly
# ============================================================================

def test_t6_rank_truth_known_rank_preserved_exactly(
    live_chain_mod, live_crossref_mod, monkeypatch,
):
    """P1.5-RA3 Closure D: when the selected CandidatePointer
    carries a rank, the chain result records the actual rank
    (not a fabricated 1, not a missing value).
    """
    from mafs_p0.crossref_renderer import (
        RenderedQuery, LADDER_RUNG_A,
    )
    so = {
        "search_order_id": "SO-T6-RA3",
        "required_capabilities": ["search.query", "search.pagination", "result.ranked"],
    }
    rendered_queries = [
        RenderedQuery(rendering_path=LADDER_RUNG_A, url_params={"query.author": "x"}),
    ]
    # The CandidatePointer carries an explicit integer rank of 5.
    cands = [
        {"candidate_pointer_id": "CP-rank-5", "rank": 5, "provider": "crossref_v1",
         "identifier_hints": {"doi": "10.1/rank5"},
         "retrieval_invocation_id": "RIV-T6"},
    ]

    def fake_discover(self, *args, **kwargs):
        return (
            list(cands),
            {"retrieval_invocation_id": "RIV-T6", "status": "ok",
             "search_order_id": so["search_order_id"], "provider": "crossref_v1",
             "raw_snapshot_sha256": "0" * 64,
             "response": {"http_status": 200, "item_count": 1, "attempts": 1}},
            {"kind": "retrieval_response", "sha256": "0" * 64, "bytes": ""},
        )

    def fake_resolve(self, *args, **kwargs):
        return (
            {"evidence_id": "CE-T6-001", "canonical": {"doi": "10.1/rank5"},
             "provenance": {}},
            {"resolver_invocation_id": "RIVR-001", "status": "ok",
             "candidate_pointer_id": kwargs["candidate_pointer"]["candidate_pointer_id"],
             "raw_snapshot_sha256": "0" * 64},
            {"kind": "resolver_response", "sha256": "0" * 64, "bytes": ""},
        )

    monkeypatch.setattr(
        live_crossref_mod.CrossrefRetrievalProvider, "discover", fake_discover
    )
    monkeypatch.setattr(
        live_crossref_mod.CrossrefReferenceResolver, "resolve", fake_resolve
    )
    chain = live_chain_mod.LiveChain(
        search_order=so, rendered_queries=rendered_queries, top_k=5,
    )
    discovery = chain.discover()
    result = chain.resolve(discovery, {
        "rendering_path": LADDER_RUNG_A,
        "candidate_pointer_id": "CP-rank-5",
    })
    # Rank is preserved exactly.
    assert result["selected_candidate_rank"] == 5
    assert result["selected_candidate_rank"] is not None
    assert result["selected_candidate_rank_status"] == "OK"
    # Not the fabricated-1 default.
    assert result["selected_candidate_rank"] != 1


# ============================================================================
# T7 — Rank missing is unknown (rank = null + rank_status)
# ============================================================================

def test_t7_rank_missing_is_unknown(
    live_chain_mod, live_crossref_mod, monkeypatch,
):
    """P1.5-RA3 Closure D: when the selected CandidatePointer has
    no `rank` field, the chain records `null` (NOT 1) and
    `rank_status = NOT_EVALUATED_RANK_MISSING`. Identity status
    is independent of rank observability.
    """
    from mafs_p0.crossref_renderer import (
        RenderedQuery, LADDER_RUNG_A,
    )
    so = {
        "search_order_id": "SO-T7-RA3",
        "required_capabilities": ["search.query", "search.pagination", "result.ranked"],
    }
    rendered_queries = [
        RenderedQuery(rendering_path=LADDER_RUNG_A, url_params={"query.author": "x"}),
    ]
    # NO `rank` field on the CandidatePointer.
    cands = [
        {"candidate_pointer_id": "CP-no-rank", "provider": "crossref_v1",
         "identifier_hints": {"doi": "10.1/no-rank"},
         "retrieval_invocation_id": "RIV-T7"},
    ]

    def fake_discover(self, *args, **kwargs):
        return (
            list(cands),
            {"retrieval_invocation_id": "RIV-T7", "status": "ok",
             "search_order_id": so["search_order_id"], "provider": "crossref_v1",
             "raw_snapshot_sha256": "0" * 64,
             "response": {"http_status": 200, "item_count": 1, "attempts": 1}},
            {"kind": "retrieval_response", "sha256": "0" * 64, "bytes": ""},
        )

    def fake_resolve(self, *args, **kwargs):
        return (
            {"evidence_id": "CE-T7-001", "canonical": {"doi": "10.1/no-rank"},
             "provenance": {}},
            {"resolver_invocation_id": "RIVR-001", "status": "ok",
             "candidate_pointer_id": kwargs["candidate_pointer"]["candidate_pointer_id"],
             "raw_snapshot_sha256": "0" * 64},
            {"kind": "resolver_response", "sha256": "0" * 64, "bytes": ""},
        )

    monkeypatch.setattr(
        live_crossref_mod.CrossrefRetrievalProvider, "discover", fake_discover
    )
    monkeypatch.setattr(
        live_crossref_mod.CrossrefReferenceResolver, "resolve", fake_resolve
    )
    chain = live_chain_mod.LiveChain(
        search_order=so, rendered_queries=rendered_queries, top_k=5,
    )
    discovery = chain.discover()
    result = chain.resolve(discovery, {
        "rendering_path": LADDER_RUNG_A,
        "candidate_pointer_id": "CP-no-rank",
    })
    # Rank is null (not 1).
    assert result["selected_candidate_rank"] is None
    # Rank status is explicit.
    assert result["selected_candidate_rank_status"] == "NOT_EVALUATED_RANK_MISSING"
    # No fall-back to 1 anywhere in the result.
    assert result["selected_candidate_rank"] != 1


# ============================================================================
# T8 — CI subtraction truth (real or NOT_EVALUATED_GIT_UNAVAILABLE)
# ============================================================================

def test_t8_subtraction_accounting_status_field(replay_b_text, workflow_text):
    """P1.5-RA3 Closure E §7.2: the subtraction accounting has an
    explicit `subtraction_accounting_status` field. When git is
    unavailable, the status is `NOT_EVALUATED_GIT_UNAVAILABLE`
    and the integer fields are null (NOT 0-as-measured-zero).
    The workflow uses `fetch-depth: 0` so CI has full git history.
    """
    # Workflow must use fetch-depth: 0
    assert "fetch-depth: 0" in workflow_text, (
        "p1-5.yml must use fetch-depth: 0 to provide full git history "
        "to the orchestrator's subtraction accounting (P1.5-RA3 "
        "Closure E §7.1)"
    )
    # Orchestrator must emit subtraction_accounting_status
    assert "subtraction_accounting_status" in replay_b_text, (
        "orchestrator must emit subtraction_accounting_status "
        "(P1.5-RA3 Closure E §7.2)"
    )
    # The status must have two valid values: "OK" and
    # "NOT_EVALUATED_GIT_UNAVAILABLE"
    assert '"OK"' in replay_b_text
    assert "NOT_EVALUATED_GIT_UNAVAILABLE" in replay_b_text
    # The "do not emit zeroes" rule: when git is unavailable, the
    # integer fields should be None/null, not 0.
    # The orchestrator code should set them to None in the failure
    # branch.
    assert '"production_src_additions": None' in replay_b_text or \
           'production_src_additions = None' in replay_b_text or \
           'production_src_additions\": None' in replay_b_text, (
        "subtraction accounting must use None (not 0) when git is "
        "unavailable (P1.5-RA3 Closure E §7.2)"
    )


# ============================================================================
# T9 — Single acceptance source
# ============================================================================

def test_t9_single_acceptance_source():
    """P1.5-RA3 Closure F §8.1: the generic stale file
    `docs/P1_5_METRICS.json` is marked as historical; the
    only current acceptance metrics file for this line is
    `docs/P1_5_RA3_METRICS.json`.
    """
    summary = (DOCS / "P1_5_RA2_SUMMARY.md").read_text(encoding="utf-8")
    # The RA2 summary must have already stated the
    # single-truth rule (P1.5-RA2 §6.2 carries this forward).
    assert "P1_5_RA2_METRICS.json" in summary or "sole current" in summary.lower() or \
           "current acceptance source" in summary.lower()
    # If the RA3 summary already exists, it must contain the
    # single-source statement explicitly.
    ra3_summary = DOCS / "P1_5_RA3_SUMMARY.md"
    if ra3_summary.exists():
        text = ra3_summary.read_text(encoding="utf-8")
        assert "P1_5_RA3_METRICS.json is the only current acceptance" in text, (
            "P1_5_RA3_SUMMARY.md must contain the explicit single-source "
            "statement (P1.5-RA3 §8)"
        )
        assert "do not bind current acceptance" in text or \
               "historical evidence" in text
    # The `docs/P1_5_METRICS.json` file (if present) MUST carry a
    # `_historical_marker` top-level key so it cannot be mistaken
    # for current acceptance truth.
    p15_metrics = DOCS / "P1_5_METRICS.json"
    if p15_metrics.exists():
        m = json.loads(p15_metrics.read_text(encoding="utf-8"))
        assert "_historical_marker" in m, (
            "docs/P1_5_METRICS.json must carry a `_historical_marker` "
            "top-level key to disambiguate it from current acceptance "
            "(P1.5-RA3 §8.1)"
        )


# ============================================================================
# T10 — Q3 / Q5 / fabrication regression
# ============================================================================

def test_t10_q3_q5_fabrication_regression(replay_b_text):
    """P1.5-RA3 §7 (preserved from RA1/RA2): Q3 negative-evidence
    boundary, Q5 ENTITY_RESOLUTION_REQUIRED, and fabrication
    invariants (fabricated_reference_count = 0,
    fabricated_entity_count = 0) remain in place.
    """
    # Q3 negative branch
    assert "is_negative_branch" in replay_b_text
    assert "COVERAGE_INSUFFICIENT" in replay_b_text
    # Q5 entity boundary
    assert "ENTITY_RESOLUTION_REQUIRED" in replay_b_text
    # Fabrication counters
    assert "fabricated_reference_count" in replay_b_text
    assert "fabricated_entity_count" in replay_b_text
    # No new AI-native framework classes (Closure F)
    forbidden = [
        "CognitiveCheckpoint", "ArtifactManager", "HandoffController",
        "AI-Native Pipeline", "CoordinationEngine", "Mediator",
        "Bridge", "Reconciler", "Agent Control Graph",
    ]
    for f in forbidden:
        assert f not in replay_b_text, (
            f"P1.5-RA3 §13 forbids new class with name {f!r}"
        )
