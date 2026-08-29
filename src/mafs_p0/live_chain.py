"""P1-minimum live chain orchestrator.

Ties the P0 plan pipeline (SearchOrder + CompiledQuery) to the P1
live retrieval + resolution chain. The full chain for one SearchOrder:

  SearchOrder
  -> CompiledQuery
  -> RetrievalProvider.discover()        [live HTTP]
  -> CandidatePointer set
  -> ReferenceResolver.resolve()         [live HTTP, top-1]
  -> CanonicalEvidence (1 record)

The orchestrator returns a dict with all the artifacts plus a
``status`` field (``ok`` or ``failed``). The CI live-smoke job
uploads the artifacts so the chain is reproducible from CI artifacts
(contract §17.10).

Bounded autonomy (per contract §16):
  * Top-k for discovery: 5.
  * Resolution depth: 1 (top-ranked CandidatePointer only).
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
    canonical`` semantics. The chain now exposes a **transparent
    ladder surface**: every rung's candidate set is recorded for
    audit, and **no rung becomes canonically "the answer"** based on
    non-emptiness alone.

    For non-benchmark production use, the caller (model / cognitive
    layer) MUST supply ``external_selection`` — the rendering_path of
    the rung the caller has decided is scientifically canonical — to
    drive the chain into the resolver. The chain does NOT adjudicate
    scientific relevance. Per P1.5-RA1 §5.4, relevance belongs
    upstream; the chain only exposes candidate evidence and
    execution state.

    For benchmark use, the orchestrator's oracle-driven scorer
    supplies ``external_selection`` based on exact-DOI identity match
    against the frozen scholarly oracle. The benchmark oracle is
    not a production relevance engine (P1.5-RA1 §5.3).

    If ``external_selection`` is None AND no rung yielded candidates,
    the chain returns ``status="ladder_completed_no_selection"`` with
    empty candidate and evidence sets. The resolver is NOT invoked.

    If ``external_selection`` is None AND at least one rung yielded
    candidates, the chain still does NOT canonize; it returns
    ``status="ladder_completed_no_selection"`` and exposes every
    rung's candidate set in ``ladder_attempts`` for the caller.
    The chain does not make relevance judgments.

    Note: this strict ladder policy applies to the P1.5 ladder path
    (``rendered_queries`` supplied). The legacy pre-P1.5 path
    (single ``compiled_query`` only, no ``rendered_queries``)
    preserves the P1 auto-canonize-top-1 semantics for backward
    compatibility with the P1 test contract; the legacy path is not
    the production interface going forward.
    """
    search_order: dict
    compiled_query: str = ""
    top_k: int = 5
    rendered_queries: list = field(default_factory=list)  # list of RenderedQuery
    external_selection: str | None = None  # rendering_path the caller has selected, or None
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
        # on non-emptiness alone. The ladder is a transparent
        # retrieval surface; selection is the caller's responsibility.
        ladder_attempts: list[dict] = []
        # per-rung candidate sets (full audit)
        rung_candidate_sets: list[dict] = []
        candidates: list[dict] = []
        retrieval_invocation = None
        retrieval_snapshot = None
        selected_rq: RenderedQuery | None = None
        if self.rendered_queries:
            for rq in self.rendered_queries:
                cands, ri, rs = provider.discover(
                    search_order_id=so_id,
                    url_params=rq.url_params,
                    rendering_path=rq.rendering_path,
                    top_k=self.top_k,
                )
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
                if self.external_selection == rq.rendering_path and selected_rq is None:
                    # Caller has explicitly selected this rung; the
                    # chain canonizes ONLY the caller-selected rung.
                    candidates = cands
                    retrieval_invocation = ri
                    retrieval_snapshot = rs
                    selected_rq = rq
            if not retrieval_invocation and ladder_attempts:
                # No rung was explicitly selected; record the last
                # attempt as the most-recent retrieval_invocation for
                # audit only. The chain does NOT promote it to canonical.
                last = ladder_attempts[-1]
                retrieval_invocation = {
                    "retrieval_invocation_id": last["retrieval_invocation_id"],
                    "search_order_id": so_id,
                    "provider": provider.name,
                    "status": "ladder_completed_no_selection",
                }
                retrieval_snapshot = {
                    "kind": "retrieval_response",
                    "note": "P1.5-RA1: no external_selection supplied; "
                            "ladder completed but no rung was canonized.",
                    "raw_snapshot_id": None,
                }
        else:
            # Legacy pre-P1.5 path: single full-text query.
            candidates, retrieval_invocation, retrieval_snapshot = provider.discover(
                search_order_id=so_id,
                compiled_query=self.compiled_query,
                top_k=self.top_k,
            )
            if candidates:
                rung_candidate_sets.append({
                    "rendering_path": LADDER_RUNG_LEGACY,
                    "candidate_count": len(candidates),
                    "candidate_pointers": list(candidates),
                })
                ladder_attempts.append({
                    "rendering_path": LADDER_RUNG_LEGACY,
                    "url_params": {"query": self.compiled_query, "rows": str(self.top_k)},
                    "candidate_count": len(candidates),
                    "top_doi": (candidates[0].get("identifier_hints", {}).get("doi") if candidates else None),
                    "retrieval_invocation_id": retrieval_invocation["retrieval_invocation_id"],
                    "http_status": retrieval_invocation.get("response", {}).get("http_status"),
                    "status": retrieval_invocation["status"],
                })
        # ---- Selection -> Resolution ----
        # The chain only invokes the resolver when the caller has
        # explicitly selected a rung (external_selection matches a
        # rung's rendering_path) OR the legacy pre-P1.5 path is in
        # use. Otherwise the chain returns
        # "ladder_completed_no_selection" with empty evidence.
        # Per P1.5-RA1 §5.4 the strict ladder policy applies only to
        # the P1.5 ladder path; the legacy pre-P1.5 path (single
        # ``compiled_query``, no ``rendered_queries``) preserves the
        # P1 auto-canonize-top-1 contract for backward compatibility.
        is_legacy_path = not self.rendered_queries
        if not candidates:
            self.status = "ladder_completed_no_selection"
            return self._result(
                candidates=[],
                retrieval_invocation=retrieval_invocation,
                retrieval_snapshot=retrieval_snapshot,
                ladder_attempts=ladder_attempts,
                rung_candidate_sets=rung_candidate_sets,
                external_selection=self.external_selection,
            )
        if not is_legacy_path and selected_rq is None:
            # P1.5 ladder path: candidates were retrieved but no
            # rung was selected by the caller. The chain does NOT
            # auto-canonize.
            self.status = "ladder_completed_no_selection"
            return self._result(
                candidates=[],
                retrieval_invocation=retrieval_invocation,
                retrieval_snapshot=retrieval_snapshot,
                ladder_attempts=ladder_attempts,
                rung_candidate_sets=rung_candidate_sets,
                external_selection=self.external_selection,
            )
        # The caller has selected a rung; canonize the top-1
        # candidate of THAT rung (per existing CP -> Resolver
        # contract §17.8) and invoke the resolver.
        top_cp = candidates[0]
        resolver = CrossrefReferenceResolver()
        # Pass the retrieval snapshot SHA-256 into the provenance so the
        # canonical evidence carries BOTH the retrieval and resolver
        # upstream snapshots (contract §17.8).
        evidence, resolver_invocation, resolver_snapshot = resolver.resolve(
            candidate_pointer=top_cp,
            retrieval_invocation_id=retrieval_invocation["retrieval_invocation_id"],
        )
        # Backfill the retrieval snapshot SHA on the evidence record's
        # provenance (the resolver does not know it directly; it knows
        # the candidate pointer but not the upstream response).
        if evidence is not None:
            evidence["provenance"]["retrieval_snapshot_sha256"] = retrieval_invocation["raw_snapshot_sha256"]
            evidence["evidence_id"] = _new_id("CE", [0])  # global counter for evidence IDs
        if evidence is None:
            self.status = "failed_resolution"
        else:
            self.status = "ok"
        return self._result(
            candidates=candidates,
            retrieval_invocation=retrieval_invocation,
            retrieval_snapshot=retrieval_snapshot,
            evidence=evidence,
            resolver_invocation=resolver_invocation,
            resolver_snapshot=resolver_snapshot,
            ladder_attempts=ladder_attempts,
            rung_candidate_sets=rung_candidate_sets,
            external_selection=self.external_selection,
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
        return {
            "status": self.status,
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
            "external_selection": external_selection,  # P1.5-RA1: which rung the caller selected
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
