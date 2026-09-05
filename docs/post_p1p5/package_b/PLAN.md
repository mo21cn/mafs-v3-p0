# Development Package B Execution Plan

## 1. Objective

- run id: `MAFS-POST-P1P5-DPB-R4-R5-v1.0`
- selected idea: Extend the M3-accepted proposition-evidence primitive into
  scope-aware collision assessment, append-only research state, explicitly
  authorized re-digestion, and an auditable EvidenceLandscapePackage.
- user requirements: execute R4 and R5 completely, preserve Package A and
  P1.5, generate the Package B audit bundle, and stop before Gate M5.
- non-negotiable constraints: exact base
  `549c4c04ec6b8ea7b8a0cf96b1b49930181654b3`; branch
  `dev/post-p1p5-semantic-r4-r5`; no production migration, optimizer,
  route-splitting, Hub-Lesion, E2, RL/GRPO, ROC, or general framework.
- research question: Can grounded PropositionEvidence be transformed into
  uncertainty-preserving scientific state and a terminal evidence landscape
  without fabricating conflict, erasing lineage, or claiming downstream
  authority?
- null hypothesis: the M3 primitives are insufficient for a bounded,
  auditable R4-R5 vertical slice without redesigning Package A.
- alternative hypothesis: minimal new R4-R5 artifacts can consume the accepted
  primitives while preserving their boundaries and regressions.

## 2. Baseline And Comparability

- baseline id: `M3_ACCEPTED_SHA`
- baseline variant: Package A bundle plus M3-S1 acceptance record
- dataset / split: hermetic contract fixtures; no dataset change
- primary metric: all Package B hard invariants and required targeted tests pass
- required metric keys: Section 42 of the Package B contract
- comparability risks: accidental Package A redesign, ungrounded evidence being
  treated as contradiction, context mismatch being labeled direct
  contradiction, or re-digestion bypassing authorization/fidelity/purity.

## 3. Code Translation Plan

| Path | Current role | Planned change | Why | Risk |
|---|---|---|---|---|
| `src/mafs_p0/collision.py` | absent | add scoped collision artifacts and guards | R4 | false contradiction |
| `src/mafs_p0/research_state.py` | absent | add append-only state, obligations, authorized re-digestion lineage | R4 | history rewrite |
| `src/mafs_p0/evidence_landscape.py` | absent | add typed terminal ELP and deterministic serialization | R5 | authority flattening |
| `schemas/post_p1p5/` | Package A schemas | add Package B schemas only | auditability | legacy fingerprint drift |
| `tests/test_package_b_*.py` | absent | add contract fixtures and regression gates | verification | shallow happy path |
| `scripts/run_package_b_vertical_slice.py` | absent | add hermetic positive and negative demo | artifact proof | demo/test divergence |
| `docs/post_p1p5/package_b/` | absent | add required Package B evidence bundle | Gate M5 handoff | stale accounting |

Package A source modules are preserve boundaries. A branch identity-guard
change is allowed only if its narrow allow-list blocks the authorized branch.

## 4. Execution Design

- minimal experiment: two grounded proposition records produce one scoped
  CollisionAssessment, a child ResearchState, an authorized ReDigestionRequest,
  a lineage-preserving revised route, and a valid ELP.
- smoke plan: R4 fixture tests followed by R5 schema/serialization tests.
- full run plan: Package B targeted, Package A targeted, full offline, P1 live,
  and applicable CI workflows.
- expected outputs: all Section 40 artifacts plus hermetic positive/negative demos.
- stop condition: Package B bundle SHA frozen and pushed; Gate M5 not entered.
- abandonment condition: exact M3 base cannot be established or a hard failure
  cannot be repaired without an unauthorized architecture change.
- strongest alternative hypothesis: a collision/state layer requires richer
  proposition semantics than M3 currently exposes; if observed, record an
  honest limitation rather than broadening scope.

## 5. Runtime Strategy

- smoke command: targeted `pytest` for new R4/R5 tests
- main command: Package B + Package A targeted, full offline, then P1 live
- expected runtime / budget: local CPU; minutes, not hours
- log / artifact locations: `docs/post_p1p5/package_b/`
- safe efficiency levers: hermetic fixtures, deterministic serialization,
  reuse existing validator and Package A dataclasses
- tooling note: the contract-mandated branch is used instead of a `run/*`
  branch. The current Codex App does not expose the experiment skill's
  `bash_exec`/artifact/memory surfaces, so the workspace terminal and Package B
  audit artifacts are the durable fallback.

Monitoring: bounded test calls; inspect outputs immediately. Kill/relaunch only
for a demonstrably wedged external live test.

## 6. Fallbacks And Recovery

- network failure: record `NOT_EVALUATED_EXTERNAL_NETWORK`; do not claim PASS.
- constrained environment: use hermetic tests for R4/R5, never replace live P1
  evidence silently.
- wrong code path after smoke: revert only the uncommitted bounded delta and
  repair the smallest failing invariant.
- non-comparable full run: retain logs and report the exact confounder.

## 7. Checklist Link

- checklist path: `docs/post_p1p5/package_b/CHECKLIST.md`
- next unchecked item: run Package A, full offline, and P1 live regressions

## 8. Revision Log

| Time (UTC) | Change | Reason | Impact |
|---|---|---|---|
| 2026-09-05T07:33:48Z | Initial plan | M3 base and branch verified | none |
| 2026-09-05T08:30:00Z | R4/R5 implementation and demos complete | 25 targeted tests pass | proceed to regressions |
