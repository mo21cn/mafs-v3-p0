"""§16 risk test 5: essential axis without SearchOrder fails (preflight C3)."""
from __future__ import annotations
from mafs_p0.demo import run_positive_demo
from mafs_p0.preflight import run_preflight, PreflightReport
from mafs_p0.axis import Axis
from mafs_p0.search_order import SearchOrder
from mafs_p0.provider_manifest import ProviderManifest
from mafs_p0.capability_negotiation import negotiate_all
from mafs_p0.gate_dependency_graph import build_default_graph
from mafs_p0.runtime_fingerprint import build_fingerprint
from mafs_p0.budget import standard_p0_budget


def _empty_so() -> SearchOrder:
    return SearchOrder(
        search_order_id="SO-A1-01",
        axis_id="A1",
        operation_type="discovery_search",
        required_capabilities=["search.query"],
        query_representation={"op": "PHRASE", "phrase": "x"},
    )


def test_essential_axis_without_so_blocks_preflight():
    # A1 essential, A2 essential. Only A1 has SO -> A2 missing -> BLOCKED.
    axes = [
        Axis(axis_id="A1", family="f1", essential=True, gate_scopes=["scientific_novelty"], blocking_role="essential"),
        Axis(axis_id="A2", family="f2", essential=True, gate_scopes=["scientific_novelty"], blocking_role="essential"),
    ]
    sos = [_empty_so()]
    providers = [ProviderManifest(
        name="p1", version="1", capabilities=["search.query", "search.pagination", "result.ranked"],
        network_requirement="offline", trust_class="synthetic_test",
    )]
    compiled = {"status": "COMPILED", "source_sha256": "x" * 64}
    budget = standard_p0_budget().to_dict()
    fp = build_fingerprint(providers, [])
    graph = build_default_graph(axes)
    negotiations = negotiate_all(sos, providers)
    compiled_queries = [{
        "schema_version": "3.0-p0", "query_ast_sha256": "a" * 64, "backend": "pubmed_esearch",
        "rendered_query": '"x"', "compiler_name": "pubmed_ebsco", "compiler_version": "3.0.0-p0",
        "validation_status": "valid",
    }]

    # We need a real path for SHA-256; use any existing file (here, the test file).
    import pathlib
    real_path = pathlib.Path(__file__).resolve()
    report = run_preflight(
        compiled_target=compiled,
        axes=axes,
        search_orders=sos,
        providers=providers,
        negotiations=negotiations,
        compiled_queries=compiled_queries,
        gate_graph=graph,
        runtime_fingerprint=fp,
        budget_state=budget,
        target_freeze_path=real_path,
    )
    c3 = next(c for c in report.checks if c.check_id == "C3")
    assert c3.outcome == "FAIL"
    assert "A2" in c3.detail
    assert report.status == "PLANNING_BLOCKED"


def test_positive_demo_all_essential_axes_have_so(real_tf_path):
    out = run_positive_demo(tf_path=real_tf_path)
    so_axes = {so["axis_id"] for so in out["search_orders"]}
    for ax in out["axes"]:
        if ax["essential"]:
            assert ax["axis_id"] in so_axes, f"essential axis {ax['axis_id']} has no SearchOrder in positive demo"
    c3 = next(c for c in out["preflight"]["checks"] if c["check_id"] == "C3")
    assert c3["outcome"] == "PASS"
