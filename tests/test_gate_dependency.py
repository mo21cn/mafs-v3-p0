"""§16 risk test 9: gate dependency scopes inspectable.

A blocked supplementary translation axis must not block scientific execution.
"""
from __future__ import annotations
from mafs_p0.axis import Axis
from mafs_p0.gate_dependency_graph import build_default_graph, scope_readiness


def test_scientific_and_translation_scopes_inspectable():
    axes = [
        Axis(axis_id="A1", family="mech", essential=True, gate_scopes=["scientific_novelty"], blocking_role="essential"),
        Axis(axis_id="A2", family="mech2", essential=True, gate_scopes=["scientific_novelty"], blocking_role="essential"),
        Axis(axis_id="A10", family="translation", essential=True, gate_scopes=["translation"], blocking_role="supplementary"),
    ]
    g = build_default_graph(axes)
    # Every axis has a gate edge
    edges = {(e.axis_id, e.scope) for e in g.edges}
    assert ("A1", "scientific_novelty") in edges
    assert ("A2", "scientific_novelty") in edges
    assert ("A10", "translation") in edges


def test_translation_block_does_not_block_scientific():
    axes = [
        Axis(axis_id="A1", family="mech", essential=True, gate_scopes=["scientific_novelty"], blocking_role="essential"),
        Axis(axis_id="A2", family="mech2", essential=True, gate_scopes=["scientific_novelty"], blocking_role="essential"),
        Axis(axis_id="A10", family="translation", essential=True, gate_scopes=["translation"], blocking_role="supplementary"),
    ]
    g = build_default_graph(axes)
    # Group axes by scope
    by_scope: dict[str, list[Axis]] = {}
    for ax in axes:
        for sc in ax.gate_scopes:
            by_scope.setdefault(sc, []).append(ax)

    # Scientific: A1 and A2 executable -> scientific ready
    sci_ok, sci_blockers = scope_readiness(
        "scientific_novelty", g, by_scope,
        executable_so_ids_by_axis={"A1", "A2"},
        so_by_id={},
    )
    assert sci_ok, sci_blockers

    # Translation: A10 supplementary is allowed to be empty; its blocking_role
    # is supplementary (not essential), so scope_readiness for translation is OK
    # when no essential translation axis exists.
    trans_ok, trans_blockers = scope_readiness(
        "translation", g, by_scope,
        executable_so_ids_by_axis={"A1", "A2"},  # A10 not executable
        so_by_id={},
    )
    assert trans_ok, trans_blockers


def test_scientific_essential_missing_blocks_scientific():
    axes = [
        Axis(axis_id="A1", family="mech", essential=True, gate_scopes=["scientific_novelty"], blocking_role="essential"),
        Axis(axis_id="A2", family="mech2", essential=True, gate_scopes=["scientific_novelty"], blocking_role="essential"),
    ]
    g = build_default_graph(axes)
    by_scope = {"scientific_novelty": axes, "translation": []}
    # A2 has no executable SO
    sci_ok, sci_blockers = scope_readiness(
        "scientific_novelty", g, by_scope,
        executable_so_ids_by_axis={"A1"},
        so_by_id={},
    )
    assert not sci_ok
    assert any("A2" in b for b in sci_blockers)
