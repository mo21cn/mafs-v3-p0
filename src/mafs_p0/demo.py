"""P0 demo: positive (executable) + negative (non-executable) runs.

The demo does NOT perform any live retrieval (P1 deferred). It proves that:
  * A planned search is mechanically executable (positive) when every essential
    axis has a SearchOrder, every SearchOrder has a compatible provider, and every
    query compiles.
  * A planned search is PLANNING_BLOCKED (negative) when a required capability is
    missing from all providers, with a concrete blocker.

Source Target Freeze resolution order:
  1. The ``tf_path`` argument if explicitly passed.
  2. The ``MAFS_P0_TF_PATH`` environment variable if set.
  3. The repository-resident byte-identical fixture at
     ``tests/fixtures/Blood_Oxygen_Ovary_Axis_Target_Freeze.md``.
  4. Otherwise: FileNotFoundError with explicit instruction.

The fixture is part of the repository so the CI can run this demo without
operator setup. Production source does NOT hard-code any machine path.
"""
from __future__ import annotations
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure src/ is on the path when run as a script (no pip install required for demo).
_PKG = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PKG / "src"))

from mafs_p0.target_compiler import compile_target
from mafs_p0.axis import Axis
from mafs_p0.search_order import SearchOrder
from mafs_p0.provider_manifest import ProviderManifest, ResolverManifest
from mafs_p0.capability_negotiation import negotiate_all
from mafs_p0.gate_dependency_graph import build_default_graph, scope_readiness
from mafs_p0.query_compiler import PubMedEbscoCompiler
from mafs_p0.query_compiler.pubmed_ebsco import compile_for_demo
from mafs_p0.budget import standard_p0_budget, unknown_p0_budget, BudgetState
from mafs_p0.runtime_fingerprint import build_fingerprint, fingerprint_self_sha256
from mafs_p0.preflight import run_preflight
from mafs_p0.util.hashing import sha256_file, sha256_json


# Repository-resident byte-identical fixture. The build script and tests
# rely on this constant path; production code never hard-codes operator paths.
FIXTURE_TF_PATH: Path = _PKG / "tests" / "fixtures" / "Blood_Oxygen_Ovary_Axis_Target_Freeze.md"

# Optional env override (used by the v0.3 historical run and for ad-hoc tests).
DEFAULT_TF_PATH: Path | None = None
_TF_ENV = os.environ.get("MAFS_P0_TF_PATH")
if _TF_ENV:
    DEFAULT_TF_PATH = Path(_TF_ENV)


def _resolve_tf_path(tf_path: Path | None) -> Path:
    """Apply the resolution order: arg > env > fixture > error."""
    if tf_path is not None:
        return tf_path
    if DEFAULT_TF_PATH is not None:
        return DEFAULT_TF_PATH
    if FIXTURE_TF_PATH.is_file():
        return FIXTURE_TF_PATH
    raise FileNotFoundError(
        "No Target Freeze path available. Set MAFS_P0_TF_PATH or pass tf_path=... "
        f"explicitly. The expected fixture path is {FIXTURE_TF_PATH}; if missing, "
        "the repository checkout is incomplete."
    )


# Axis and SearchOrder factory: 10 axes per source TF; A10 is translation/supplementary.
def build_axes() -> list[Axis]:
    return [
        Axis(axis_id="A1", family="terminology_and_category_ancestry", essential=True,
             gate_scopes=["scientific_novelty"], blocking_role="essential"),
        Axis(axis_id="A2", family="ovarian_microcirculation_and_oxygen_delivery", essential=True,
             gate_scopes=["scientific_novelty"], blocking_role="essential"),
        Axis(axis_id="A3", family="follicular_oxygen_transport_and_spatial_gradients", essential=True,
             gate_scopes=["scientific_novelty"], blocking_role="essential"),
        Axis(axis_id="A4", family="dynamic_oxygen_perturbation_in_reproductive_systems", essential=True,
             gate_scopes=["scientific_novelty"], blocking_role="essential"),
        Axis(axis_id="A5", family="hbot_normobaric_oxygen_and_ovarian_outcomes", essential=True,
             gate_scopes=["scientific_novelty"], blocking_role="essential"),
        Axis(axis_id="A6", family="measurement_and_identifiability", essential=True,
             gate_scopes=["scientific_novelty"], blocking_role="essential"),
        Axis(axis_id="A7", family="oxygen_redox_sensing_and_ovarian_decoding", essential=True,
             gate_scopes=["scientific_novelty"], blocking_role="essential"),
        Axis(axis_id="A8", family="adjacent_organ_and_systems_engineering_prior_art", essential=True,
             gate_scopes=["scientific_novelty"], blocking_role="essential"),
        Axis(axis_id="A9", family="counterexample_and_boundary_evidence", essential=True,
             gate_scopes=["scientific_novelty"], blocking_role="essential"),
        Axis(axis_id="A10", family="translation_and_device_precedent", essential=True,
             gate_scopes=["translation"], blocking_role="supplementary"),
    ]


# SearchOrder factory: at least one SO per essential axis.
# Query AST is a simple (well-typed) expression that exercises AND/OR/PHRASE/FIELD
# Boolean precedence so the compiler must emit parentheses when mixing.
def build_search_orders() -> list[SearchOrder]:
    sos: list[SearchOrder] = []
    # A1: terminology — phrase search
    sos.append(SearchOrder(
        search_order_id="SO-A1-01",
        axis_id="A1",
        operation_type="discovery_search",
        required_capabilities=["search.query", "search.pagination", "result.ranked"],
        query_representation={
            "op": "AND", "children": [
                {"op": "PHRASE", "phrase": "ovarian oxygenation"},
                {"op": "OR", "children": [
                    {"op": "PHRASE", "phrase": "blood-ovary axis"},
                    {"op": "PHRASE", "phrase": "ovary oxygen delivery"},
                ]},
            ]
        },
        expected_output="candidate_pointer_set",
        gate_scope="scientific_novelty",
        blocking_role="essential",
        essential=True,
    ))
    # A2: microcirculation — phrase + field
    sos.append(SearchOrder(
        search_order_id="SO-A2-01",
        axis_id="A2",
        operation_type="discovery_search",
        required_capabilities=["search.query", "search.fielded_query", "search.pagination", "result.ranked"],
        query_representation={
            "op": "AND", "children": [
                {"op": "OR", "children": [
                    {"op": "PHRASE", "phrase": "ovarian blood flow"},
                    {"op": "PHRASE", "phrase": "ovarian perfusion"},
                ]},
                {"op": "OR", "children": [
                    {"op": "PHRASE", "phrase": "oxygen extraction"},
                    {"op": "PHRASE", "phrase": "oxygen delivery"},
                ]},
            ]
        },
        expected_output="candidate_pointer_set",
        gate_scope="scientific_novelty",
        blocking_role="essential",
        essential=True,
    ))
    # A3: follicular oxygen — phrase only
    sos.append(SearchOrder(
        search_order_id="SO-A3-01",
        axis_id="A3",
        operation_type="discovery_search",
        required_capabilities=["search.query", "search.pagination"],
        query_representation={
            "op": "AND", "children": [
                {"op": "PHRASE", "phrase": "follicular fluid pO2"},
                {"op": "PHRASE", "phrase": "theca granulosa diffusion"},
            ]
        },
        expected_output="candidate_pointer_set",
        gate_scope="scientific_novelty",
        blocking_role="essential",
        essential=True,
    ))
    # A4: dynamic perturbation — AND mixes with OR -> parentheses REQUIRED.
    sos.append(SearchOrder(
        search_order_id="SO-A4-01",
        axis_id="A4",
        operation_type="discovery_search",
        required_capabilities=["search.query", "search.pagination", "result.ranked"],
        query_representation={
            "op": "AND", "children": [
                {"op": "OR", "children": [
                    {"op": "PHRASE", "phrase": "intermittent hypoxia"},
                    {"op": "PHRASE", "phrase": "intermittent hyperoxia"},
                ]},
                {"op": "OR", "children": [
                    {"op": "PHRASE", "phrase": "ovary"},
                    {"op": "PHRASE", "phrase": "follicle"},
                ]},
            ]
        },
        expected_output="candidate_pointer_set",
        gate_scope="scientific_novelty",
        blocking_role="essential",
        essential=True,
    ))
    # A5: HBOT/normobaric — phrase search
    sos.append(SearchOrder(
        search_order_id="SO-A5-01",
        axis_id="A5",
        operation_type="discovery_search",
        required_capabilities=["search.query", "search.pagination", "result.ranked"],
        query_representation={
            "op": "AND", "children": [
                {"op": "OR", "children": [
                    {"op": "PHRASE", "phrase": "hyperbaric oxygen"},
                    {"op": "PHRASE", "phrase": "HBOT"},
                ]},
                {"op": "OR", "children": [
                    {"op": "PHRASE", "phrase": "ovarian reserve"},
                    {"op": "PHRASE", "phrase": "poor ovarian response"},
                ]},
            ]
        },
        expected_output="candidate_pointer_set",
        gate_scope="scientific_novelty",
        blocking_role="essential",
        essential=True,
    ))
    # A6: measurement — phrase + field
    sos.append(SearchOrder(
        search_order_id="SO-A6-01",
        axis_id="A6",
        operation_type="fielded_search",
        required_capabilities=["search.query", "search.fielded_query", "result.ranked"],
        query_representation={
            "op": "AND", "children": [
                {"op": "OR", "children": [
                    {"op": "FIELD", "field": "TI", "value": "oxygen-sensitive microelectrode"},
                    {"op": "PHRASE", "phrase": "phosphorescence quenching"},
                    {"op": "PHRASE", "phrase": "EPR oximetry"},
                ]},
                {"op": "OR", "children": [
                    {"op": "PHRASE", "phrase": "ovary"},
                    {"op": "PHRASE", "phrase": "follicle"},
                ]},
            ]
        },
        expected_output="candidate_pointer_set",
        gate_scope="scientific_novelty",
        blocking_role="essential",
        essential=True,
    ))
    # A7: decoding (the axis that v0.3 missed)
    sos.append(SearchOrder(
        search_order_id="SO-A7-01",
        axis_id="A7",
        operation_type="discovery_search",
        required_capabilities=["search.query", "search.pagination", "result.ranked"],
        query_representation={
            "op": "AND", "children": [
                {"op": "OR", "children": [
                    {"op": "PHRASE", "phrase": "PHD HIF"},
                    {"op": "PHRASE", "phrase": "ROS NRF2"},
                    {"op": "PHRASE", "phrase": "NF-kB"},
                ]},
                {"op": "OR", "children": [
                    {"op": "PHRASE", "phrase": "granulosa"},
                    {"op": "PHRASE", "phrase": "theca"},
                    {"op": "PHRASE", "phrase": "cumulus"},
                ]},
            ]
        },
        expected_output="candidate_pointer_set",
        gate_scope="scientific_novelty",
        blocking_role="essential",
        essential=True,
    ))
    # A8: adjacent organ prior art
    sos.append(SearchOrder(
        search_order_id="SO-A8-01",
        axis_id="A8",
        operation_type="discovery_search",
        required_capabilities=["search.query", "search.pagination", "result.ranked"],
        query_representation={
            "op": "OR", "children": [
                {"op": "PHRASE", "phrase": "tissue oxygen transfer function"},
                {"op": "PHRASE", "phrase": "oxygen compartment model"},
                {"op": "PHRASE", "phrase": "organ oxygen impulse response"},
            ]
        },
        expected_output="candidate_pointer_set",
        gate_scope="scientific_novelty",
        blocking_role="essential",
        essential=True,
    ))
    # A9: counterexample
    sos.append(SearchOrder(
        search_order_id="SO-A9-01",
        axis_id="A9",
        operation_type="discovery_search",
        required_capabilities=["search.query", "search.pagination"],
        query_representation={
            "op": "AND", "children": [
                {"op": "PHRASE", "phrase": "ovarian hyperoxia"},
                {"op": "PHRASE", "phrase": "primordial follicle activation"},
            ]
        },
        expected_output="candidate_pointer_set",
        gate_scope="scientific_novelty",
        blocking_role="essential",
        essential=True,
    ))
    # A10: translation (supplementary, allowed to fail without blocking scientific gate)
    sos.append(SearchOrder(
        search_order_id="SO-A10-01",
        axis_id="A10",
        operation_type="discovery_search",
        required_capabilities=["search.query", "search.pagination"],
        query_representation={
            "op": "OR", "children": [
                {"op": "PHRASE", "phrase": "ovarian oxygen clinical trial"},
                {"op": "PHRASE", "phrase": "HBOT fertility clinical trial"},
            ]
        },
        expected_output="candidate_pointer_set",
        gate_scope="translation",
        blocking_role="supplementary",
        essential=True,
    ))
    return sos


def build_providers() -> list[ProviderManifest]:
    """A mock provider that exposes the capabilities the positive demo needs."""
    return [
        ProviderManifest(
            name="pubmed_mock_v1",
            version="3.0.0-p0",
            capabilities=[
                "search.query",
                "search.fielded_query",
                "search.pagination",
                "result.ranked",
            ],
            network_requirement="offline",   # P0 only proves planning; live is P1
            trust_class="synthetic_test",
        ),
    ]


def build_resolvers() -> list[ResolverManifest]:
    return [
        ResolverManifest(
            name="crossref_mock_v1",
            version="3.0.0-p0",
            capabilities=["resolve.doi", "resolve.pmid", "metadata.snapshot"],
            trust_class="synthetic_test",
        ),
    ]


def _build_run_objects(target_freeze_path: Path) -> dict:
    """Compile + axes + SOs + providers + resolvers + budget + fingerprint.

    This is the shared data used by both the positive and negative demos.
    """
    compiled = compile_target(target_freeze_path)
    axes = build_axes()
    sos = build_search_orders()
    providers = build_providers()
    resolvers = build_resolvers()
    budget = standard_p0_budget()
    fingerprint = build_fingerprint(providers, resolvers)
    return {
        "compiled_target": compiled,
        "axes": axes,
        "search_orders": sos,
        "providers": providers,
        "resolvers": resolvers,
        "budget": budget,
        "fingerprint": fingerprint,
    }


def _compile_all_queries(sos: list[SearchOrder]) -> list[dict]:
    out: list[dict] = []
    compiler = PubMedEbscoCompiler()
    for so in sos:
        ast = so.query_representation
        try:
            cq = compile_for_demo(ast)
        except Exception as e:
            cq = {
                "schema_version": "3.0-p0",
                "query_ast_sha256": "",
                "backend": compiler.backend,
                "rendered_query": "",
                "compiler_name": compiler.compiler_name,
                "compiler_version": compiler.compiler_version,
                "validation_status": "rejected",
                "rejection_reason": str(e),
            }
        out.append(cq)
    return out


def run_positive_demo(tf_path: Path | None = None, out_path: Path | None = None) -> dict:
    tf_path = _resolve_tf_path(tf_path)
    objs = _build_run_objects(tf_path)
    compiled = objs["compiled_target"]
    axes = objs["axes"]
    sos = objs["search_orders"]
    providers = objs["providers"]
    resolvers = objs["resolvers"]
    budget = objs["budget"]
    fingerprint = objs["fingerprint"]

    negotiations = negotiate_all(sos, providers)
    compiled_queries = _compile_all_queries(sos)
    gate_graph = build_default_graph(axes)
    report = run_preflight(
        compiled_target=compiled,
        axes=axes,
        search_orders=sos,
        providers=providers,
        negotiations=negotiations,
        compiled_queries=compiled_queries,
        gate_graph=gate_graph,
        runtime_fingerprint=fingerprint,
        budget_state=budget.to_dict(),
        target_freeze_path=tf_path,
    )

    run_manifest = {
        "schema_version": "3.0-p0",
        "run_id": "P0-DEMO-POSITIVE",
        "target_freeze_sha256": compiled["source_sha256"],
        "compiled_target_sha256": sha256_json(compiled),
        "search_order_count": len(sos),
        "axes_count": len(axes),
        "provider_count": len(providers),
        "fingerprint_sha256": fingerprint_self_sha256(fingerprint),
        "preflight_status": report.status,
        "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "notes": "positive demo: 10 axes, 10 SearchOrders (incl. A7), pubmed_mock_v1, PubMed ESearch compiler",
    }

    out = {
        "run_manifest": run_manifest,
        "compiled_target": compiled,
        "axes": [a.to_dict() for a in axes],
        "search_orders": [so.to_dict() for so in sos],
        "providers": [p.to_dict() for p in providers],
        "resolvers": [r.to_dict() for r in resolvers],
        "negotiations": [n.__dict__ for n in negotiations],
        "compiled_queries": compiled_queries,
        "gate_graph": gate_graph.to_dict(),
        "budget": budget.to_dict(),
        "runtime_fingerprint": fingerprint,
        "preflight": report.to_dict(),
    }
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def run_negative_demo(tf_path: Path | None = None, out_path: Path | None = None) -> dict:
    """Negative demo: provider manifest is INTENTIONALLY truncated (no search.pagination),
    so capability negotiation fails for any SO that requires it. Result: PLANNING_BLOCKED
    with a concrete blocker.
    """
    tf_path = _resolve_tf_path(tf_path)
    objs = _build_run_objects(tf_path)
    compiled = objs["compiled_target"]
    axes = objs["axes"]
    sos = objs["search_orders"]
    budget = objs["budget"]
    fingerprint = objs["fingerprint"]

    # Truncated provider
    weak_provider = ProviderManifest(
        name="pubmed_mock_weak_v1",
        version="3.0.0-p0",
        capabilities=["search.query"],   # no pagination, no ranking
        network_requirement="offline",
        trust_class="synthetic_test",
    )
    providers = [weak_provider]
    resolvers = objs["resolvers"]
    negotiations = negotiate_all(sos, providers)
    compiled_queries = _compile_all_queries(sos)
    gate_graph = build_default_graph(axes)
    report = run_preflight(
        compiled_target=compiled,
        axes=axes,
        search_orders=sos,
        providers=providers,
        negotiations=negotiations,
        compiled_queries=compiled_queries,
        gate_graph=gate_graph,
        runtime_fingerprint=fingerprint,
        budget_state=budget.to_dict(),
        target_freeze_path=tf_path,
    )

    run_manifest = {
        "schema_version": "3.0-p0",
        "run_id": "P0-DEMO-NEGATIVE",
        "target_freeze_sha256": compiled["source_sha256"],
        "compiled_target_sha256": sha256_json(compiled),
        "search_order_count": len(sos),
        "axes_count": len(axes),
        "provider_count": len(providers),
        "fingerprint_sha256": fingerprint_self_sha256(fingerprint),
        "preflight_status": report.status,
        "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "notes": "negative demo: provider is intentionally truncated (no search.pagination) -> PLANNING_BLOCKED",
    }

    out = {
        "run_manifest": run_manifest,
        "compiled_target": compiled,
        "axes": [a.to_dict() for a in axes],
        "search_orders": [so.to_dict() for so in sos],
        "providers": [p.to_dict() for p in providers],
        "resolvers": [r.to_dict() for r in resolvers],
        "negotiations": [n.__dict__ for n in negotiations],
        "compiled_queries": compiled_queries,
        "gate_graph": gate_graph.to_dict(),
        "budget": budget.to_dict(),
        "runtime_fingerprint": fingerprint,
        "preflight": report.to_dict(),
    }
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
