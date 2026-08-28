"""Replay A — Retrieval Recall Checkpoint (contract MAFS-v3.0-REPLAY-A).

Reuses the v3.0 live chain (SearchOrder -> Query AST -> Retrieval
Provider -> CandidatePointer -> Reference Resolver -> Canonical Evidence)
and runs a bounded benchmark against the Blood-Oxygen-Ovary
historical task. The benchmark is **diagnostic**, not self-healing.

Inputs (machine-readable benchmark files under
``benchmarks/blood_oxygen_ovary/``):
  - known_anchors.json — the small reference set; historical_status
    is one of {recovered_v0_1, missed_v0_1, known_critical_prior}
  - selected_axes.json — 2-3 axes with diagnostic rationale
  - query_plan.json — 2-3 query families per axis (literal / structural
    / adjacent)

Outputs (12 required artifacts under ``examples/runs/ReplayA/``):
  REPLAY_A_SUMMARY.md, REPLAY_A_METRICS.json, REPLAY_A_CI_PROVENANCE.md,
  REPLAY_A_SHA256_MANIFEST.txt, retrieval_results.json,
  anchor_recovery_matrix.json, missed_anchor_diagnostics.json,
  plus the existing benchmark files (copied) and runtime_fingerprint.json.
  P1 invocation / snapshot objects are not duplicated; the
  ``retrieval_results.json`` references them by id.

Bounded autonomy (per contract §15):
  - we choose the exact 2-3 axes (A1, A2, A3 — see
    benchmarks/blood_oxygen_ovary/selected_axes.json for rationale)
  - we choose the exact 2-3 query families per axis
  - top_k = 10 (small bounded)
  - we do NOT add providers, do NOT rewrite scientific framing, do NOT
    issue a final scientific Gate.
"""
from __future__ import annotations
import difflib
import hashlib
import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---- Constants --------------------------------------------------------------

USER_AGENT = "MAFS-v3.0-Replay-A/0.1 (Local-Claw; mailto:mo21cn@example.invalid)"
HTTP_TIMEOUT = 30


# ---- Live HTTP (independent of the P1 chain to keep this benchmark
# ---- self-contained and to avoid coupling on internals) ---------------

def _http_get_json(url: str) -> tuple[int, dict | None, str]:
    """Single GET that returns parsed JSON or (status, None, body_str).
    0 status means network / parse failure.
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            status = resp.getcode()
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return status, json.loads(body), body
            except json.JSONDecodeError:
                return status, None, body
    except urllib.error.HTTPError as e:
        return e.code, None, e.read().decode("utf-8", errors="replace") if e.fp else ""
    except (urllib.error.URLError, TimeoutError, Exception):
        return 0, None, ""


# ---- Anchor matching -------------------------------------------------------

def _normalize_title(t: str | None) -> str:
    if not t:
        return ""
    t = t.lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _title_similarity(a: str | None, b: str | None) -> float:
    """Crude similarity in [0, 1]. We use the SequenceMatcher ratio on
    normalized titles; we do NOT use fuzzy stemmers or embeddings
    because the contract says the benchmark should be lightweight.
    """
    a, b = _normalize_title(a), _normalize_title(b)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _keyword_score(query_match_keys: list[str], title: str) -> float:
    """Fraction of match_keys that appear (as substrings) in the title.
    Used to recover anchors that lack a stable identifier."""
    if not query_match_keys:
        return 0.0
    nlow = _normalize_title(title)
    if not nlow:
        return 0.0
    hits = 0
    for k in query_match_keys:
        if _normalize_title(k) in nlow:
            hits += 1
    return hits / len(query_match_keys)


# ---- One benchmark call ---------------------------------------------------

@dataclass
class BenchmarkResult:
    axis_id: str
    family: str
    compiled_query: str
    http_status: int
    items_returned: int
    candidate_dois: list[str]
    candidate_titles: list[str]
    matched_anchor_ids: list[str]
    raw_attempts: int

    def to_dict(self) -> dict:
        return {
            "axis_id": self.axis_id,
            "family": self.family,
            "compiled_query": self.compiled_query,
            "http_status": self.http_status,
            "items_returned": self.items_returned,
            "candidate_dois": self.candidate_dois,
            "candidate_titles": self.candidate_titles,
            "matched_anchor_ids": self.matched_anchor_ids,
        }


def _run_one_query(query_entry: dict, anchors: list[dict], top_k: int) -> BenchmarkResult:
    """Run one benchmark query against Crossref and match the result set
    against the anchor list.

    The matching is twofold:
      1. If the anchor has a doi, we match by exact doi.
      2. Otherwise, we use the ``match_keys`` + ``title_hint`` fields
         on the anchor: an anchor is "recovered" if any of the
         candidate titles has either:
         - SequenceMatcher ratio >= 0.65 with the anchor's title_hint, OR
         - keyword_score(anchor.match_keys, candidate_title) >= 0.5
    """
    q = query_entry["compiled_query"]
    url = f"https://api.crossref.org/works?{urllib.parse.urlencode({'query': q, 'rows': str(top_k)})}"
    status, payload, _body = _http_get_json(url)
    items = []
    if payload and isinstance(payload, dict):
        msg = payload.get("message") or {}
        items = msg.get("items") or []
    dois = []
    titles = []
    for item in items:
        d = item.get("DOI")
        if d:
            dois.append(d.lower())
        tlist = item.get("title") or []
        t0 = tlist[0] if tlist else None
        if t0:
            titles.append(t0)
    # Match against anchors
    matched: list[str] = []
    for anc in anchors:
        if anc.get("relevant_axis") and anc.get("relevant_axis") != query_entry.get("axis_id"):
            # skip anchors from other axes for this query (avoids
            # accidental cross-axis matches)
            continue
        anc_doi = (anc.get("doi") or "").lower() or None
        anc_title = anc.get("title_hint")
        anc_keys = anc.get("match_keys") or []
        anchor_id = anc["anchor_id"]
        # DOI exact match
        if anc_doi and anc_doi in dois:
            matched.append(anchor_id)
            continue
        # Title / keyword fuzzy match
        for ct in titles:
            sim = _title_similarity(anc_title, ct)
            ks = _keyword_score(anc_keys, ct)
            if sim >= 0.65 or ks >= 0.5:
                matched.append(anchor_id)
                break
    return BenchmarkResult(
        axis_id=query_entry["axis_id"],
        family=query_entry["family"],
        compiled_query=q,
        http_status=status,
        items_returned=len(items),
        candidate_dois=dois,
        candidate_titles=titles,
        matched_anchor_ids=matched,
        raw_attempts=1,
    )


# ---- Diagnostic attribution -----------------------------------------------

def _classify_miss(miss: dict, all_results: list[BenchmarkResult]) -> str:
    """One of the contract §9 categories.

    Heuristics (the contract allows UNKNOWN when causality is unclear):
      - BENCHMARK_AMBIGUITY: anchor's match_keys are very generic
      - RANKING_TOPK: anchor's title appears in a candidate list but
        outside top_k (we searched 10)
      - PROVIDER_RECALL: no Crossref hit at all (http_status != 200 OR
        item_count == 0)
      - QUERY_COMPILER: Crossref returned items but the anchor's
        distinct terms don't appear in any result title
      - RESOLUTION: n/a for retrieval recall (we don't resolve anchors)
      - TERMINOLOGY_EXPANSION: Crossref returned items but only for
        some families; the literal family fails
      - UNKNOWN: cannot attribute
    """
    keys = miss.get("match_keys") or []
    if not keys:
        return "BENCHMARK_AMBIGUITY"
    # Did ANY query family for this axis return the anchor in candidates?
    axis_results = [r for r in all_results if r.axis_id == miss.get("relevant_axis")]
    if not axis_results:
        return "UNKNOWN"
    any_200 = any(r.http_status == 200 and r.items_returned > 0 for r in axis_results)
    if not any_200:
        return "PROVIDER_RECALL"
    # If we found anything, but never the anchor's exact words, attribute
    # to QUERY_COMPILER or TERMINOLOGY_EXPANSION.
    found_keys = False
    for r in axis_results:
        titles_concat = " ".join(_normalize_title(t) for t in r.candidate_titles)
        for k in keys:
            if _normalize_title(k) in titles_concat:
                found_keys = True
                break
        if found_keys:
            break
    if not found_keys:
        return "QUERY_COMPILER"
    # If literal family failed but structural succeeded, it's expansion.
    literal_results = [r for r in axis_results if r.family == "literal"]
    structural_results = [r for r in axis_results if r.family == "structural"]
    if literal_results and not any(miss["anchor_id"] in r.matched_anchor_ids for r in literal_results):
        if structural_results and any(miss["anchor_id"] in r.matched_anchor_ids for r in structural_results):
            return "TERMINOLOGY_EXPANSION"
    return "UNKNOWN"


# ---- Top-level orchestrator -----------------------------------------------

def run_replay_a(*, package_root: Path) -> dict:
    """Run the bounded Replay A benchmark.

    Returns a dict with all the per-query results, the anchor recovery
    matrix, the metrics vector, and the missed-anchor diagnostics.
    Caller is expected to persist the result via scripts/replay_a.py.
    """
    pkg = Path(package_root)
    bench_dir = pkg / "benchmarks" / "blood_oxygen_ovary"
    axes_doc = json.loads((bench_dir / "selected_axes.json").read_text(encoding="utf-8"))
    anchors_doc = json.loads((bench_dir / "known_anchors.json").read_text(encoding="utf-8"))
    query_plan = json.loads((bench_dir / "query_plan.json").read_text(encoding="utf-8"))
    anchors = anchors_doc["anchors"]
    top_k = int(query_plan.get("top_k", 10))

    results: list[BenchmarkResult] = []
    for q in query_plan["query_families"]:
        results.append(_run_one_query(q, anchors, top_k))

    # Anchor recovery matrix: which anchor was recovered by which query
    # family at which rank.
    matrix: dict[str, dict] = {}
    for anc in anchors:
        aid = anc["anchor_id"]
        rows = []
        for r in results:
            if aid in r.matched_anchor_ids:
                # Find the rank of the first match in candidate_titles /
                # candidate_dois. We don't track per-candidate rank
                # precisely, so we record "matched" with the family
                # and the items_returned of that family.
                rows.append({
                    "axis_id": r.axis_id,
                    "family": r.family,
                    "items_returned_in_family": r.items_returned,
                    "rank_in_family": "matched",  # not tracked per-rank here
                })
        matrix[aid] = {
            "anchor_id": aid,
            "title_hint": anc.get("title_hint"),
            "relevant_axis": anc.get("relevant_axis"),
            "historical_status": anc.get("historical_status"),
            "recovered": bool(rows),
            "recovered_by": rows,
        }

    recovered_ids = sorted({aid for aid, m in matrix.items() if m["recovered"]})
    missed_ids = sorted({aid for aid, m in matrix.items() if not m["recovered"]})

    # Missed-anchor diagnostics
    diagnostics = []
    for aid in missed_ids:
        anc = next(a for a in anchors if a["anchor_id"] == aid)
        diagnostics.append({
            "anchor_id": aid,
            "title_hint": anc.get("title_hint"),
            "relevant_axis": anc.get("relevant_axis"),
            "category": _classify_miss(anc, results),
        })

    # Top-k anchor recall: how many of the recovered anchors were
    # surfaced by the literal family? (literal == the most demanding
    # test; a recovered-but-not-by-literal anchor is a terminology
    # expansion success, not a top-k success).
    topk_anchor_recall = sum(
        1 for aid in recovered_ids
        if any(r.family == "literal" and aid in r.matched_anchor_ids
               for r in results if r.axis_id == next(a for a in anchors if a["anchor_id"] == aid)["relevant_axis"])
    )
    topk_anchor_recall = topk_anchor_recall / max(1, len(anchors))

    # Per-family contribution: how many unique anchors did each family recover?
    family_contribution: dict[str, int] = {}
    for r in results:
        family_contribution.setdefault(r.family, 0)
        for aid in r.matched_anchor_ids:
            family_contribution[r.family] += 1

    # Duplicate rate: how many duplicate candidate_dois across all families
    all_dois: list[str] = []
    for r in results:
        all_dois.extend(r.candidate_dois)
    n_total = len(all_dois)
    n_unique = len(set(all_dois))
    duplicate_rate = (n_total - n_unique) / max(1, n_total)

    # Provider / resolver call counts
    provider_call_count = len(results)  # one per query family
    resolver_call_count = 0  # this benchmark does not resolve the
                              # top-1; resolution is the P1 chain's job.
                              # Replay A is retrieval-quality only.

    # High-reasoning call count: 0 (no LLM calls in this benchmark).
    high_reasoning_call_count = 0

    # Token usage: 0 (no LLM calls).
    approximate_token_usage = 0

    metrics = {
        "axes_evaluated": [a["axis_id"] for a in axes_doc["selected_axes"]],
        "query_families_per_axis": 3,
        "top_k": top_k,
        "known_anchor_count": len(anchors),
        "recovered_anchor_count": len(recovered_ids),
        "missed_anchor_count": len(missed_ids),
        "known_anchor_recall": len(recovered_ids) / max(1, len(anchors)),
        "top_k_anchor_recall": topk_anchor_recall,
        "query_family_contribution": family_contribution,
        "candidate_relevance": {
            # We do NOT do full Level 3/4 adjudication in Replay A;
            # the contract §8 says this is retrieval-quality only.
            # We report raw counts; HO + GPT decide relevance.
            "total_candidates": n_total,
            "unique_candidates": n_unique,
        },
        "metadata_accuracy": "not_evaluated_in_replay_a (P2+ concern)",
        "duplicate_rate": duplicate_rate,
        "unresolved_candidate_rate": 0.0,  # we don't resolve in Replay A
        "provider_call_count": provider_call_count,
        "resolver_call_count": resolver_call_count,
        "high_reasoning_call_count": high_reasoning_call_count,
        "approximate_token_usage": approximate_token_usage,
    }

    primary_failure = "NONE"
    if missed_ids:
        # Pick the most common SPECIFIC diagnostic category among misses.
        # UNKNOWN is the "I don't know" answer and must NOT dominate over
        # a known classification; the heuristic prefers the largest
        # specific (non-UNKNOWN) category. Only if every miss is UNKNOWN
        # do we report UNKNOWN.
        cats: dict[str, int] = {}
        for d in diagnostics:
            cats[d["category"]] = cats.get(d["category"], 0) + 1
        specific = {k: v for k, v in cats.items() if k != "UNKNOWN"}
        if specific:
            primary_failure = max(specific, key=specific.get)
        elif cats:
            primary_failure = "UNKNOWN"

    return {
        "selected_axes": axes_doc["selected_axes"],
        "anchors": anchors,
        "query_plan": query_plan,
        "results": [r.to_dict() for r in results],
        "anchor_recovery_matrix": matrix,
        "missed_anchor_diagnostics": diagnostics,
        "metrics": metrics,
        "primary_failure_attribution": primary_failure,
    }


# ---- Public entry ----------------------------------------------------------

def main() -> int:
    import sys
    # Run from the package root (parent of src/).
    pkg_root = Path(__file__).resolve().parent.parent
    result = run_replay_a(package_root=pkg_root)
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
