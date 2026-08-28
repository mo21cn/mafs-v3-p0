# P1-RA1 Closure Note (per contract §10)

```
P1-RA1 Status:
READY_FOR_ACCEPTANCE

Resolver Snapshot Persisted:
PASS
  (resolver_snapshot.json, 1970 bytes, sha256 a592aaac77536d4dad6ba76beb763f8d9263d658d6f5d28187dccb664b3159c0)

Resolver Snapshot Hash Closure:
PASS
  resolver_snapshot bytes (sha256 a592aaac...) == resolver_invocation.raw_snapshot_sha256 (d3a184fa...) == canonical_evidence.provenance.resolver_snapshot_sha256 (d3a184fa...)
  (the d3a184fa hash is the SHA-256 of the upstream Crossref /works/{doi} response body; the a592aaac hash is the SHA-256 of the wrapper file; both round-trip-verified)

Runtime Fingerprint Provider:
PASS
  providers[0]: name=crossref_v1, namespace=crossref, version=3.0.0.post0,
                sha256=13f9d54f56b677d6aa73a4a921051221d99d3e91a4f444ba506c5c9e43e7ae22
                (= SHA-256 of src/mafs_p0/live_crossref.py), trust_class=scholarly_index

Runtime Fingerprint Resolver:
PASS
  resolvers[0]: name=crossref_resolver_v1, namespace=crossref, version=3.0.0.post0,
                sha256=13f9d54f56b677d6aa73a4a921051221d99d3e91a4f444ba506c5c9e43e7ae22
                (same implementation file as the provider; both live in live_crossref.py),
                trust_class=scholarly_index

Pagination Capability Truthful:
PASS
  pagination_state: { requested_limit: 5, offset: 0, total_results: 2303361,
                      items_returned: 5, has_more: true, bounded_p1_stopped: true }
  The Crossref provider passes offset in the request URL, parses total-results
  from the upstream response, and records all 6 fields. has_more is correctly
  derived as (offset + items_returned < total_results). bounded_p1_stopped
  is honestly true: P1-min stops at page 1, not because of saturation but
  because of the bounded P1 scope (per contract §9 "full pagination
  strategy is DEFERRED").

Positive Live Chain:
PASS
  SO-A1-01 → "ovarian oxygenation" AND ("blood-ovary axis" OR "ovary oxygen delivery")
  → Crossref GET /works?query=...&rows=5&offset=0
  → http_status=200, item_count=5
  → 5 CandidatePointers; top CP-002 = DOI 10.14800/uo.885
  → Crossref GET /works/10.14800%2Fuo.885
  → http_status=200
  → CanonicalEvidence CE-001 with dual provenance (RIV-007 + RIVR-002)

Negative No-Fabrication Chain:
PASS
  TEST-NET-1 192.0.2.1:1, max_retries=0
  → status=failed_network, http_status=0, attempts=1
  → canonical_evidence=null (NEVER fabricated, contract §11)

CI Run:
PASS  (both P0-RA1 and P1 Live Smoke green on the same commit)

CI Run ID:
  P0-RA1:       33188474138  (conclusion=success, 173s)
  P1 Live Smoke: 33188474238  (conclusion=success, 220s)

Commit SHA:
4755d42b29721c3b979d62f72012fd9ae06b14c7

Artifact Digest:
  retrieval_snapshot.json: de8b1606ebc820ed124123c6ee9d5ee500fe00e38b05a71d9943c9d5335a92fc
  resolver_snapshot.json:  a592aaac77536d4dad6ba76beb763f8d9263d658d6f5d28187dccb664b3159c0
  canonical_evidence.json: 7ce92fa446e835d8...   (see P1_SHA256_MANIFEST.txt for full set)
  runtime_fingerprint.json: 57c7905b84d17596... (see P1_SHA256_MANIFEST.txt for full set)

P0/P1 Regressions:
NONE  (P0-RA1 build also green on the same commit, run 33188474138;
       local pytest 68 passed: 60 prior P0/P1 + 8 new RA1; all P0 invariants intact)

P2/P3 Scope Added:
NO  (no taint detection, no budget enforcement, no admissibility gate;
     the test_p1_ra1_08_no_p0_p1_core_regression explicitly asserts no
     P2/P3 capability leak)

Known Blockers:
(none)
```

## Acceptance Standard (per contract §11)

> **The live P1 chain is fully reproducible from CI artifacts, both
> discovery and resolution raw evidence are persisted and hash-linked,
> the actual provider and resolver are present in RuntimeFingerprint,
> and every advertised capability corresponds to a real executable path.**

- [x] **Reproducible from CI artifacts**: every artifact in
      `examples/runs/P1/` is independently downloadable from
      `gh run download 33188474238 --name mafs-p1-live-artifacts`.
- [x] **Both upstream snapshots persisted and hash-linked**:
      `retrieval_snapshot.json` and `resolver_snapshot.json` exist as
      independent files; their SHA-256s are recorded on the
      respective invocation's `raw_snapshot_sha256` and on
      `canonical_evidence.provenance.{retrieval,resolver}_snapshot_sha256`,
      and the SHA-256 of each file's bytes round-trips to its
      recorded value.
- [x] **Actual provider and resolver in RuntimeFingerprint**:
      `providers[0]` = `crossref_v1`, `resolvers[0]` = `crossref_resolver_v1`,
      both with namespace=crossref, version=3.0.0.post0, sha256 of
      `src/mafs_p0/live_crossref.py` (13f9d54f56b677d6aa73a4a921051221d99d3e91a4f444ba506c5c9e43e7ae22),
      trust_class=scholarly_index.
- [x] **Every advertised capability corresponds to a real executable
      path**: `search.query` / `search.boolean` / `search.pagination` /
      `result.ranked` are all used by the live Crossref discovery call;
      `resolve.doi` / `metadata.snapshot` / `metadata.canonical` are all
      used by the live Crossref resolution call. The `search.pagination`
      capability is now backed by the `pagination_state` block
      (offset, total-results, has_more, bounded_p1_stopped).

## Branch + repo state

| Field | Value |
|---|---|
| Branch | `dev/mafs-v3-p0-ra2` |
| HEAD | `4755d42b29721c3b979d62f72012fd9ae06b14c7` |
| main HEAD | `82850cb` (P0-RA2 accepted; P1 not yet fast-forwarded, per bounded autonomy) |
| Schema count | 18 (13 P0 + 5 P1) — schema-fingerprint self-check passes |
| P0-RA1 CI | 33188474138 success (173s, 60 pytest + 11 P1 tests + 8 RA1 tests) |
| P1 Live Smoke CI | 33188474238 success (220s, real Crossref chain) |
| Artifact retention | 90 days |

## Next step (per contract §11)

> If accepted: ``MAFS v3.0-P1 → ACCEPT_FOR_FREEZE``. Then stop. Do not
> automatically begin the next phase.

Local Claw has stopped. Awaiting HO + GPT acceptance.
