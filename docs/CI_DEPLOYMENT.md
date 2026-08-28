# CI_DEPLOYMENT.md — How to trigger the MAFS v3.0-P0-RA1 build

This document is hand-written (not CI-generated) and is part of the package
that goes into git. It is the **only** document the Local Claw (or any future
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
`scripts/build_p0_ra1.py` entrypoint and uploads the artifacts. The HO only
reviews the produced artifacts.

## How to deploy (Local Claw, one-time per repo)

```bash
cd <repo-root>
git init                      # if not already a repo
git add .
git commit -m "MAFS v3.0-P0-RA1: initial import"
gh repo create <owner>/mafs-p0-ra1 --public --source=. --push
# Enable GitHub Actions in the repo settings (Settings -> Actions -> General -> Allow all actions)
```

That is the **only** step Local Claw does. From that point on, every push
triggers the CI.

## How a single CI run works

1. `actions/checkout@v4` checks out the repo
2. `actions/setup-python@v5` installs Python 3.10
3. `pip install -e ".[test]"` installs `pytest` only
4. `python scripts/build_p0_ra1.py` runs the SOLE entrypoint. The script:
   - Verifies the byte-identical Target Freeze fixture
   - Runs the full `pytest tests/` suite
   - Runs the positive demo (must produce READY preflight)
   - Runs the negative demo (must produce PLANNING_BLOCKED preflight)
   - Calls `validate_run` on both demos
   - Writes 13 artifacts to `examples/runs/RA1/`:
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
   - Regenerates `docs/P0_SUMMARY.md`, `docs/SHA256_MANIFEST.txt`, and `docs/TEST_SUMMARY.md` from the actual run
5. `actions/upload-artifact@v4` uploads the artifacts
6. If `build_p0_ra1.py` returned non-zero, the CI step fails and the workflow turns red

## How Local Claw reads the CI result

```bash
# After a CI run, download the artifact:
gh run download <run-id> --name mafs-p0-ra1-artifacts

# Inspect the P0_SUMMARY (auto-generated; never hand-written):
cat docs/P0_SUMMARY.md

# Inspect the build log:
cat examples/runs/RA1/build.log

# Inspect the failing preflight check, if any:
jq '.checks[] | select(.outcome == "FAIL")' examples/runs/RA1/preflight_report.json
```

If the CI is red, Local Claw reads `examples/runs/RA1/build.log` and
`docs/P0_SUMMARY.md`, identifies the BLOCKER, patches, and pushes again.
**Local Claw does not ask HO to fix the failure** unless it is a true
contract ambiguity or an authorization blocker.

## How HO + GPT accepts (governance plane)

After a green CI run, HO + GPT download the same artifact and review:

| Artifact | What to look for |
|---|---|
| `docs/P0_SUMMARY.md` | Overall disposition = `READY_FOR_ACCEPTANCE`; positive preflight = READY; negative preflight = PLANNING_BLOCKED |
| `examples/runs/RA1/preflight_report.json` | All BLOCKER checks PASS; no `ready_with_blocker_check` in semantic errors |
| `examples/runs/RA1/negative_preflight_report.json` | A subset of checks FAIL; PLANNING_BLOCKED |
| `docs/SHA256_MANIFEST.txt` | The real SHA-256 of every artifact; fixture SHA-256 matches `3b080b50e1d0801915f5d6c6ab8d3b6cb9ee10f5ad1705e3bf45e9c2164b7e54` |
| `examples/runs/RA1/build.log` | The full execution log; no silent skips |

If all five artifacts look right, HO + GPT issue `ACCEPT_FOR_FREEZE` (or
`ACCEPT_WITH_LIMITATIONS` if minor issues are noted). Otherwise they issue
`REJECT_RA_REQUIRED` with a specific BLOCKER cited from the artifacts.

## What happens if the workflow file is wrong

If `.github/workflows/mafs-p0-ra1.yml` is invalid YAML or references a wrong
action version, GitHub Actions reports the parse error on the Actions tab.
Local Claw sees the red workflow, reads the parse error, fixes the YAML, and
pushes again. **HO is not involved**.

## Self-test for the workflow

A quick way to verify the workflow file itself is valid without running the
whole build: `gh workflow view mafs-p0-ra1.yml`. If the YAML parses, the file
is structurally valid. (This still requires push; there's no local
GitHub-Actions simulator in CI-less environments.)

## What is NOT in this package

- No live retrieval (P1). The `pubmed_mock_v1` provider has
  `network_requirement=offline`.
- No `EvidenceObject`, `CandidatePointer`, or raw snapshot. P1-min is the
  next bounded contract.
- No `jsonschema` library dependency. The P0 self-rolled validator is
  restricted to a documented JSON Schema subset
  (see `docs/HIGH_RISK_INVARIANTS.md`).
- No global installation. This package is local; the v3.0-P0 contract
  prohibits global install until the master contract's full P0 + P1 + P2 +
  P3 + benchmarks are accepted.
