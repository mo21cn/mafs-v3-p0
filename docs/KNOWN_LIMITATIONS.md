# KNOWN_LIMITATIONS.md

This file is hand-written to describe the known limitations of the package
*as designed*, not the limitations of a particular build.

## P1 deferred (real retrieval)

- No live HTTP call is made. `pubmed_mock_v1` has
  `network_requirement=offline` and `trust_class=synthetic_test`.
- No `CandidatePointer`, no `EvidenceObject`, no raw snapshot are produced.
- The master-contract "non-mock" rule (§8.15) is not satisfied at P0.
- P1-min is the next bounded contract, not part of P0-RA1.

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
  - nested schema

It does **not** support:

  - `oneOf`, `anyOf` (schemas must avoid these; rewrite as `type: [a, b]`)
  - `if` / `then` / `else` (use Python code instead)
  - `$ref` to external files
  - format keywords other than `date-time`

If a schema uses an unsupported feature, the validator either silently
passes (oneOf) or rejects the schema at load time. We deliberately **do not
use oneOf** in any of the 12 P0 schemas.

## Path portability

- `tests/conftest.py` no longer hard-codes any Windows path; the real Target
  Freeze is `tests/fixtures/Blood_Oxygen_Ovary_Axis_Target_Freeze.md`
  (byte-identical to the source, SHA-256 verified in CI).
- `scripts/build_p0_ra1.py` uses the fixture path, not env vars.
- Production source (`src/mafs_p0/`) contains zero hard-coded machine paths
  (verified by `test_path_portability`).

## Real-task benchmark

- P0 is validated against ONE real task fixture. The Step C (real-task
  replay checkpoint) of the v3.0 master contract happens at P1-min.
- No known-answer benchmark, no unseen-domain benchmark at P0.

## Global installation

- The package is **not** globally installed. It is local to
  `C:\Users\Administrator\.minimax\agents\mavis\skills\multi_axis_falsification_search_v3_p0\`
  and is not auto-loaded by the Mavis skill loader.
- v0.1, v0.2, v0.3 skill packages are not modified.
