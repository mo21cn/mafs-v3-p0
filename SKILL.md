# MAFS v3.0-P0 — Executable Plan Foundation

Scope: **P0 only**. A planned MAFS search must be **technically executable** before HO is asked to authorize live retrieval.

## P0 contract

This package implements the bounded foundation defined by contract `MAFS-v3.0-P0-EXECUTABLE-PLAN-FOUNDATION`. It does **not** implement:

- Live retrieval (P1)
- Trust/taint (P2)
- Budget enforcement (P3)
- Benchmarks
- Global installation

## Core thesis (carried from master)

> **Discovery is not Resolution.**
> A planned search is executable only when a target provider's declared capabilities mechanically subsume every SearchOrder's declared `required_capabilities`.

## What is proven here

```text
Target Freeze
  → compiled target (11 sections; TARGET_COMPILE_PARTIAL on omission)
  → admitted axes
  → SearchOrders (≥1 per essential axis; each declares required_capabilities)
  → capability negotiation (mechanical ⊆)
  → Query AST (AND/OR/NOT/PHRASE/FIELD)
  → compiled query (backend-specific; precedence preserved)
  → preflight (READY | PLANNING_BLOCKED)
  → Runtime Fingerprint
  → budget (null semantics, never 0 for unknown)
```

## Non-goals (deferred)

| Out of P0 | Belongs to |
|---|---|
| Live OpenAlex / PubMed / Crossref calls | Step B (P1-min) |
| CandidatePointer production | Step B |
| EvidenceObject production | Step B |
| Automatic taint detection | Step D (P2-min) |
| Trust-class enforcement | Step D |
| Hard budget enforcement | Step E (P3-min) |
| Resume | Step E |
| Real-task benchmark | Step C |
| Unseen-domain benchmark | Step C |
| Global installation | post-acceptance |

## Layout

```text
schemas/                 # 12 JSON Schemas
src/mafs_p0/             # implementation
  paths.py, hashing.py   # relative-path + BOM-free SHA-256
  capability_vocabulary.py
  target_compiler.py
  gate_dependency_graph.py
  axis.py, search_order.py, provider_manifest.py
  capability_negotiation.py
  query_ast.py
  query_compiler/
    base.py
    pubmed_ebsco.py      # one backend, sufficient to prove compile
  budget.py
  runtime_fingerprint.py
  preflight.py
  validator.py
  demo.py
tests/                   # 12 risk-focused tests (§16 of P0 contract)
examples/
  run_p0_demo.py
  fixtures/              # byte-identical Target Freeze
docs/                    # P0_SUMMARY, KNOWN_LIMITATIONS, HIGH_RISK_INVARIANTS
scripts/                 # SHA256 manifest generator
```

## Quick start

```text
python examples/run_p0_demo.py            # positive + negative demo
pytest tests/ -q                          # 12 §16 risk tests
```

Historical MAFS versions (v0.1 / v0.2 / v0.3) are not modified by this package.
