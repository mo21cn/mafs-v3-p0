"""§16 risk test 11: unknown budget uses null/explicit status.

0 is NOT used to mean unknown. The budget_state schema enforces null semantics;
this test asserts that a BudgetState with cost_status=unknown has null ranges.
"""
from __future__ import annotations
import pytest
from mafs_p0.budget import standard_p0_budget, unknown_p0_budget, BudgetState, BudgetError


def test_standard_budget_estimated_has_range():
    b = standard_p0_budget()
    d = b.to_dict()
    assert d["cost_status"] == "estimated"
    assert d["estimated_token_range"] is not None
    assert d["estimated_token_range"][0] <= d["estimated_token_range"][1]


def test_unknown_budget_uses_null_not_zero():
    b = unknown_p0_budget()
    d = b.to_dict()
    assert d["cost_status"] == "unknown"
    assert d["estimated_token_range"] is None, "0 is forbidden for unknown; null is required"
    assert d["estimated_cost_range_usd"] is None
    for k, v in d["hard_limits"].items():
        assert v is None, f"hard_limits[{k}] must be null for unknown budget; got {v!r}"


def test_budget_validates_cost_status():
    b = BudgetState(mode="standard", cost_status="bogus")
    with pytest.raises(BudgetError):
        b.validate()


def test_budget_validates_mode():
    b = BudgetState(mode="bogus", cost_status="unknown")
    with pytest.raises(BudgetError):
        b.validate()


def test_budget_rejects_token_range_wrong_length():
    b = BudgetState(mode="standard", cost_status="estimated", estimated_token_range=[100])
    with pytest.raises(BudgetError):
        b.validate()


def test_budget_rejects_negative_token_range():
    b = BudgetState(mode="standard", cost_status="estimated", estimated_token_range=[-1, 10])
    with pytest.raises(BudgetError):
        b.validate()


def test_configured_cap_requires_at_least_one_limit():
    b = BudgetState(mode="standard", cost_status="configured_cap", hard_limits={})
    with pytest.raises(BudgetError):
        b.validate()


def test_not_configured_requires_explanation():
    b = BudgetState(mode="standard", cost_status="not_configured", hard_limits={})
    with pytest.raises(BudgetError):
        b.validate()
