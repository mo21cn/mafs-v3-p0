"""P1-minimum live chain: Crossref RetrievalProvider + ReferenceResolver.

This module is the implementation of the MAFS v3.0-P1 Minimum Live Chain
Contract. It provides:

  * ``CrossrefRetrievalProvider`` — Discovery role. Calls
    ``GET https://api.crossref.org/works?query=...&rows=...`` and emits
    ``CandidatePointer`` objects + a ``RetrievalInvocation``.

  * ``CrossrefReferenceResolver`` — Resolution role. Calls
    ``GET https://api.crossref.org/works/{doi}`` and emits
    canonical metadata + a ``ResolverInvocation``.

The two roles are kept on distinct interfaces per the contract §4
("Discovery and Resolution Must Remain Separate").

Bounded autonomy choices (per contract §16):
  * Backend: Crossref (no API key, JSON REST, polite pool mailto for
    higher rate limits).
  * top_k: 5 (a small bounded top-k is sufficient for P1-min).
  * User-Agent: identifies the MAFS project (Crossref requests a
    descriptive User-Agent; this also helps the polite pool).
  * Timeout: 30 seconds per request.
  * Retries: zero (P1-min is one bounded call; failure is recorded
    explicitly in the invocation status, not retried silently).

Not implemented here (deferred):
  * Multiple provider backends.
  * Pagination beyond the first page.
  * Taint / admissibility (P2).
  * Budget / cost enforcement (P3).
"""
from __future__ import annotations
import base64
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---- Constants --------------------------------------------------------------

CROSSREF_BASE = "https://api.crossref.org"
CROSSREF_PROVIDER_NAME = "crossref_v1"
CROSSREF_RESOLVER_NAME = "crossref_resolver_v1"
USER_AGENT = "MAFS-v3.0-P1/0.1 (Local-Claw; mailto:mo21cn@example.invalid)"
HTTP_TIMEOUT = 30  # seconds per request
HTTP_MAX_RETRIES = 2  # bounded retry count for the positive chain (transient
                      # network errors are NOT acceptable causes of P1
                      # acceptance failure; the contract §11 mandates
                      # that failures are recorded as explicit status,
                      # so the negative chain still relies on a single
                      # attempt with no retry)


# ---- Capability advertisement ------------------------------------------------

PROVIDER_CAPABILITIES: list[str] = [
    # discovery role
    "search.query",
    "search.boolean",
    "search.pagination",
    "result.ranked",
]

RESOLVER_CAPABILITIES: list[str] = [
    # resolution role
    "resolve.doi",
    "metadata.snapshot",
    "metadata.canonical",
]


# ---- Helpers ----------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _http_get(url: str, *, max_retries: int = 0, retry_sleep: float = 2.0) -> tuple[int, bytes, str, int]:
    """HTTP GET with bounded retry. Returns (http_status, body_bytes, content_type, attempts).

    ``max_retries`` defaults to 0 (no retry) for the negative-path chain,
    which must record a single explicit failure. The positive chain
    uses ``max_retries=HTTP_MAX_RETRIES`` to absorb transient network
    blips without making P1 acceptance flaky.

    A retry is triggered only for ``http_status == 0`` (network /
    timeout) or for ``5xx`` HTTP responses — not for ``4xx`` (those
    are caller errors that won't be fixed by retrying).
    """
    last_status = 0
    last_body = b""
    last_ctype = ""
    attempts = 0
    for attempt in range(1, max_retries + 2):  # 1..(max_retries+1)
        attempts = attempt
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                status = resp.getcode()
                body = resp.read()
                ctype = resp.headers.get("Content-Type", "")
                last_status, last_body, last_ctype = status, body, ctype
                if status >= 500 and attempt <= max_retries:
                    time.sleep(retry_sleep)
                    continue
                return status, body, ctype, attempts
        except urllib.error.HTTPError as e:
            status = e.code
            body = e.read() if e.fp else b""
            ctype = e.headers.get("Content-Type", "") if e.headers else ""
            last_status, last_body, last_ctype = status, body, ctype
            # 5xx -> retry; 4xx -> don't retry (caller error).
            if status >= 500 and attempt <= max_retries:
                time.sleep(retry_sleep)
                continue
            return status, body, ctype, attempts
        except (urllib.error.URLError, TimeoutError, Exception):
            last_status, last_body, last_ctype = 0, b"", ""
            if attempt <= max_retries:
                time.sleep(retry_sleep)
                continue
            return 0, b"", "", attempts
    return last_status, last_body, last_ctype, attempts


def _new_id(prefix: str, counter: list[int]) -> str:
    counter[0] += 1
    return f"{prefix}-{counter[0]:03d}"


# ---- Provider (Discovery) ---------------------------------------------------

@dataclass
class CrossrefRetrievalProvider:
    """Discovery role. Calls Crossref's /works?query= and emits CandidatePointers.

    Lifecycle (P1-min):
      provider = CrossrefRetrievalProvider()
      candidates, retrieval_invocation, snapshot = provider.discover(
          search_order_id="SO-A1-01",
          compiled_query='"ovarian oxygenation" AND ("blood-ovary axis" OR "ovary oxygen delivery")',
          top_k=5,
      )

    Output:
      candidates:           list[dict] — CandidatePointer objects
      retrieval_invocation: dict        — RetrievalInvocation object
      snapshot:              dict        — RawSnapshot object (response body)
    """
    base_url: str = CROSSREF_BASE
    name: str = CROSSREF_PROVIDER_NAME
    capabilities: list[str] = field(default_factory=lambda: list(PROVIDER_CAPABILITIES))
    _counter: list[int] = field(default_factory=lambda: [0], init=False, repr=False)

    def discover(
        self,
        *,
        search_order_id: str,
        compiled_query: str,
        top_k: int = 5,
        offset: int = 0,
        max_retries: int = HTTP_MAX_RETRIES,
    ) -> tuple[list[dict], dict, dict]:
        """Run a live Crossref search and return the candidate set + invocation.

        Returns ``(candidates, retrieval_invocation, raw_snapshot)``.

        ``max_retries`` defaults to ``HTTP_MAX_RETRIES`` (bounded retry
        for transient 5xx / network errors). The negative-path chain
        passes ``max_retries=0`` so a deliberate failure is recorded
        as a single attempt.

        P1-RA1 §3 (Blocker C): ``search.pagination`` is now truthful.
        The provider passes the ``offset`` query parameter to
        Crossref, parses the response's ``total-results`` field, and
        records a ``pagination_state`` block on the
        ``retrieval_invocation``. P1-min always sets
        ``bounded_p1_stopped=True`` because the demo stops at page 1
        (no further pages are fetched). This is honest about the P1
        scope: a one-page bounded retrieval, not exhaustive
        pagination. Full pagination strategy is DEFERRED per contract §9.
        """
        # Build the request URL.
        params = {"query": compiled_query, "rows": str(top_k), "offset": str(offset)}
        url = f"{self.base_url}/works?{urllib.parse.urlencode(params)}"
        started_at = _now_iso()
        t0 = time.time()
        status, body, ctype, attempts = _http_get(url, max_retries=max_retries)
        ended_at = _now_iso()
        snapshot_sha = _sha256_bytes(body)
        snapshot = {
            "schema_version": "3.0-p1",
            "raw_snapshot_id": _new_id("RSNAP", self._counter),
            "kind": "retrieval_response",
            "sha256": snapshot_sha,
            "bytes": base64.b64encode(body).decode("ascii"),
            "byte_length": len(body),
            "content_type": ctype or None,
            "captured_at": ended_at,
        }
        # Parse the JSON body. Crossref returns {"status": "...", "message": {"items": [...]}}
        item_count = 0
        candidates: list[dict] = []
        invocation_status: str
        total_results: int | None = None
        pagination_state: dict = {
            "requested_limit": top_k,
            "offset": offset,
            "total_results": None,
            "items_returned": 0,
            "has_more": False,
            "bounded_p1_stopped": True,
        }
        if status != 200:
            invocation_status = "error_http"
        else:
            try:
                payload = json.loads(body.decode("utf-8"))
                msg = payload.get("message") or {}
                items = msg.get("items") or []
                item_count = len(items)
                # P1-RA1 §3 (Blocker C): Crossref exposes total-results
                # in message.total-results. We record it; has_more is
                # derivable as offset + items_returned < total_results.
                tr = msg.get("total-results")
                if isinstance(tr, int):
                    total_results = tr
                pagination_state["total_results"] = total_results
                pagination_state["items_returned"] = item_count
                if total_results is not None:
                    pagination_state["has_more"] = (offset + item_count) < total_results
                for rank, item in enumerate(items, start=1):
                    cp = self._build_candidate_pointer(item, rank)
                    if cp is not None:
                        candidates.append(cp)
                if item_count == 0:
                    invocation_status = "empty_result"
                else:
                    invocation_status = "ok"
            except (json.JSONDecodeError, UnicodeDecodeError):
                invocation_status = "error_parse"
        riv_id = _new_id("RIV", self._counter)
        retrieval_invocation = {
            "schema_version": "3.0-p1",
            "retrieval_invocation_id": riv_id,
            "search_order_id": search_order_id,
            "compiled_query": compiled_query,
            "provider": self.name,
            "request": {
                "url": url,
                "method": "GET",
                "headers": {"User-Agent": USER_AGENT, "Accept": "application/json"},
                "body": None,
            },
            "response": {
                "http_status": status,
                "item_count": item_count,
                "raw_snapshot_sha256": snapshot_sha,
                "attempts": attempts,
            },
            "pagination_state": pagination_state,
            "status": invocation_status,
            "raw_snapshot_sha256": snapshot_sha,
            "started_at": started_at,
            "ended_at": ended_at,
        }
        # Backfill the retrieval_invocation_id on each candidate.
        for cp in candidates:
            cp["retrieval_invocation_id"] = riv_id
        # Suppress unused 't0' lint (kept for future timing telemetry).
        del t0
        return candidates, retrieval_invocation, snapshot

    def _build_candidate_pointer(self, item: dict, rank: int) -> dict | None:
        """Map a Crossref ``items[]`` entry to a CandidatePointer.

        Returns ``None`` if the item has no resolvable identifier (no DOI),
        because without a resolvable identifier the resolver cannot
        canonicalize it (per contract §5: A CandidatePointer is not
        yet canonical evidence, but it must be resolvable).
        """
        doi = item.get("DOI")
        if not doi:
            return None
        title_list = item.get("title") or []
        title_hint = title_list[0] if title_list else None
        cp = {
            "schema_version": "3.0-p1",
            "candidate_pointer_id": _new_id("CP", self._counter),
            "provider": self.name,
            "provider_result_id": doi,
            "title_hint": title_hint,
            "identifier_hints": {
                "doi": doi,
                "pmid": None,
            },
            "rank": rank,
            "retrieval_invocation_id": None,  # backfilled by caller
        }
        return cp


# ---- Resolver (Resolution) --------------------------------------------------

@dataclass
class CrossrefReferenceResolver:
    """Resolution role. Calls Crossref's /works/{doi} and emits canonical metadata.

    Lifecycle:
      resolver = CrossrefReferenceResolver()
      evidence, resolver_invocation, snapshot = resolver.resolve(
          candidate_pointer=candidate,
          retrieval_invocation_id="RIV-001",
      )
    """
    base_url: str = CROSSREF_BASE
    name: str = CROSSREF_RESOLVER_NAME
    capabilities: list[str] = field(default_factory=lambda: list(RESOLVER_CAPABILITIES))
    _counter: list[int] = field(default_factory=lambda: [0], init=False, repr=False)

    def resolve(
        self,
        *,
        candidate_pointer: dict,
        retrieval_invocation_id: str,
        max_retries: int = HTTP_MAX_RETRIES,
    ) -> tuple[dict | None, dict, dict]:
        """Resolve a CandidatePointer to canonical evidence via Crossref.

        Returns ``(evidence_or_None, resolver_invocation, raw_snapshot)``.

        If resolution fails, ``evidence_or_None`` is ``None`` and the
        resolver_invocation status reflects the failure mode. The
        contract §11 mandates that a failure does not fabricate evidence.
        """
        doi = (candidate_pointer.get("identifier_hints") or {}).get("doi")
        if not doi:
            # Defensive: should not happen because the provider only
            # emits CP with a DOI. If it does, record the failure.
            return None, self._failed_invocation(
                candidate_pointer, retrieval_invocation_id,
                doi=None, http_status=0, body=b"", ctype="", attempts=0,
                status="not_found",
            )
        # URL-encode the DOI (it may contain /).
        encoded = urllib.parse.quote(doi, safe="")
        url = f"{self.base_url}/works/{encoded}"
        started_at = _now_iso()
        status, body, ctype, attempts = _http_get(url, max_retries=max_retries)
        ended_at = _now_iso()
        snapshot_sha = _sha256_bytes(body)
        snapshot = {
            "schema_version": "3.0-p1",
            "raw_snapshot_id": _new_id("RSNAP", self._counter),
            "kind": "resolver_response",
            "sha256": snapshot_sha,
            "bytes": base64.b64encode(body).decode("ascii"),
            "byte_length": len(body),
            "content_type": ctype or None,
            "captured_at": ended_at,
        }
        invocation_status: str
        evidence: dict | None = None
        if status != 200:
            invocation_status = "not_found" if status == 404 else "error_http"
        else:
            try:
                payload = json.loads(body.decode("utf-8"))
                msg = payload.get("message") or {}
                evidence = self._build_canonical_evidence(
                    doi=doi, msg=msg,
                    candidate_pointer=candidate_pointer,
                    retrieval_invocation_id=retrieval_invocation_id,
                    resolver_snapshot_sha=snapshot_sha,
                )
                invocation_status = "ok"
            except (json.JSONDecodeError, UnicodeDecodeError):
                invocation_status = "error_parse"
        rivr_id = _new_id("RIVR", self._counter)
        resolver_invocation = {
            "schema_version": "3.0-p1",
            "resolver_invocation_id": rivr_id,
            "candidate_pointer_id": candidate_pointer["candidate_pointer_id"],
            "resolver": self.name,
            "request": {
                "url": url,
                "method": "GET",
                "headers": {"User-Agent": USER_AGENT, "Accept": "application/json"},
                "body": None,
            },
            "response": {
                "http_status": status,
                "raw_snapshot_sha256": snapshot_sha,
                "attempts": attempts,
            },
            "status": invocation_status,
            "raw_snapshot_sha256": snapshot_sha,
            "started_at": started_at,
            "ended_at": ended_at,
        }
        if evidence is not None:
            evidence["provenance"]["resolver_invocation_id"] = rivr_id
        return evidence, resolver_invocation, snapshot

    def _failed_invocation(
        self,
        candidate_pointer: dict, retrieval_invocation_id: str,
        *,
        doi: str | None, http_status: int, body: bytes, ctype: str, attempts: int,
        status: str,
    ) -> tuple[None, dict, dict]:
        # Internal: build a snapshot + invocation for a pre-flight failure.
        # Currently only used when the candidate has no DOI.
        snapshot_sha = _sha256_bytes(body)
        snapshot = {
            "schema_version": "3.0-p1",
            "raw_snapshot_id": _new_id("RSNAP", self._counter),
            "kind": "resolver_response",
            "sha256": snapshot_sha,
            "bytes": base64.b64encode(body).decode("ascii"),
            "byte_length": len(body),
            "content_type": ctype or None,
            "captured_at": _now_iso(),
        }
        rivr_id = _new_id("RIVR", self._counter)
        invocation = {
            "schema_version": "3.0-p1",
            "resolver_invocation_id": rivr_id,
            "candidate_pointer_id": candidate_pointer.get("candidate_pointer_id", "CP-????"),
            "resolver": self.name,
            "request": {
                "url": "" if doi is None else f"{self.base_url}/works/{urllib.parse.quote(doi, safe='')}",
                "method": "GET",
                "headers": {"User-Agent": USER_AGENT, "Accept": "application/json"},
                "body": None,
            },
            "response": {"http_status": http_status, "raw_snapshot_sha256": snapshot_sha, "attempts": attempts},
            "status": status,
            "raw_snapshot_sha256": snapshot_sha,
            "started_at": _now_iso(),
            "ended_at": _now_iso(),
        }
        # Suppress unused-arg warnings.
        del retrieval_invocation_id
        return None, invocation, snapshot

    def _build_canonical_evidence(
        self,
        *,
        doi: str,
        msg: dict,
        candidate_pointer: dict,
        retrieval_invocation_id: str,
        resolver_snapshot_sha: str,
    ) -> dict:
        """Build a CanonicalEvidence record from Crossref's /works/{doi} payload.

        Per contract §7: "Do not invent unavailable metadata." Every
        field in the canonical block is either present in the upstream
        response or explicitly null. No fabricated placeholders.
        """
        title_list = msg.get("title") or []
        title = title_list[0] if title_list else None
        authors_raw = msg.get("author") or []
        authors: list[str] = []
        for a in authors_raw:
            given = a.get("given") or ""
            family = a.get("family") or ""
            full = (given + " " + family).strip()
            if full:
                authors.append(full)
        # Year: prefer issued.date-parts[0][0], fall back to created.
        year: int | None = None
        for date_field in ("issued", "published-print", "published-online", "created"):
            d = msg.get(date_field) or {}
            parts = (d.get("date-parts") or [[None]])[0]
            if parts and parts[0] is not None:
                try:
                    year = int(parts[0])
                    break
                except (TypeError, ValueError):
                    year = None
        venue = (msg.get("container-title") or [None])[0]
        source_locator = msg.get("URL") or f"https://doi.org/{doi}"
        return {
            "schema_version": "3.0-p1",
            "evidence_id": "",  # backfilled by caller (resolve())
            "candidate_pointer_id": candidate_pointer["candidate_pointer_id"],
            "canonical": {
                "title": title,
                "authors": authors,
                "year": year,
                "venue": venue,
                "doi": doi,
                "source_locator": source_locator,
                "resolver_identity": self.name,
            },
            "provenance": {
                "retrieval_invocation_id": retrieval_invocation_id,
                "resolver_invocation_id": "",  # backfilled by caller
                "retrieval_snapshot_sha256": candidate_pointer.get("_retrieval_snapshot_sha256", ""),
                "resolver_snapshot_sha256": resolver_snapshot_sha,
            },
            "created_at": _now_iso(),
        }


# ---- Runtime fingerprint helpers (P1-RA1 Blocker B) -----------------------

def _implementation_file_sha256() -> str:
    """SHA-256 of this file's bytes, used as the implementation hash
    for both the provider and the resolver manifest (they share the
    same file). Deterministic and traceable to repository code.
    """
    import pathlib
    here = pathlib.Path(__file__).resolve()
    return _sha256_bytes(here.read_bytes())


def _package_version() -> str:
    """The package's PEP 440 ``__version__``. P1 components version
    alongside the package; the schema namespace ``3.0-p0`` /
    ``3.0-p1`` is documented separately in VERSION.md.
    """
    try:
        from . import __version__
        return __version__
    except Exception:
        return "0.0.0+unknown"


def build_provider_manifest() -> dict:
    """Return a dict ready to be wrapped in ``ProviderManifest`` for the
    CrossrefRetrievalProvider. P1-RA1 §2 (Blocker B).
    """
    return {
        "name": CROSSREF_PROVIDER_NAME,
        "version": _package_version(),
        "capabilities": list(PROVIDER_CAPABILITIES),
        "network_requirement": "online_required",
        "trust_class": "scholarly_index",
        "namespace": "crossref",
        "sha256": _implementation_file_sha256(),
    }


def build_resolver_manifest() -> dict:
    """Return a dict ready to be wrapped in ``ResolverManifest`` for the
    CrossrefReferenceResolver. P1-RA1 §2 (Blocker B).
    """
    return {
        "name": CROSSREF_RESOLVER_NAME,
        "version": _package_version(),
        "capabilities": list(RESOLVER_CAPABILITIES),
        "trust_class": "scholarly_index",
        "namespace": "crossref",
        "sha256": _implementation_file_sha256(),
    }
