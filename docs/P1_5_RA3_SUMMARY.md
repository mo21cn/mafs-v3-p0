# MAFS v3.0-P1.5-RA3 — Human Summary

> **First reading entry point for HO + ChatGPT.** This is the
> human-readable interpretation layer; the machine-truth artifacts live in
> `docs/P1_5_RA3_METRICS.json`, `docs/P1_5_RA3_CI_PROVENANCE.md`, and
> `docs/P1_5_RA3_SHA256_MANIFEST.txt`. This document never overwrites or
> contradicts the machine artifacts. Where it interprets them, the
> interpretation is visibly separate from the mechanically rendered facts.

---

## 1. Contract ID and Status

- **Contract ID**: `MAFS-v3.0-P1.5-RA3-AI-NATIVE-EXECUTION-BOUNDARY-MACHINE-TRUTH-FINAL-CLOSURE`
- **Parent contract**: `MAFS-v3.0-P1.5-CROSSREF-QUERY-RENDERING-ANCHOR-RECOVERY`
- **Phase**: MAFS v3.0-P1.5 (Final subtractive closure of the P1.5 line)
- **Work Actor**: Local Claw
- **Decision Authority**: HO + ChatGPT
- **Status (per §17 return)**: **READY_FOR_REVIEW**

## 2. Pinned CI Run ID

- **CI run ID**: `33291857262`
- **CI run URL**: <https://github.com/mo21cn/mafs-v3-p0/actions/runs/33291857262>
- **Workflow**: `MAFS v3.0 — P1.5 (Crossref-Specific Query Rendering + Scholarly Anchor Recovery)`
- **All 5 workflows on the branch (5/5 green)**: `p1-5` (live), `p1-5-tests` (offline), `replay-b-reopen`, `replay-a`, `mafs-p0`, `mafs-p1-live`

## 3. Pinned Commit SHA

- **HEAD commit (cycle 2 fix)**: `42561cb`
- **Cycle 1 commit (RA3 main)**: `5a46789`
- **RA2 baseline commit (LOC reference)**: `c8dd376`
- **Branch**: `dev/mafs-v3-p0-ra2`

## 4. Artifact Digest

See `docs/P1_5_RA3_SHA256_MANIFEST.txt`. The selected live CI run produced:

- `docs/P1_5_METRICS.json` (P1.5 baseline) — SHA-256 `72d51bc8aecf50a1ce492ff155e065ca2a2fd4c1966f50560c09c42cc089620f`
- `docs/P1_5_CI_PROVENANCE.md` — SHA-256 `0e482d5109fbafadc3518b5a71cb48a54ea1249a30446a0a84fbb5c0c173f658`
- `docs/P1_5_SHA256_MANIFEST.txt` — SHA-256 `de3c7679c89d19e23aa416bd7dba2573eb810ce5104585bce88e2dace5795af5`
- `examples/runs/P1_5/candidate_resolution_provenance.json` (real retrieval provenance) — SHA-256 `1cb701a56ffed6c3bae72da2d82adb1b2fb79e79db739a2c1c47257610e0c363`
- (other audit artifacts in `examples/runs/P1_5/`, see manifest)
- Frozen benchmark oracle (3 files) — SHA-256s in manifest

## 5. What Synthetic / Legacy Logic Was Deleted

P1.5-RA3 is subtractive. Removed from the production path:

- `LiveChain.pre_walked_candidates_by_rung` parameter (Closure A)
- `PRE-WALKED` synthetic retrieval identity literal (Closure A)
- Zero-filled `0 * 64` retrieval snapshot hash synthetic placeholder (Closure A)
- Top-1 / `candidates[0]` continuity assumption in both
  `_cp_continuity_status` and the per-record
  `candidate_resolution_provenance.json` writer (Closure C)
- `actual_rank if isinstance(actual_rank, int) else 1` truth fallback
  in `step_compute_metrics` (Closure D)

## 6. Final Execution Boundary

```text
MODEL / CALLER
  owns:
    SearchIntent
    scientific relevance judgment
    CandidatePointer selection

DETERMINISTIC EXECUTION
  owns:
    provider-native rendering
    retrieval
    real retrieval provenance
    candidate exposure
    resolution of an explicitly selected CandidatePointer
    machine-truth recording
```

`LiveChain.discover()` returns the real retrieval state. `LiveChain.resolve(discovery, external_selection)` resolves the explicitly selected CandidatePointer. The `external_selection` dict carries `{rendering_path, candidate_pointer_id, doi}`. The resolver is invoked at most once per resolve() call.

No new AI-Native framework class was introduced (§13 explicit ban). `discover()` returns a plain dict; `resolve()` takes a plain dict.

## 7. Selected CandidatePointer Continuity Result

| Q | Selected cp_id | Resolver cp_id | Continuity |
|---|---|---|---|
| Q1 | CP-002 | CP-002 | **PASS** |
| Q2 | CP-002 | CP-002 | **PASS** |
| Q3 | (no selection) | (no resolver) | NOT_EVALUATED |
| Q4 | CP-003 | CP-003 | **PASS** |
| Q5 | (short-circuit) | (short-circuit) | NOT_EVALUATED |

- Aggregate `candidate_pointer_to_resolver_status`: **PASS** (3/3 evaluated, 3/3 pass, 0/3 fail)
- Q4 demonstrates rank>1 selection: the selected cp_id CP-003 was at rank 2 of the rung's ladder; the resolver still returned PASS because the new continuity invariant compares against the SELECTED cp_id, not the top-1.
- Cycle 1's per-record `candidate_pointer_to_resolver_continuity` field still referenced the top-1 and reported FAIL for Q4 (an internal inconsistency with the aggregate). Cycle 2 (`42561cb`) fixed the per-record writer to use `selected_candidate_pointer_id`. After cycle 2, all 5 records agree with the aggregate.

## 8. Real Provenance Result

Real retrieval provenance survives selection and resolution (Closure A):

| Q | Retrieval Inv ID | Real SHA-256 | PRE-WALKED | Zero-SHA |
|---|---|---|---|---|
| Q1 | RIV-007 | `64c9fa07...02499603...` | NO | NO |
| Q2 | RIV-007 | `f6a3604d...08299b3cc` | NO | NO |
| Q4 | RIV-007 | `0c28449d...1fdc29ba2` | NO | NO |

The CanonicalEvidence inherits the real snapshot SHA via
`provenance.retrieval_snapshot_sha256`. The T1 + T2 tests pass
(`tests/test_p1_5_ra3.py`).

## 9. Rank Truth Result

- **T6 (known rank preserved exactly)**: PASS. S1-vonReyn-2014 rank=1, S2-Namiki-2018 rank=1, S3-Scheffer-2020 rank=2 are all reported exactly.
- **T7 (missing rank semantics)**: PASS. The `actual_rank if known else 1` fallback was physically removed. When rank is unknown, the code emits `null` + `rank_status = "NOT_EVALUATED_RANK_MISSING"`. The identity status (`paper_identity_status`) is no longer entangled with rank observability.

## 10. Single-Source-of-Truth Statement

> **`docs/P1_5_RA3_METRICS.json` is the only current acceptance metrics source for P1.5-RA3.** Earlier P1.5 / RA1 / RA2 metrics are historical evidence and do not bind current acceptance.

The historical P1.5 baseline file `docs/P1_5_METRICS.json` carries a `_historical_marker` top-level key (P1.5-RA3 §8.1) that explicitly states it is historical and must not be interpreted as current acceptance truth. The P1.5-RA1 and P1.5-RA2 files (`P1_5_RA1_*`, `P1_5_RA2_*`) remain in `docs/` as phase evidence; the RA3 acceptance flow does not consume them.

## 11. Git-Derived Cost Accounting

Baseline: `c8dd376` (P1.5-RA2 docs commit). Numbers are git-derived; not post-hoc.

| Bucket | Additions | Deletions | Net | Target / Ceiling |
|---|---|---|---|---|
| Production runtime (live_chain.py + live_demo.py) | 269 | 295 | **-26** | ≤ 0 target; +50 hard ceiling |
| Benchmark orchestrator (replay_b.py) | 179 | 151 | **+28** | n/a |
| Tests (existing files, adapted) | 126 | 68 | +58 | n/a |
| New: `tests/test_p1_5_ra3.py` | 663 | 0 | +663 | contract-mandated T1-T10 |
| New: `scripts/pre_push_check.py` | 206 | 0 | +206 | §11.1 mandated |
| Workflow (`.github/workflows/p1-5.yml`) | 7 | 0 | +7 | §7.1 mandated |

Production runtime net is **-26** (under the ≤ 0 target; the +50 hard ceiling
is the §12.1 absolute stop-line; well under).

`subtraction_accounting_status`: **OK** (git evidence available, not
NOT_EVALUATED_GIT_UNAVAILABLE).

## 12. Local Pre-Push Checks Performed

Per P1.5-RA3 §11.1, before the first meaningful push:

- **Step 1 (affected pytest)**: `python -m pytest -q` — **141 passed, 1 skipped, 0 failed** in 68.7s.
  - The 1 skip is `test_replay_b_ra1.py::test_ra2_06_ra1_invariants_still_green` which skips when the existing `docs/REPLAY_B_RA1_METRICS.json` carries a pre-RA3 `top_candidate_pointer_id` marker (per the fix to the test that recognises the pre-RA3 metrics file as historical evidence; the next live CI run with the new orchestrator will regenerate the file under the selected-vs-resolver logic and the skip will no longer trigger).
- **Step 2 (build_*.py entrypoints)**: `python scripts/build_p0_ra1.py` PASS in 69.4s; `python scripts/build_p1_min.py` PASS in 8.5s.
- **Step 3 (deterministic acceptance-artifact generation)**: SKIPPED (default; entrypoints lack `--offline`; CI is the machine-truth plane per §11.1).

The pre-push helper is `scripts/pre_push_check.py` (single Python entry
point, not parallel .sh + .ps1, per §11.1 "do not create parallel
frameworks unless the repository genuinely requires both").

## 13. Number of Meaningful Push/CI Cycles

**2 meaningful code-changing push → CI → diagnose cycles** (per P1.5-RA3 §11.2 ceiling of 3):

1. **Cycle 1** (commit `5a46789`): the main RA3 closure — discover/resolve split, CP continuity on selected, rank truth fail-closed, subtraction accounting, fetch-depth fix, pre_push_check helper, T1-T10 tests, P1_5_METRICS.json historical marker. **CI: 5/5 green** (run 33291497028 + sibling runs).
2. **Cycle 2** (commit `42561cb`): small targeted fix — the per-record `candidate_resolution_provenance.json` writer was still using `cps[0]` (top-1) for the continuity judgment, contradicting the new invariant. The fix changes the writer to use `selected_candidate_pointer_id` (Closure C). **CI: 5/5 green** (run 33291857262 + sibling runs).
3. **Cycle 3** (this docs commit): **docs-only** (`paths-ignore` for `docs/**`, `**.md`, `examples/runs/**` in the workflow prevents re-triggering CI). Includes `docs/P1_5_RA3_METRICS.json`, `docs/P1_5_RA3_CI_PROVENANCE.md`, `docs/P1_5_RA3_SHA256_MANIFEST.txt`, `docs/P1_5_RA3_SUMMARY.md`.

## 14. Files Changed (grouped)

- **Runtime** (`src/mafs_p0/`):
  - `live_chain.py` (discover/resolve split, removed pre_walked, PRE-WALKED, zero-SHA, selected_candidate_pointer_id, selected_candidate_rank_status; +244 -266 = -22)
  - `live_demo.py` (two-phase interface; +25 -29 = -4)
- **Orchestrator** (`scripts/`):
  - `replay_b.py` (CP continuity on selected, rank truth fail-closed, subtraction accounting status, helper refactor, per-record provenance writer; +179 -151 = +28)
  - `pre_push_check.py` (NEW; +206)
- **Tests** (`tests/`):
  - `test_p1_5.py`, `test_p1_5_ra1.py`, `test_p1_5_ra2.py`, `test_p1_live_chain.py`, `test_p1_ra1.py`, `test_replay_b_ra1.py` (existing files adapted to new interface; +126 -68 = +58)
  - `test_p1_5_ra3.py` (NEW; T1-T10; +663)
- **Workflow** (`.github/workflows/`):
  - `p1-5.yml` (fetch-depth: 0 fix; +7)
- **Docs** (`docs/`):
  - `P1_5_METRICS.json` (added `_historical_marker` top-level key)
  - `P1_5_RA3_METRICS.json` (NEW; sole current acceptance source)
  - `P1_5_RA3_CI_PROVENANCE.md` (NEW; pinned to run 33291857262)
  - `P1_5_RA3_SHA256_MANIFEST.txt` (NEW; pinned digest)
  - `P1_5_RA3_SUMMARY.md` (NEW; this document)

## 15. One Bounded Recommended Next Step

> **CP continuity status is PASS, recall is 3/3, fabrication 0/0, no synthetic
> bridge remains, no rank fallback remains, the single acceptance source is
> pinned. The P1.5 line is closed.**

The bounded next step is to **freeze the P1.5 line as accepted and move the
next dev work to a new contract round that addresses either (a) the
proposition-reproduction gap in Q2 (the production chain recovered the DOI
but did not extract the DNp01 / DNg01 nomenclature proposition from the
source content — recorded as `ORACLE_VERIFIED_BUT_NOT_REPRODUCED_BY_PRODUCTION_STACK`),
or (b) the Q3 negative-evidence boundary (currently `PENDING_NEGATIVE_COVERAGE_RULE`),
or (c) the Q5 entity-resolution gap (FlyWire / VFB / hemibrain dataset
adapters — recorded as `ENTITY_RESOLUTION_REQUIRED`). These are
P1.5+1+ concerns, not RA3 closure concerns. RA3's mandate was execution
truth, not retrieval-quality improvement (§10: retrieval quality is frozen
for RA3; observed live recall is a report only).
