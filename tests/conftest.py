"""Test fixtures for P0.

The real-task Target Freeze is a byte-identical fixture in
``tests/fixtures/Blood_Oxygen_Ovary_Axis_Target_Freeze.md``. No environment
variable is consulted; the fixture is part of the repository so the
repository CI can run the acceptance test without operator setup.
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

_PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PKG / "src"))


# Byte-identical real-task fixture. SHA-256 verified by tests/test_target_freeze.py.
FIXTURE_TF_PATH = _PKG / "tests" / "fixtures" / "Blood_Oxygen_Ovary_Axis_Target_Freeze.md"


# Expected SHA-256 of the byte-identical fixture.
EXPECTED_FIXTURE_SHA256 = "3b080b50e1d0801915f5d6c6ab8d3b6cb9ee10f5ad1705e3bf45e9c2164b7e54"


# Minimal-but-complete synthetic Target Freeze used by tests that need
# hermetic input. Uses the plain ``A1: text`` form so we also exercise the
# third assumptions-parser branch.
MINIMAL_TF = """# Synthetic Test Target Freeze (P0 unit-test fixture)

## Frozen Root Question

> Is the proposal Q a defensible scientific object?

## Atomic Claims

### C1 — Test claim one

**Type:** scientific hypothesis
**Proposition:** The proposal is a defensible scientific object.
**Evidence that would change the framing:** Prior work already closes the object.

## Claims Explicitly Not Frozen as True

- A linear mechanism is not assumed.

## Assumptions to Stress-Test

A1: A controlled input is achievable.
A2: Output is measurable.

## Scope Boundaries

### In scope

- in-scope item

### Out of scope

- out-of-scope item

## Required Candidate Search Axes

1. **terminology:** alternate names
2. **mechanism:** underlying process
3. **translation:** device precedent

## High-Risk Semantic Neighborhoods

- structural equivalents

## Gate Decision Semantics

- PASS: no major collision

## Downstream Permission Matrix

| downstream_allowed | false |
| stop_downstream     | true  |

## Freeze Invariants

1. Do not silently rewrite claims.
2. No final framing gate without admissible evidence.
"""


@pytest.fixture(scope="session")
def real_tf_path() -> Path:
    p = FIXTURE_TF_PATH
    if not p.is_file():
        pytest.skip(
            f"real-task fixture not present at {p}. "
            f"This is a repository-resident fixture; if missing, the test "
            f"is being run from a wrong checkout."
        )
    return p


@pytest.fixture
def minimal_tf_path(tmp_path) -> Path:
    p = tmp_path / "minimal_target_freeze.md"
    p.write_text(MINIMAL_TF, encoding="utf-8")
    return p
