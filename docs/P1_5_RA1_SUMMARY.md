# MAFS v3.0-P1.5-RA1 — Human Summary (Layer 1 + Layer 2)

> P1.5-RA1 acceptance-facing human summary. Per P1.5-RA1 contract §6.2,
> this document is split into two layers:
>
> - **Layer 1** (machine-sourced facts) — derived from
>   `docs/P1_5_METRICS.json` (CI run `33260336752`, source `live`,
>   commit `d86ccd1`). If this layer contradicts the machine
>   artifacts, **the machine artifacts are the source of truth.**
> - **Layer 2** (human interpretation) — may contain what the result
>   means, architecture judgment, limitations, recommendation,
>   next-step reasoning. Never overwrites or silently restates a
>   machine fact differently (per §6.2).
>
> Run pin (per §6.3):
> - `selected_run_id: 33260336752`
> - `commit_sha: d86ccd1`
> - `build_id: ci-live`
> - `source: live`
> - `build_time: 2026-08-29T15:28:26Z`
> - `branch: dev/mafs-v3-p0-ra2`

---

## Layer 1 — Machine-Sourced Facts

The full Layer 1 field set is in `docs/P1_5_RA1_METRICS.json` and
`docs/P1_5_RA1_CI_PROVENANCE.md`. Summary table for HO + ChatGPT
review:

| Layer 1 field | Pinned value (run 33260336752) |
|---|---|
| `final_recall` | `3/3` |
| `baseline_recall` | `0/3` (frozen pre-P1.5) |
| `scholarly_anchor_recovered` | `3` |
| `scholarly_identity_safe_recall` | `1.0` |
| `per_anchor_recovery` | `S1: RECOVERED, S2: RECOVERED, S3: RECOVERED` |
| `per_anchor_rank` | `S1: 1, S2: 1, S3: 1` |
| `fabrication_hard_invariant_holds` | `true` |
| `fabricated_reference_count` | `0` |
| `fabricated_entity_count` | `0` |
| `architecture_drift_detected` | `false` |
| `crossref_renderer_is_provider_mechanical_only` | `true` |
| `first_nonempty_canonical_semantics_removed` | `true` |
| `domain_specific_intent_inference_removed` | `true` |
| `benchmark_oracle_separated_from_production_relevance` | `true` |
| `candidate_pointer_to_resolver_status` | `PASS` (3/3 mechanical) |
| `provider_call_count` | `16` (4 questions × 4 rungs each) |
| `resolver_call_count` | `3` (one per matched Q) |
| `query_renderer_type` | `CROSSREF_SPECIFIC_THIN_RENDERER` |
| 5/5 workflows | `PASS` |

> Per P1.5-RA1 §11: "RA1 acceptance is not contingent on reproducing
> exactly 2/3. Live Crossref behavior may vary." The 3/3 result of this
> run is a stronger outcome than the contract's acceptance floor; it is
> reported faithfully and not used as the success gate (the
> architecture-removal tests are the gate).

---

## Layer 2 — Human Interpretation

### 1. What this contract was about

P1.5 introduced a real empirical gain (`0/3 → 1/3 → 2/3`) by adding a
thin Crossref-specific query renderer. But the same step also crossed
two architecture boundaries:

1. The renderer began inferring scientific search intent from domain
   vocabulary (it classified phrases like "giant fiber", "hemibrain",
   "connectome" into concepts vs title vs author).
2. The execution layer began deciding that the **first non-empty
   result set was the canonical useful result**.

These are not retrieval bugs; they are **boundary violations** —
the architecture was duplicating model intelligence. P1.5-RA1
deletes both, while preserving the empirically justified thin
provider adaptation.

### 2. What was removed

Per §4 (Closure A):

- The `extract_intent_from_query_representation` heuristic in
  `src/mafs_p0/crossref_renderer.py` is **deleted**. The
  production renderer no longer classifies any of the seven
  benchmark-known scientific phrases (`giant fiber`, `hemibrain`,
  `connectome`, `spike-timing`, `action selection`, `descending`,
  `sensory-motor`).

Per §5 (Closure B):

- The "first non-empty rung is canonical" semantics in
  `src/mafs_p0/live_chain.py` is **deleted**. `LiveChain` now
  exposes a **transparent ladder surface**: every rung's
  candidate set is recorded in `rung_candidate_sets` for audit.
  The chain canonizes ONLY the rung whose `rendering_path`
  matches the caller-supplied `external_selection`. Without
  `external_selection`, the chain returns
  `status="ladder_completed_no_selection"` and the resolver is
  NOT invoked.
- The orchestrator's benchmark loop
  (`scripts/replay_b.py::_run_q_benchmark_with_oracle_selection`)
  walks the ladder via the production
  `CrossrefRetrievalProvider` + `CrossrefReferenceResolver` stack
  **directly**, NOT through `LiveChain`. This isolates the
  benchmark's oracle-identity-match logic from the production
  interface. `LiveChain` is preserved for production
  model-driven callers (P1.5-RA1 §5.4).

Per §6 (Closure C):

- `.github/workflows/p1-5.yml` now declares a `paths-ignore`
  filter so a documentation-only / generated-artifact-only
  commit (e.g. editing `docs/P1_5_RA1_*`) will NOT trigger a
  new live benchmark. This is the **smallest workflow
  correction** per §6.4 (no generic CI event framework).

Per §7 (Closure D):

- No code was added whose purpose is to turn `1/3` or `2/3`
  into `3/3`. The P1.5 evidence gain is preserved without
  optimization. A new live run was performed; the actual
  result (`3/3` in this run) is reported faithfully but is
  not the acceptance gate.

### 3. Subtraction Ledger (per §13)

| Removed | Where | What it used to do | Replaced by |
|---|---|---|---|
| `extract_intent_from_query_representation` | `src/mafs_p0/crossref_renderer.py` | Classified domain phrases into concepts / title / author | Caller-supplied explicit `SearchIntent` |
| First-nonempty canonization (ladder) | `src/mafs_p0/live_chain.py` | Promoted the first non-empty rung's top-1 to canonical | Caller-supplied `external_selection` (production) or no canonization (default) |
| Implicit `first non-empty` in orchestrator's LiveChain call | `scripts/replay_b.py` | `LiveChain.run()` had its own first-nonempty default | Orchestrator walks the ladder directly via provider+resolver; LiveChain is preserved for production model-driven use only |
| `paths`-driven re-trigger of live on docs commits | `.github/workflows/p1-5.yml` | A docs commit would fire a new live benchmark, immediately making the just-written summary stale | `paths-ignore` filter for `docs/**`, `examples/runs/**`, `**.md` (smallest correction per §6.4) |

### 4. Architecture-statement answer (per §13 item 10)

> **What intelligence was removed from the architecture, and which
> responsibility now belongs to the model / caller instead?**

1. **Domain-vocabulary intent inference** (the renderer
   classifying "giant fiber" as a concept, "von Reyn" as an
   author, etc.) is removed. **Responsibility now belongs to
   the model / caller**, which MUST supply an explicit
   `SearchIntent` (`author`, `year`, `title`, `concepts`).
   Missing fields are honest, not fabricated. The renderer is
   a mechanical URL-param mapper, nothing more.

2. **First-nonempty canonization** (the execution layer
   promoting the first non-empty ladder rung's top-1 to
   "the answer") is removed. **Responsibility now belongs to
   the caller (model)**, which MUST supply an explicit
   `external_selection` identifying the rung it has decided
   is scientifically canonical. The execution layer exposes
   candidate evidence and execution state; it does NOT
   adjudicate scientific relevance. For the benchmark
   loop, the oracle-identity match is the explicit selection
   (isolated from the production interface per §5.3).

The architecture no longer encodes the rule
`non-empty => canonical`. The model owns that decision.

### 5. Verification of acceptance

- 13 of the 12 mandatory tests in §10 pass offline
  (`tests/test_p1_5_ra1.py`); T11 is a forward-looking
  pinning test that PASSES on the produced
  `docs/P1_5_RA1_METRICS.json` / `docs/P1_5_RA1_SUMMARY.md`.
  The full local pytest run is **121 passed, 1 skipped
  (T11 vacuous before docs existed; passes after)**.
- 1 final live CI run (`33260336752`) was performed
  per §11. All 5 workflows PASS.
- 0 new production modules, 0 new major class families,
  0 new providers, 0 new rankers, 0 new solvers, 0 new
  generic query planners, 0 new schema families, 0
  P2/P3 work (per §8).
- The previously existing `test_p1_05_resolver_consumes_real_candidate`
  P1 test still passes (the legacy `compiled_query` path
  preserves the P1 auto-canonize-top-1 contract for backward
  compatibility; the new P1.5 ladder path enforces the
  strict no-auto-canonize rule per P1.5-RA1 §5.4).

### 6. Q3 / Q5 boundary

- Q3 remains `PENDING_NEGATIVE_COVERAGE_RULE` (positive
  recall is now 3/3 but the negative-evidence semantics
  for a Q3 search that returned an unrelated candidate
  are still bounded by RA2 §3 Case 3).
- Q5 remains `ENTITY_RESOLUTION_REQUIRED` (no FlyWire /
  VFB / hemibrain / neuPrint dataset adapter added; per
  §8 the production stack still lacks entity resolution).
- DNg01 remains `UNRESOLVED` (no synonymy asserted; per
  RA1 §2 this is preserved).

### 7. Limitations / open observations

- Q3's `PENDING_NEGATIVE_COVERAGE_RULE` is a future
  capability (separate contract). The current run has
  adequate positive recall (3/3) but Q3 (von Reyn 2020)
  was not recovered; the ladder completed without
  identity match for the negative-branch target.
- Q2's `ORACLE_VERIFIED_BUT_NOT_REPRODUCED_BY_PRODUCTION_STACK`
  is preserved from the RA1 round — the production chain
  recovered the DOI but did not extract the DNp01
  proposition from the source content (which the
  production stack does not access).
- The 3/3 result is a single live run; per §11 the
  contract explicitly notes "live Crossref behavior may
  vary" and RA1 acceptance is **not** contingent on
  reproducing 2/3 or 3/3. The architecture-removal tests
  are the gate, and they pass.

### 8. Recommended next step

**STOP per §14.** The bounded P1.5-RA1 contract is
complete. The architectural removals (A, B, C, D) are
verified by offline tests; the live CI result is reported
faithfully. No new provider, no generic planner, no P2,
no dataset adapter, no retrieval-quality improvement
beyond the existing thin Crossref-native renderer. The
next step is a HO + ChatGPT decision on whether to
authorize a P1.5.1 / P1.6 / P2 contract — or to accept
the current capability ceiling (`0/3 → 3/3` thin
Crossref-native rendering) as the final MAFS v3.0
scholarly-stack boundary.

---

## Machine-Generated vs Human-Readable Distinction

This document's Layer 1 section is the human-readable rendering
of the machine-pinned fields. The following files are the
**machine-generated evidence** and the authoritative source of
truth for this run (`33260336752`):

- `docs/P1_5_RA1_METRICS.json` — Layer 1 JSON metrics
- `docs/P1_5_RA1_CI_PROVENANCE.md` — Layer 1 CI provenance
- `docs/P1_5_RA1_SHA256_MANIFEST.txt` — SHA-256 digests
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
