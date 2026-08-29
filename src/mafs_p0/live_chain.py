"""P1-minimum live chain orchestrator.

Ties the P0 plan pipeline (SearchOrder + CompiledQuery) to the P1
live retrieval + resolution chain. The full chain for one SearchOrder:

  SearchOrder
  -> CompiledQuery
  -> RetrievalProvider.discover()        [live HTTP]
  -> CandidatePointer set
  -> ReferenceResolver.resolve()         [live HTTP, caller-selected CandidatePointer]
  -> CanonicalEvidence (1 record)

The orchestrator returns a dict with all the artifacts plus a
``status`` field (``ok`` or ``failed``). The CI live-smoke job
uploads the artifacts so the chain is reproducible from CI artifacts
(contract §17.10).

Bounded autonomy (per contract §16):
  * Top-k for discovery: 5.
  * Resolution depth: 1 (the single caller-selected CandidatePointer).
  * No retries. Failures are recorded with explicit status; they
    do not fabricate evidence (contract §11).
  * The chain does NOT use a hard-coded list of SearchOrders — the
    caller passes the SearchOrder and its compiled query.

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

    Inputs: one SearchOrder and either a compiled query string
    (legacy pre-P1.5 path) or a list of P1.5 ``RenderedQuery`` rungs
    (the Crossref-native path).

    P1.5-RA1 (Closure B) removed the prior ``first non-empty rung is
    canonical`` semantics. P1.5-RA2 (Closure A) tightens the
    ownership boundary further: the chain now requires the caller
    to explicitly select the **specific CandidatePointer** it has
    decided is canonical — not just the rung. The execution layer
    does NOT auto-pick top-1. The selection is a small object:

    ```yaml
    external_selection:
      rendering_path: B_author_year_strongest
      candidate_pointer_id: CP-007
    ```

    If no ``external_selection`` is supplied, the chain returns
    ``status="ladder_completed_no_selection"``. The resolver is NOT
    invoked.

    If ``external_selection`` is supplied without
    ``candidate_pointer_id`` (i.e. only the rung), the chain returns
    ``status="candidate_selection_required"`` — rung selection alone
    is no longer sufficient.

    If ``external_selection.candidate_pointer_id`` does not exist in
    the selected rung's candidate set, the chain returns
    ``status="invalid_external_selection"``.

    On a valid selection, the chain resolves only that specific
    CandidatePointer and emits a single CanonicalEvidence. The
    resolver is invoked at most once per chain. The selected
    ``candidate_pointer_id`` is preserved mechanically through
    ``CandidateSet -> Selected CandidatePointer -> ResolverInvocation
    -> CanonicalEvidence`` (P1.5-RA2 §2.4).

    This policy applies uniformly to both the P1.5 ladder path
    (``rendered_queries`` supplied) and the legacy pre-P1.5 path
    (single ``compiled_query`` only). The earlier P1.5-RA1
    ``is_legacy_path`` carve-out (legacy path auto-canonizes top-1)
    is removed in P1.5-RA2; the legacy path is treated as a single
    rung with ``rendering_path=LADDER_RUNG_LEGACY`` and the same
    explicit selection boundary applies.

    For benchmark use, the orchestrator's oracle-driven scorer
    identifies the actual matched ``candidate_pointer_id`` (not just
    the rung) and passes it through this same explicit selection
    boundary (P1.5-RA2 §3). The benchmark reuses the production
    LiveChain for resolution; it does not duplicate the resolver
    path. Per P1.5-RA2 §3, the benchmark is allowed to find the
    exact-DOI/PMID match inside the bounded CandidateSets because
    the benchmark already knows the answer, but the selection
    itself must be explicit and must traverse the same
    candidate-level boundary.
    """
    search_order: dict
    compiled_query: str = ""
    top_k: int = 5
    rendered_queries: list = field(default_factory=list)  # list of RenderedQuery
    # P1.5-RA2 §2.2: selection is a candidate-level object, not just a rung.
    # Shape: {"rendering_path": str, "candidate_pointer_id": str} | None
    external_selection: dict | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"

    def run(self) -> dict:
        so_id = self.search_order["search_order_id"]
        # ---- Discovery ----
        provider = CrossrefRetrievalProvider()
        # Capability advertisement check (contract §17.1): the provider
        # must advertise the SearchOrder's required_capabilities.
        required = set(self.search_order.get("required_capabilities") or [])
        advertised = set(provider.capabilities)
        missing = required - advertised
        if missing:
            self.status = "failed_capability_mismatch"
            return self._result(missing_capabilities=sorted(missing))
        # P1.5-RA1 Closure B: walk the bounded fallback ladder; record
        # every rung's candidate set; do NOT canonize any rung based
        # on non-emptiness alone.
        # P1.5-RA2 Closure A: the chain does NOT auto-pick top-1
        # either. The caller must identify the specific
        # CandidatePointer to resolve.
        ladder_attempts: list[dict] = []
        # per-rung candidate sets (full audit). For the ladder path
        # the rendering_path is per-rung; for the legacy path it is
        # LADDER_RUNG_LEGACY.
        rung_candidate_sets: list[dict] = []
        # Map: rendering_path -> list[candidate_dict]. Populated by
        # both the ladder path and the legacy path.
        candidates_by_rung: dict[str, list[dict]] = {}
        # The most-recent retrieval snapshot (audit only; not promoted
        # to canonical without a candidate-level selection).
        last_retrieval_invocation: dict | None = None
        last_retrieval_snapshot: dict | None = None
        if self.rendered_queries:
            for rq in self.rendered_queries:
                cands, ri, rs = provider.discover(
                    search_order_id=so_id,
                    url_params=rq.url_params,
                    rendering_path=rq.rendering_path,
                    top_k=self.top_k,
                )
                candidates_by_rung[rq.rendering_path] = list(cands)
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
                last_retrieval_invocation = ri
                last_retrieval_snapshot = rs
        else:
            # Legacy pre-P1.5 path: single full-text query, treated
            # as a single rung with rendering_path=LADDER_RUNG_LEGACY.
            # The P1.5-RA2 boundary (explicit candidate selection) is
            # enforced identically — no top-1 auto-canonize.
            cands, ri, rs = provider.discover(
                search_order_id=so_id,
                compiled_query=self.compiled_query,
                top_k=self.top_k,
            )
            candidates_by_rung[LADDER_RUNG_LEGACY] = list(cands)
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
            last_retrieval_invocation = ri
            last_retrieval_snapshot = rs
        # ---- Selection -> Resolution ----
        # P1.5-RA2 §2.2: the chain resolves ONLY the explicit
        # CandidatePointer. No top-1 auto-canonize. No rung-level
        # auto-canonize. No implicit fallback.
        es = self.external_selection
        if es is None:
            # No selection at all -> no resolution. Audit-only.
            self.status = "ladder_completed_no_selection"
            return self._result(
                candidates=[],
                retrieval_invocation=last_retrieval_invocation,
                retrieval_snapshot=last_retrieval_snapshot,
                ladder_attempts=ladder_attempts,
                rung_candidate_sets=rung_candidate_sets,
                external_selection=es,
            )
        # External selection shape: must carry BOTH rendering_path
        # AND candidate_pointer_id.
        if not isinstance(es, dict) or "candidate_pointer_id" not in es or not es.get("candidate_pointer_id"):
            # Rung selected but no candidate pointer named -> honest
            # failure, NOT a top-1 fallback. P1.5-RA2 §2.3.
            self.status = "candidate_selection_required"
            return self._result(
                candidates=[],
                retrieval_invocation=last_retrieval_invocation,
                retrieval_snapshot=last_retrieval_snapshot,
                ladder_attempts=ladder_attempts,
                rung_candidate_sets=rung_candidate_sets,
                external_selection=es,
            )
        sel_rung = es.get("rendering_path")
        sel_cp_id = es.get("candidate_pointer_id")
        if not sel_rung:
            # candidate_pointer_id without a rendering_path is not
            # enough — we still need the rung provenance.
            self.status = "candidate_selection_required"
            return self._result(
                candidates=[],
                retrieval_invocation=last_retrieval_invocation,
                retrieval_snapshot=last_retrieval_snapshot,
                ladder_attempts=ladder_attempts,
                rung_candidate_sets=rung_candidate_sets,
                external_selection=es,
            )
        rung_candidates = candidates_by_rung.get(sel_rung)
        if rung_candidates is None:
            # rendering_path did not exist in the ladder.
            self.status = "invalid_external_selection"
            return self._result(
                candidates=[],
                retrieval_invocation=last_retrieval_invocation,
                retrieval_snapshot=last_retrieval_snapshot,
                ladder_attempts=ladder_attempts,
                rung_candidate_sets=rung_candidate_sets,
                external_selection=es,
            )
        # Find the exact CandidatePointer in the selected rung.
        selected_cp = next(
            (c for c in rung_candidates if c.get("candidate_pointer_id") == sel_cp_id),
            None,
        )
        if selected_cp is None:
            # CandidatePointer not in the selected rung -> honest
            # failure. P1.5-RA2 §2.3: "the selected CandidatePointer
            # does not exist in the selected rung" -> must NOT
            # choose top-1.
            self.status = "invalid_external_selection"
            return self._result(
                candidates=[],
                retrieval_invocation=last_retrieval_invocation,
                retrieval_snapshot=last_retrieval_snapshot,
                ladder_attempts=ladder_attempts,
                rung_candidate_sets=rung_candidate_sets,
                external_selection=es,
            )
        # Valid candidate-level selection. Resolve exactly that
        # CandidatePointer.
        resolver = CrossrefReferenceResolver()
        evidence, resolver_invocation, resolver_snapshot = resolver.resolve(
            candidate_pointer=selected_cp,
            retrieval_invocation_id=last_retrieval_invocation["retrieval_invocation_id"],
        )
        if evidence is not None:
            evidence["provenance"]["retrieval_snapshot_sha256"] = last_retrieval_invocation["raw_snapshot_sha256"]
            evidence["evidence_id"] = _new_id("CE", [0])
        # The chain returns the resolved candidate set of the SELECTED
        # rung (not the union of all rungs). Per P1.5-RA2 §2.4, the
        # chain preserves the CP -> Resolver identity.
        return self._result(
            candidates=list(rung_candidates),
            retrieval_invocation=last_retrieval_invocation,
            retrieval_snapshot=last_retrieval_snapshot,
            evidence=evidence,
            resolver_invocation=resolver_invocation,
            resolver_snapshot=resolver_snapshot,
            ladder_attempts=ladder_attempts,
            rung_candidate_sets=rung_candidate_sets,
            external_selection=es,
            status=("ok" if evidence is not None else "failed_resolution"),
            selected_candidate_pointer_id=sel_cp_id,
            selected_candidate_rank=selected_cp.get("rank"),
        )

    # ---- Artifact assembly ----
    def _result(self, **kwargs) -> dict:
        # Build the canonical artifact dict. ``candidates`` is required;
        # the rest may be missing on early failure paths.
        candidates = kwargs.get("candidates", [])
        retrieval_invocation = kwargs.get("retrieval_invocation")
        retrieval_snapshot = kwargs.get("retrieval_snapshot")
        evidence = kwargs.get("evidence")
        resolver_invocation = kwargs.get("resolver_invocation")
        resolver_snapshot = kwargs.get("resolver_snapshot")
        missing_capabilities = kwargs.get("missing_capabilities")
        ladder_attempts = kwargs.get("ladder_attempts", [])
        rung_candidate_sets = kwargs.get("rung_candidate_sets", [])
        external_selection = kwargs.get("external_selection")
        status = kwargs.get("status", self.status)
        selected_candidate_pointer_id = kwargs.get("selected_candidate_pointer_id")
        selected_candidate_rank = kwargs.get("selected_candidate_rank")
        return {
            "status": status,
            "search_order_id": self.search_order["search_order_id"],
            "compiled_query": self.compiled_query,
            "candidate_pointers": candidates,
            "retrieval_invocation": retrieval_invocation,
            "retrieval_snapshot": retrieval_snapshot,
            "canonical_evidence": evidence,
            "resolver_invocation": resolver_invocation,
            "resolver_snapshot": resolver_snapshot,
            "missing_capabilities": missing_capabilities,
            "ladder_attempts": ladder_attempts,  # P1.5: list of rung attempts
            "rung_candidate_sets": rung_candidate_sets,  # P1.5-RA1: full per-rung candidate audit
            "external_selection": external_selection,  # P1.5-RA2: candidate-level {rung, cp_id} object
            "selected_candidate_pointer_id": selected_candidate_pointer_id,  # P1.5-RA2
            "selected_candidate_rank": selected_candidate_rank,  # P1.5-RA2
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
