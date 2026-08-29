# P1_5_RA1_CI_PROVENANCE.md

> P1.5-RA1 acceptance-facing CI provenance. All factual fields below are
> mechanically derived from the selected run `33260336752` (commit `d86ccd1`,
> build_id `ci-live`, source `live`). The human interpretation layer lives in
> `docs/P1_5_RA1_SUMMARY.md`; this file is the machine-pinned Layer 1 of the
> summary per P1.5-RA1 contract §6.2 / §6.3.

## Run Pin

```yaml
contract_id: MAFS-v3.0-P1.5-RA1-THIN-RENDERER-BOUNDARY-LADDER-SEMANTICS-CLOSURE
selected_run_id: "33260336752"
commit_sha: "d86ccd1"
branch: "dev/mafs-v3-p0-ra2"
build_id: "ci-live"
source: "live"
build_time: "2026-08-29T15:28:26Z"
parent_p1_5_commit: "cd9b9680dafdbc7a4aef55bfcd51aa0b750fd494"
observed_branch_head_at_contract_issue: "6a635abf90fb5cb26bca158323ad4080ecb7035f"
```

## Layer 1 — Machine-Sourced Facts

### Architecture acceptance (per P1.5-RA1 §12)

| Field | Value |
|---|---|
| `crossref_renderer_is_provider_mechanical_only` | `true` |
| `scientific_intent_owned_by_model_or_caller` | `true` |
| `domain_specific_intent_inference_removed` | `true` |
| `first_nonempty_canonical_semantics_removed` | `true` |
| `benchmark_oracle_separated_from_production_relevance` | `true` |
| `architecture_drift_detected` | `false` |

### Execution acceptance (per P1.5-RA1 §12)

| Field | Value |
|---|---|
| `bounded_ladder` | `true` (≤ 4 rungs: A, B, C, LEGACY) |
| `rung_candidate_sets_auditable` | `true` (every rung's full candidate_pointers is recorded) |
| `resolver_continuity_if_invoked` | `PASS` (3/3 mechanical; CP→Resolver identity preserved) |
| `fabricated_reference_count` | `0` |
| `fabricated_entity_count` | `0` |
| `fabrication_hard_invariant_holds` | `true` |

### Reporting acceptance (per P1.5-RA1 §6 + §12)

| Field | Value |
|---|---|
| `human_summary_pins_run_id` | `true` (`33260336752`) |
| `human_summary_pins_commit_sha` | `true` (`d86ccd1`) |
| `factual_fields_machine_sourced` | `true` (this file) |
| `stale_docs_trigger_failure_closed` | `true` (workflow `paths-ignore` per §6.4) |

### Scope acceptance (per P1.5-RA1 §8 + §12)

| Field | Value |
|---|---|
| `new_provider_count` | `0` (Crossref only) |
| `new_ranker_count` | `0` |
| `new_solver_count` | `0` |
| `new_generic_query_planner_count` | `0` |
| `new_major_schema_family_count` | `0` |
| `p2_or_p3_work_entered` | `false` |

### Subtraction acceptance (per P1.5-RA1 §9 + §12)

| Field | Value |
|---|---|
| `production_loc_increase` | `false` (rendered heuristic extraction in `crossref_renderer.py` deleted; live_chain gains only the `external_selection` boundary field) |
| `unearned_architecture_added` | `false` |
| `heuristic_intent_extractor_removed` | `true` (`extract_intent_from_query_representation` deleted) |
| `first_nonempty_canonization_removed` | `true` (LiveChain returns `ladder_completed_no_selection` without `external_selection`) |

### Scholarly anchor recovery (per P1.5-RA1 §11 / §12)

| Field | Value |
|---|---|
| `baseline_recall` | `0/3` (frozen pre-P1.5) |
| `final_recall` | `3/3` |
| `scholarly_anchor_count` | `3` |
| `scholarly_anchor_recovered` | `3` |
| `scholarly_identity_safe_recall` | `1.0` |
| `per_anchor_recovery.S1-vonReyn-2014` | `RECOVERED` |
| `per_anchor_recovery.S2-Namiki-2018` | `RECOVERED` |
| `per_anchor_recovery.S3-Scheffer-2020` | `RECOVERED` |
| `per_anchor_rank.S1-vonReyn-2014` | `1` |
| `per_anchor_rank.S2-Namiki-2018` | `1` |
| `per_anchor_rank.S3-Scheffer-2020` | `1` |
| `per_anchor_evidence_doi.S1-vonReyn-2014` | `10.1038/nn.3741` |
| `per_anchor_evidence_doi.S2-Namiki-2018` | `10.7554/elife.34272` |
| `per_anchor_evidence_doi.S3-Scheffer-2020` | `10.7554/elife.57443` |

> Per P1.5-RA1 §11: "RA1 acceptance is not contingent on reproducing exactly 2/3.
> Live Crossref behavior may vary." The 3/3 result of this run is a stronger
> outcome than the contract's acceptance floor; it is reported faithfully and
> not used as the success gate (the architecture-removal tests are the gate).

### Per-question machine status (per P1.5-RA1 §10 T10)

| Question | paper_identity_status | other_status | rung_used | rung_rank |
|---|---|---|---|---|
| Q1 | RECOVERED | source_content_status: SOURCE_CONTENT_NOT_ACCESSIBLE | A_author_year_bibliographic | 1 |
| Q2 | RECOVERED | proposition_status: ORACLE_VERIFIED_BUT_NOT_REPRODUCED_BY_PRODUCTION_STACK | C_title_exact | 3 |
| Q3 | n/a (negative branch) | negative_branch_status: PENDING_NEGATIVE_COVERAGE_RULE | null | null |
| Q4 | RECOVERED | n/a | A_author_year_bibliographic | 2 |
| Q5 | n/a (entity boundary) | entity_resolution_status: ENTITY_RESOLUTION_REQUIRED | null | null |

### Execution metrics

| Field | Value |
|---|---|
| `provider_call_count` | `16` (4 questions × 4 rungs each; bounded ladder fully walked) |
| `resolver_call_count` | `3` (one per Q with an oracle-identity match: Q1, Q2, Q4) |
| `candidate_pointer_to_resolver_status` | `PASS` |
| `query_renderer_type` | `CROSSREF_SPECIFIC_THIN_RENDERER` |

### Machine diagnostic enums (per P1.5-RA1 §6.2)

```yaml
Q3.negative_branch_status: PENDING_NEGATIVE_COVERAGE_RULE
Q5.entity_resolution_status: ENTITY_RESOLUTION_REQUIRED
Q1.source_content_status: SOURCE_CONTENT_NOT_ACCESSIBLE
Q2.proposition_status: ORACLE_VERIFIED_BUT_NOT_REPRODUCED_BY_PRODUCTION_STACK
DNg01_disposition: UNRESOLVED
```

## Workflow Run Status (5/5 PASS)

| Workflow | Run ID | Result |
|---|---|---|
| MAFS v3.0 — P1.5 (Crossref-Specific Query Rendering + Scholarly Anchor Recovery) | `33260336752` | **PASS** |
| MAFS v3.0 — Replay B Reopen-RA2 (Oracle Consistency & Negative-Evidence Semantics Closure) | `33260336759` | **PASS** |
| MAFS v3.0-P0-RA1 | `33260336761` | **PASS** |
| MAFS v3.0 — Replay A-RA1 (Benchmark Fidelity) | `33260336748` | **PASS** |
| MAFS v3.0-P1 Live Smoke | `33260336765` | **PASS** |

## Source-of-Truth Machine Artifacts

The Layer 1 fields above are derived from the following artifacts (all
produced by CI run `33260336752`, source `live`, build_id `ci-live`):

- `docs/P1_5_METRICS.json` — primary machine metrics (JSON)
- `docs/P1_5_CI_PROVENANCE.md` — primary CI provenance
- `docs/P1_5_SHA256_MANIFEST.txt` — SHA-256 digest list
- `examples/runs/P1_5/scholarly_recovery_matrix.json` — per-anchor recovery
- `examples/runs/P1_5/candidate_resolution_provenance.json` — per-Q CP→Resolver audit
- `examples/runs/P1_5/miss_diagnostics.json` — per-Q miss diagnostics
- `examples/runs/P1_5/rendered_queries.json` — every Crossref URL the renderer constructed
- `examples/runs/P1_5/runtime_fingerprint.json` — production stack fingerprint
- `examples/runs/P1_5/build.log` — full stdout/stderr from the live orchestrator run
- `examples/runs/ReplayB/evidence_landscape.json` — RA1 evidence landscape (Q1-Q5)
- `examples/runs/ReplayB/fabrication_audit.json` — RA1 mechanical fabrication audit
- `examples/runs/ReplayB/negative_anchor_result.json` — Q3 negative branch evidence
- `examples/runs/ReplayB/candidate_resolution_provenance.json` — per-Q CP→Resolver audit (RA1 format)
- `examples/runs/ReplayB/scholarly_recovery_matrix.json` — RA1 scholarly recovery matrix
- `examples/runs/ReplayB/runtime_fingerprint.json` — RA1 runtime fingerprint

> Per P1.5-RA1 §6.2: "If [this document] contradicts any of the above files,
> the machine artifacts are the source of truth."

## Stale-Docs-Trigger Closure (per P1.5-RA1 §6.4)

The smallest workflow correction was applied to `.github/workflows/p1-5.yml`:

```yaml
on:
  push:
    branches:
      - dev/mafs-v3-p0-ra2
    paths-ignore:
      - "docs/**"
      - "examples/runs/**"
      - "**.md"
      - "examples/runs/P1_5/**"
      - "examples/runs/ReplayB/**"
```

A documentation-only / generated-artifact-only commit (e.g. updating
`docs/P1_5_RA1_*` after the live run) will NOT trigger a new live
benchmark. Per P1.5-RA1 §6.4: "documentation-only / generated-artifact-only
commits should not create a new acceptance benchmark unless they change
executable benchmark semantics." This change is the smallest workflow
correction (no generic CI event framework).
