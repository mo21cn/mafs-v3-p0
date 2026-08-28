# HIGH_RISK_INVARIANTS.md

These invariants are the things P0-RA1 is deliberately hardening against.
Each one corresponds to a known v0.3 failure mode or a master-contract rule.
Violations are BLOCKERs in the preflight engine and the validator.

## I-1. Target Freeze is immutable

The compiler reads but never writes the source artifact. The compiled target
carries the source SHA-256. Preflight check C1 re-verifies the SHA-256 on every
run. **Violation = BLOCKER**.

## I-2. Compiled target partial → not silently dropped

If any required section cannot be extracted, the compiler returns
`status=TARGET_COMPILE_PARTIAL` and lists the missing sections in
`missing_sections`. The compiler does NOT fabricate missing content. Preflight
check C2 fails. **Violation = BLOCKER**.

## I-3. Essential axis without SearchOrder → blocked

Every axis with `essential=true` must have at least one SearchOrder. Preflight
check C3 enforces this. **Violation = BLOCKER**.

## I-4. SearchOrder.required_capabilities ⊆ Provider.capabilities

Capability negotiation is a set-theoretic ⊆ check. Extension namespaces match
the provider's `namespace` (or `name` if `namespace` is unset), not the versioned
provider identity string. Preflight check C4 enforces this. **Violation = BLOCKER**.

## I-5. Query AST and Boolean precedence

The QueryAST encodes precedence structurally (AND binds tighter than OR; NOT
is unary; parentheses are explicit). The PubMed compiler emits parentheses
when a parent operator differs from the child's operator. Regression test:
`tests/test_query_compiler.py::test_mixed_and_or_emits_parens_around_or`.
**Violation = BLOCKER**.

## I-6. Gate dependency is per-scope, not global

A blocked translation/patent axis (A10, blocking_role=supplementary) does NOT
block the `scientific_novelty` scope. The GateDependencyGraph records per-axis
scope and blocking_role. **Violation = BLOCKER**.

## I-7. Runtime Fingerprint is present and complete

The fingerprint must include 64-hex SHA-256 for: SKILL.md, schemas_manifest,
validator, query_compiler, every provider and resolver manifest. Preflight
check C7 enforces this. **Violation = BLOCKER**.

## I-8. Budget uses explicit status; null for unknown

`0` is forbidden for unknown ranges. The `cost_status` enum disambiguates.
When `cost_status=unknown`, all numeric ranges and hard_limits MUST be `null`,
not 0. Preflight check C8 enforces this. **Violation = BLOCKER**.

## I-9. Non-executable plan cannot return READY

If any preflight BLOCKER check fails, the overall status is
`PLANNING_BLOCKED`, never `READY_FOR_HO_EXECUTION_APPROVAL`. The semantic
validator (`validator.validate_run`) cross-checks this invariant and reports
`ready_with_blocker_check` if violated. **Violation = BLOCKER**.

## I-10. Path portability

No production source file contains hard-coded machine path patterns
(`H:\`, `I:\`, `C:\Users\`, `/Users/`, `/home/<user>`). The
`tests/test_path_portability.py` and the build script's static scan enforce
this. **Violation = BLOCKER**.

## I-11. Sidecar files have no UTF-8 BOM

SHA-256 sidecars are written as 64 hex chars + LF, no BOM. The
`mafs_p0.util.hashing.write_sidecar` and `read_sidecar_strict` utilities
enforce this. **Violation = BLOCKER**.

## I-12. Historical versions are immutable

v0.1, v0.2, v0.3 packages are not modified. The v3.0-P0 package does not
import from or write to any historical version's path. **Violation = BLOCKER**.

## I-13. Validation Evidence is Executed, not Statically Attested

`docs/P0_SUMMARY.md`, `docs/SHA256_MANIFEST.txt`, and `docs/TEST_SUMMARY.md`
are produced exclusively by `scripts/build_p0_ra1.py` running under the
repository CI. Hand-written PASS values for any of these are a contract
violation. **Violation = BLOCKER**.

## I-14. The Human Operator is not a CI runner

The build does not require the human operator to set local paths, transfer
a package to another runtime, or return tracebacks. The execution plane is
the repository CI; the human operator is the governance / acceptance plane.
**Violation = BLOCKER**.

## I-15. `__version__` and `schema_version` are separate identifiers

The package's PEP 440 `__version__` (`3.0.0.post0`) and the JSON Schema
`schema_version` (`3.0-p0`) are two distinct identifiers with two distinct
consumers. PEP 440 does not accept `-` as a post-release separator, so the
PEP 440 `__version__` uses `.post0`; the schema namespace must keep the
`p0` suffix to mark this as the P0 deliverable, so the schema's
`schema_version` uses `3.0-p0`. The two must not be conflated, "fixed" to
match, or substituted for one another in tooling. The runtime fingerprint
emits `schema_version: "3.0-p0"` and `skill.version: "3.0.0-p0"`; the
latter is the schema namespace's own version, not the package's
`__version__`. **Violation = BLOCKER**.
