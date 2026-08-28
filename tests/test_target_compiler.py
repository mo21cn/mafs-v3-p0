"""§16 risk test 4: target compiler reports partial rather than silently dropping.

If a required section is missing, the compiler returns status=TARGET_COMPILE_PARTIAL
and lists the missing sections. It NEVER silently drops or fabricates.
"""
from __future__ import annotations
from pathlib import Path

import pytest

from mafs_p0.target_compiler import compile_target


# A Target Freeze that lacks the required search axes section entirely.
PARTIAL_TF_NO_AXES = """# Partial Target Freeze (missing required_search_axes)

## Frozen Root Question

> Is the proposal Q a defensible scientific object?

## Atomic Claims

### C1 — Only claim

**Type:** scientific_hypothesis
**Proposition:** The proposal is defensible.
**Evidence that would change the framing:** Prior work closes it.

## Assumptions to Stress-Test

A1: An input is achievable.

## Scope Boundaries

### In scope

- in-scope item

### Out of scope

- out-of-scope item

## Gate Decision Semantics

- PASS: no major collision

## Downstream Permission Matrix

| downstream_allowed | false |
| stop_downstream     | true  |

## Freeze Invariants

1. Do not silently rewrite.
"""


def test_compiler_reports_partial_when_required_section_missing(tmp_path):
    p = tmp_path / "partial.md"
    p.write_text(PARTIAL_TF_NO_AXES, encoding="utf-8")
    compiled = compile_target(p)
    assert compiled["status"] == "TARGET_COMPILE_PARTIAL"
    assert "required_search_axes" in compiled["missing_sections"]


def test_compiler_reports_partial_when_assumptions_missing(tmp_path):
    src = PARTIAL_TF_NO_AXES.replace(
        "## Assumptions to Stress-Test\n\nA1: An input is achievable.\n",
        "",
    )
    p = tmp_path / "partial2.md"
    p.write_text(src, encoding="utf-8")
    compiled = compile_target(p)
    assert compiled["status"] == "TARGET_COMPILE_PARTIAL"
    assert "assumptions" in compiled["missing_sections"]


def test_compiler_does_not_invent_sections(tmp_path):
    p = tmp_path / "partial3.md"
    p.write_text(PARTIAL_TF_NO_AXES, encoding="utf-8")
    compiled = compile_target(p)
    # Compiler must NOT fabricate axes from nothing.
    assert compiled.get("required_search_axes") in (None, [])
    assert "required_search_axes" in compiled.get("missing_sections", [])
