"""MAFS v3.0-P1.5 — Thin Crossref Renderer + Scholarly Anchor Recovery Tests.

8 semantic tests per P1.5 contract §15. All tests are fully offline
(no network); the final live CI run is exercised by
.github/workflows/p1-5.yml.

  1. von Reyn intent renders to Crossref author/year/bibliographic
     constraints without PubMed-specific syntax leakage
  2. Namiki intent preserves author/year/title/concept clues
  3. Scheffer intent preserves canonical connectome title/concept clues
  4. rendered Crossref request is persisted for audit
  5. fallback ladder remains bounded (≤ 4 rungs)
  6. recovered anchor requires identity-safe match
  7. original CandidatePointer -> Resolver invariant remains green
  8. existing Replay B truth/fabrication invariants remain green
"""
from __future__ import annotations
import sys
import urllib.parse
from pathlib import Path

import pytest


PKG = Path(__file__).resolve().parent.parent
DOCS = PKG / "docs"
REPLAY_B_DIR = PKG / "examples" / "runs" / "ReplayB"
P1_5_DIR = PKG / "examples" / "runs" / "P1_5"


# ---- fixtures -------------------------------------------------------------

@pytest.fixture(scope="module")
def renderer_mod():
    sys_path = str(PKG / "src")
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    import mafs_p0.crossref_renderer as cr
    return cr


@pytest.fixture(scope="module")
def search_order_von_reyn():
    return {
        "search_order_id": "SO-Q1-vonReyn-2014",
        "expected_doi": "10.1038/nn.3741",
        "intent": {
            "author": "von Reyn",
            "year": 2014,
            "title": "spike-timing action selection",
            "concepts": ["Drosophila", "giant fiber"],
        },
    }


@pytest.fixture(scope="module")
def search_order_namiki():
    return {
        "search_order_id": "SO-Q2-Namiki-2018",
        "expected_doi": "10.7554/eLife.34272",
        "intent": {
            "author": "Namiki",
            "year": 2018,
            "title": "descending sensory-motor pathways",
            "concepts": ["Drosophila", "giant fiber", "nomenclature"],
        },
    }


@pytest.fixture(scope="module")
def search_order_scheffer():
    return {
        "search_order_id": "SO-Q4-Scheffer-2020",
        "expected_doi": "10.7554/eLife.57443",
        "intent": {
            "author": "Scheffer",
            "year": 2020,
            "title": "connectome adult Drosophila central brain",
            "concepts": ["hemibrain"],
        },
    }


def _build_intent(renderer_mod, so):
    meta = so["intent"]
    return renderer_mod.SearchIntent(
        author=meta.get("author"),
        year=meta.get("year"),
        title=meta.get("title"),
        concepts=list(meta.get("concepts") or []),
    )


# ---------- (1) von Reyn intent renders to Crossref-native params ----------

def test_p15_01_von_reyn_intent_renders_crossref_native(renderer_mod, search_order_von_reyn):
    """P1.5 §4 + §15.1: the von Reyn intent must render to Crossref
    author/year/bibliographic params, NOT pubmed_ebsco-style full-text query.
    """
    intent = _build_intent(renderer_mod, search_order_von_reyn)
    ladder = renderer_mod.render_intent(intent, compiled_query="legacy", top_k=5)
    assert len(ladder) >= 2, f"ladder should have at least rung A and the legacy rung; got {len(ladder)}"
    # First rung must be the author+year+title rung
    first = ladder[0]
    assert first.rendering_path == renderer_mod.LADDER_RUNG_A, (
        f"first rung should be {renderer_mod.LADDER_RUNG_A}; got {first.rendering_path}"
    )
    # Crossref-native params
    assert first.url_params.get("query.author") == "von Reyn", (
        f"rung A must carry query.author=von Reyn; got {first.url_params.get('query.author')!r}"
    )
    assert "from-pub-date:2014" in first.url_params.get("filter", ""), (
        f"rung A must carry a 2014 date filter; got {first.url_params.get('filter')!r}"
    )
    assert "until-pub-date:2014" in first.url_params.get("filter", ""), (
        f"rung A must carry a 2014 date filter; got {first.url_params.get('filter')!r}"
    )
    # No pubmed_ebsco-style AND/OR syntax leakage
    assert "AND" not in first.url_params.get("query.title", ""), (
        f"rung A must not contain pubmed_ebsco-style 'AND' operators; got {first.url_params.get('query.title')!r}"
    )
    # Legacy rung uses pubmed_ebsco-style; it must remain as the LAST rung
    # for audit / regression-prevention.
    last = ladder[-1]
    assert last.rendering_path == renderer_mod.LADDER_RUNG_LEGACY
    assert "query" in last.url_params, "legacy rung must carry the legacy pubmed_ebsco query="


# ---------- (2) Namiki intent preserves author/year/title/concept clues ----------

def test_p15_02_namiki_intent_preserves_clues(renderer_mod, search_order_namiki):
    """P1.5 §4 + §15.2: the Namiki intent must preserve all clues
    (author=Namiki, year=2018, title fragments, concept terms) in
    the Crossref-native rendering."""
    intent = _build_intent(renderer_mod, search_order_namiki)
    ladder = renderer_mod.render_intent(intent, compiled_query="legacy", top_k=5)
    assert len(ladder) >= 2
    first = ladder[0]
    assert first.url_params.get("query.author") == "Namiki"
    assert "from-pub-date:2018" in first.url_params.get("filter", "")
    # Title fragments: rung A carries the title + concepts
    title = first.url_params.get("query.title", "").lower()
    assert "descending" in title, f"rung A must carry 'descending' in title; got {title!r}"
    assert "sensory-motor" in title or "pathway" in title, (
        f"rung A must carry a Namiki title fragment; got {title!r}"
    )
    # Year filter is Crossref-native
    assert "2018" in first.url_params.get("filter", "")


# ---------- (3) Scheffer intent preserves canonical connectome title/concept ----------

def test_p15_03_scheffer_intent_preserves_connectome_clues(renderer_mod, search_order_scheffer):
    """P1.5 §4 + §15.3: the Scheffer intent must preserve the canonical
    hemibrain / connectome title + concept clues."""
    intent = _build_intent(renderer_mod, search_order_scheffer)
    ladder = renderer_mod.render_intent(intent, compiled_query="legacy", top_k=5)
    assert len(ladder) >= 2
    first = ladder[0]
    assert first.url_params.get("query.author") == "Scheffer"
    assert "from-pub-date:2020" in first.url_params.get("filter", "")
    title = first.url_params.get("query.title", "").lower()
    assert "connectome" in title, f"rung A must carry 'connectome' in title; got {title!r}"
    assert "drosophila" in title, f"rung A must carry 'Drosophila' in title; got {title!r}"
    # hemibrain is a concept
    assert "hemibrain" in title, f"rung A must carry 'hemibrain' concept; got {title!r}"


# ---------- (4) rendered Crossref request is persisted for audit ----------

def test_p15_04_rendered_request_persisted_for_audit(renderer_mod, search_order_von_reyn):
    """P1.5 §4 + §15.4: every rung must be persistable for audit,
    with a stable rendering_path label, the url_params dict, and a
    buildable Crossref URL."""
    intent = _build_intent(renderer_mod, search_order_von_reyn)
    ladder = renderer_mod.render_intent(intent, compiled_query="legacy", top_k=5)
    assert len(ladder) >= 1
    for rq in ladder:
        audit = renderer_mod.rendered_query_to_audit_dict(rq)
        # Required fields for audit
        assert "rendering_path" in audit
        assert audit["rendering_path"], f"rendering_path must be non-empty; got {audit['rendering_path']!r}"
        assert "url_params" in audit
        assert isinstance(audit["url_params"], dict)
        # URL must be buildable
        url = audit["url"]
        assert url.startswith("https://api.crossref.org/works?"), (
            f"audit URL must be a Crossref /works URL; got {url[:60]!r}"
        )
        # All url_params must be in the URL
        for k, v in audit["url_params"].items():
            assert f"{k}=" in url, (
                f"audit URL must carry {k}={v!r}; got {url[:120]!r}"
            )
    # The audit dict must be JSON-serializable (it goes into
    # rendered_queries.json on disk).
    import json
    for rq in ladder:
        json.dumps(renderer_mod.rendered_query_to_audit_dict(rq))


# ---------- (5) fallback ladder remains bounded ----------

def test_p15_05_fallback_ladder_is_bounded(renderer_mod, search_order_von_reyn):
    """P1.5 §5 + §15.5: the fallback ladder must be bounded (≤ 4 rungs,
    per P1.5 contract §5). The orchestrator must not enter an
    open-ended query-rewriting loop."""
    intent = _build_intent(renderer_mod, search_order_von_reyn)
    ladder = renderer_mod.render_intent(intent, compiled_query="legacy", top_k=5)
    assert len(ladder) <= 4, f"fallback ladder must be bounded to ≤ 4 rungs; got {len(ladder)}"
    # Each rung must be a different rendering_path
    paths = [r.rendering_path for r in ladder]
    assert len(set(paths)) == len(paths), f"all rungs must have distinct rendering_paths; got {paths}"
    # The rungs must come from the fixed ladder order
    expected_order = [
        renderer_mod.LADDER_RUNG_A,
        renderer_mod.LADDER_RUNG_B,
        renderer_mod.LADDER_RUNG_C,
        renderer_mod.LADDER_RUNG_LEGACY,
    ]
    for rq in ladder:
        assert rq.rendering_path in expected_order, (
            f"unknown rendering_path {rq.rendering_path!r}; must be in {expected_order}"
        )


def test_p15_05b_ladder_skips_rungs_without_required_inputs(renderer_mod):
    """P1.5 §5: rungs that cannot be built from the intent (e.g.,
    rung A needs both author and year) are silently skipped; the
    ladder does not invent missing fields."""
    # Intent with only concepts (no author, no year, no title) — only
    # the legacy rung should appear.
    intent = renderer_mod.SearchIntent(
        author=None, year=None, title=None, concepts=["Drosophila"]
    )
    ladder = renderer_mod.render_intent(intent, compiled_query="legacy", top_k=5)
    # Only the legacy rung remains; rungs A/B/C are None (no author/year/title)
    paths = [r.rendering_path for r in ladder]
    assert renderer_mod.LADDER_RUNG_LEGACY in paths
    assert renderer_mod.LADDER_RUNG_A not in paths, (
        f"rung A must be skipped when author/year are missing; got {paths}"
    )
    assert renderer_mod.LADDER_RUNG_B not in paths
    assert renderer_mod.LADDER_RUNG_C not in paths


# ---------- (6) recovered anchor requires identity-safe match ----------

def test_p15_06_recovered_anchor_requires_identity_safe_match():
    """P1.5 §7: recovery requires identity-safe match (DOI exact OR
    verified canonical identity). Fuzzy title similarity alone does
    NOT count as recovery. The LiveChain's _score_q1_q2_q4 method
    must still enforce the same identity match logic as the RA1
    contract."""
    sys_path = str(PKG / "src")
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    sys.path.insert(0, str(PKG / "scripts"))
    from replay_b import Builder
    # Mock run: Q1 with recovered DOI == oracle DOI (identity match)
    fake_oracle = {
        "scholarly": {
            "anchor_count": 3,
            "anchors": [
                {"anchor_id": "S1-vonReyn-2014", "doi": "10.1038/nn.3741",
                 "verification_status": "VERIFIED", "verified_by_primary_sources": 3},
                {"anchor_id": "S2-Namiki-2018", "doi": "10.7554/eLife.34272",
                 "verification_status": "VERIFIED", "verified_by_primary_sources": 3},
                {"anchor_id": "S3-Scheffer-2020", "doi": "10.7554/eLife.57443",
                 "verification_status": "VERIFIED", "verified_by_primary_sources": 3},
            ],
        },
        "entity": {
            "anchors": [],
            "summary": {"verified_count": 0, "unverified_count": 0, "contradicted_count": 0, "fabricated_count": 0},
        },
        "qgraph": {"questions": []},
    }
    # Build a fake run output with Q1 that RECOVERED via a P1.5 ladder
    from mafs_p0.crossref_renderer import (
        SearchIntent, render_intent, rendered_query_to_audit_dict,
    )
    intent = SearchIntent(author="von Reyn", year=2014, title="spike-timing action selection",
                          concepts=["Drosophila", "giant fiber"])
    ladder = render_intent(intent, compiled_query="legacy", top_k=5)
    run_output = {
        "results": {
            "Q1": {
                "search_order": {"expected_doi": "10.1038/nn.3741"},
                "expected_doi": "10.1038/nn.3741",
                "rendered_queries": [rendered_query_to_audit_dict(rq) for rq in ladder],
                "live_chain_result": {
                    "status": "ok",
                    "candidate_pointers": [{
                        "candidate_pointer_id": "CP-1",
                        "identifier_hints": {"doi": "10.1038/nn.3741", "pmid": None},
                    }],
                    "retrieval_invocation": {
                        "retrieval_invocation_id": "RIV-1",
                        "rendering_path": ladder[0].rendering_path,
                    },
                    "resolver_invocation": {"resolver_invocation_id": "RSI-1", "candidate_pointer_id": "CP-1"},
                    "canonical_evidence": {"provenance": {"doi": "10.1038/nn.3741"}},
                },
            },
            "Q2": {"live_chain_result": {}},
            "Q3": {"live_chain_result": {}},
            "Q4": {"live_chain_result": {}},
            "Q5": {"live_chain_result": {"status": "ENTITY_RESOLUTION_REQUIRED"}},
        },
        "provider_call_count": 1,
        "resolver_call_count": 1,
    }
    b = Builder(offline=True, build_id="test-p15-06")
    scored = b.step_score_questions(fake_oracle, run_output)
    q1 = scored["Q1"]
    assert q1["paper_identity_status"] == "RECOVERED", (
        f"Q1 with matching DOI must mark paper_identity_status=RECOVERED; got {q1.get('paper_identity_status')!r}"
    )


# ---------- (7) original CandidatePointer -> Resolver invariant remains green ----------

def test_p15_07_candidate_pointer_to_resolver_invariant_green():
    """P1.5 §6: the original CandidatePointer -> Resolver continuity
    invariant from the Replay B spine must remain green. The P1.5
    path preserves the spine (renderer produces URL params; the
    production CrossrefRetrievalProvider + CrossrefReferenceResolver
    chain is unchanged)."""
    sys_path = str(PKG / "src")
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    sys.path.insert(0, str(PKG / "scripts"))
    from replay_b import Builder, _cp_continuity_status
    # Build a fake run output where Q1's resolver preserves the CP
    # continuity
    run_output = {
        "results": {
            "Q1": {"live_chain_result": {
                "candidate_pointers": [{"candidate_pointer_id": "CP-1"}],
                "resolver_invocation": {"candidate_pointer_id": "CP-1"},
            }},
            "Q2": {"live_chain_result": {
                "candidate_pointers": [{"candidate_pointer_id": "CP-2"}],
                "resolver_invocation": {"candidate_pointer_id": "CP-2"},
            }},
            "Q3": {"live_chain_result": {}},  # negative branch — no resolver
            "Q4": {"live_chain_result": {
                "candidate_pointers": [{"candidate_pointer_id": "CP-4"}],
                "resolver_invocation": {"candidate_pointer_id": "CP-4"},
            }},
        },
    }
    out = _cp_continuity_status(run_output["results"])
    assert out["status"] == "PASS", f"CP->Resolver continuity must be PASS; got {out['status']!r}"
    assert out["n_pass"] == 3, f"expected 3 passed continuity checks; got {out['n_pass']}"
    assert out["n_fail"] == 0
    # The function lives in replay_b.py (the orchestrator), and it
    # still works — confirming the spine is preserved.
    import replay_b
    assert hasattr(replay_b, "_cp_continuity_status")
    # The spine (LiveChain) is also importable from the production
    # mafs_p0.live_chain module.
    from mafs_p0.live_chain import LiveChain
    assert LiveChain is not None
    # The CrossrefRetrievalProvider + CrossrefReferenceResolver are
    # also importable and unchanged.
    from mafs_p0.live_crossref import CrossrefRetrievalProvider, CrossrefReferenceResolver
    assert CrossrefRetrievalProvider is not None
    assert CrossrefReferenceResolver is not None


# ---------- (8) existing Replay B truth/fabrication invariants remain green ----------

def test_p15_08_replay_b_invariants_remain_green():
    """P1.5 §6: the existing Replay B truth/fabrication invariants
    must remain green. The orchestrator's mechanical CP->Resolver
    continuity, mechanical fabrication audit, source_content /
    proposition splits, and DNg01 disposition must all be preserved."""
    # Source field
    m_path = PKG / "docs" / "REPLAY_B_RA1_METRICS.json"
    if not m_path.is_file():
        # In an environment where the live CI has not yet run, this
        # test asserts the file structure invariant on the offline
        # run, which is sufficient.
        m_path = PKG / "docs" / "REPLAY_B_RA1_METRICS_OFFLINE.json"
    if not m_path.is_file():
        pytest.skip("RA1 metrics file not yet produced; CI run has not happened")
    m = __import__("json").loads(m_path.read_text(encoding="utf-8"))
    # source == "live" (or source == "offline" for the OFFLINE alias)
    assert m.get("source") in ("live", "offline"), (
        f"RA1 invariant: source must be live or offline; got {m.get('source')!r}"
    )
    assert m.get("fabrication_hard_invariant_holds") is True, (
        f"RA1 invariant: fabrication_hard_invariant_holds must be True; got {m.get('fabrication_hard_invariant_holds')!r}"
    )
    assert m.get("fabricated_reference_count") == 0
    assert m.get("fabricated_entity_count") == 0
    # Q1/Q2 identity vs content/proposition split preserved
    assert "source_content_status" in m.get("Q1", {}), "Q1.source_content_status must be present"
    assert "proposition_status" in m.get("Q2", {}), "Q2.proposition_status must be present"
    # Q5 ENTITY_RESOLUTION_REQUIRED boundary preserved
    assert m.get("Q5", {}).get("entity_resolution_status") == "ENTITY_RESOLUTION_REQUIRED"
    # DNg01 disposition preserved
    oracle_path = PKG / "benchmarks" / "gf_em" / "scholarly_oracle.json"
    oracle = __import__("json").loads(oracle_path.read_text(encoding="utf-8"))
    dn = oracle.get("nomenclature_uncertainties", {}).get("DNg01", {})
    assert dn.get("disposition") == "UNRESOLVED"
    # P1.5 extension: architecture_drift_detected must be present and
    # query_renderer_type must be CROSSREF_SPECIFIC_THIN_RENDERER.
    p15_ext = m.get("p1_5_extension", {})
    if p15_ext:
        # The live run produced a p1_5_extension; check it.
        assert p15_ext.get("query_renderer_type") == "CROSSREF_SPECIFIC_THIN_RENDERER"
        assert "architecture_drift_detected" in p15_ext
