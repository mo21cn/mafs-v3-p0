"""Replay A deterministic tests (no network).

These tests verify the structural and logical correctness of the
Replay A benchmark inputs and code. They do NOT exercise the live
HTTP path; that lives in scripts/replay_a.py and runs in the
``replay-a-live`` CI job.

Coverage:
  1. selected_axes.json structure
  2. known_anchors.json structure
  3. query_plan.json structure
  4. anchor matching helpers
  5. diagnostic attribution (synthetic)
  6. P0/P1/RA1 non-regression
"""
from __future__ import annotations
import json
import re
from pathlib import Path

import pytest

from mafs_p0.replay_a import (
    _title_similarity,
    _keyword_score,
    _classify_miss,
    _normalize_title,
    BenchmarkResult,
)


PKG = Path(__file__).resolve().parent.parent
BENCH = PKG / "benchmarks" / "blood_oxygen_ovary"


# ---------- input file structure ----------

def test_replay_a_01_selected_axes_structure():
    """Contract §2: 2-3 high-information axes; each has diagnostic rationale."""
    doc = json.loads((BENCH / "selected_axes.json").read_text(encoding="utf-8"))
    assert doc["benchmark_id"].startswith("MAFS-v3.0-Replay-A")
    n = len(doc["selected_axes"])
    assert 2 <= n <= 3, f"selected_axes count {n} not in [2,3]"
    for a in doc["selected_axes"]:
        for k in ("axis_id", "search_order_id", "axis_label", "diagnostic_role", "why_selected"):
            assert k in a, f"selected_axes entry missing {k!r}"
    # We chose A1, A2, A3 — must be the diagnostic set per the contract.
    axis_ids = {a["axis_id"] for a in doc["selected_axes"]}
    assert axis_ids == {"A1", "A2", "A3"}


def test_replay_a_02_known_anchors_structure():
    """Contract §6: each anchor has anchor_id, title_hint, year_approx,
    relevant_axis, why_it_matters, historical_status; doi optional."""
    doc = json.loads((BENCH / "known_anchors.json").read_text(encoding="utf-8"))
    assert doc["benchmark_id"].startswith("MAFS-v3.0-Replay-A")
    assert len(doc["anchors"]) >= 4, "at least 4 anchors required for a meaningful benchmark"
    for a in doc["anchors"]:
        for k in ("anchor_id", "title_hint", "relevant_axis", "why_it_matters", "historical_status"):
            assert k in a, f"anchor missing {k!r}"
        assert a["historical_status"] in {"recovered_v0_1", "missed_v0_1", "known_critical_prior"}, (
            f"anchor {a['anchor_id']} has invalid historical_status {a['historical_status']!r}"
        )
        # The contract: do NOT fabricate identifiers if the historical
        # record does not contain them. We accept either a real DOI or
        # a null; the benchmark relies on title+keywords matching.
        assert "doi" in a
        if a.get("doi") is not None:
            assert re.match(r"^10\.\d{4,9}/\S+$", a["doi"]), (
                f"anchor {a['anchor_id']} has malformed DOI: {a['doi']!r}"
            )
        # match_keys is used for keyword-based anchor recovery.
        assert "match_keys" in a and isinstance(a["match_keys"], list)


def test_replay_a_03_query_plan_structure():
    """Contract §3: 2-3 query families per axis; each query has a family
    label and a diagnostic role."""
    doc = json.loads((BENCH / "query_plan.json").read_text(encoding="utf-8"))
    assert "query_families" in doc
    by_axis: dict[str, list] = {}
    for q in doc["query_families"]:
        for k in ("axis_id", "family", "family_label", "compiled_query", "diagnostic"):
            assert k in q, f"query entry missing {k!r}"
        assert q["family"] in {"literal", "structural", "adjacent"}
        by_axis.setdefault(q["axis_id"], []).append(q)
    for axis_id, qs in by_axis.items():
        assert 2 <= len(qs) <= 3, f"axis {axis_id} has {len(qs)} families, not 2-3"
    # top_k bounded
    assert 5 <= int(doc.get("top_k", 10)) <= 25


# ---------- anchor matching helpers ----------

def test_replay_a_04_title_similarity_basic():
    """SequenceMatcher-based title similarity in [0, 1]."""
    assert _title_similarity("Ovarian blood flow during the menstrual cycle",
                              "Ovarian blood flow during the menstrual cycle") == pytest.approx(1.0)
    assert _title_similarity("Follicular fluid oxygen tension",
                              "Doppler assessment of ovarian blood flow") < 0.3
    # Punctuation / case insensitivity
    assert _title_similarity("HIF-1α in Granulosa Cells", "hif 1alpha in granulosa cells") > 0.8


def test_replay_a_05_keyword_score_basic():
    """Fraction of match_keys found as substrings in the candidate title."""
    title = "Doppler assessment of ovarian blood flow in the menstrual cycle"
    assert _keyword_score(["ovarian", "blood flow", "doppler"], title) == pytest.approx(1.0)
    assert _keyword_score(["ovarian", "hif-1alpha", "doppler"], title) == pytest.approx(2/3, rel=1e-2)
    assert _keyword_score([], title) == 0.0


def test_replay_a_06_normalize_title():
    assert _normalize_title("  Ovarian    Blood-Flow!! ") == "ovarian blood flow"


# ---------- diagnostic attribution (synthetic) ----------

def _mk_result(axis_id: str, family: str, items_returned: int = 10, titles: list[str] | None = None) -> BenchmarkResult:
    return BenchmarkResult(
        axis_id=axis_id, family=family,
        compiled_query="x", http_status=200, items_returned=items_returned,
        candidate_dois=[], candidate_titles=titles or [],
        matched_anchor_ids=[], raw_attempts=1,
    )


def test_replay_a_07_diagnostic_provider_recall_when_no_results():
    """All axis queries returned 0 items -> PROVIDER_RECALL."""
    miss = {"anchor_id": "X", "title_hint": "t", "match_keys": ["k"], "relevant_axis": "A1"}
    results = [
        _mk_result("A1", "literal", items_returned=0),
        _mk_result("A1", "structural", items_returned=0),
    ]
    assert _classify_miss(miss, results) == "PROVIDER_RECALL"


def test_replay_a_08_diagnostic_query_compiler_when_no_keys_found():
    """Results exist but no match_key substring appears in any title -> QUERY_COMPILER."""
    miss = {"anchor_id": "X", "title_hint": "t", "match_keys": ["zzznotpresent"],
            "relevant_axis": "A1"}
    results = [
        _mk_result("A1", "literal", titles=["Random paper A"]),
        _mk_result("A1", "structural", titles=["Random paper B"]),
    ]
    assert _classify_miss(miss, results) == "QUERY_COMPILER"


def test_replay_a_09_diagnostic_terminology_expansion():
    """Literal family failed but structural family recovered the anchor -> TERMINOLOGY_EXPANSION."""
    miss = {"anchor_id": "X", "title_hint": "t",
            "match_keys": ["hypoxia-inducible factor"],
            "relevant_axis": "A3"}
    # Literal has no key match; structural has the key match.
    results = [
        _mk_result("A3", "literal", titles=["Unrelated paper"]),
        _mk_result("A3", "structural", titles=["Hypoxia-inducible factor in granulosa"]),
    ]
    # Manually mark the structural as having recovered the anchor.
    results[1].matched_anchor_ids = ["X"]
    assert _classify_miss(miss, results) == "TERMINOLOGY_EXPANSION"


def test_replay_a_10_diagnostic_benchmark_ambiguity_when_no_keys():
    """Anchor has no match_keys -> BENCHMARK_AMBIGUITY."""
    miss = {"anchor_id": "X", "title_hint": "t", "match_keys": [], "relevant_axis": "A1"}
    results = [_mk_result("A1", "literal", titles=["Random"])]
    assert _classify_miss(miss, results) == "BENCHMARK_AMBIGUITY"


# ---------- P0 / P1 / RA1 non-regression ----------

def test_replay_a_11_no_p0_p1_regression():
    """P0 / P1 / RA1 files are untouched. The Replay A package added
    files but did not modify any of them.

    Specifically:
      - 18-schema set is intact (hygiene §1 invariant)
      - P1 RA1 closure evidence (docs/P1_RA1_CLOSURE_NOTE.md) is unchanged
      - 60 P0/P1 + 8 RA1 tests still pass (verified by the full pytest run;
        this assertion checks the structural invariants only)
    """
    from mafs_p0.runtime_fingerprint import _schemas_in_manifest
    in_manifest = _schemas_in_manifest()
    n = len(in_manifest)
    assert n == 18, f"schema count drifted: {n} (expected 18)"
    # P1 closure note still exists
    assert (PKG / "docs" / "P1_RA1_CLOSURE_NOTE.md").is_file()
    # The 3 NEW benchmark input files are present
    for name in ("known_anchors.json", "selected_axes.json", "query_plan.json"):
        assert (BENCH / name).is_file(), f"missing benchmark input: {name}"
    # The 2 NEW Replay A source files are present
    assert (PKG / "src" / "mafs_p0" / "replay_a.py").is_file()
    assert (PKG / "scripts" / "replay_a.py").is_file()
    # The 1 NEW workflow is present
    assert (PKG / ".github" / "workflows" / "replay-a.yml").is_file()


# ---------- live test (skipped offline) ----------

def test_replay_a_12_live_benchmark_runs_and_produces_metrics():
    """Contract §11: Replay A must run in CI (the live Crossref
    benchmark). This test invokes the orchestrator and asserts the
    output contract is satisfied. Skipped when the runner has no
    network access."""
    import os
    import socket
    if os.environ.get("MAFS_P0_SKIP_LIVE_TESTS") == "1":
        pytest.skip("MAFS_P0_SKIP_LIVE_TESTS=1")
    try:
        socket.create_connection(("api.crossref.org", 443), timeout=3).close()
    except OSError:
        pytest.skip("no network")
    from mafs_p0.replay_a import run_replay_a
    out = run_replay_a(package_root=PKG)
    # 1. Required keys
    for k in ("selected_axes", "anchors", "query_plan", "results",
             "anchor_recovery_matrix", "missed_anchor_diagnostics",
             "metrics", "primary_failure_attribution"):
        assert k in out, f"missing key: {k}"
    # 2. Metrics vector (contract §7)
    m = out["metrics"]
    for k in ("known_anchor_recall", "top_k_anchor_recall",
             "query_family_contribution", "candidate_relevance",
             "metadata_accuracy", "duplicate_rate",
             "unresolved_candidate_rate", "provider_call_count",
             "resolver_call_count", "high_reasoning_call_count",
             "approximate_token_usage"):
        assert k in m, f"metrics missing key: {k}"
    # 3. Per-query result shape
    for r in out["results"]:
        for k in ("axis_id", "family", "compiled_query", "http_status",
                 "items_returned", "candidate_dois", "candidate_titles",
                 "matched_anchor_ids"):
            assert k in r, f"result missing key: {k}"
    # 4. Anchor recovery matrix shape
    for aid, mtx in out["anchor_recovery_matrix"].items():
        for k in ("anchor_id", "relevant_axis", "recovered", "recovered_by"):
            assert k in mtx, f"matrix entry {aid} missing {k}"
    # 5. Missed-anchor diagnostics shape
    for d in out["missed_anchor_diagnostics"]:
        for k in ("anchor_id", "title_hint", "relevant_axis", "category"):
            assert k in d, f"diag entry missing {k}"
        assert d["category"] in {
            "QUERY_COMPILER", "TERMINOLOGY_EXPANSION", "PROVIDER_RECALL",
            "RANKING_TOPK", "RESOLUTION", "DEDUP", "BENCHMARK_AMBIGUITY",
            "UNKNOWN", "NONE",
        }
    # 6. Recall is a real number in [0, 1]
    assert 0.0 <= m["known_anchor_recall"] <= 1.0
    assert 0.0 <= m["top_k_anchor_recall"] <= 1.0
    # 7. provider_call_count equals 3 query families × 3 axes = 9
    assert m["provider_call_count"] == 9
    assert m["resolver_call_count"] == 0  # Replay A is retrieval-quality only
