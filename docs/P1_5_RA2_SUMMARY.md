# MAFS v3.0-P1.5-RA2 — Human Summary (Layer 1 + Layer 2)

> P1.5-RA2 acceptance-facing human summary. Per P1.5-RA2 contract §6.2,
> this document is split into two layers:
>
> - **Layer 1** (machine-sourced facts) — derived from
>   `docs/P1_5_RA2_METRICS.json` (CI run `33267536220`, source `live`,
>   commit `508bde3`). If this layer contradicts the machine
>   artifacts, **the machine artifacts are the source of truth.**
> - **Layer 2** (human interpretation) — may contain what the result
>   means, architecture judgment, limitations, recommendation,
>   next-step reasoning. Never overwrites or silently restates a
>   machine fact differently (per §6.2).
>
> Run pin (per §6.3):
> - `selected_run_id: 33267536220`
> - `commit_sha: 508bde3`
> - `build_id: ci-live`
> - `source: live`
> - `build_time: 2026-08-29T18:10:37Z`
> - `branch: dev/mafs-v3-p0-ra2`

---

## Layer 1 — Machine-Sourced Facts

The full Layer 1 field set is in `docs/P1_5_RA2_METRICS.json` and
`docs/P1_5_RA2_CI_PROVENANCE.md`. Summary table for HO + ChatGPT
review:

| Layer 1 field | Pinned value (run 33267536220) |
|---|---|
| `final_recall` | `3/3` |
| `baseline_recall` | `0/3` (frozen pre-P1.5) |
| `scholarly_anchor_recovered` | `3` |
| `scholarly_identity_safe_recall` | `1.0` |
| `per_anchor_recovery` | `S1: RECOVERED, S2: RECOVERED, S3: RECOVERED` |
| `per_anchor_rank` (actual matched rank, NOT hard-coded) | `S1: 1, S2: 1, S3: 2` |
| `fabrication_hard_invariant_holds` | `true` |
| `fabricated_reference_count` | `0` |
| `fabricated_entity_count` | `0` |
| `architecture_drift_detected` | `false` |
| `caller_selects_candidate_pointer` | `true` |
| `execution_auto_selects_top1` | `false` |
| `no_selection_means_no_resolution` | `true` |
| `invalid_selection_fails_honestly` | `true` |
| `oracle_logic_benchmark_only` | `true` |
| `oracle_selects_explicit_candidate_pointer` | `true` |
| `production_relevance_logic_added` | `false` |
| `per_anchor_rank_is_actual_candidate_rank` | `true` |
| `hardcoded_rank_one_removed` | `true` |
| `subtraction_metrics_git_derived` | `true` |
| `new_ranker_count` / `new_solver_count` / `new_provider_count` | `0` / `0` / `0` |
| `production_loc_increase` | **`true`** (honest; +180 production_src net) |
| 5/5 workflows | `PASS` |

> Per P1.5-RA2 §11: "RA2 acceptance is not contingent on reproducing
> exactly 2/3. Live Crossref behavior may vary." The 3/3 result of this
> run is reported faithfully; the architecture-removal tests (T1-T10)
> are the gate, and they all pass.

---

## Layer 2 — Human Interpretation

### 1. What this contract was about

P1.5-RA1 left three residual problems:

1. **Caller selected a rung, but execution still auto-picked top-1.**
   The P1.5-RA1 LiveChain required an `external_selection` (a
   rendering_path) but once that rung was selected, the chain
   still resolved that rung's top-1 CandidatePointer. The model
   had not actually chosen the *specific* paper.

2. **`per_anchor_rank` was hard-coded to 1.** The score code
   reported `per_anchor_rank[anchor_id] = 1` whenever the
   paper_identity_status was RECOVERED, regardless of the actual
   matched rank. A rank-3 oracle match was reported as rank 1.

3. **Subtraction accounting was a hand-coded boolean.** The
   P1.5-RA1 acceptance artifacts reported
   `production_loc_increase=false` even though the actual git
   diff supported a positive net production/runtime delta.

P1.5-RA2 closes only these three problems. It does not optimize
recall, add a new provider, or build a new selection engine.

### 2. What was removed (Subtraction Ledger)

| Removed / tightened | Where | What it used to do | Replaced by |
|---|---|---|---|
| `external_selection: str \| None` (rung only) | `src/mafs_p0/live_chain.py` | Caller could select a rung; chain auto-picked top-1 | `external_selection: dict {rendering_path, candidate_pointer_id or doi}` — caller MUST name the specific paper |
| `selected_rq = candidates[0]` (implicit top-1) | `src/mafs_p0/live_chain.py` | Chain auto-resolved the top-1 of the selected rung | Chain finds the exact candidate by cp_id OR doi; honest failure (`invalid_external_selection` / `candidate_selection_required`) if absent |
| `is_legacy_path` auto-canonize carve-out | `src/mafs_p0/live_chain.py` | Legacy `compiled_query` path auto-picked top-1 even when explicit-selection policy was in force | Legacy path is one rung with `rendering_path=LADDER_RUNG_LEGACY`; same explicit-selection boundary applies |
| Orchestrator's duplicate `resolver.resolve(...)` | `scripts/replay_b.py::_run_q_benchmark_with_oracle_selection` | Benchmark had its own resolver path AND a separate LiveChain call | Orchestrator identifies the oracle-matched CandidatePointer, then calls `LiveChain` with `external_selection={rendering_path, doi}` and `pre_walked_candidates_by_rung`; LiveChain owns resolution |
| `per_anchor_rank[anchor_id] = 1` (hard-coded) | `scripts/replay_b.py` | Score reported rank 1 for any RECOVERED anchor | `per_anchor_rank[anchor_id] = chain.selected_candidate_rank` (actual matched rank) |
| `_resolved_doi(evidence)` reading `evidence.provenance.doi` | `scripts/replay_b.py` | DOI fallback mis-attributed the resolved paper to the top-1 | Reads `evidence.canonical.doi` (the actually-resolved paper) |
| `production_loc_increase=false` (hand-coded) | `docs/P1_5_RA1_*` (round 1) | Round 1 claimed subtraction without git evidence | `subtraction_accounting.production_loc_increase = (production_src_net > 0)` derived from `git diff --numstat f59c02e..HEAD` |

**Production LOC delta (P1.5-RA2, vs f59c02e):**

| Bucket | Additions | Deletions | Net |
|---|---:|---:|---:|
| `src/mafs_p0/*.py` (production src) | 302 | 122 | **+180** |
| `scripts/*.py` (benchmark orchestrator) | 285 | 80 | **+205** |
| `tests/*.py` (tests) | 916 | 73 | **+843** |
| `docs/*.{md,json,txt}` (docs) | 0 | 0 | **0** |

> Per P1.5-RA2 §5.2: "Do not claim subtraction unless git evidence
> supports it. Report actual numbers." The numbers above are
> real `git diff --numstat` output. `production_loc_increase=true`
> is honest: the RA2 boundary repair required enlarging the
> explicit-selection surface in LiveChain, the orchestrator's
> pre-walk helper, and the score code. The per-file add/delete
> ratios (e.g. live_chain.py +249/-120) show many additions are
> matched by deletions of the prior auto-canonize / heuristic
> code — the implementation net is bounded; what grew is the
> explicit-selection surface, not new cleverness.

### 3. Architecture-statement answer (per P1.5-RA2 §12 item 10)

> **Before RA2:**
> the caller could select a *rung*, but execution still
> auto-selected that rung's top-1 CandidatePointer. The
> execution layer also mis-reported the matched rank as 1
> regardless of the actual rank. The subtraction accounting
> reported a hand-coded `false`.
>
> **After RA2:**
> the model / caller selects the *specific CandidatePointer*;
> execution only resolves and records it. The reported rank
> is the actual matched rank. The subtraction accounting is
> git-derived.

### 4. The selected rung is no longer a sufficient boundary

The P1.5-RA1 contract called for `external_selection = {rendering_path}`.
P1.5-RA2 §2.2 strengthens this: the selection must identify the
**specific CandidatePointer**, not just the rung. The chain
accepts either `candidate_pointer_id` (intra-walk stable) or
`doi` (cross-walk stable). The chain returns one of:

- `ladder_completed_no_selection` — no selection supplied
- `candidate_selection_required` — rung selected but no pointer
- `invalid_external_selection` — rung/pointer does not exist in the walked candidates
- `ok` — the specific pointer was resolved

The chain does NOT auto-canonize top-1 in any of these paths.

### 5. The benchmark no longer duplicates the resolver

The P1.5-RA1 orchestrator's helper walked the ladder with the
production provider, found the oracle-matched candidate, and
*also* called `resolver.resolve(...)` directly. P1.5-RA2 §3
says: do not duplicate the resolver path. The orchestrator now
identifies the matched candidate, then calls LiveChain with
`external_selection={rendering_path, doi}` and the
pre-walked candidates. LiveChain owns the resolver.

The pre-walked-candidates optimization is a small extension to
avoid two failure modes: (1) the chain's own ladder walk can
re-issue HTTP and hit Crossref rate limits (429); (2) the
chain's per-walk cp_id namespace is not stable across walks,
so passing `candidate_pointer_id` from the orchestrator's
walk can fail to find it. Passing the pre-walked candidates
+ `doi` resolves both.

### 6. Verification of acceptance

- 10 of 10 mandatory RA2 tests pass offline
  (`tests/test_p1_5_ra2.py` T1-T10):
  - T1: rung-only selection does NOT resolve top-1
  - T2: explicit cp_id is resolved even at rank > 1
  - T3: invalid cp_id fails honestly (no top-1 fallback)
  - T4: no selection means no resolver (CandidateSets exposed)
  - T5: benchmark uses candidate-level selection (LiveChain + doi)
  - T6: per_anchor_rank is the actual matched rank (no hard-coded 1)
  - T7: CP -> Resolver continuity (selected cp_id == resolver's cp_id)
  - T8: fabrication invariant (no evidence/entity fabrication)
  - T9: Q3 / Q5 boundaries preserved
  - T10: subtraction metrics are git-derived (not a hard-coded boolean)
- Local pytest: **132 passed, 1 skipped (legacy warning)**.
- 1 final live CI run (`33267536220`) was performed per §10.
  All 5 workflows PASS.
- 0 new providers, 0 new rankers, 0 new solvers, 0 new
  generic query planners, 0 new schema families, 0 P2/P3
  work (per §8).
- The previously existing P1 tests were updated to the new
  explicit-selection shape via a small test helper that does
  discovery first, picks the top-1, then explicitly selects
  it. No production semantics changed.

### 7. Q3 / Q5 boundary

- Q3 remains `PENDING_NEGATIVE_COVERAGE_RULE` (positive
  recall is now 3/3; the negative-evidence semantics for a
  Q3 search that returned an unrelated candidate are still
  bounded by RA2 §3 Case 3).
- Q5 remains `ENTITY_RESOLUTION_REQUIRED` (no FlyWire /
  VFB / hemibrain / neuPrint dataset adapter added; per
  §8 the production stack still lacks entity resolution).
- DNg01 remains `UNRESOLVED` (no synonymy asserted; per
  RA1 §2 this is preserved).

### 8. Limitations / open observations

- The P1.5-RA2 acceptance gate is the architecture-removal
  tests (T1-T10), not the recall number. The 3/3 result is a
  faithful report of the live run; Crossref behavior can
  vary, and a future run may yield a different number.
- The P1.5-RA1 `is_legacy_path` carve-out that the prior
  round acknowledged as a "soft compromise" is now removed
  in RA2. The legacy `compiled_query` path uses the same
  strict explicit-selection boundary as the P1.5 ladder.
- The subtraction accounting reports `production_loc_increase=true`
  honestly. The contract §5.3 note that "achieving a negative
  LOC delta is desirable, not a reason to distort code" was
  honored: no code was distorted to make the number smaller
  or the boolean false.

### 9. Recommended next step

**STOP per §14.** The bounded P1.5-RA2 contract is complete.
The architectural removals (Closure A, B, C, D) are verified
by offline tests; the live CI result is reported faithfully.
No new provider, no generic planner, no P2, no dataset
adapter, no retrieval-quality improvement beyond the
existing thin Crossref-native renderer + explicit
candidate-level selection boundary. The next step is a HO
+ ChatGPT decision on whether to authorize a P1.5.1 / P1.6
/ P2 contract — or to accept the current capability ceiling
(`0/3 → 3/3` thin Crossref-native rendering with explicit
candidate-level ownership, no hidden auto-canonization, and
git-derived subtraction accounting) as the final MAFS v3.0
scholarly-stack boundary.

---

## Machine-Generated vs Human-Readable Distinction

This document's Layer 1 section is the human-readable rendering
of the machine-pinned fields. The following files are the
**machine-generated evidence** and the authoritative source of
truth for this run (`33267536220`):

- `docs/P1_5_RA2_METRICS.json` — Layer 1 JSON metrics
- `docs/P1_5_RA2_CI_PROVENANCE.md` — Layer 1 CI provenance
- `docs/P1_5_RA2_SHA256_MANIFEST.txt` — SHA-256 digests
- `docs/P1_5_METRICS.json` — P1.5 source-run metrics
- `docs/P1_5_CI_PROVENANCE.md` — P1.5 source-run CI provenance
- `docs/P1_5_HUMAN_SUMMARY.md` — P1.5 source-run human summary
- `docs/P1_5_SHA256_MANIFEST.txt` — P1.5 source-run SHA-256 manifest
- `docs/REPLAY_B_RA1_METRICS.json` — Replay B RA1 metrics
- `docs/REPLAY_B_RA1_CI_PROVENANCE.md` — Replay B RA1 CI provenance
- `docs/REPLAY_B_RA1_SUMMARY.md` — Replay B RA1 human summary
- `docs/REPLAY_B_RA1_SHA256_MANIFEST.txt` — Replay B RA1 SHA-256 manifest
- `examples/runs/P1_5/*` — P1.5 example runs (gitignored, on disk)
- `examples/runs/ReplayB/*` — Replay B example runs (gitignored, on disk)

> If this document contradicts any of the above files, the machine
> artifacts are the source of truth.
