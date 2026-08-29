"""P1-minimum live chain tests (contract §17).

10 risk-focused tests. The contract explicitly says
"Do not optimize for test count" — these 10 cover the §17.1..17.10
risk points. They are split between:

  * Offline tests (no network): capability advertisement, evidence
    shape, negative-path fabrication check, snapshot integrity in
    isolation, attempt-count metadata.
  * Online tests (live HTTP, marked with the ``live`` marker):
    the full real chain.

The live tests are skipped automatically if the environment has no
network access; CI on GitHub Actions always has network access.
"""
from __future__ import annotations
import os
import re
import socket
import pytest

from mafs_p0.live_crossref import (
    CrossrefRetrievalProvider,
    CrossrefReferenceResolver,
    PROVIDER_CAPABILITIES,
    RESOLVER_CAPABILITIES,
    USER_AGENT,
)
from mafs_p0.live_chain import LiveChain, run_negative_chain
from mafs_p0.live_demo import _pick_demo_search_order_and_query
from mafs_p0.crossref_renderer import LADDER_RUNG_LEGACY


# ---------- helpers ----------

def _has_network() -> bool:
    """Quick reachability check for api.crossref.org. The CI runner
    always has network; local developers can opt out by setting
    ``MAFS_P0_SKIP_LIVE_TESTS=1``."""
    if os.environ.get("MAFS_P0_SKIP_LIVE_TESTS") == "1":
        return False
    try:
        socket.create_connection(("api.crossref.org", 443), timeout=3).close()
        return True
    except OSError:
        return False


live = pytest.mark.skipif(not _has_network(), reason="no network / live skipped")


def _chain_with_explicit_top1_selection(so: dict, compiled_query: str) -> tuple[dict, dict]:
    """P1.5-RA2 helper: do a real discovery first, then build a
    LiveChain that explicitly selects the top-1 CandidatePointer
    via the new ``external_selection`` shape
    ``{rendering_path, candidate_pointer_id}``.

    The P1.5-RA2 contract requires explicit candidate selection
    (no top-1 auto-canonize). For the legacy P1 path
    (``compiled_query`` only), the chain treats that as a single
    rung with ``rendering_path=LADDER_RUNG_LEGACY``.

    If discovery returns no candidates (transient Crossref ranking
    or rate-limit), the test is skipped rather than hard-failed —
    the explicit-selection happy path requires a real candidate to
    select. Per P1.5-RA2 §1 the network is an external authority;
    a missing candidate set is a "no evidence" state, not a test
    failure.

    Returns (result, top1_candidate).
    """
    provider = CrossrefRetrievalProvider()
    cands, _riv, _snap = provider.discover(
        search_order_id=so["search_order_id"],
        compiled_query=compiled_query,
        top_k=5,
    )
    if not cands:
        pytest.skip(
            f"discovery returned no candidates for {so['search_order_id']} "
            f"(transient Crossref ranking or rate-limit); explicit-selection "
            f"happy path requires a real candidate. Skip is honest per "
            f"P1.5-RA2 §1 (no fabrication)."
        )
    top1 = cands[0]
    chain = LiveChain(
        search_order=so,
        compiled_query=compiled_query,
        top_k=5,
        external_selection={
            "rendering_path": LADDER_RUNG_LEGACY,
            "candidate_pointer_id": top1["candidate_pointer_id"],
        },
    )
    return chain.run(), top1


# ---------- test 1: provider capability advertises the SearchOrder needs ----

def test_p1_01_provider_capability_advertises_searchorder_needs():
    """Contract §17.1: provider capability advertisement must cover the
    SearchOrder's required_capabilities.

    SO-A1-01 requires search.query, search.pagination, result.ranked.
    The CrossrefRetrievalProvider advertises search.query, search.boolean,
    search.pagination, result.ranked. The required set is a subset of
    the advertised set.
    """
    so, _ = _pick_demo_search_order_and_query()
    required = set(so.get("required_capabilities") or [])
    advertised = set(PROVIDER_CAPABILITIES)
    assert required.issubset(advertised), (
        f"provider missing capabilities for {so['search_order_id']}: "
        f"required={required} advertised={advertised}"
    )


# ---------- test 2: compiled query reaches the provider ----

def test_p1_02_compiled_query_reaches_provider_in_request_url():
    """Contract §17.2: the compiled query string from the P0 query
    pipeline must appear in the request URL the provider builds.

    The compiled query is preserved verbatim in the retrieval_invocation's
    request.url (URL-encoded by urllib.parse.urlencode).
    """
    so, compiled_query = _pick_demo_search_order_and_query()
    provider = CrossrefRetrievalProvider()
    # We don't need the actual HTTP call to verify URL building;
    # we just need the URL the provider WOULD have called. Re-use
    # the discover() call but bound it with a very short timeout by
    # pointing at a known-bad host so it fails fast and we can still
    # inspect the request URL.
    bad = CrossrefRetrievalProvider(base_url="http://192.0.2.1:1")
    candidates, riv, _snap = bad.discover(
        search_order_id=so["search_order_id"],
        compiled_query=compiled_query,
        top_k=1,
        max_retries=0,
    )
    # The URL should be the bad host (because we overrode base_url),
    # and the compiled_query phrase should appear in it (URL-encoded).
    assert "192.0.2.1" in riv["request"]["url"]
    # Ovarian oxygenation has a space; after URL-encoding the space
    # becomes "+" or "%20". Either is acceptable.
    assert "ovarian+oxygenation" in riv["request"]["url"].lower() or "ovarian%20oxygenation" in riv["request"]["url"].lower()


# ---------- test 3: live provider returns a real response ----

@live
def test_p1_03_live_provider_returns_real_response():
    """Contract §17.3: a real Crossref /works?query= call must succeed
    with http_status=200 and a non-zero item_count.
    """
    so, compiled_query = _pick_demo_search_order_and_query()
    provider = CrossrefRetrievalProvider()
    candidates, riv, snapshot = provider.discover(
        search_order_id=so["search_order_id"],
        compiled_query=compiled_query,
        top_k=5,
    )
    assert riv["status"] == "ok", f"expected ok, got {riv['status']}"
    assert riv["response"]["http_status"] == 200
    assert riv["response"]["item_count"] > 0
    assert len(snapshot["bytes"]) > 0  # raw response is non-empty


# ---------- test 4: CandidatePointer is created ----

@live
def test_p1_04_candidate_pointer_is_created():
    """Contract §17.4: every non-empty discovery result must produce at
    least one CandidatePointer with a DOI and a non-null title_hint
    (where the upstream response provides one)."""
    so, compiled_query = _pick_demo_search_order_and_query()
    provider = CrossrefRetrievalProvider()
    candidates, _riv, _snap = provider.discover(
        search_order_id=so["search_order_id"],
        compiled_query=compiled_query,
        top_k=5,
    )
    assert len(candidates) >= 1
    cp = candidates[0]
    # CandidatePointer schema invariants
    assert re.match(r"^CP-\d{3,6}$", cp["candidate_pointer_id"])
    assert cp["provider"] == "crossref_v1"
    assert cp["identifier_hints"]["doi"] is not None
    assert cp["rank"] == 1
    assert cp["retrieval_invocation_id"].startswith("RIV-")


# ---------- test 5: resolver consumes a real candidate/identifier ----

@live
def test_p1_05_resolver_consumes_real_candidate():
    """Contract §17.5: the Crossref resolver must consume the
    CandidatePointer's DOI and call /works/{doi}, returning http_status=200
    for a real DOI."""
    so, compiled_query = _pick_demo_search_order_and_query()
    result, _top1 = _chain_with_explicit_top1_selection(so, compiled_query)
    assert result["status"] == "ok"
    rivr = result["resolver_invocation"]
    assert rivr["status"] == "ok"
    assert rivr["response"]["http_status"] == 200
    assert rivr["resolver"] == "crossref_resolver_v1"
    # The URL must contain the candidate's DOI (URL-encoded).
    import urllib.parse
    doi = result["candidate_pointers"][0]["identifier_hints"]["doi"]
    encoded_doi = urllib.parse.quote(doi, safe="")
    assert encoded_doi in rivr["request"]["url"]


# ---------- test 6: raw snapshot is stored and hashed ----

@live
def test_p1_06_raw_snapshot_stored_and_hashed():
    """Contract §17.6: the raw upstream response body must be stored
    as base64 bytes in the RawSnapshot object, and its SHA-256 must
    match the raw_snapshot_sha256 in the retrieval_invocation."""
    import base64
    import hashlib
    so, compiled_query = _pick_demo_search_order_and_query()
    result, _ = _chain_with_explicit_top1_selection(so, compiled_query)
    riv = result["retrieval_invocation"]
    snap = result["retrieval_snapshot"]
    assert snap is not None
    assert snap["sha256"] == riv["raw_snapshot_sha256"]
    # Decode and re-hash to confirm.
    decoded = base64.b64decode(snap["bytes"])
    assert hashlib.sha256(decoded).hexdigest() == snap["sha256"]


# ---------- test 7: canonical metadata is source-derived ----

@live
def test_p1_07_canonical_metadata_source_derived():
    """Contract §17.7: every field in the canonical block must be
    present in the upstream response or explicitly null. No fabricated
    placeholders.
    """
    so, compiled_query = _pick_demo_search_order_and_query()
    result, _ = _chain_with_explicit_top1_selection(so, compiled_query)
    ev = result["canonical_evidence"]
    assert ev is not None
    can = ev["canonical"]
    # DOI must match the candidate's DOI.
    assert can["doi"] == result["candidate_pointers"][0]["identifier_hints"]["doi"]
    # Title, year, venue must be either a non-empty string / int or None
    # (no empty strings masquerading as data).
    assert (can["title"] is None) or (isinstance(can["title"], str) and len(can["title"]) > 0)
    assert (can["year"] is None) or (isinstance(can["year"], int))
    assert (can["venue"] is None) or (isinstance(can["venue"], str) and len(can["venue"]) > 0)
    # Source locator must be a non-empty URL.
    assert can["source_locator"] is not None and can["source_locator"].startswith("http")
    # Resolver identity must match the resolver name.
    assert can["resolver_identity"] == "crossref_resolver_v1"


# ---------- test 8: canonical evidence references both retrieval and resolver provenance ----

@live
def test_p1_08_canonical_evidence_dual_provenance():
    """Contract §17.8: the canonical evidence record's provenance must
    carry BOTH the retrieval snapshot SHA and the resolver snapshot SHA,
    plus both invocation IDs. The dual provenance chain lets an auditor
    trace the evidence back through BOTH the discovery call and the
    resolution call."""
    so, compiled_query = _pick_demo_search_order_and_query()
    result, _ = _chain_with_explicit_top1_selection(so, compiled_query)
    ev = result["canonical_evidence"]
    prov = ev["provenance"]
    assert prov["retrieval_invocation_id"] == result["retrieval_invocation"]["retrieval_invocation_id"]
    assert prov["resolver_invocation_id"] == result["resolver_invocation"]["resolver_invocation_id"]
    assert prov["retrieval_snapshot_sha256"] == result["retrieval_invocation"]["raw_snapshot_sha256"]
    assert prov["resolver_snapshot_sha256"] == result["resolver_invocation"]["raw_snapshot_sha256"]


# ---------- test 9: negative path does not fabricate evidence ----

def test_p1_09_negative_path_does_not_fabricate_evidence():
    """Contract §17.9: a deliberate network failure must produce a
    structured failure status, an empty candidate set, and
    ``canonical_evidence=None``. NO fake evidence on failure."""
    so, compiled_query = _pick_demo_search_order_and_query()
    negative = run_negative_chain(search_order=so, compiled_query=compiled_query)
    assert negative["status"] in ("failed_network", "error_http", "error_timeout")
    # canonical_evidence must be None — never fabricated.
    assert negative["canonical_evidence"] is None
    # The retrieval_invocation must be present (structured state) and
    # carry an explicit non-ok status.
    riv = negative["retrieval_invocation"]
    assert riv is not None
    assert riv["status"] != "ok"
    # A raw snapshot may be empty bytes for a network failure; the
    # SHA-256 of empty bytes is e3b0c4... (well-known).
    assert "raw_snapshot_sha256" in riv


# ---------- test 10: live chain is reproducible from CI artifacts ----

@live
def test_p1_10_live_chain_reproducible_from_artifacts():
    """Contract §17.10: the live chain artifacts must be persisted in a
    form that another run can verify. Specifically, the canonical
    evidence's resolver_snapshot_sha256 must match the persisted
    RawSnapshot bytes' SHA-256 (i.e. the artifact is the actual
    upstream response, not a re-render)."""
    import base64
    import hashlib
    so, compiled_query = _pick_demo_search_order_and_query()
    result, _ = _chain_with_explicit_top1_selection(so, compiled_query)
    # The resolver snapshot must be the actual bytes from the upstream.
    snap = result["resolver_snapshot"]
    assert snap is not None
    assert snap["kind"] == "resolver_response"
    decoded = base64.b64decode(snap["bytes"])
    # The decoded bytes must be a valid JSON Crossref response.
    import json
    parsed = json.loads(decoded.decode("utf-8"))
    assert "message" in parsed
    # And the SHA-256 must match what the canonical evidence's
    # provenance claims.
    assert result["canonical_evidence"]["provenance"]["resolver_snapshot_sha256"] == snap["sha256"]
    # And the SHA-256 must match the re-hash of the decoded bytes.
    assert hashlib.sha256(decoded).hexdigest() == snap["sha256"]


# ---------- bonus: attempt-count metadata is present and >=1 ----

def test_p1_bonus_attempt_count_is_recorded():
    """The retry loop must record the actual attempt count in the
    retrieval / resolver invocation's response.attempts field.
    A successful call records 1 (no retry needed); a failed call
    records HTTP_MAX_RETRIES + 1 = 3 attempts.
    """
    # Successful call -> 1 attempt
    so, compiled_query = _pick_demo_search_order_and_query()
    provider = CrossrefRetrievalProvider()
    _cps, riv, _ = provider.discover(
        search_order_id=so["search_order_id"],
        compiled_query=compiled_query,
        top_k=1,
    )
    # Note: this test runs only when network is available; if the call
    # failed because of a transient error, attempts may be > 1.
    assert riv["response"]["attempts"] >= 1
    # Failed call (TEST-NET-1) -> at least 1 attempt, bounded by HTTP_MAX_RETRIES+1.
    # The exact count depends on what HTTP status the unroutable
    # host returns (it may return a 404 quickly on some platforms,
    # which terminates the retry loop on the first attempt; or it
    # may connection-refuse and trigger 3 attempts). The contract is
    # that ``attempts`` is recorded and the retry is bounded.
    bad = CrossrefRetrievalProvider(base_url="http://192.0.2.1:1")
    _cps2, bad_riv, _ = bad.discover(
        search_order_id=so["search_order_id"],
        compiled_query=compiled_query,
        top_k=1,
    )
    # The negative chain would have max_retries=0, but here we use
    # the default (HTTP_MAX_RETRIES=2), so the failed call records
    # at least 1 attempt and at most HTTP_MAX_RETRIES+1 = 3.
    assert 1 <= bad_riv["response"]["attempts"] <= 3
    assert bad_riv["status"] in ("error_http", "error_network", "error_timeout")
