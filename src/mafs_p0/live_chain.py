"""P1.5-minimum live chain — two-phase deterministic execution.

P1.5-RA3 §1 governing principle: a deterministic execution step
may return before resolution. That is a normal state.

The LiveChain class exposes the execution boundary as two separate
deterministic calls:

  chain = LiveChain(search_order=so, rendered_queries=rungs)
  discovery = chain.discover()        # real retrieval, no resolution
  # ... model / caller decides which CandidatePointer to resolve ...
  result = chain.resolve(discovery,    # real retrieval state carried through
                         {rendering_path: "A_...",
                          candidate_pointer_id: "CP-..."})  # explicit selection

The chain does NOT auto-pick top-1, does NOT auto-canonize, does
NOT synthesize a fake retrieval identity, does NOT
fabricate a zero-filled snapshot hash. Real retrieval provenance
survives from `discover()` through `resolve()` and into the
CanonicalEvidence (P1.5-RA3 Closure A).

If selection authority belongs to the model / caller, the
deterministic code must expose the intermediate state and stop
until an explicit selection exists. There is no requirement
that one method call must run discover → select → resolve
end-to-end. The implementation must not preserve a one-shot
pipeline merely because that is a familiar software pattern.

The chain still preserves the explicit-selection boundary
introduced in P1.5-RA2: rung selection alone is insufficient
(`candidate_selection_required`); the selected CandidatePointer
must exist in the selected rung (`invalid_external_selection`
otherwise); a valid selection resolves exactly that one
CandidatePointer. Per P1.5-RA2 §2.4 the chain preserves the
CP -> Resolver identity. Per P1.5-RA3 Closure C continuity is
defined as `selected_candidate_pointer_id ==
resolver_invocation.candidate_pointer_id`, with no top-1
dependency. Per P1.5-RA3 Closure D rank truth is fail-closed:
known rank → integer; missing rank → null + rank_status =
NOT_EVALUATED_RANK_MISSING. No `else 1` fallback.

Bounded autonomy (per contract §16):
  * Top-k for discovery: 5.
  * Resolution depth: 1 (the single caller-selected CandidatePointer).
  * No retries. Failures are recorded with explicit status; they
    do not fabricate evidence (contract §11).

The orchestrator is deliberately small (no caching, no streaming,
no concurrency). It is a one-chain smoke.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from .live_crossref import (
    CrossrefRetrievalProvider,
    CrossrefReferenceResolver,
    PROVIDER_CAPABILITIES,
    RESOLVER_CAPABILITIES,
    _new_id,
    _now_iso,
)
from .crossref_renderer import LADDER_RUNG_LEGACY


@dataclass
class LiveChain:
    """A single bounded live chain.

    P1.5-RA3 (Closure A): the prior synthetic-bridge parameter and
    the synthetic retrieval identity are physically removed.
    The chain has exactly two public
    execution methods:

    - `discover()` returns the real retrieval state.
    - `resolve(discovery, selection)` returns CanonicalEvidence
      for an explicitly selected CandidatePointer drawn from
      the discovery.

    `run()` is removed. Callers that previously did
    ``chain.run()`` must call ``chain.discover()`` and then
    ``chain.resolve(discovery, selection)`` separately. The
    intermediate `discovery` is the handoff artifact between the
    two phases (P1.5-RA3 Closure B).
    """
    search_order: dict
    compiled_query: str = ""
    top_k: int = 5
    rendered_queries: list = field(default_factory=list)  # list of RenderedQuery
    artifacts: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"

    def discover(self) -> dict:
        """Walk the bounded Crossref ladder (or the legacy path) and
        return the real retrieval state. No resolution is performed;
        the resolver is NOT invoked. The returned dict carries the
        real retrieval_invocation_id and real raw_snapshot_sha256
        for every rung the chain walked.

        Returned shape:
        {
          "status": "discovered" | "failed_capability_mismatch",
          "search_order_id": str,
          "compiled_query": str,
          "retrieval_invocations": [list of rung retrieval invocations],
          "retrieval_snapshots":   [list of rung retrieval snapshots],
          "rung_candidate_sets":   [list of {rendering_path,
                                             candidate_count,
                                             candidate_pointers: [...]}],
          "ladder_attempts":       [list of audit dicts per rung],
          "candidates_by_rung":    {rendering_path: [candidates]}  # internal
        }
        """
        so_id = self.search_order["search_order_id"]
        # Capability advertisement check (contract §17.1): the
        # provider must advertise the SearchOrder's required capabilities.
        provider = CrossrefRetrievalProvider()
        required = set(self.search_order.get("required_capabilities") or [])
        advertised = set(provider.capabilities)
        missing = required - advertised
        if missing:
            return {
                "status": "failed_capability_mismatch",
                "search_order_id": so_id,
                "compiled_query": self.compiled_query,
                "retrieval_invocations": [],
                "retrieval_snapshots": [],
                "rung_candidate_sets": [],
                "ladder_attempts": [],
                "candidates_by_rung": {},
                "missing_capabilities": sorted(missing),
            }
        # Walk the bounded ladder. P1.5-RA1 §5.2: every rung's full
        # candidate set is recorded for audit. P1.5-RA2 §2.2 + RA3
        # Closure A: NO synthetic bridge. NO zero-SHA provenance.
        # NO `pre_walked` path. Real HTTP, real snapshot, real
        # retrieval_invocation_id.
        retrieval_invocations: list[dict] = []
        retrieval_snapshots: list[dict] = []
        rung_candidate_sets: list[dict] = []
        ladder_attempts: list[dict] = []
        candidates_by_rung: dict[str, list[dict]] = {}
        if self.rendered_queries:
            for rq in self.rendered_queries:
                cands, ri, rs = provider.discover(
                    search_order_id=so_id,
                    url_params=rq.url_params,
                    rendering_path=rq.rendering_path,
                    top_k=self.top_k,
                )
                candidates_by_rung[rq.rendering_path] = list(cands)
                retrieval_invocations.append(ri)
                retrieval_snapshots.append(rs)
                rung_candidate_sets.append({
                    "rendering_path": rq.rendering_path,
                    "candidate_count": len(cands),
                    "candidate_pointers": list(cands),  # full audit
                })
                ladder_attempts.append({
                    "rendering_path": rq.rendering_path,
                    "url_params": dict(rq.url_params),
                    "candidate_count": len(cands),
                    "top_doi": (cands[0].get("identifier_hints", {}).get("doi") if cands else None),
                    "retrieval_invocation_id": ri["retrieval_invocation_id"],
                    "http_status": ri.get("response", {}).get("http_status"),
                    "status": ri["status"],
                })
        else:
            # Legacy pre-P1.5 path: single full-text query, treated
            # as a single rung with rendering_path=LADDER_RUNG_LEGACY.
            # Same strict explicit-selection boundary applies
            # (P1.5-RA2 §2.2; P1.5-RA3 Closure A).
            cands, ri, rs = provider.discover(
                search_order_id=so_id,
                compiled_query=self.compiled_query,
                top_k=self.top_k,
            )
            candidates_by_rung[LADDER_RUNG_LEGACY] = list(cands)
            retrieval_invocations.append(ri)
            retrieval_snapshots.append(rs)
            if cands:
                rung_candidate_sets.append({
                    "rendering_path": LADDER_RUNG_LEGACY,
                    "candidate_count": len(cands),
                    "candidate_pointers": list(cands),
                })
                ladder_attempts.append({
                    "rendering_path": LADDER_RUNG_LEGACY,
                    "url_params": {"query": self.compiled_query, "rows": str(self.top_k)},
                    "candidate_count": len(cands),
                    "top_doi": (cands[0].get("identifier_hints", {}).get("doi") if cands else None),
                    "retrieval_invocation_id": ri["retrieval_invocation_id"],
                    "http_status": ri.get("response", {}).get("http_status"),
                    "status": ri["status"],
                })
        return {
            "status": "discovered",
            "search_order_id": so_id,
            "compiled_query": self.compiled_query,
            "retrieval_invocations": retrieval_invocations,
            "retrieval_snapshots": retrieval_snapshots,
            "rung_candidate_sets": rung_candidate_sets,
            "ladder_attempts": ladder_attempts,
            "candidates_by_rung": candidates_by_rung,
        }

    def resolve(self, discovery_result: dict, external_selection: dict | None) -> dict:
        """Resolve the explicitly selected CandidatePointer.

        P1.5-RA3 Closure C: the only valid continuity invariant is
            selected_candidate_pointer_id == resolver_invocation.candidate_pointer_id
        (NOT `candidates[0]`). The resolver is invoked at most once.
        The real retrieval state from `discovery_result` is carried
        through (no synthetic bridge).

        `external_selection` shape:
            {rendering_path: str, candidate_pointer_id: str} | None
        (or {rendering_path, doi} as a cross-walk stable identifier).

        Returned shape:
        {
          "status": "ok" | "failed_resolution"
                 | "ladder_completed_no_selection"
                 | "candidate_selection_required"
                 | "invalid_external_selection"
                 | "discovery_mismatch",
          ...
          "canonical_evidence": ...,
          "resolver_invocation": ...,
          "resolver_snapshot": ...,
          "selected_candidate_pointer_id": ...,
          "selected_candidate_rank": int | null,
          "selected_candidate_rank_status": "OK" | "NOT_EVALUATED_RANK_MISSING",
        }
        """
        # Validate that the discovery belongs to this chain's
        # search_order (caller hygiene; refuse cross-instance mixing).
        if discovery_result.get("search_order_id") != self.search_order.get("search_order_id"):
            return {
                "status": "discovery_mismatch",
                "search_order_id": self.search_order.get("search_order_id"),
                "discovery_search_order_id": discovery_result.get("search_order_id"),
            }
        candidates_by_rung: dict[str, list[dict]] = (
            discovery_result.get("candidates_by_rung") or {}
        )
        retrieval_invocations: list[dict] = (
            discovery_result.get("retrieval_invocations") or []
        )
        retrieval_snapshots: list[dict] = (
            discovery_result.get("retrieval_snapshots") or []
        )
        # Find the retrieval invocation + snapshot for the selected
        # rung (so the real retrieval_invocation_id and
        # raw_snapshot_sha256 propagate into CanonicalEvidence).
        ladder_attempts: list[dict] = discovery_result.get("ladder_attempts") or []
        rung_candidate_sets: list[dict] = discovery_result.get("rung_candidate_sets") or []
        # ---- Selection validation ----
        es = external_selection
        if es is None:
            return self._resolve_result(
                discovery_result, es, status="ladder_completed_no_selection",
            )
        if not isinstance(es, dict):
            return self._resolve_result(
                discovery_result, es, status="invalid_external_selection",
            )
        sel_rung = es.get("rendering_path")
        sel_cp_id = es.get("candidate_pointer_id")
        sel_doi = es.get("doi") or es.get("matched_doi")
        if not sel_rung:
            return self._resolve_result(
                discovery_result, es, status="candidate_selection_required",
            )
        if not sel_cp_id and not sel_doi:
            return self._resolve_result(
                discovery_result, es, status="candidate_selection_required",
            )
        rung_candidates = candidates_by_rung.get(sel_rung)
        if rung_candidates is None:
            return self._resolve_result(
                discovery_result, es, status="invalid_external_selection",
            )
        # Find the selected CandidatePointer. P1.5-RA2 §2.4 +
        # P1.5-RA3 Closure A: the chain accepts EITHER
        # candidate_pointer_id (intra-walk stable) OR doi
        # (cross-walk stable). EITHER WAY the resolution must
        # produce a real CanonicalEvidence with a real
        # retrieval_invocation_id and real raw_snapshot_sha256.
        selected_cp: dict | None = None
        if sel_cp_id:
            selected_cp = next(
                (c for c in rung_candidates if c.get("candidate_pointer_id") == sel_cp_id),
                None,
            )
        if selected_cp is None and sel_doi:
            doi_norm = sel_doi.strip().lower()
            selected_cp = next(
                (c for c in rung_candidates
                 if (c.get("identifier_hints", {}) or {}).get("doi", "").strip().lower() == doi_norm),
                None,
            )
        if selected_cp is None:
            return self._resolve_result(
                discovery_result, es, status="invalid_external_selection",
            )
        # Find the retrieval invocation for the selected rung. The
        # invocations list is parallel to the rungs in walk order.
        sel_invocation = None
        sel_snapshot = None
        for inv, snap, rcs in zip(retrieval_invocations, retrieval_snapshots, rung_candidate_sets):
            if rcs.get("rendering_path") == sel_rung:
                sel_invocation = inv
                sel_snapshot = snap
                break
        if sel_invocation is None:
            sel_invocation = retrieval_invocations[-1] if retrieval_invocations else None
            sel_snapshot = retrieval_snapshots[-1] if retrieval_snapshots else None
        # ---- Resolution ----
        # P1.5-RA3 Closure C: the resolver is invoked at most once
        # with the explicitly selected CandidatePointer. The real
        # retrieval_invocation_id and raw_snapshot_sha256 propagate
        # to the CanonicalEvidence (no synthetic bridge).
        resolver = CrossrefReferenceResolver()
        evidence, resolver_invocation, resolver_snapshot = resolver.resolve(
            candidate_pointer=selected_cp,
            retrieval_invocation_id=(sel_invocation or {}).get("retrieval_invocation_id"),
        )
        # P1.5-RA3 Closure D: rank truth is fail-closed. If the
        # selected candidate carries a rank, record it as an
        # integer; if not, record null + rank_status =
        # NOT_EVALUATED_RANK_MISSING. Do NOT default to 1.
        actual_rank = selected_cp.get("rank")
        rank_status = "OK" if isinstance(actual_rank, int) else "NOT_EVALUATED_RANK_MISSING"
        if evidence is not None:
            evidence["provenance"]["retrieval_snapshot_sha256"] = (
                (sel_invocation or {}).get("raw_snapshot_sha256")
            )
            evidence["evidence_id"] = _new_id("CE", [0])
        return self._resolve_result(
            discovery_result,
            es,
            status=("ok" if evidence is not None else "failed_resolution"),
            candidates=rung_candidates,
            retrieval_invocation=sel_invocation,
            retrieval_snapshot=sel_snapshot,
            evidence=evidence,
            resolver_invocation=resolver_invocation,
            resolver_snapshot=resolver_snapshot,
            selected_candidate_pointer_id=selected_cp.get("candidate_pointer_id"),
            selected_candidate_rank=actual_rank,
            selected_candidate_rank_status=rank_status,
        )

    def _resolve_result(self, discovery_result, external_selection,
                        *, status, candidates=None,
                        retrieval_invocation=None, retrieval_snapshot=None,
                        evidence=None, resolver_invocation=None,
                        resolver_snapshot=None,
                        selected_candidate_pointer_id=None,
                        selected_candidate_rank=None,
                        selected_candidate_rank_status=None) -> dict:
        """Assemble the resolve() result dict. Carries the real
        retrieval state through; never fabricates a synthetic
        bridge (P1.5-RA3 Closure A).
        """
        return {
            "status": status,
            "search_order_id": self.search_order.get("search_order_id"),
            "compiled_query": self.compiled_query,
            "discovery": discovery_result,
            "external_selection": external_selection,
            "candidate_pointers": (candidates if candidates is not None else []),
            "retrieval_invocations": (discovery_result.get("retrieval_invocations") or []),
            "retrieval_snapshots": (discovery_result.get("retrieval_snapshots") or []),
            "rung_candidate_sets": (discovery_result.get("rung_candidate_sets") or []),
            "ladder_attempts": (discovery_result.get("ladder_attempts") or []),
            "retrieval_invocation": retrieval_invocation,
            "retrieval_snapshot": retrieval_snapshot,
            "canonical_evidence": evidence,
            "resolver_invocation": resolver_invocation,
            "resolver_snapshot": resolver_snapshot,
            "selected_candidate_pointer_id": selected_candidate_pointer_id,
            "selected_candidate_rank": selected_candidate_rank,
            "selected_candidate_rank_status": (
                selected_candidate_rank_status
                if selected_candidate_rank_status is not None
                else "NOT_EVALUATED_RANK_MISSING"
            ),
            "capability_check": {
                "required": self.search_order.get("required_capabilities", []),
                "advertised_by_provider": PROVIDER_CAPABILITIES,
                "advertised_by_resolver": RESOLVER_CAPABILITIES,
            },
        }


def run_negative_chain(*, search_order: dict, compiled_query: str) -> dict:
    """Negative-path demo: simulate a network timeout / provider failure.

    Per contract §11 the system must preserve structured state and
    MUST NOT fabricate evidence. This function exercises the negative
    path by deliberately using a Crossref base URL that will not
    resolve (RFC 5737 TEST-NET-1) so the call returns ``URLError``
    / non-200 status. The chain records the failure as
    ``status="failed_network"`` and produces empty candidate and
    evidence sets.

    ``max_retries=0`` is critical: a retry would mask the deliberate
    failure with extra latency and a different status. The negative
    chain must fail on the FIRST attempt.
    """
    # We construct a provider with an unreachable base URL.
    from .live_crossref import CrossrefRetrievalProvider
    bad_provider = CrossrefRetrievalProvider(
        base_url="http://192.0.2.1:1"  # RFC 5737 TEST-NET-1, guaranteed unroutable
    )
    candidates, retrieval_invocation, retrieval_snapshot = bad_provider.discover(
        search_order_id=search_order["search_order_id"],
        compiled_query=compiled_query,
        top_k=1,
        max_retries=0,  # no retry: the negative chain must record a single explicit failure
    )
    return {
        "status": "failed_network" if retrieval_invocation["status"] != "ok" else "ok_unexpected",
        "search_order_id": search_order["search_order_id"],
        "compiled_query": compiled_query,
        "candidate_pointers": candidates,
        "retrieval_invocation": retrieval_invocation,
        "retrieval_snapshot": retrieval_snapshot,
        "canonical_evidence": None,  # negative path never fabricates evidence (contract §11)
        "resolver_invocation": None,
        "resolver_snapshot": None,
    }
