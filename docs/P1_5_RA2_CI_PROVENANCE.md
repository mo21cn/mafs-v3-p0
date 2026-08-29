# P1_5_RA2_CI_PROVENANCE.md

> P1.5-RA2 acceptance-facing CI provenance. All factual fields below are
> mechanically derived from the selected run `33267536220` (commit `508bde3`,
> build_id `ci-live`, source `live`). The human interpretation layer lives in
> `docs/P1_5_RA2_SUMMARY.md`; this file is the machine-pinned Layer 1 of the
> summary per P1.5-RA2 contract §6.2 / §6.3.

## Run Pin

```yaml
contract_id: MAFS-v3.0-P1.5-RA2-CANDIDATE-OWNERSHIP-SUBTRACTION-TRUTH-CLOSURE
selected_run_id: "33267536220"
commit_sha: "508bde3"
branch: "dev/mafs-v3-p0-ra2"
build_id: "ci-live"
source: "live"
build_time: "2026-08-29T18:10:37Z"
parent_p1_5_ra1_commit: "f59c02e"
observed_branch_head_at_contract_issue: "6a635abf90fb5cb26bca158323ad4080ecb7035f"
```

## Layer 1 — Machine-Sourced Facts

### Candidate ownership acceptance (per P1.5-RA2 §2, §11)

| Field | Value |
|---|---|
| `caller_selects_candidate_pointer` | `true` |
| `execution_auto_selects_top1` | `false` |
| `no_selection_means_no_resolution` | `true` |
| `invalid_selection_fails_honestly` | `true` |

### Benchmark boundary acceptance (per P1.5-RA2 §3, §11)

| Field | Value |
|---|---|
| `oracle_logic_benchmark_only` | `true` |
| `oracle_selects_explicit_candidate_pointer` | `true` |
| `production_relevance_logic_added` | `false` |

### Truth acceptance (per P1.5-RA2 §4, §5, §11)

| Field | Value |
|---|---|
| `per_anchor_rank_is_actual_candidate_rank` | `true` |
| `hardcoded_rank_one_removed` | `true` |
| `subtraction_metrics_git_derived` | `true` |

### Architecture acceptance (per P1.5-RA2 §8, §11)

| Field | Value |
|---|---|
| `new_ranker_count` | `0` |
| `new_solver_count` | `0` |
| `new_provider_count` | `0` |
| `new_generic_selection_framework_count` | `0` |
| `new_major_schema_family_count` | `0` |

### Safety acceptance (per P1.5-RA2 §11)

| Field | Value |
|---|---|
| `candidate_pointer_to_resolver_status` | `PASS` |
| `fabricated_reference_count` | `0` |
| `fabricated_entity_count` | `0` |

### Scholarly anchor recovery (per P1.5-RA2 §11)

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
| `per_anchor_rank.S1-vonReyn-2014` | `1` (actual matched rank) |
| `per_anchor_rank.S2-Namiki-2018` | `1` (actual matched rank) |
| `per_anchor_rank.S3-Scheffer-2020` | `2` (actual matched rank — NOT hard-coded 1) |
| `per_anchor_selected_candidate_pointer_id.S1-vonReyn-2014` | `CP-001` |
| `per_anchor_selected_candidate_pointer_id.S2-Namiki-2018` | `CP-001` |
| `per_anchor_selected_candidate_pointer_id.S3-Scheffer-2020` | `CP-002` |
| `per_anchor_evidence_doi.S1-vonReyn-2014` | `10.1038/nn.3741` |
| `per_anchor_evidence_doi.S2-Namiki-2018` | `10.7554/elife.34272` |
| `per_anchor_evidence_doi.S3-Scheffer-2020` | `10.7554/elife.57443` |

> Per P1.5-RA2 §11: "RA1 acceptance is not contingent on reproducing
> exactly 2/3. Live Crossref behavior may vary." The 3/3 result of this
> run is reported faithfully and is not used as the success gate (the
> boundary-removal tests are the gate, and they pass).

### Per-question machine status (per P1.5-RA2 §10 T10)

| Question | paper_identity_status | other_status | rung_used | rung_rank |
|---|---|---|---|---|
| Q1 | RECOVERED | source_content_status: SOURCE_CONTENT_NOT_ACCESSIBLE | B_author_year_strongest | 1 |
| Q2 | RECOVERED | proposition_status: ORACLE_VERIFIED_BUT_NOT_REPRODUCED_BY_PRODUCTION_STACK | A_author_year_bibliographic | 1 |
| Q3 | n/a (negative branch) | negative_branch_status: PENDING_NEGATIVE_COVERAGE_RULE | null | null |
| Q4 | RECOVERED | n/a | A_author_year_bibliographic | 2 |
| Q5 | n/a (entity boundary) | entity_resolution_status: ENTITY_RESOLUTION_REQUIRED | null | null |

### Execution metrics

| Field | Value |
|---|---|
| `provider_call_count` | `16` (4 questions × 4 rungs each; bounded ladder fully walked) |
| `resolver_call_count` | `3` (one per matched Q) |
| `candidate_pointer_to_resolver_status` | `PASS` |
| `query_renderer_type` | `CROSSREF_SPECIFIC_THIN_RENDERER` |

### Machine diagnostic enums (per P1.5-RA2 §6.2)

```yaml
Q3.negative_branch_status: PENDING_NEGATIVE_COVERAGE_RULE
Q5.entity_resolution_status: ENTITY_RESOLUTION_REQUIRED
Q1.source_content_status: SOURCE_CONTENT_NOT_ACCESSIBLE
Q2.proposition_status: ORACLE_VERIFIED_BUT_NOT_REPRODUCED_BY_PRODUCTION_STACK
DNg01_disposition: UNRESOLVED
```

### Subtraction accounting (per P1.5-RA2 §5)

```yaml
method: git_numstat
baseline_commit: f59c02e
current_commit: 508bde3
production_src_additions: 302
production_src_deletions: 122
production_src_net: 180
benchmark_orchestrator_additions: 285
benchmark_orchestrator_deletions: 80
benchmark_orchestrator_net: 205
test_additions: 916
test_deletions: 73
test_net: 843
docs_additions: 0
docs_deletions: 0
docs_net: 0
production_loc_increase: true
```

> Per P1.5-RA2 §5.2: "Do not claim subtraction unless git evidence
> supports it. Report actual numbers." P1.5-RA1's `production_loc_increase=false`
> was a hand-coded claim that the actual git diff did not support.
> RA2's subtraction accounting is git-derived: `production_src_net=+180`
> is an honest INCREASE; the RA2 boundary repair required enlarging
> LiveChain's explicit-selection surface, the orchestrator's
> pre-walk helper, and the score code. The increase is bounded and
> per-file balanced (e.g. live_chain.py +249/-120 is a net rewrite).

## Workflow Run Status (5/5 PASS)

| Workflow | Run ID | Result |
|---|---|---|
| MAFS v3.0 — P1.5 (Crossref-Specific Query Rendering + Scholarly Anchor Recovery) | `33267536220` | **PASS** |
| MAFS v3.0 — Replay B Reopen-RA2 (Oracle Consistency & Negative-Evidence Semantics Closure) | `33267536237` | **PASS** |
| MAFS v3.0-P0-RA1 | `33267536249` | **PASS** |
| MAFS v3.0 — Replay A-RA1 (Benchmark Fidelity) | `33267536201` | **PASS** |
| MAFS v3.0-P1 Live Smoke | `33267536215` | **PASS** |

## Source-of-Truth Machine Artifacts

The Layer 1 fields above are derived from the following artifacts (all
produced by CI run `33267536220`, source `live`, build_id `ci-live`):

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

> Per P1.5-RA2 §6.2: "If [this document] contradicts any of the above files,
> the machine artifacts are the source of truth."

## Stale-Docs-Trigger Closure (per P1.5-RA1 §6.4, preserved by RA2)

The smallest workflow correction was applied in P1.5-RA1 and is still
in effect for RA2:

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
`docs/P1_5_RA2_*` after the live run) will NOT trigger a new live
benchmark. Verified by the latest P1.5 workflow run being the prior
commit's push (33267536220 = a65966b's push, before f59c02e's
docs-only push that did not re-trigger).
