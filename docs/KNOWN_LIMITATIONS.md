# KNOWN_LIMITATIONS.md

This file is hand-written to describe the known limitations of the package
*as designed*, not the limitations of a particular build.

## P1 deferred (real retrieval)

- No live HTTP call is made. `pubmed_mock_v1` has
  `network_requirement=offline` and `trust_class=synthetic_test`.
- No `CandidatePointer`, no `EvidenceObject`, no raw snapshot are produced.
- The master-contract "non-mock" rule (§8.15) is not satisfied at P0.
- P1-min is the next bounded contract, not part of P0-RA2.

## P2 deferred (trust / admissibility)

- Trust class enforcement is nominal.
- No automatic taint detection.
- No Evidence Admissibility gate object (the `validate_run` function only
  runs JSON Schema + cross-object semantic checks on the preflight; the
  full evidence-class taint comes at P2).

## P3 deferred (budget / production hardening)

- `hard_limits` are declared but **not mechanically enforced**.
- No resume, no telemetry, no cap-refusal on DEEP.

## Validator subset (P0 only)

The built-in `_MiniSchemaValidator` is intentionally minimal. It supports:

  - `type` (object, array, string, integer, number, boolean, null, and unions)
  - `properties`, `required`, `additionalProperties`
  - `enum`, `const`
  - `pattern` (regex)
  - `items`, `minItems`, `maxItems`
  - `minLength`, `minimum`, `maximum`
  - `allOf`
  - `$ref` to local node (`#/...`)
  - nested schema

It does **not** support:

  - `oneOf`, `anyOf` (schemas must avoid these; rewrite as `type: [a, b]`)
  - `if` / `then` / `else` (use Python code instead)
  - `$ref` to external files
  - format keywords other than `date-time`

If a schema uses an unsupported feature, the validator raises
`UnsupportedSchemaFeatureError` at load time (not a silent pass). None of
the 13 P0 schemas use `oneOf` / `anyOf` / `if` / `then` / `else`.

## Path portability

- `tests/conftest.py` no longer hard-codes any Windows path; the real Target
  Freeze is `tests/fixtures/Blood_Oxygen_Ovary_Axis_Target_Freeze.md`
  (byte-identical to the source, SHA-256 verified in CI STEP 1).
- `scripts/build_p0_ra1.py` uses the fixture path, not env vars.
- Production source (`src/mafs_p0/`) contains zero hard-coded machine paths
  (verified by `tests/test_path_portability.py`).

## Real-task benchmark

- P0 is validated against ONE real task fixture. The Step C (real-task
  replay checkpoint) of the v3.0 master contract happens at P1-min.
- No known-answer benchmark, no unseen-domain benchmark at P0.

## Global installation

- The package is **not** globally installed. It is local to its repository
  clone (`C:\Users\Administrator\.minimax\agents\mavis\skills\multi_axis_falsification_search_v3_p0\`
  for the development plane) and is not auto-loaded by the Mavis skill
  loader.
- v0.1, v0.2, v0.3 skill packages are not modified.

## Version identifiers (P0-RA2)

- The package `__version__` (PEP 440) is `3.0.0.post0`. This is what
  `pip install -e ".[test]"` and any `importlib.metadata.version(...)`
  consumer sees.
- The JSON Schema `schema_version` is `3.0-p0` (separate namespace).
  This is what the schemas and the runtime fingerprint carry.
- The two identifiers are **deliberately separate**: PEP 440 does not
  accept `-` as a post-release separator, but the schema namespace
  must keep the `p0` suffix to mark this as the P0 deliverable. Do
  not conflate them; do not "fix" one to match the other.
- See `VERSION.md` and `src/mafs_p0/__init__.py` docstring for the
  authoritative version note.

## Branch state (P0-RA2)

- The work / acceptance branch is `dev/mafs-v3-p0-ra2`. As of the
  CI-green commit `69f5a12`, this branch is at the full RA2 state.
- The `main` branch is at the initial import commit `caf1e1a`
  (schema/runtime-closure commit, pre-PEP-440-fix). It is **stale**
  with respect to `dev/mafs-v3-p0-ra2`. Per RA2 contract §12,
  Local Claw does not push to `main` until HO + GPT grant P0
  acceptance. After acceptance, a fast-forward merge is permitted.

## CI infrastructure (P0-RA2)

- CI is provided by GitHub Actions on `ubuntu-latest` with Python 3.10.
- The CI workflow file is `.github/workflows/mafs-p0.yml` (renamed from
  `mafs-p0-ra1.yml` in RA2; the workflow display name and the artifact
  name keep the `-ra1` suffix for back-compat).
- The CI runs `scripts/build_p0_ra1.py` as the **single deterministic
  entrypoint**. The workflow file contains no Python logic.
- One GitHub-side informational warning fires on every CI run:
  "Node.js 20 is deprecated" on the `ubuntu-latest` runner
  (2025-09-19 GitHub changelog). This is a GitHub Actions runtime
  notice, not a MAFS defect; it does not affect the run conclusion.
- One pytest informational warning fires on every CI run:
  `PytestReturnNotNoneWarning` from
  `tests/test_path_portability.py::tests_dir`. This is a test-style
  warning, not a test failure. pytest exit code is 0; count is 45 passed.

## Dev-only artifacts (not in git, not in CI)

The following files exist in the development-plane working tree but
are excluded from git via `.gitignore`. They are convenience artifacts
from the P0-RA1 / pre-RA2 development phase and are fully superseded
by `scripts/build_p0_ra1.py`:

- `smoke_import.py` (12-schema pre-RA2 import sanity test)
- `scripts/run_self_test.py` (single-step smoke test)
- `scripts/gen_sha256_manifest.py` (one-off manifest writer)

These files are NOT part of the P0-RA2 deliverable. They are listed
here for traceability only.
