"""Gate Dependency Graph (P0 §4 / master §7.7).

A blocked supplementary translation axis must not automatically block unrelated
scientific execution. This module models per-axis scope and blocking_role and
exposes a per-scope readiness check used by preflight.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Iterable

from .axis import Axis
from .search_order import SearchOrder


@dataclass
class GateEdge:
    axis_id: str
    scope: str
    blocking_role: str  # essential | supplementary | optional


@dataclass
class GateDependencyGraph:
    graph_id: str
    scopes: list[str] = field(default_factory=lambda: ["scientific_novelty", "translation", "overall"])
    edges: list[GateEdge] = field(default_factory=list)
    blocking_rules: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "schema_version": "3.0-p0",
            "graph_id": self.graph_id,
            "scopes": list(self.scopes),
            "edges": [asdict(e) for e in self.edges],
            "blocking_rules": list(self.blocking_rules),
        }


def build_default_graph(axes: Iterable[Axis]) -> GateDependencyGraph:
    """P0 default: scientific_novelty covers A1-A9; translation covers A10 (supplementary).

    A10's patent-inaccessibility is NOT an automatic block on scientific execution.
    """
    g = GateDependencyGraph(graph_id="GDG-1")
    scientific = []
    translation = []
    for ax in axes:
        # Heuristic: A10 is the typical "translation / device precedent" axis.
        # Anything with family containing "translation" or "device" is sent to translation scope.
        is_translation = (
            ax.axis_id == "A10"
            or "translation" in ax.family.lower()
            or "device" in ax.family.lower()
        )
        if is_translation:
            translation.append(ax)
            g.edges.append(GateEdge(axis_id=ax.axis_id, scope="translation", blocking_role=ax.blocking_role))
        else:
            scientific.append(ax)
            g.edges.append(GateEdge(axis_id=ax.axis_id, scope="scientific_novelty", blocking_role=ax.blocking_role))

    g.blocking_rules.append({
        "scope": "scientific_novelty",
        "rule": "essential axes without SearchOrder or compatible provider => READY for this scope is blocked",
    })
    g.blocking_rules.append({
        "scope": "translation",
        "rule": "supplementary axes may be blocked without blocking scientific_novelty",
    })
    g.blocking_rules.append({
        "scope": "overall",
        "rule": "overall readiness requires the strictest scope to be READY; supplementary-only blocks do not by themselves block overall",
    })
    return g


def scope_readiness(
    scope: str,
    g: GateDependencyGraph,
    axes_for_scope: dict[str, list[Axis]],
    executable_so_ids_by_axis: set[str],
    so_by_id: dict[str, SearchOrder],
) -> tuple[bool, list[str]]:
    """Return (is_ready, blockers) for one scope.

    ``executable_so_ids_by_axis`` is a set of axis_ids that have at least one executable
    SearchOrder (capability negotiation succeeded).
    """
    blockers: list[str] = []
    essential_axes = [a for a in axes_for_scope.get(scope, []) if a.blocking_role == "essential"]
    for a in essential_axes:
        if a.axis_id not in executable_so_ids_by_axis:
            blockers.append(
                f"scope={scope}: essential axis {a.axis_id} ({a.family}) has no executable SearchOrder"
            )
    return (not blockers), blockers
