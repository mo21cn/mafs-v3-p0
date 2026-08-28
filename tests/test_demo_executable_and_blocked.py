"""Risk test 2 (supplemental): missing required object/schema fails.

We intentionally do NOT have a runtime that 'succeeds by checking zero objects'.
The validator (validate_against_schema) raises if the schema is missing; preflight
fails closed if any required object is missing.
"""
from __future__ import annotations
import pytest
from mafs_p0.validator import validate_against_schema


def test_missing_schema_raises():
    with pytest.raises(FileNotFoundError):
        validate_against_schema({}, "this_schema_does_not_exist.schema.json")
