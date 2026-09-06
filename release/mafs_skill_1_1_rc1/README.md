# MAFS Skill 1.1.0-rc1

This portable, offline-installable release candidate packages the accepted
MAFS Skill 1.1 semantic engine and the pinned CQC runtime/protocol subset.
GitHub is not required for installation. Scientific-provider network access is
required only for live scholarly discovery.

## Product and engine identity

- Product: MAFS Skill 1.1
- Artifact: 1.1.0-rc1
- Stage: RELEASE_CANDIDATE
- Engine lineage: MAFS v3 / Post-P1.5 semantic engine

The repository-root `SKILL.md` and `VERSION.md` remain historical engine
surfaces. This file and the adjacent `SKILL.md` are the canonical product
surfaces inside the release artifact.

## Install and verify

PowerShell wrappers are in `installer/`, `doctor/`, and `migration/`. They use
the Python executable selected by `MAFS_PYTHON` or `python` on PATH. All tools
emit a machine-readable JSON record.

Fresh staging install:

```powershell
./installer/install.ps1 -InstallRoot "C:\staging\mafs"
./doctor/doctor.ps1 -InstallPath "C:\staging\mafs\MAFS_Skill_1.1.0-rc1"
```

The installer verifies the package manifest, C1/source identity, and pinned
CQC dependency before writing. It installs into a versioned directory and
never overwrites MAFS Skill 1.0. Re-running install/migrate/rollback is either
idempotent or returns an explicit `ALREADY_*` status.

The installed runtime uses its explicit `manifests/`, `runtime/`, `schemas/`,
and `dependencies/` product topology. It does not require a repository
checkout, Git metadata, `src/`, or `pyproject.toml`. The deep doctor validates
critical imports, schema resolution, runtime fingerprint construction, and a
hermetic CQC-to-Package-C consumer handoff from the installed artifact.

The canonical release smoke starts from a hermetic frozen-format CQC artifact
chain and reaches the mandatory CandidatePointer STOP boundary:

```powershell
python ./examples/canonical_release_smoke.py --output smoke.json --discovery-mode hermetic
```

Use `--discovery-mode live` only when provider network access is intended. The
smoke never selects or resolves a candidate.

Migration and rollback are rehearsal-safe and preserve a rollback anchor.
`docs/ACTIVATION_PLAN.md` describes a future atomic cutover; this RC never
performs production activation.

## STOP behavior

The release preserves CandidatePointer → STOP → explicit SelectionArtifact →
resolve. No installer, launcher, or example performs automatic top-1
selection.

## Known limitations

- Provider reachability and credentials are environment-dependent; their
  absence yields `DEGRADED`, not a corrupt installation.
- Evidence sufficiency remains a model-reviewed scientific judgment and is
  never upgraded from missing or inaccessible source content.
- Gate R1 must independently accept this release before production cutover.

RC1 is not production-released until Gate R1 acceptance.
