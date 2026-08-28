"""SearchOrder (P0 §6)."""
from __future__ import annotations
from dataclasses import dataclass, asdict, field


@dataclass
class SearchOrder:
    search_order_id: str
    axis_id: str
    operation_type: str
    required_capabilities: list[str]
    query_representation: dict
    expected_output: str = "candidate_pointer_set"
    gate_scope: str = "scientific_novelty"
    blocking_role: str = "essential"
    essential: bool = True

    def to_dict(self) -> dict:
        return asdict(self)
