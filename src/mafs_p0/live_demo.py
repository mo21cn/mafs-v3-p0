"""P1-minimum live demo: positive (one real chain) + negative (no fabricated evidence).

This is the entrypoint for the P1 live smoke. It:

  1. Reuses the P0 positive demo to obtain a real SearchOrder and its
     compiled query (one of the A1-A10 axes from the Blood Oxygen Ovary
     Axis Target Freeze fixture).
  2. Runs the Crossref live chain: discover -> resolve -> canonical evidence.
  3. Runs the negative-path chain: deliberately unreachable backend,
     which must produce ``status="failed_network"`` and ``canonical_evidence=None``
     (contract §11: never fabricate evidence).
  4. Returns a dict containing both runs, plus the capability-check
     matrix and the live evidence snapshot digests.

The CI live-smoke job (``mafs-p1-live.yml``) calls this function and
uploads the resulting artifacts as the P1 acceptance evidence.

Bounded autonomy (per contract §16):
  * Single chain (SO-A1-01) for the positive demo.
  * Single deliberate failure for the negative demo.
  * Top-k = 5 for discovery, top-1 for resolution.
  * No retries. Failures are recorded explicitly.
"""
from __future__ import annotations
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Ensure src/ is on sys.path so this file works as a script.
_PKG = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PKG / "src"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pick_demo_search_order_and_query() -> tuple[dict, str]:
    """Reuse the P0 demo to obtain a real SearchOrder and its compiled query.

    Returns ``(search_order_dict, compiled_query_string)``.

    The P0 demo compiles all 10 search orders. We pick the FIRST one
    (A1, ``SO-A1-01``) because its query is a simple AND-of-(phrase,
    OR-of-2-phrases) that Crossref's /works?query= endpoint handles
    cleanly (no field tags, no MeSH, no date ranges).
    """
    from mafs_p0.demo import run_positive_demo
    # The P0 demo writes its full run JSON to a temp file by default;
    # we re-run it here and grab the in-memory result instead.
    p0 = run_positive_demo(tf_path=None, out_path=None)
    sos = p0["search_orders"]
    cqs = p0["compiled_queries"]
    # The two lists are in the same axis order; pair by axis.
    so_by_id = {so["search_order_id"]: so for so in sos}
    cq_by_id = {cq["query_ast_sha256"]: cq for cq in cqs}
    so = sos[0]
    # Find the compiled query whose search_order matches. The P0 demo
    # doesn't carry the search_order_id in the compiled_query, so we
    # pair by axis order instead.
    idx = 0
    cq = cqs[idx]
    return so, cq["rendered_query"]


def run_p1_live_demo(*, allow_network: bool = True) -> dict:
    """Run the P1 live chain + negative path.

    Returns a dict with the full artifact set (contract §19):
        positive_run, negative_run, capability_check, summary
    """
    from mafs_p0.live_chain import LiveChain, run_negative_chain
    from mafs_p0.live_crossref import CrossrefRetrievalProvider
    from mafs_p0.crossref_renderer import LADDER_RUNG_LEGACY

    # ---- Positive chain ----
    so, compiled_query = _pick_demo_search_order_and_query()
    if allow_network:
        # P1.5-RA2 §2.2 + §2.4: LiveChain requires explicit candidate-
        # level selection. The legacy pre-P1.5 path (compiled_query
        # only) is treated as a single rung with rendering_path=
        # LADDER_RUNG_LEGACY. We do a real discovery first, then
        # build the chain with the explicit external_selection. The
        # selection uses {rendering_path, doi} rather than
        # {rendering_path, candidate_pointer_id} so the caller's
        # discovery (whose cp_id namespace differs from the
        # LiveChain's internal walk) can still target the same
        # paper.
        provider = CrossrefRetrievalProvider()
        cands, _riv, _snap = provider.discover(
            search_order_id=so["search_order_id"],
            compiled_query=compiled_query,
            top_k=5,
        )
        if cands:
            top1 = cands[0]
            top1_doi = (top1.get("identifier_hints", {}) or {}).get("doi")
            chain = LiveChain(
                search_order=so,
                compiled_query=compiled_query,
                top_k=5,
                external_selection={
                    "rendering_path": LADDER_RUNG_LEGACY,
                    "doi": top1_doi,
                    "candidate_pointer_id": top1["candidate_pointer_id"],
                },
            )
            positive = chain.run()
        else:
            # Honest no-evidence state; the P1 contract's expected
            # "ok" status is not forced — the network is an
            # external authority per P1.5-RA2 §1.
            positive = {
                "status": "ladder_completed_no_selection",
                "search_order_id": so["search_order_id"],
                "compiled_query": compiled_query,
                "candidate_pointers": [],
                "retrieval_invocation": _riv,
                "retrieval_snapshot": _snap,
                "canonical_evidence": None,
                "resolver_invocation": None,
                "resolver_snapshot": None,
                "missing_capabilities": None,
                "capability_check": {
                    "required": so.get("required_capabilities", []),
                    "advertised_by_provider": ["search.query", "search.boolean", "search.pagination", "result.ranked"],
                    "advertised_by_resolver": ["resolve.doi", "metadata.snapshot", "metadata.canonical"],
                },
            }
    else:
        # Offline mode: same call structure, but the live provider
        # would have to be mocked. The CI live smoke runs with
        # network; local developers can pass allow_network=False
        # if they want to skip the network call (not used in CI).
        positive = {
            "status": "skipped_offline",
            "search_order_id": so["search_order_id"],
            "compiled_query": compiled_query,
            "candidate_pointers": [],
            "retrieval_invocation": None,
            "retrieval_snapshot": None,
            "canonical_evidence": None,
            "resolver_invocation": None,
            "resolver_snapshot": None,
            "missing_capabilities": None,
            "capability_check": {
                "required": so.get("required_capabilities", []),
                "advertised_by_provider": ["search.query", "search.boolean", "search.pagination", "result.ranked"],
                "advertised_by_resolver": ["resolve.doi", "metadata.snapshot", "metadata.canonical"],
            },
        }
    # ---- Negative chain (always; uses TEST-NET-1 unroutable host) ----
    if allow_network:
        negative = run_negative_chain(search_order=so, compiled_query=compiled_query)
    else:
        negative = {
            "status": "skipped_offline",
            "search_order_id": so["search_order_id"],
            "compiled_query": compiled_query,
            "candidate_pointers": [],
            "retrieval_invocation": None,
            "retrieval_snapshot": None,
            "canonical_evidence": None,
        }
    # ---- Summary ----
    summary = {
        "positive_status": positive["status"],
        "negative_status": negative["status"],
        "search_order_id": so["search_order_id"],
        "compiled_query": compiled_query,
        "evidence_count": 1 if positive.get("canonical_evidence") else 0,
        "candidate_count": len(positive.get("candidate_pointers") or []),
        "snapshot_digests": {
            "retrieval": (positive.get("retrieval_invocation") or {}).get("raw_snapshot_sha256"),
            "resolver": (positive.get("resolver_invocation") or {}).get("raw_snapshot_sha256"),
        },
        "completed_at": _now_iso(),
    }
    return {
        "summary": summary,
        "positive_run": positive,
        "negative_run": negative,
        "search_order": so,
    }
