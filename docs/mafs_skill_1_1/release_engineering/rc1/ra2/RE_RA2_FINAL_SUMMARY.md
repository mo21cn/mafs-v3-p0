# MAFS Skill 1.1 Release Engineering RA2 Final Summary

RA2 closes the portable-runtime-topology defect that caused Gate R1 Attempt 1 to fail. The accepted scientific semantics and Package C integration were not redesigned. The change is confined to development/release path topology, release loading and doctor checks, canonical installed smoke coverage, uninstall ownership, schemas, tests, and audit evidence.

## Frozen identities

- Release branch: `release/mafs-skill-1p1-rc1`
- C1 accepted SHA: `a20377dfa447f1bd6008c6d84764b1c2544c665b`
- Parent RA1 source SHA: `c36ef0d46a5a147dce7372869ef4ca7544d5dd97`
- Parent RA1 bundle SHA: `006cc85feb7ae1acc71134fc7ec48d3b1b259d49`
- Parent RA1 RC SHA-256: `bf073518093c56ada89d8a6e8b41f4a912daf63d7123b392384469f3b0a63e3f`
- RA2 evaluated source SHA: `b9843ac3e3a8eab4c480664141547ce4fdf2702e`
- RA2 bundle SHA: reported out of band after the audit-only commit
- RA2 RC SHA-256: `cdb9e3f79f7a5b4879aa9b9898f7d886bd436eb0086a70da06bcd9e085c30b7b`

## Closure result

- Explicit `DEV_MODE` and `INSTALLED_RELEASE` layouts: PASS.
- Installed critical module imports: 10/10 PASS, all from `runtime/mafs_p0`.
- Repository checkout or release `pyproject.toml` required: no.
- Deep doctor: READY offline and online; the offline provider plane is separately DEGRADED.
- Package C installed consumer probe: PASS.
- Canonical installed CQC → Package C → MAFS → CandidatePointer → STOP smoke: PASS in hermetic and live modes.
- Selection/resolve during canonical smoke: not performed.
- Fresh install/reinstall, migration/second migration, rollback/second rollback, uninstall, and fail-closed matrix: PASS.
- Portable archive reproducibility: byte-identical.
- Legacy 1.0 mutation: 0. CQC mutation: 0. Scientific semantic behavior changes: 0.

## Verification

- RA2 dedicated: 11 passed.
- Release Engineering combined: 24 passed.
- Full MAFS offline: 244 passed, 15 skipped, 1 existing warning.
- P1 live: 11 passed.
- Package C: 26 passed.
- Package B RA1: 12 passed.
- Package B: 23 passed.
- Package A: 32 passed.
- Frozen CQC: 100 passed, 1 skipped.
- Source CI: Release Engineering run `34043100865` and P0 run `34043100859`, both success.
- Bundle CI: reported out of band after the audit-only bundle commit.

## Governance state

Gate R1 Attempt 1 remains recorded as `R1_FAIL`. RA2 makes a fresh Gate R1 Attempt 2 ready, but does not run it, accept the release, activate production, replace MAFS Skill 1.0, or authorize migration.
