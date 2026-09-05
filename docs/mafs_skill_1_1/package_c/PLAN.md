# Package C Execution Plan

## 1. Objective

- run id: `MAFS-SKILL-1.1-PACKAGE-C-CQC-MAFS-INTEGRATION-v1.0`
- selected idea: Add a thin, deterministic MAFS-side consumer adapter that validates the frozen CQC artifact chain, preserves CQC scientific and budget authority, records an auditable consumer binding, and hands only validated mechanical inputs to the accepted MAFS semantic engine.
- user's core requirement: Execute Package C completely and stop before independent Gate C1.
- non-negotiable constraints: start from M5 SHA `ecfa39e9fdeced45848c643544477e408e872d60`; keep CQC read-only at `c5c00a19f9812058050ba16ad61b717a1c1f1ca2`; preserve STOP/selection/resolve; make zero scientific mutations; perform no production migration.
- research question: Can the frozen CQC producer protocol be consumed by MAFS through a deterministic, fail-closed, lineage-complete adapter without changing either system's scientific authority?
- null hypothesis: The frozen producer protocol cannot be mapped without ambiguity, authority loss, stale acceptance, or MAFS semantic/runtime regression.
- alternative hypothesis: A small consumer-side adapter can validate and map the frozen protocol losslessly, preserve held/conditional authority and STOP, and attach CQC lineage through ELP.

## 2. Baseline And Comparability

- baseline id: M5 accepted MAFS `ecfa39e9fdeced45848c643544477e408e872d60`
- upstream producer: CQC freeze `c5c00a19f9812058050ba16ad61b717a1c1f1ca2`
- producer historical compatibility baseline: retained verbatim from each `CQCMAFSIntegrationBinding`
- primary metrics: hash/identity/authority preservation, deterministic binding, fail-closed mismatch rate, STOP preservation, cross-system lineage completeness, regression status
- required metric keys: all metrics in contract section 45
- comparability risks: confusing historical producer MAFS pin with current consumer compatibility; treating conditional routes as active; regenerating CQC scientific text; allowing audit-only bundle edits to change evaluated source.

## 3. Code Translation Plan

| Path | Current role | Planned change | Why this is needed | Risk |
|---|---|---|---|---|
| `src/mafs_p0/cqc_integration.py` | absent | deterministic validation, mapping, receipt, ELP provenance sidecar | consumer-side bridge | semantic drift if mapping guesses |
| `schemas/post_p1p5/cqc_mafs_consumer_binding.schema.json` | absent | binding schema | machine contract | schema too permissive |
| `schemas/post_p1p5/cqc_mafs_requirement.schema.json` | absent | mechanical MAFS requirement wrapper schema | preserve CQS/SRP identity and authority | accidental cognition |
| `scripts/run_package_c_integration.py` | absent | hermetic demos and bounded live smoke entrypoint | reproducible package execution | STOP bypass |
| `tests/test_package_c_integration.py` | absent | contract-targeted positive/negative/boundary tests | acceptance evidence | incomplete negative matrix |
| `docs/mafs_skill_1_1/package_c/` | absent | protocol, run, acceptance, provenance artifacts | durable audit package | mutable/self-hashing artifacts |

No existing MAFS scientific primitive is planned for redesign. Existing runtime edits, if any become necessary after a measured integration failure, require a plan revision first.

## 4. Execution Design

- minimal experiment: validate CQC `m1_s4_shared`, emit deterministic consumer binding and mechanical requirements, prove HELD remains non-active.
- smoke/pilot: targeted Package C tests plus hermetic positive, stale negative, and held/conditional demos.
- full run: Package C targeted; frozen CQC validators/tests; Package B RA1/B/A targeted; full MAFS offline; P0/Replay workflows; bounded live integration to CandidatePointer STOP; CI.
- expected outputs: contract section 41 artifacts, evaluated-source SHA, audit-only bundle SHA, manifest closure.
- stop condition: Package C completion criteria pass and artifacts are frozen, then stop before Gate C1.
- abandonment condition: wrong pins, non-clean starting tree, CQC mutation, unavoidable semantic ambiguity, or material M5 regression.
- strongest alternative hypothesis: protocol incompatibility requires an upstream CQC revision rather than a consumer adapter.

## 5. Runtime Strategy

- smoke command: `python -m pytest -q tests/test_package_c_integration.py`
- main commands: discovered CQC freeze/P5 validation; MAFS targeted and full offline regressions; bounded live smoke after hermetic pass
- expected runtime/budget: bounded local CPU tests plus one small live retrieval; no new dependencies
- durable logs/artifacts: `docs/mafs_skill_1_1/package_c/`
- efficiency: reuse existing dataclasses, hashing utilities, LiveChain, hermetic package demos, and pytest surface.
- tool deviation: the selected skill's `bash_exec`, memory, and artifact services are unavailable in this Codex App session; workspace shell plus repository artifacts will provide durable evidence and will be recorded in `C_DEVIATIONS.json`.

Monitoring: commands expected to finish within minutes; poll any yielded command at 10-30 second intervals. Stop/relaunch only on a concrete timeout, environment error, or invalid output.

## 6. Fallbacks And Recovery

- network failure: classify separately and retain hermetic evidence; retry only the bounded network operation.
- CQC schema ambiguity: return `SCHEMA_INCOMPATIBLE`; do not guess.
- live provider failure: classify `NETWORK_FAILURE` or `ENVIRONMENT_FAILURE`; do not weaken STOP or seed target identity.
- regression failure: diagnose from the last-known-good M5 SHA and modify only Package C scope.

## 7. Checklist Link

- checklist path: `docs/mafs_skill_1_1/package_c/CHECKLIST.md`
- next unchecked item: inspect exact frozen producer artifacts and MAFS integration seams

## 8. Revision Log

| Time | What changed | Why | Impact |
|---|---|---|---|
| 2026-09-06 | Initial contract-bound plan | Package C start | None; pins and scope fixed |
