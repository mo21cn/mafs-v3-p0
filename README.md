# MAFS v3.0-P0 — Executable Plan Foundation

Bounded P0 implementation of MAFS v3.0. Goal: prove a planned search is executable
before HO is asked to authorize live retrieval.

## Install (development only — not globally installed)

```text
pip install -e .[test]
```

## Run

```text
python examples/run_p0_demo.py
pytest tests/ -q
```

## Status of this package

- v0.1 / v0.2 / v0.3 packages are immutable and untouched
- This package is a sibling skill at `multi_axis_falsification_search_v3_p0/`
- Not globally installed; not auto-loaded by the Mavis skill loader (directory name differs from v0.3)
- v3.0 master contract and v3.0-P0 contract are documents of record, not code
