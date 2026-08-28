# CI_DEPLOYMENT.md — How to trigger the MAFS v3.0-P0-RA2 build

This document is hand-written (not CI-generated) and is part of the package
that goes into git. It is the **only** document Local Claw (or any future
agent) needs to read to deploy the package onto a CI platform.

## Architecture: Three Planes

```
HO + GPT               Governance Plane
  ↑                       (architecture / contract / risk decision / acceptance)
  │
Local Claw (Mavis)    Development Plane
                        (implementation / commit / CI configuration / PR / artifact packaging)
  ↑
CI (GitHub Actions)   Execution Plane
                        (checkout / setup-python / pip install / run build_p0_ra1.py / upload artifacts)
```

HO is **not** in the execution plane. The CI runs the deterministic
`scripts/build_p0_ra1.py` entrypoint and uploads the artifacts. HO only
reviews the produced artifacts.

## The actual repository (deployed in P0-RA2)

| Field | Value |
|---|---|
| Repository | `mo21cn/mafs-v3-p0` (public) |
| Remote URL | `https://github.com/mo21cn/mafs-v3-p0.git` |
| Work branch | `dev/mafs-v3-p0-ra2` |
| Acceptance branch | `main` (frozen at initial import; advanced only on P0 acceptance) |
| Workflow file | `.github/workflows/mafs-p0.yml` |
| Workflow display name | `MAFS v3.0-P0-RA1` (back-compat) |
| Artifact name | `mafs-p0-ra1-artifacts` (back-compat) |
| Runner | `ubuntu-latest` (Python 3.10) |

The P0-RA2 acceptance evidence (commit `69f5a12`, CI run `33156814708`,
conclusion=success) is recorded in `docs/CI_PROVENANCE.md`.

## How a single CI run works

1. `actions/checkout@v4` checks out the repo.
2. `actions/setup-python@v5` installs Python 3.10.
3. `pip install -e ".[test]"` installs `pytest` only.
4. `python scripts/build_p0_ra1.py` runs the SOLE entrypoint. The script:
   - Verifies the byte-identical Target Freeze fixture
     (`tests/fixtures/Blood_Oxygen_Ovary_Axis_Target_Freeze.md`,
     SHA-256 `3b080b50e1d0801915f5d6c6ab8d3b6cb9ee10f5ad1705e3bf45e9c2164b7e54`).
   - Runs the full `pytest tests/` suite (45 tests expected).
   - Runs the positive demo (must produce
     `READY_FOR_HO_EXECUTION_APPROVAL`).
   - Runs the negative demo (must produce `PLANNING_BLOCKED`).
   - Calls `validate_run` on both demos. The validator now also
     covers `providers`, `resolvers`, `negotiations`, and
     `gate_graph` (P0-RA2 Blocker A closure).
   - Writes 14 artifacts to `examples/runs/RA1/`:
     - `compiled_target.json`
     - `preflight_report.json`
     - `negative_preflight_report.json`
     - `positive_run.json`
     - `negative_run.json`
     - `runtime_fingerprint.json`
     - `axes.json`
     - `search_orders.json`
     - `providers.json`
     - `compiled_queries.json`
     - `negotiations.json`
     - `gate_graph.json`
     - `budget.json`
     - `build.log`
   - Regenerates `docs/P0_SUMMARY.md`, `docs/SHA256_MANIFEST.txt`,
     and `docs/TEST_SUMMARY.md` from the actual run.
5. `actions/upload-artifact@v4` uploads the artifacts as
   `mafs-p0-ra1-artifacts`.
6. If `build_p0_ra1.py` returned non-zero, the CI step fails and the
   workflow turns red.

## How Local Claw reads the CI result

```bash
# After a CI run, list the runs on the work branch:
gh run list --repo mo21cn/mafs-v3-p0 --branch dev/mafs-v3-p0-ra2 --limit 5

# Inspect a specific run:
gh run view <run-id> --repo mo21cn/mafs-v3-p0

# Download the artifacts:
gh run download <run-id> --repo mo21cn/mafs-v3-p0 --name mafs-p0-ra1-artifacts \
  --dir .ci_run_<run-id>
```

Then Local Claw reads (in this order):

| Artifact | What to look for |
|---|---|
| `docs/P0_SUMMARY.md` | Overall disposition = `READY_FOR_ACCEPTANCE`; positive preflight = READY; negative preflight = PLANNING_BLOCKED |
| `examples/runs/RA1/build.log` | The full execution log; no silent skips; all 6 steps completed |
| `docs/SHA256_MANIFEST.txt` | The real SHA-256 of every artifact; fixture SHA-256 matches `3b080b50...` |
| `docs/TEST_SUMMARY.md` | `45 passed`; 12 §16 risk checks all PASS |
| `examples/runs/RA1/preflight_report.json` | All BLOCKER checks PASS; no `ready_with_blocker_check` in semantic errors |
| `examples/runs/RA1/negative_preflight_report.json` | A subset of checks FAIL; `PLANNING_BLOCKED` |
| `examples/runs/RA1/runtime_fingerprint.json` | Every provider/resolver entry has `namespace`; SHA-256s present |
| `examples/runs/RA1/negotiations.json` | Every search_order has a `negotiation_result` with `executable` and `missing_capabilities` populated |

If the CI is red, Local Claw reads `examples/runs/RA1/build.log` and
`docs/P0_SUMMARY.md`, identifies the BLOCKER, patches, and pushes again.
**Local Claw does not ask HO to fix the failure** unless it is a true
contract ambiguity or an authorization blocker (HIGH_RISK_INVARIANTS I-14).

## How HO + GPT accepts (governance plane)

After a green CI run, HO + GPT download the same artifact (or read it
directly from the GitHub Actions web UI) and review:

| Artifact | What to look for |
|---|---|
| `docs/CI_PROVENANCE.md` | Commit SHA, branch, workflow file, run ID, conclusion=success, artifact set, per-file SHA-256 |
| `docs/P0_SUMMARY.md` | Overall disposition = `READY_FOR_ACCEPTANCE`; positive preflight = READY; negative preflight = PLANNING_BLOCKED |
| `examples/runs/RA1/preflight_report.json` | All BLOCKER checks PASS; no `ready_with_blocker_check` in semantic errors |
| `examples/runs/RA1/negative_preflight_report.json` | A subset of checks FAIL; PLANNING_BLOCKED |
| `docs/SHA256_MANIFEST.txt` | The real SHA-256 of every artifact; fixture SHA-256 matches `3b080b50...` |
| `examples/runs/RA1/build.log` | The full execution log; no silent skips |

If all six artifacts look right, HO + GPT issue `ACCEPT_FOR_FREEZE` (or
`ACCEPT_WITH_LIMITATIONS` if minor issues are noted). Otherwise they issue
`REJECT_RA_REQUIRED` with a specific BLOCKER cited from the artifacts.

## What happens if the workflow file is wrong

If `.github/workflows/mafs-p0.yml` is invalid YAML or references a wrong
action version, GitHub Actions reports the parse error on the Actions tab.
Local Claw sees the red workflow, reads the parse error, fixes the YAML, and
pushes again. **HO is not involved**.

## How to verify the workflow file is structurally valid

A quick way to verify the workflow file itself parses without running the
whole build:

```bash
gh workflow view mafs-p0.yml --repo mo21cn/mafs-v3-p0
```

If the YAML parses, the file is structurally valid. (This still requires
push; there is no local GitHub-Actions simulator in CI-less environments.)

## Line-ending policy

The repo uses `.gitattributes`:

- `* -text` (no automatic line-ending translation; content is treated
  as binary bytes for line-ending purposes).
- `tests/fixtures/*.md` and `schemas/*.json` are explicitly `binary`
  so a Windows checkout does not corrupt them with CR-LF translation.

The development plane's local `core.autocrlf=input` is a local safety net;
it does not change what CI sees (CI checks out with default Linux line
endings).

## What is NOT in this package

- No live retrieval (P1). The `pubmed_mock_v1` provider has
  `network_requirement=offline`.
- No `EvidenceObject`, `CandidatePointer`, or raw snapshot. P1-min is the
  next bounded contract.
- No `jsonschema` library dependency. The P0 self-rolled validator is
  restricted to a documented JSON Schema subset
  (see `docs/HIGH_RISK_INVARIANTS.md` and the
  `UnsupportedSchemaFeatureError` raised at schema load time).
- No global installation. This package is local to its repository clone;
  the v3.0-P0 contract prohibits global install until the master
  contract's full P0 + P1 + P2 + P3 + benchmarks are accepted.
- No hand-written `P0_SUMMARY.md` / `SHA256_MANIFEST.txt` /
  `TEST_SUMMARY.md`. The CI script regenerates them on every run
  (HIGH_RISK_INVARIANTS I-13).
