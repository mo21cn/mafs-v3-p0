"""Axis definition (P0 §1.6)."""
from __future__ import annotations
from dataclasses import dataclass, asdict, field


@dataclass
class Axis:
    axis_id: str
    family: str
    proposition: str = ""
    admission: str = "admitted"
    essential: bool = True
    gate_scopes: list[str] = field(default_factory=lambda: ["scientific_novelty"])
    blocking_role: str = "essential"

    def to_dict(self) -> dict:
        return asdict(self)
