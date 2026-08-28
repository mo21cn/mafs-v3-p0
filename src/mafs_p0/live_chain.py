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


@dataclass
class LiveChain:
    """A single bounded live chain.

    Inputs: one SearchOrder and its compiled query string.
    Outputs: a dict containing the full artifact set and an overall
    ``status`` field. Field names mirror the contract §19 required
    CI artifacts.
    """
    search_order: dict
    compiled_query: str
    top_k: int = 5
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
        candidates, retrieval_invocation, retrieval_snapshot = provider.discover(
            search_order_id=so_id,
            compiled_query=self.compiled_query,
            top_k=self.top_k,
        )
        # ---- Take top-1 for resolution ----
        if not candidates:
            self.status = "empty_candidate_set"
            return self._result(candidates=[], retrieval_invocation=retrieval_invocation, retrieval_snapshot=retrieval_snapshot)
        top_cp = candidates[0]
        # ---- Resolution ----
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
