# P1_5_RA3_CI_PROVENANCE.md

> **Single current acceptance truth** for P1.5-RA3.
> `docs/P1_5_RA3_METRICS.json` is the only current acceptance metrics source for
> P1.5-RA3. Earlier P1.5 / RA1 / RA2 metrics are historical evidence and do not
> bind current acceptance.

contract_id: MAFS-v3.0-P1.5-RA3-AI-NATIVE-EXECUTION-BOUNDARY-MACHINE-TRUTH-FINAL-CLOSURE
parent_contract_id: MAFS-v3.0-P1.5-CROSSREF-QUERY-RENDERING-ANCHOR-RECOVERY
build_id: ci-live
source: live
build_time: 2026-08-30T04:09:33Z
pinned_commit_sha: 42561cb
pinned_branch: dev/mafs-v3-p0-ra2
pinned_ci_run_id: 33291857262
pinned_ci_run_url: https://github.com/mo21cn/mafs-v3-p0/actions/runs/33291857262
cycle_1_commit_sha: 5a46789
cycle_2_commit_sha: 42561cb
meaningful_push_ci_cycles: 2
cycle_3_was_docs_only: true

## Acceptance facts (machine-rendered from CI artifact)

baseline_recall: 0/3
final_recall: 3/3
scholarly_anchor_count: 3
scholarly_anchor_recovered: 3
scholarly_identity_safe_recall: 1.0
per_anchor_recovery:
  S1-vonReyn-2014: RECOVERED
  S2-Namiki-2018: RECOVERED
  S3-Scheffer-2020: RECOVERED
per_anchor_rank:
  S1-vonReyn-2014: 1
  S2-Namiki-2018: 1
  S3-Scheffer-2020: 2
per_anchor_rank_status:
  S1-vonReyn-2014: OK
  S2-Namiki-2018: OK
  S3-Scheffer-2020: OK
selected_candidate_pointer_id:
  Q1: CP-002
  Q2: CP-002
  Q4: CP-003
resolver_candidate_pointer_id:
  Q1: CP-002
  Q2: CP-002
  Q4: CP-003
continuity_status:
  Q1: PASS
  Q2: PASS
  Q3: NOT_EVALUATED
  Q4: PASS
  Q5: NOT_EVALUATED
candidate_pointer_to_resolver_status: PASS
real_retrieval_invocation_id (all evaluated Qs): RIV-007
raw_snapshot_sha256 (Q1, real): 64c9fa07a3a46e3824212e3c02d5f2e11a7b230b2e8e9099db74f89c24900296
raw_snapshot_sha256 (Q2, real): f6a3604df26853f7eacc993f9bc42b9ccac31f3ca6bfb9562360f5e82a99b3cc
raw_snapshot_sha256 (Q4, real): 0c28449dd9f9f84657f251871a8a2a349ca303ddaa7ea10d0805f3df1dc29ba2
pre_walked_synthetic_observed: false
zero_filled_sha_observed: false
fabricated_reference_count: 0
fabricated_entity_count: 0
fabrication_hard_invariant_holds: true
Q1.paper_identity_status: RECOVERED
Q1.source_content_status: SOURCE_CONTENT_NOT_ACCESSIBLE
Q2.paper_identity_status: RECOVERED
Q2.proposition_status: ORACLE_VERIFIED_BUT_NOT_REPRODUCED_BY_PRODUCTION_STACK
Q3.negative_branch_status: PENDING_NEGATIVE_COVERAGE_RULE
Q4.paper_identity_status: RECOVERED
Q5.entity_resolution_status: ENTITY_RESOLUTION_REQUIRED
exit_code: 0

## Subtraction accounting (git-derived; status OK)

baseline_ref: c8dd376 (P1.5-RA2 docs commit)
subtraction_accounting_status: OK
production_runtime_additions: 269
production_runtime_deletions: 295
production_runtime_net: -26
production_runtime_target_ceiling: 50
benchmark_orchestrator_additions: 179
benchmark_orchestrator_deletions: 151
benchmark_orchestrator_net: 28
test_existing_additions: 126
test_existing_deletions: 68
test_existing_net: 58
new_test_p1_5_ra3_py_lines: 663
new_pre_push_check_py_lines: 206
workflow_additions: 7
workflow_deletions: 0

## Workflow result

p1-5 workflow conclusion: success
p1-5-tests workflow conclusion: success
replay-b-reopen workflow conclusion: success
replay-a workflow conclusion: success
mafs-p0 workflow conclusion: success
mafs-p1-live workflow conclusion: success
all_5_workflows_green: true

## Single acceptance source

docs/P1_5_RA3_METRICS.json is the only current acceptance metrics source for
P1.5-RA3. Earlier P1.5 / RA1 / RA2 metrics are historical evidence and do not
bind current acceptance.

The P1.5 baseline file `docs/P1_5_METRICS.json` carries a `_historical_marker`
top-level key (P1.5-RA3 §8.1) that explicitly states it is historical and
must not be interpreted as current acceptance truth.
