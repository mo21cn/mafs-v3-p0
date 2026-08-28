"""Budget state with explicit null semantics (P0 §10).

Unknown values are ``null``, never ``0``. ``0`` is reserved for a *configured* cap
or for an *actual* measured value. The status field disambiguates the meaning.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Any


VALID_STATUSES: frozenset[str] = frozenset({
    "estimated", "unknown", "configured_cap", "not_configured", "explicitly_unbounded",
})


class BudgetError(ValueError):
    pass


@dataclass
class BudgetState:
    mode: str
    cost_status: str
    estimated_token_range: list[int] | None = None
    estimated_cost_range_usd: list[float] | None = None
    hard_limits: dict[str, int | None] = field(default_factory=dict)
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = {
            "schema_version": "3.0-p0",
            "mode": self.mode,
            "cost_status": self.cost_status,
            "estimated_token_range": self.estimated_token_range,
            "estimated_cost_range_usd": self.estimated_cost_range_usd,
            "hard_limits": dict(self.hard_limits),
        }
        if self.explanation:
            d["explanation"] = self.explanation
        return d

    def validate(self) -> None:
        if self.cost_status not in VALID_STATUSES:
            raise BudgetError(f"invalid cost_status: {self.cost_status!r}")
        if self.mode not in {"quick", "standard", "deep"}:
            raise BudgetError(f"invalid mode: {self.mode!r}")
        if self.estimated_token_range is not None:
            if len(self.estimated_token_range) != 2:
                raise BudgetError("estimated_token_range must be [min, max] or null")
            lo, hi = self.estimated_token_range
            if not (isinstance(lo, int) and isinstance(hi, int)):
                raise BudgetError("estimated_token_range entries must be int")
            if lo < 0 or hi < 0:
                raise BudgetError("estimated_token_range entries must be >= 0")
            if lo > hi:
                raise BudgetError("estimated_token_range min must be <= max")
        if self.estimated_cost_range_usd is not None:
            if len(self.estimated_cost_range_usd) != 2:
                raise BudgetError("estimated_cost_range_usd must be [min, max] or null")
            lo, hi = self.estimated_cost_range_usd
            if not (isinstance(lo, (int, float)) and isinstance(hi, (int, float))):
                raise BudgetError("estimated_cost_range_usd entries must be number")
            if lo < 0 or hi < 0:
                raise BudgetError("estimated_cost_range_usd entries must be >= 0")
            if lo > hi:
                raise BudgetError("estimated_cost_range_usd min must be <= max")
        for k, v in self.hard_limits.items():
            if v is not None and (not isinstance(v, int) or v < 0):
                raise BudgetError(f"hard_limits[{k}] must be int >= 0 or null")
        if self.cost_status == "not_configured":
            if not self.explanation:
                raise BudgetError("cost_status=not_configured requires an 'explanation' string")
        if self.cost_status == "configured_cap":
            if not any(v is not None for v in self.hard_limits.values()):
                raise BudgetError("cost_status=configured_cap requires at least one hard_limit entry")


def standard_p0_budget() -> BudgetState:
    """P0 default budget: token range estimated from a small executable plan; caps explicit."""
    return BudgetState(
        mode="standard",
        cost_status="estimated",
        estimated_token_range=[8000, 18000],
        estimated_cost_range_usd=None,    # unknown -> null
        hard_limits={
            "provider_invocations": 40,
            "resolver_invocations": 80,
            "fulltext_adjudications": 8,
            "high_reasoning_calls": 10,
            "hard_cap": None,           # no hard cap at P0; null, not 0
        },
        explanation="P0 plan-based estimate; cost not yet quoted (null).",
    )


def unknown_p0_budget() -> BudgetState:
    """For tests: explicit unknown state. ``0`` is NOT used to mean unknown."""
    return BudgetState(
        mode="standard",
        cost_status="unknown",
        estimated_token_range=None,
        estimated_cost_range_usd=None,
        hard_limits={
            "provider_invocations": None,
            "resolver_invocations": None,
            "fulltext_adjudications": None,
            "high_reasoning_calls": None,
            "hard_cap": None,
        },
        explanation="token/cost not yet estimated; all hard_limits null (not 0).",
    )


def reject_zero_as_unknown() -> None:
    """Helper that documents the rule: 0 is reserved for configured/measured values.
    Use ``None`` for unknown. Calling code MUST NOT pass 0 where it means 'unknown'."""
    # This is a documentation hook; the real enforcement lives in validate() and in
    # the schema (which uses null, not 0, for unknown).
    return None
