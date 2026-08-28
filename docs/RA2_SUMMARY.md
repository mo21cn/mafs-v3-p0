# RA2_SUMMARY.md — MAFS v3.0-P0-RA2 Return Package

This is the **RA2 return package** (P0-RA2 contract §15/§16). It
documents the two-blocker closure, the CI execution evidence, and the
bounded scope that Local Claw actually delivered. HO + GPT use this
document to make the P0 acceptance decision.

## 1. Identity of the package

| Field | Value |
|---|---|
| Package | MAFS v3.0-P0 |
| Round | P0-RA2 (Repository-native + CI provenance) |
| Repository | `mo21cn/mafs-v3-p0` (public) |
| Triggering commit | `69f5a125c868c534bae5cb7a8dba4d5bc498f57e` |
| Branch | `dev/mafs-v3-p0-ra2` |
| CI run | `33156814708` (conclusion=success, 14s) |
| `__version__` (PEP 440) | `3.0.0.post0` |
| `schema_version` (separate) | `3.0-p0` |

## 2. Two P0 blockers — closure evidence

### 2.1 Blocker A: schema ↔ runtime closure (CLOSED)

The P0-RA1 package shipped 12 schemas, but the runtime produced
objects (a `negotiation_result` record and a `namespace`-qualified
provider/resolver entry) that did not have a corresponding schema.
This created a runtime-truth-vs-schema-truth gap that would surface
as a silent or loud failure at P1-min.

**What was done (committed at `caf1e1a`):**

1. **Schema 13 added**: `schemas/negotiation_result.schema.json`
   (Draft 2020-12, no `oneOf`, all required fields explicit,
   `additionalProperties: false`).
2. **Three schemas widened** to accept the existing runtime fields:
   - `schemas/provider_manifest.schema.json` — added optional
     `namespace: { type: ["string", "null"] }`.
   - `schemas/resolver_manifest.schema.json` — same as above.
   - `schemas/runtime_fingerprint.schema.json` — added **required**
     `namespace: { type: "string" }` on every `providers[]` and
     `resolvers[]` entry. This is the inverse of the prior
     "schema requires empty `sha256`" defect: schema now enforces
     the field the runtime already populates.
3. **`src/mafs_p0/validator.py::validate_run` widened** to also
   validate `providers`, `resolvers`, `negotiations`, `gate_graph`.
   All four are optional kwargs with `None` defaults, so prior
   callers keep working; the demo now passes the full object set,
   and the validator covers them.
4. **`src/mafs_p0/runtime_fingerprint.py::build_fingerprint`
   populates `namespace`** on every provider/resolver entry, falling
   back to `name` when the manifest's `namespace` is `None`.
5. **`src/mafs_p0/provider_manifest.py::to_dict()` auto-computes
   `sha256`** when empty, using a stable JSON canonical form. This
   catches the prior "manifest serializes with empty `sha256` then
   validator rejects 0/64-hex mismatch" defect at the source.

**How the closure is proven:**

The CI-generated `runtime_fingerprint.json` (artifact
`c59e2434313bb53e013588dfcc454ed26e44749cd6d0f1c806c7df66c2811cba`)
contains:

```json
"providers": [
  {"name": "pubmed_mock_v1", "namespace": "pubmed_mock_v1",
   "sha256": "85baa7c3...", "trust_class": "synthetic_test",
   "version": "3.0.0-p0"}
],
"resolvers": [
  {"name": "crossref_mock_v1", "namespace": "crossref_mock_v1",
   "sha256": "3c0178cb...", "trust_class": "synthetic_test",
   "version": "3.0.0-p0"}
]
```

`validate_run` at CI STEP 4 returned `PASS` for both demos, meaning
every emitted provider/resolver/negotiation/gate_graph object passed
schema validation. The full 13-schema set is now exercised end-to-end.

### 2.2 Blocker B: CI provenance closure (CLOSED)

The P0-RA1 package was "static review green" only — the test suite
was never run by an actual CI execution plane. The HO was, in effect,
the human CI runner. This violates the three-plane architecture
(Governance ≠ Development ≠ Execution) and the explicit
HIGH_RISK_INVARIANTS I-14 ("HO is not a CI runner").

**What was done (committed at `caf1e1a` and `69f5a12`):**

1. **GitHub repository created** at `mo21cn/mafs-v3-p0` (public).
2. **Local git repository initialized** with:
   - `.gitattributes` (`* -text` plus explicit `binary` for fixture
     files and `schemas/`, preventing line-ending drift on
     Windows-checkout / Linux-CI).
   - `.gitignore` excluding dev-only artifacts
     (`smoke_import.py`, `scripts/run_self_test.py`,
     `scripts/gen_sha256_manifest.py`) and the local
     `examples/runs/` directory.
   - `core.autocrlf=input` set as a local safety net.
3. **Repository CI workflow** at
   `.github/workflows/mafs-p0.yml` (renamed from `mafs-p0-ra1.yml`
   in RA2 to drop the RA-suffix on the file path; the workflow
   display name `MAFS v3.0-P0-RA1` and the artifact name
   `mafs-p0-ra1-artifacts` are kept for back-compat with HO's
   pre-existing review scripts). The workflow:
   - Checks out the repo
   - Sets up Python 3.10
   - Runs `pip install -e ".[test]"`
   - Runs `python scripts/build_p0_ra1.py` (the **single**
     deterministic entrypoint)
   - Uploads the 3 auto-generated docs and the 14-file
     `examples/runs/RA1/` directory
   - Fails the job if the build script returns non-zero
4. **Branch `dev/mafs-v3-p0-ra2`** created and used as the work /
   acceptance branch. The `main` branch is at the initial import
   (`caf1e1a`) and is **not** updated until P0 acceptance is
   granted by HO + GPT.
5. **PEP 440 compliance fix** committed at `69f5a12`:
   - `pyproject.toml` `version` → `3.0.0.post0`
   - `src/mafs_p0/__init__.py` `__version__` → `3.0.0.post0`
   - `VERSION.md` → `3.0.0.post0`
   - `schema_version` namespace stays `3.0-p0` (separate concern,
     documented in `VERSION.md` and `__init__.py` docstring).

**How the closure is proven:**

The CI run `33156814708` was triggered by the `69f5a12` push to
`dev/mafs-v3-p0-ra2`. It:

- Ran on a fresh `ubuntu-latest` GitHub-hosted runner.
- Returned `conclusion=success` after 14s.
- Re-verified the fixture SHA-256 at STEP 1.
- Ran all 45 pytest tests, exit code 0.
- Produced both positive (`READY_FOR_HO_EXECUTION_APPROVAL`) and
  negative (`PLANNING_BLOCKED`) demo outputs.
- Validated both demos via `validate_run` (PASS).
- Wrote the 14 build artifacts and 3 auto-generated docs from
  real run results.
- Uploaded the 17-file artifact set as `mafs-p0-ra1-artifacts`.

The full provenance record (run ID, commit SHA, branch, workflow
file, conclusion, artifact set, SHA-256 manifest) is in
`docs/CI_PROVENANCE.md`.

**Failure that was repaired during this round:**

The first push (`caf1e1a`) failed CI run `33156704408` with
`project.version must be pep440` (the version `3.0.0-p0` is not
PEP 440). Local Claw read the CI error, identified the defect
as a `pyproject.toml` `version` field, applied the fix
(`3.0.0.post0`), pushed (`69f5a12`), and re-ran the CI. The
follow-up run was green. **HO was not involved in this
remediation loop** — it was an in-plane Development→Execution
self-correction, exactly as the three-plane architecture
prescribes.

## 3. What Local Claw did (the bounded autonomy of RA2 §12)

Within the contract's bounded autonomy, Local Claw:

- Chose the workflow file name (`mafs-p0.yml`) and content.
- Chose the work branch name (`dev/mafs-v3-p0-ra2`).
- Made the schema ↔ runtime reconciliation decision (widen
  schemas, not narrow runtime — preserves forward compat with
  the capability-extension mechanism already designed in
  `capability_vocabulary.py`).
- Decided the Python matrix (3.10 — the package's
  `requires-python = ">=3.10"`).
- Made the PEP 440 / `schema_version` split decision
  (`__version__` follows PEP 440 for `pip install`;
  `schema_version` keeps the `3.0-p0` namespace for JSON
  Schemas and the runtime fingerprint).
- Made the line-ending policy (`.gitattributes` `* -text` plus
  explicit `binary` for fixtures and schemas; `core.autocrlf=input`
  as a local safety net).
- Renamed the workflow file (kept the workflow display name
  and the artifact name unchanged for back-compat).

Local Claw **did not**:

- Enter P1 live retrieval (forbidden at P0).
- Weaken Target Freeze immutability (the fixture is still
  byte-identical and the SHA-256 is re-verified at CI STEP 1).
- Modify v0.1 / v0.2 / v0.3 (immutable per master contract).
- Globally install v3.0 (the package is local; global install
  is gated on the full P0 + P1 + P2 + P3 + benchmarks chain).
- Push to `main` (acceptance branch only after P0 acceptance).
- Hand-write `P0_SUMMARY.md` / `SHA256_MANIFEST.txt` /
  `TEST_SUMMARY.md` (forbidden by I-13).

## 4. P0-SUMMARY.md (CI-generated, included for the record)

The CI-generated `docs/P0_SUMMARY.md` from run `33156814708`:

```
# P0_SUMMARY.md — AUTO-GENERATED by scripts/build_p0_ra1.py

This file is regenerated by every CI build. Hand-written content here is
a contract violation (HIGH_RISK_INVARIANTS.md I-13).

## Step 1: Byte-identical Target Freeze fixture
Status: PASS  (fixture sha256 matches 3b080b50e1d08019...)

## Step 2: pytest tests/
pytest exit code: 0
tests passed: 45

## Step 3: Positive + Negative demos
Positive preflight: READY_FOR_HO_EXECUTION_APPROVAL
Negative preflight: PLANNING_BLOCKED

## Step 4: validate_run
Status: PASS  (validator ok for both demos)

## Overall Disposition
READY_FOR_ACCEPTANCE

exit code: 0
build_time: 2026-08-28T08:48:51Z
```

## 5. Artifact set (CI-uploaded, run 33156814708)

The CI run uploaded exactly these files. The full per-file SHA-256
is in `docs/CI_PROVENANCE.md` §7 and the CI-generated
`docs/SHA256_MANIFEST.txt`.

```
docs/P0_SUMMARY.md                     (auto-generated, 648B)
docs/SHA256_MANIFEST.txt               (auto-generated, 1939B)
docs/TEST_SUMMARY.md                   (auto-generated, 1599B)

examples/runs/RA1/axes.json
examples/runs/RA1/budget.json
examples/runs/RA1/build.log
examples/runs/RA1/compiled_queries.json
examples/runs/RA1/compiled_target.json
examples/runs/RA1/gate_graph.json
examples/runs/RA1/negative_preflight_report.json
examples/runs/RA1/negative_run.json
examples/runs/RA1/negotiations.json
examples/runs/RA1/positive_run.json
examples/runs/RA1/preflight_report.json
examples/runs/RA1/providers.json
examples/runs/RA1/runtime_fingerprint.json
examples/runs/RA1/search_orders.json
```

## 6. HIGH_RISK_INVARIANTS — what is enforced

The P0-RA2 package now enforces **15 invariants** (I-1 through I-15).
The two new ones (added in RA2):

- **I-14. The Human Operator is not a CI runner.** The build does
  not require HO to set local paths, transfer a package, or return
  tracebacks. The execution plane is the repository CI; HO is the
  governance / acceptance plane. **Violation = BLOCKER**.

- **I-15. The package `__version__` and the schema `schema_version`
  are separate identifiers.** `__version__` follows PEP 440
  (currently `3.0.0.post0`); `schema_version` keeps the `3.0-p0`
  namespace across JSON Schemas and the runtime fingerprint. They
  must not be conflated. **Violation = BLOCKER**.

I-1 through I-13 are unchanged from P0-RA1.

## 7. KNOWN_LIMITATIONS — what is still bounded out

- P1 (live retrieval) is out of scope.
- P2 (trust / admissibility / taint) is out of scope.
- P3 (budget / production hardening) is out of scope.
- No global installation. Package is local to its repo clone.
- The `main` branch is **stale** at `caf1e1a` (the PEP 440 fix
  is on `dev/mafs-v3-p0-ra2` only). After P0 acceptance, HO +
  GPT can authorize a fast-forward merge.
- The pytest run produces one informational warning
  (`PytestReturnNotNoneWarning` from `test_path_portability.py::tests_dir`).
  This is a test-style warning, not a test failure. Exit code is
  0; count is 45 passed.
- GitHub Actions annotation: "Node.js 20 is deprecated" on
  `ubuntu-latest` — GitHub-side, not a MAFS defect.

## 8. The return package (RA2 §15)

The full RA2 return package that HO + GPT can use for acceptance:

| File | Source | Role |
|---|---|---|
| `docs/RA2_SUMMARY.md` | this file | acceptance summary (RA2 §15, §16) |
| `docs/CI_PROVENANCE.md` | hand-written | CI execution evidence (RA2 §7) |
| `docs/P0_SUMMARY.md` | CI-generated | disposition (CI STEP 5 output) |
| `docs/SHA256_MANIFEST.txt` | CI-generated | per-file SHA-256 (CI STEP 5 output) |
| `docs/TEST_SUMMARY.md` | CI-generated | pytest tail + 12 §16 risk checks (CI STEP 5 output) |
| `docs/CI_DEPLOYMENT.md` | hand-written | three-plane architecture + workflow doc |
| `docs/HIGH_RISK_INVARIANTS.md` | hand-written | invariants I-1..I-15 |
| `docs/KNOWN_LIMITATIONS.md` | hand-written | bounded-out scope |
| `CHANGED_FILES.txt` | hand-written | file list |
| `pyproject.toml` | hand-written | PEP 440 metadata |
| `src/mafs_p0/__init__.py` | hand-written | `__version__` + docstring |
| `VERSION.md` | hand-written | version note + schema namespace |
| `SKILL.md` | hand-written | package-level skill |
| `README.md` | hand-written | repo entry point |
| `.github/workflows/mafs-p0.yml` | hand-written | CI workflow |
| `.gitignore`, `.gitattributes` | hand-written | line-ending + dev-artifact policy |
| `schemas/*.schema.json` (13 files) | hand-written | 13 schema set |
| `src/mafs_p0/*.py` (24 files) | hand-written | package implementation |
| `tests/test_*.py` (12 files) | hand-written | pytest test set |
| `scripts/build_p0_ra1.py` | hand-written | CI entrypoint |
| `examples/run_p0_demo.py` | hand-written | demo runner |
| `examples/runs/RA1/*.json` (14 files) | CI-generated | CI build artifacts |

## 9. Recommended next step (Local Claw → HO + GPT)

If `ACCEPT_FOR_FREEZE` is granted on P0:

1. HO + GPT issue `ACCEPT_FOR_FREEZE` for the P0-RA2 deliverable.
2. Local Claw fast-forwards `main` to `69f5a12` (or the latest green
   commit on `dev/mafs-v3-p0-ra2`).
3. CP freeze is recorded; S5 is unblocked.

If `ACCEPT_WITH_LIMITATIONS` is granted:

- Local Claw documents the accepted limitations in
  `KNOWN_LIMITATIONS.md` and re-issues the return package.

If `REJECT_RA_REQUIRED` is granted:

- HO + GPT cite a specific BLOCKER from the artifact set
  (the docs/P0_SUMMARY.md, the per-file SHA-256, the build log,
  or a specific HIGH_RISK_INVARIANTS violation).
- Local Claw enters the bounded self-remediation loop:
  read artifact → patch → commit → push → re-run → re-verify.
  HO + GPT are not involved in the remediation mechanics.

---

This document closes P0-RA2. The two blockers (schema ↔ runtime
closure and CI provenance closure) are both closed, with executed
CI evidence (`run 33156814708`, `conclusion=success`,
`exit_code=0`). The 13-schema set is exercised end-to-end; the
3 auto-generated docs are not hand-written; the HO is no longer
a CI runner.
