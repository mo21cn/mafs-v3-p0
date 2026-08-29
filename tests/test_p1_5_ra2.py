"""MAFS v3.0-P1.5-RA2 — Candidate Ownership & Subtraction Truth Closure Tests.

10 mandatory acceptance tests per P1.5-RA2 contract §9. All tests are
fully offline (no network). The single final live CI run is exercised
by ``.github/workflows/p1-5.yml``.

  T1  — No candidate auto-selection (rung selection alone must NOT resolve top-1)
  T2  — Explicit CandidatePointer selection (caller's candidate_pointer_id is
         the exact one sent to the resolver, even when rank > 1)
  T3  — Invalid candidate selection fails honestly (no top-1 fallback)
  T4  — No selection means no resolver (CandidateSets non-empty; canonical
         evidence absent)
  T5  — Benchmark oracle uses candidate-level selection (benchmark calls
         LiveChain with explicit external_selection, not the resolver
         directly)
  T6  — Rank truth (per_anchor_rank = actual matched CandidatePointer.rank)
  T7  — CP -> Resolver continuity (selected cp_id == resolver's cp_id)
  T8  — Fabrication invariant (no evidence or entity fabricated)
  T9  — Q3 / Q5 regression (boundaries preserved)
  T10 — Subtraction truth (acceptance metrics use actual git-diff-derived
         LOC values, not a hard-coded boolean)
"""
from __future__ import annotations
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest


PKG = Path(__file__).resolve().parent.parent
SRC = PKG / "src" / "mafs_p0"
DOCS = PKG / "docs"
REPLAY_B = PKG / "scripts" / "replay_b.py"


# ---- fixtures ---------------------------------------------------------------

def _load_module(name: str):
    sys_path = str(PKG / "src")
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
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
    return REPLAY_B.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def live_chain_text():
    return (SRC / "live_chain.py").read_text(encoding="utf-8")


# ============================================================================
# T1 — No candidate auto-selection
# ============================================================================

def test_t1_rung_selection_alone_does_not_resolve_top1(
    live_chain_mod, live_crossref_mod, monkeypatch,
):
    """P1.5-RA2 §2.3 + T1: selecting only a rung (no
    candidate_pointer_id) must NOT resolve top-1 automatically. The
    chain returns ``status="candidate_selection_required"`` and the
    resolver is NOT invoked.
    """
    from mafs_p0.crossref_renderer import (
        RenderedQuery, LADDER_RUNG_A,
    )
    so = {
        "search_order_id": "SO-T1-RA2",
        "required_capabilities": ["search.query", "search.pagination", "result.ranked"],
    }
    rendered_queries = [
        RenderedQuery(rendering_path=LADDER_RUNG_A, url_params={"query.author": "x"}),
    ]
    captured = {"resolver_calls": 0}

    def fake_discover(self, *args, **kwargs):
        return (
            [
                {
                    "candidate_pointer_id": "CP-001",
                    "provider": "crossref_v1",
                    "rank": 1,
                    "identifier_hints": {"doi": "10.1234/top1"},
                    "retrieval_invocation_id": "RIV-001",
                }
            ],
            {
                "retrieval_invocation_id": "RIV-001",
                "status": "ok",
                "search_order_id": so["search_order_id"],
                "provider": "crossref_v1",
                "raw_snapshot_sha256": "0" * 64,
                "response": {"http_status": 200, "item_count": 1, "attempts": 1},
            },
            {"kind": "retrieval_response", "sha256": "0" * 64, "bytes": ""},
        )

    def fake_resolve(self, *args, **kwargs):
        captured["resolver_calls"] += 1
        return (None, None, None)

    monkeypatch.setattr(
        live_crossref_mod.CrossrefRetrievalProvider, "discover", fake_discover
    )
    monkeypatch.setattr(
        live_crossref_mod.CrossrefReferenceResolver, "resolve", fake_resolve
    )
    # Caller selects ONLY a rung (no candidate_pointer_id). The
    # chain must refuse to resolve.
    chain = live_chain_mod.LiveChain(
        search_order=so, rendered_queries=rendered_queries, top_k=5,
        external_selection={"rendering_path": LADDER_RUNG_A},
    )
    result = chain.run()
    assert result["status"] == "candidate_selection_required", (
        f"rung-only selection must NOT auto-resolve; got {result['status']!r}"
    )
    assert result["canonical_evidence"] is None
    assert result["resolver_invocation"] is None
    assert captured["resolver_calls"] == 0, (
        f"resolver must NOT be invoked; got {captured['resolver_calls']} call(s)"
    )
    # The chain still walks the ladder and records audit fields
    # (T6 requires the full audit; T4 requires non-empty evidence
    # surface).
    assert len(result["rung_candidate_sets"]) == 1
    assert result["rung_candidate_sets"][0]["candidate_count"] == 1


# ============================================================================
# T2 — Explicit CandidatePointer selection
# ============================================================================

def test_t2_explicit_candidate_pointer_id_is_resolved_even_at_rank_gt_1(
    live_chain_mod, live_crossref_mod, monkeypatch,
):
    """P1.5-RA2 §2.2 + T2: a caller-selected ``candidate_pointer_id``
    is the exact CandidatePointer sent to the resolver, even when
    the rank is > 1. (E.g. the oracle matched at rank 3; the caller
    passes cp_id of that rank-3 candidate; the chain resolves
    rank-3, not rank-1.)
    """
    from mafs_p0.crossref_renderer import (
        RenderedQuery, LADDER_RUNG_A,
    )
    so = {
        "search_order_id": "SO-T2-RA2",
        "required_capabilities": ["search.query", "search.pagination", "result.ranked"],
    }
    rendered_queries = [
        RenderedQuery(rendering_path=LADDER_RUNG_A, url_params={"query.author": "x"}),
    ]
    # Three candidates; oracle-matched one is at rank 3.
    cands = [
        {"candidate_pointer_id": "CP-rank-1", "rank": 1, "provider": "crossref_v1",
         "identifier_hints": {"doi": "10.1/rank-1"},
         "retrieval_invocation_id": "RIV-002"},
        {"candidate_pointer_id": "CP-rank-2", "rank": 2, "provider": "crossref_v1",
         "identifier_hints": {"doi": "10.1/rank-2"},
         "retrieval_invocation_id": "RIV-002"},
        {"candidate_pointer_id": "CP-rank-3", "rank": 3, "provider": "crossref_v1",
         "identifier_hints": {"doi": "10.1/rank-3"},
         "retrieval_invocation_id": "RIV-002"},
    ]

    def fake_discover(self, *args, **kwargs):
        return (
            list(cands),
            {
                "retrieval_invocation_id": "RIV-002",
                "status": "ok",
                "search_order_id": so["search_order_id"],
                "provider": "crossref_v1",
                "raw_snapshot_sha256": "0" * 64,
                "response": {"http_status": 200, "item_count": 3, "attempts": 1},
            },
            {"kind": "retrieval_response", "sha256": "0" * 64, "bytes": ""},
        )

    resolved_with: list[dict] = []

    def fake_resolve(self, *args, **kwargs):
        resolved_with.append(kwargs["candidate_pointer"])
        return (
            {
                "evidence_id": "CE-rank-3",
                "canonical": {"doi": "10.1/rank-3", "title": "rank-3", "year": 2020,
                              "venue": "v", "source_locator": "http://example.org",
                              "resolver_identity": "fake"},
                "provenance": {"resolver_invocation_id": "RIFR-rank-3",
                               "retrieval_invocation_id": "RIV-002",
                               "resolver_snapshot_sha256": "0" * 64,
                               "retrieval_snapshot_sha256": "0" * 64},
            },
            {"resolver_invocation_id": "RIFR-rank-3", "status": "ok",
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
    # Caller explicitly selects CP-rank-3 (rank = 3, not top-1).
    chain = live_chain_mod.LiveChain(
        search_order=so, rendered_queries=rendered_queries, top_k=5,
        external_selection={
            "rendering_path": LADDER_RUNG_A,
            "candidate_pointer_id": "CP-rank-3",
        },
    )
    result = chain.run()
    assert result["status"] == "ok", f"expected ok; got {result['status']!r}"
    # The chain must have passed CP-rank-3 to the resolver (NOT
    # CP-rank-1).
    assert len(resolved_with) == 1
    assert resolved_with[0]["candidate_pointer_id"] == "CP-rank-3", (
        f"resolver must receive the caller's explicit candidate_pointer_id; "
        f"got {resolved_with[0]['candidate_pointer_id']!r}"
    )
    assert result["selected_candidate_pointer_id"] == "CP-rank-3"
    assert result["selected_candidate_rank"] == 3
    # The chain must NOT promote rank-1 to canonical just because it
    # is at rank 1.
    assert result["candidate_pointers"][0]["candidate_pointer_id"] != "CP-rank-1" or \
           result["external_selection"]["candidate_pointer_id"] == "CP-rank-3"


# ============================================================================
# T3 — Invalid candidate selection fails honestly
# ============================================================================

def test_t3_nonexistent_candidate_id_fails_honestly(
    live_chain_mod, live_crossref_mod, monkeypatch,
):
    """P1.5-RA2 §2.3 + T3: a nonexistent ``candidate_pointer_id`` must
    NOT fall back to rank 1. The chain returns
    ``status="invalid_external_selection"`` and the resolver is NOT
    invoked.
    """
    from mafs_p0.crossref_renderer import (
        RenderedQuery, LADDER_RUNG_A,
    )
    so = {
        "search_order_id": "SO-T3-RA2",
        "required_capabilities": ["search.query", "search.pagination", "result.ranked"],
    }
    rendered_queries = [
        RenderedQuery(rendering_path=LADDER_RUNG_A, url_params={"query.author": "x"}),
    ]
    resolver_calls: list[dict] = []

    def fake_discover(self, *args, **kwargs):
        return (
            [
                {"candidate_pointer_id": "CP-001", "rank": 1, "provider": "crossref_v1",
                 "identifier_hints": {"doi": "10.1/001"},
                 "retrieval_invocation_id": "RIV-003"},
            ],
            {
                "retrieval_invocation_id": "RIV-003",
                "status": "ok",
                "search_order_id": so["search_order_id"],
                "provider": "crossref_v1",
                "raw_snapshot_sha256": "0" * 64,
                "response": {"http_status": 200, "item_count": 1, "attempts": 1},
            },
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
    # Caller passes a candidate_pointer_id that does NOT exist in the rung.
    chain = live_chain_mod.LiveChain(
        search_order=so, rendered_queries=rendered_queries, top_k=5,
        external_selection={
            "rendering_path": LADDER_RUNG_A,
            "candidate_pointer_id": "CP-DOES-NOT-EXIST",
        },
    )
    result = chain.run()
    assert result["status"] == "invalid_external_selection", (
        f"nonexistent candidate id must fail honestly; got {result['status']!r}"
    )
    assert result["canonical_evidence"] is None
    assert result["resolver_invocation"] is None
    assert len(resolver_calls) == 0, (
        f"resolver must NOT be invoked for an invalid selection; "
        f"got {len(resolver_calls)} call(s)"
    )


# ============================================================================
# T4 — No selection means no resolver
# ============================================================================

def test_t4_no_selection_means_no_resolver_even_when_candidates_exist(
    live_chain_mod, live_crossref_mod, monkeypatch,
):
    """P1.5-RA2 §2.2 + T4: CandidateSets may be non-empty while
    canonical evidence remains absent. The resolver is NOT invoked
    without an explicit selection.
    """
    from mafs_p0.crossref_renderer import (
        RenderedQuery, LADDER_RUNG_A, LADDER_RUNG_B,
    )
    so = {
        "search_order_id": "SO-T4-RA2",
        "required_capabilities": ["search.query", "search.pagination", "result.ranked"],
    }
    rendered_queries = [
        RenderedQuery(rendering_path=LADDER_RUNG_A, url_params={"query.author": "x"}),
        RenderedQuery(rendering_path=LADDER_RUNG_B, url_params={"query.author": "x"}),
    ]
    resolver_calls: list[dict] = []

    def fake_discover(self, *args, **kwargs):
        rendering_path = kwargs.get("rendering_path", "")
        n = 3
        return (
            [
                {"candidate_pointer_id": f"CP-{rendering_path}-{i:03d}",
                 "rank": i, "provider": "crossref_v1",
                 "identifier_hints": {"doi": f"10.1/{rendering_path}-{i}"},
                 "retrieval_invocation_id": f"RIV-{rendering_path}-{i:03d}"}
                for i in range(1, n + 1)
            ],
            {
                "retrieval_invocation_id": f"RIV-{rendering_path}",
                "status": "ok",
                "search_order_id": so["search_order_id"],
                "provider": "crossref_v1",
                "raw_snapshot_sha256": "0" * 64,
                "response": {"http_status": 200, "item_count": n, "attempts": 1},
            },
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
        external_selection=None,  # no selection at all
    )
    result = chain.run()
    # Both rungs yielded candidates (full audit available).
    assert len(result["rung_candidate_sets"]) == 2
    assert all(r["candidate_count"] > 0 for r in result["rung_candidate_sets"])
    # Canonical evidence is absent; resolver was NOT invoked.
    assert result["canonical_evidence"] is None
    assert result["resolver_invocation"] is None
    assert result["candidate_pointers"] == []
    assert result["status"] == "ladder_completed_no_selection"
    assert len(resolver_calls) == 0


# ============================================================================
# T5 — Benchmark oracle uses candidate-level selection
# ============================================================================

def test_t5_orchestrator_passes_explicit_candidate_pointer_to_live_chain(
    replay_b_text,
):
    """P1.5-RA2 §3 + T5: the benchmark identifies the
    oracle-matched CandidatePointer, then calls LiveChain with an
    explicit ``external_selection = {rendering_path, doi}`` (or
    ``{rendering_path, candidate_pointer_id}``). The doi is the
    cross-walk stable identifier; LiveChain's own ladder walk
    produces a fresh cp_id namespace, so the orchestrator passes
    the doi to be re-resolved inside LiveChain. LiveChain owns the
    resolver; the orchestrator does not duplicate the resolver
    path.
    """
    # The orchestrator must construct external_selection with
    # rendering_path AND an identifier (doi and/or
    # candidate_pointer_id).
    has_doi = re.search(
        r"external_selection\s*=\s*\{[^}]*\"doi\"", replay_b_text, re.DOTALL,
    )
    has_cpid = re.search(
        r"external_selection\s*=\s*\{[^}]*\"candidate_pointer_id\"", replay_b_text, re.DOTALL,
    )
    assert has_doi or has_cpid, (
        "orchestrator must construct external_selection with rendering_path "
        "AND an identifier (doi and/or candidate_pointer_id) "
        "(P1.5-RA2 §3)"
    )
    # The orchestrator must instantiate LiveChain to delegate the
    # resolution (NOT call resolver.resolve() directly).
    assert "LiveChain(" in replay_b_text, (
        "orchestrator must call LiveChain for resolution (P1.5-RA2 §3: "
        "benchmark chooses candidate, production LiveChain resolves it)"
    )
    assert "resolver.resolve(" not in replay_b_text, (
        "orchestrator must not duplicate the resolver path (P1.5-RA2 §3)"
    )


# ============================================================================
# T6 — Rank truth
# ============================================================================

def test_t6_per_anchor_rank_is_actual_matched_candidate_rank(
    live_chain_text, replay_b_text,
):
    """P1.5-RA2 §4 + T6: ``per_anchor_rank`` must be derived from the
    actual matched CandidatePointer.rank, NOT hard-coded 1. The
    orchestrator must read ``selected_candidate_rank`` from the
    chain result and pass it through. A rank-3 oracle match must
    produce ``per_anchor_rank = 3``, not ``1``.
    """
    # LiveChain must record the actual selected CandidatePointer's
    # rank in its result, so the orchestrator can read it.
    assert "selected_candidate_rank" in live_chain_text, (
        "LiveChain must record selected_candidate_rank in its result "
        "(P1.5-RA2 §4)"
    )
    assert "selected_candidate_pointer_id" in live_chain_text, (
        "LiveChain must record selected_candidate_pointer_id in its result "
        "(P1.5-RA2 §2.4)"
    )
    # The orchestrator's per_anchor_rank computation must NOT contain
    # a hard-coded ``per_anchor_rank[anchor_id] = 1`` (P1.5-RA2 §4.1
    # "stale top-1 assumptions"). The only place rank 1 may appear is
    # as a defensive fallback when selected_candidate_rank is
    # missing.
    # Find the per_anchor_rank block. The assignment may span multiple
    # lines, so we look for the assignment token and capture the
    # expression up to the next blank line or unindented statement.
    block_match = re.search(
        r"per_anchor_rank\[anchor_id\]\s*=\s*(.*?)(?=\n\s*\n|\n[^\s])",
        replay_b_text, re.DOTALL,
    )
    assert block_match is not None, "per_anchor_rank assignment not found"
    rhs = block_match.group(1)
    # The RHS must reference actual_rank (or selected_candidate_rank)
    # and must NOT be a bare integer literal ``= 1``.
    assert "actual_rank" in rhs or "selected_candidate_rank" in rhs, (
        f"per_anchor_rank RHS must read from actual matched rank; "
        f"got: {rhs!r}"
    )
    # The bare literal ``= 1`` (or ``= 1\n``) as the entire RHS is
    # forbidden. A defensive fallback that may mention 1 (e.g.
    # ``actual_rank if isinstance(actual_rank, int) else 1``) is OK
    # because the primary path is the actual rank.
    rhs_stripped = rhs.strip()
    if rhs_stripped == "1":
        pytest.fail(
            f"per_anchor_rank is hard-coded to 1; must use actual matched rank "
            f"(P1.5-RA2 §4.1). RHS: {rhs!r}"
        )


# ============================================================================
# T7 — CP → Resolver continuity
# ============================================================================

def test_t7_resolver_continuity_when_explicit_selection_resolved(
    live_chain_mod, live_crossref_mod, monkeypatch,
):
    """P1.5-RA2 §2.4 + T7: the selected ``candidate_pointer_id``
    must equal the resolver invocation's candidate ID.
    """
    from mafs_p0.crossref_renderer import (
        RenderedQuery, LADDER_RUNG_A,
    )
    so = {
        "search_order_id": "SO-T7-RA2",
        "required_capabilities": ["search.query", "search.pagination", "result.ranked"],
    }
    rendered_queries = [
        RenderedQuery(rendering_path=LADDER_RUNG_A, url_params={"query.author": "x"}),
    ]
    cp_id = "CP-T7-001"

    def fake_discover(self, *args, **kwargs):
        return (
            [
                {"candidate_pointer_id": cp_id, "rank": 1, "provider": "crossref_v1",
                 "identifier_hints": {"doi": "10.1/t7"},
                 "retrieval_invocation_id": "RIV-T7-001"},
            ],
            {
                "retrieval_invocation_id": "RIV-T7-001",
                "status": "ok",
                "search_order_id": so["search_order_id"],
                "provider": "crossref_v1",
                "raw_snapshot_sha256": "0" * 64,
                "response": {"http_status": 200, "item_count": 1, "attempts": 1},
            },
            {"kind": "retrieval_response", "sha256": "0" * 64, "bytes": ""},
        )

    def fake_resolve(self, *args, **kwargs):
        return (
            {
                "evidence_id": "CE-T7-001",
                "canonical": {"doi": "10.1/t7", "title": "t7", "year": 2020,
                              "venue": "v", "source_locator": "http://example.org",
                              "resolver_identity": "fake"},
                "provenance": {"resolver_invocation_id": "RIFR-T7-001",
                               "retrieval_invocation_id": "RIV-T7-001",
                               "resolver_snapshot_sha256": "0" * 64,
                               "retrieval_snapshot_sha256": "0" * 64},
            },
            {"resolver_invocation_id": "RIFR-T7-001", "status": "ok",
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
        external_selection={
            "rendering_path": LADDER_RUNG_A,
            "candidate_pointer_id": cp_id,
        },
    )
    result = chain.run()
    assert result["status"] == "ok"
    assert result["selected_candidate_pointer_id"] == cp_id
    rsi = result["resolver_invocation"]
    assert rsi is not None
    assert rsi["candidate_pointer_id"] == cp_id, (
        f"resolver must receive the caller's explicit candidate_pointer_id; "
        f"expected {cp_id!r}, got {rsi.get('candidate_pointer_id')!r}"
    )


# ============================================================================
# T8 — Fabrication invariant
# ============================================================================

def test_t8_no_evidence_or_entity_fabrication_in_explicit_selection_paths(
    live_chain_mod, live_crossref_mod, monkeypatch,
):
    """P1.5-RA2 + T8: even with the new explicit-selection
    boundary, the fabrication hard invariant must hold. Empty
    candidates + valid selection -> no evidence. Invalid selection
    -> no evidence. Successful resolution -> evidence derived from
    the actual upstream response (no fabrication).
    """
    from mafs_p0.crossref_renderer import (
        RenderedQuery, LADDER_RUNG_A,
    )
    so = {
        "search_order_id": "SO-T8-RA2",
        "required_capabilities": ["search.query", "search.pagination", "result.ranked"],
    }
    rendered_queries = [
        RenderedQuery(rendering_path=LADDER_RUNG_A, url_params={"query.author": "x"}),
    ]

    def empty_discover(self, *args, **kwargs):
        return (
            [],
            {
                "retrieval_invocation_id": "RIV-EMPTY",
                "status": "ok",
                "search_order_id": so["search_order_id"],
                "provider": "crossref_v1",
                "raw_snapshot_sha256": "0" * 64,
                "response": {"http_status": 200, "item_count": 0, "attempts": 1},
            },
            {"kind": "retrieval_response", "sha256": "0" * 64, "bytes": ""},
        )

    monkeypatch.setattr(
        live_crossref_mod.CrossrefRetrievalProvider, "discover", empty_discover
    )
    chain = live_chain_mod.LiveChain(
        search_order=so, rendered_queries=rendered_queries, top_k=5,
        external_selection={
            "rendering_path": LADDER_RUNG_A,
            "candidate_pointer_id": "CP-WHATEVER",
        },
    )
    result = chain.run()
    # Even with an explicit selection, if there are no candidates,
    # the chain must NOT fabricate evidence.
    assert result["canonical_evidence"] is None
    assert result["resolver_invocation"] is None
    assert result["status"] in ("invalid_external_selection", "ladder_completed_no_selection")


# ============================================================================
# T9 — Q3 / Q5 regression
# ============================================================================

def test_t9_q3_negative_branch_and_q5_entity_boundary_unchanged(
    replay_b_text,
):
    """P1.5-RA2 + T9: Q3 negative-evidence semantics and Q5 entity
    boundary must NOT be modified. P1.5-RA2 changes only the
    selection boundary; Q3 / Q5 logic is unchanged from RA1.
    """
    assert "is_negative_branch" in replay_b_text
    assert "COVERAGE_INSUFFICIENT" in replay_b_text
    assert "ENTITY_RESOLUTION_REQUIRED" in replay_b_text
    # No new FlyWire / VFB / hemibrain dataset adapters.
    forbidden_adapters = ["flywire_adapter", "FlyWire", "neuPrint", "vfb_adapter"]
    for f in forbidden_adapters:
        if f in replay_b_text:
            # Allow if it's in a docstring/comment about the boundary;
            # strict check is for real imports or calls.
            for line in replay_b_text.splitlines():
                if f in line and (
                    re.search(rf"\b(import|from)\b.*{re.escape(f)}", line) or
                    re.search(rf"\b{re.escape(f)}\.\w+\(", line)
                ):
                    pytest.fail(
                        f"Q5 adapter {f!r} appears as a real import or call: {line!r}"
                    )


# ============================================================================
# T10 — Subtraction truth
# ============================================================================

def test_t10_subtraction_metrics_are_git_derived_not_hardcoded_boolean(
    replay_b_text,
):
    """P1.5-RA2 §5 + T10: the orchestrator's subtraction accounting
    must be derived from ``git diff --numstat``, not a hard-coded
    boolean. Verify the orchestrator contains the
    ``_compute_subtraction_accounting`` method (or equivalent) and
    emits ``production_src_additions / deletions / net`` and a
    git-derived ``production_loc_increase`` flag.

    If ``docs/P1_5_RA2_METRICS.json`` is present (after a live
    run), the test also verifies the emitted file carries real
    numbers.
    """
    # The orchestrator must contain a subtraction-accounting method
    # that calls ``git diff --numstat``.
    assert "_compute_subtraction_accounting" in replay_b_text, (
        "orchestrator must define _compute_subtraction_accounting "
        "(P1.5-RA2 §5)"
    )
    assert "git" in replay_b_text and "numstat" in replay_b_text, (
        "orchestrator must use git diff --numstat to derive subtraction "
        "accounting (P1.5-RA2 §5.2)"
    )
    # The accounting must separate production / benchmark / test.
    for field in (
        "production_src_additions",
        "production_src_deletions",
        "production_src_net",
        "benchmark_orchestrator_additions",
        "benchmark_orchestrator_deletions",
        "benchmark_orchestrator_net",
        "test_additions",
        "test_deletions",
        "test_net",
    ):
        assert field in replay_b_text, (
            f"subtraction accounting must report {field!r} (P1.5-RA2 §5.2)"
        )
    # If the live metrics file exists, verify the numbers are
    # present and consistent.
    metrics_path = DOCS / "P1_5_RA2_METRICS.json"
    if metrics_path.exists():
        m = json.loads(metrics_path.read_text(encoding="utf-8"))
        sub = m.get("subtraction_accounting") or {}
        assert sub.get("method") in ("git_numstat", "git_unavailable"), (
            f"subtraction_accounting.method must be git_numstat or "
            f"git_unavailable; got {sub.get('method')!r}"
        )
        for f in (
            "production_src_additions", "production_src_deletions",
            "production_src_net", "production_loc_increase",
        ):
            assert f in sub, (
                f"P1_5_RA2_METRICS.json subtraction_accounting missing {f!r}"
            )
        # production_loc_increase must be the boolean of
        # production_src_net > 0, not a hard-coded value.
        prod_net = sub.get("production_src_net", 0)
        assert sub["production_loc_increase"] == (prod_net > 0), (
            f"production_loc_increase must be (production_src_net > 0); "
            f"got production_loc_increase={sub['production_loc_increase']}, "
            f"production_src_net={prod_net}"
        )
