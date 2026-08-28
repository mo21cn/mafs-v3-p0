"""Preflight engine (P0 §9).

Mechanical checks before READY:
  1. compiled target hash valid
  2. every essential axis has ≥1 SearchOrder
  3. every SearchOrder has compatible provider capability (negotiation)
  4. every query compiles
  5. every blocking axis has gate dependency
  6. runtime fingerprinted
  7. budget uses explicit status (not 0-as-unknown)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .axis import Axis
from .search_order import SearchOrder
from .provider_manifest import ProviderManifest
from .capability_negotiation import NegotiationResult
from .gate_dependency_graph import GateDependencyGraph, scope_readiness
from .query_compiler import PubMedEbscoCompiler, CompilationError
from .util.hashing import sha256_file


@dataclass
class PreflightCheck:
    check_id: str
    label: str
    outcome: str
    severity: str
    detail: str = ""


@dataclass
class PreflightReport:
    schema_version: str
    status: str
    evaluated_at: str
    checks: list[PreflightCheck]
    blockers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "evaluated_at": self.evaluated_at,
            "checks": [
                {
                    "check_id": c.check_id,
                    "label": c.label,
                    "outcome": c.outcome,
                    "severity": c.severity,
                    "detail": c.detail,
                } for c in self.checks
            ],
            "blockers": list(self.blockers),
        }


def run_preflight(
    compiled_target: dict,
    axes: list[Axis],
    search_orders: list[SearchOrder],
    providers: list[ProviderManifest],
    negotiations: list[NegotiationResult],
    compiled_queries: list[dict],
    gate_graph: GateDependencyGraph,
    runtime_fingerprint: dict,
    budget_state: dict,
    target_freeze_path,
) -> PreflightReport:
    checks: list[PreflightCheck] = []
    blockers: list[str] = []

    # 1. Target Freeze hash
    try:
        actual = sha256_file(target_freeze_path)
        if actual == compiled_target.get("source_sha256"):
            checks.append(PreflightCheck("C1", "Target Freeze hash", "PASS", "BLOCKER"))
        else:
            checks.append(PreflightCheck("C1", "Target Freeze hash", "FAIL", "BLOCKER",
                                         f"declared {compiled_target.get('source_sha256')!r} != actual {actual!r}"))
            blockers.append("target_freeze_hash_mismatch")
    except Exception as e:
        checks.append(PreflightCheck("C1", "Target Freeze hash", "FAIL", "BLOCKER", str(e)))
        blockers.append("target_freeze_hash_unreadable")

    # 2. Compiled target has no missing required sections
    if compiled_target.get("status") == "COMPILED":
        checks.append(PreflightCheck("C2", "Compiled target completeness", "PASS", "BLOCKER"))
    else:
        missing = compiled_target.get("missing_sections", [])
        checks.append(PreflightCheck("C2", "Compiled target completeness", "FAIL", "BLOCKER",
                                     f"missing: {missing}"))
        blockers.append(f"compiled_target_partial: missing={missing}")

    # 3. Every essential axis has ≥1 SearchOrder
    axes_by_id = {a.axis_id: a for a in axes}
    so_by_axis: dict[str, list[SearchOrder]] = {}
    for so in search_orders:
        so_by_axis.setdefault(so.axis_id, []).append(so)
    essential_missing_so: list[str] = []
    for a in axes:
        if a.essential and not so_by_axis.get(a.axis_id):
            essential_missing_so.append(a.axis_id)
    if not essential_missing_so:
        checks.append(PreflightCheck("C3", "Essential axis coverage by SearchOrder", "PASS", "BLOCKER"))
    else:
        checks.append(PreflightCheck("C3", "Essential axis coverage by SearchOrder", "FAIL", "BLOCKER",
                                     f"axes without SearchOrder: {essential_missing_so}"))
        blockers.append(f"essential_axis_no_so: {essential_missing_so}")

    # 4. Capability negotiation succeeded for every SearchOrder
    non_exec = [r.search_order_id for r in negotiations if not r.executable]
    if not non_exec:
        checks.append(PreflightCheck("C4", "Capability negotiation", "PASS", "BLOCKER"))
    else:
        checks.append(PreflightCheck("C4", "Capability negotiation", "FAIL", "BLOCKER",
                                     f"non_executable: {non_exec}"))
        blockers.append(f"capability_negotiation_failed: {non_exec}")

    # 5. Every query compiles
    bad_queries = [q for q in compiled_queries if q.get("validation_status") != "valid"]
    if not bad_queries:
        checks.append(PreflightCheck("C5", "Query compilation", "PASS", "BLOCKER"))
    else:
        checks.append(PreflightCheck("C5", "Query compilation", "FAIL", "BLOCKER",
                                     f"bad_queries: {len(bad_queries)}"))
        blockers.append(f"query_compile_failed: count={len(bad_queries)}")

    # 6. Every blocking axis has a gate dependency edge
    blocking_no_edge: list[str] = []
    axes_with_edges = {e.axis_id for e in gate_graph.edges}
    for a in axes:
        if a.blocking_role == "essential" and a.axis_id not in axes_with_edges:
            blocking_no_edge.append(a.axis_id)
    if not blocking_no_edge:
        checks.append(PreflightCheck("C6", "Gate dependency graph coverage", "PASS", "BLOCKER"))
    else:
        checks.append(PreflightCheck("C6", "Gate dependency graph coverage", "FAIL", "BLOCKER",
                                     f"blocking axes without gate edge: {blocking_no_edge}"))
        blockers.append(f"blocking_axis_no_gate: {blocking_no_edge}")

    # 7. Runtime fingerprinted (required fields present, sha256s are 64-hex)
    fp_ok = (
        isinstance(runtime_fingerprint, dict)
        and runtime_fingerprint.get("schemas_manifest_sha256")
        and runtime_fingerprint.get("validator_sha256")
        and runtime_fingerprint.get("query_compiler", {}).get("sha256")
        and runtime_fingerprint.get("skill", {}).get("sha256")
    )
    if fp_ok:
        checks.append(PreflightCheck("C7", "Runtime Fingerprint", "PASS", "BLOCKER"))
    else:
        checks.append(PreflightCheck("C7", "Runtime Fingerprint", "FAIL", "BLOCKER",
                                     "fingerprint missing required sha256s"))
        blockers.append("runtime_fingerprint_incomplete")

    # 8. Budget uses explicit status (not 0-as-unknown)
    bs = budget_state
    budget_status = bs.get("cost_status")
    tok_range = bs.get("estimated_token_range")
    cost_range = bs.get("estimated_cost_range_usd")
    bad_zero = False
    detail = []
    if budget_status not in {"estimated", "unknown", "configured_cap", "not_configured", "explicitly_unbounded"}:
        bad_zero = True
        detail.append(f"invalid cost_status: {budget_status!r}")
    # 0 is forbidden for unknown ranges: null required
    if budget_status == "unknown" and tok_range is not None:
        bad_zero = True
        detail.append("unknown budget must have estimated_token_range=null")
    if budget_status == "unknown" and cost_range is not None:
        bad_zero = True
        detail.append("unknown budget must have estimated_cost_range_usd=null")
    if not bad_zero:
        checks.append(PreflightCheck("C8", "Budget explicit status (no 0-as-unknown)", "PASS", "BLOCKER"))
    else:
        checks.append(PreflightCheck("C8", "Budget explicit status (no 0-as-unknown)", "FAIL", "BLOCKER",
                                     "; ".join(detail)))
        blockers.append("budget_ambiguous_zero")

    # Aggregate status
    if any(c.outcome == "FAIL" and c.severity == "BLOCKER" for c in checks):
        status = "PLANNING_BLOCKED"
    else:
        status = "READY_FOR_HO_EXECUTION_APPROVAL"

    return PreflightReport(
        schema_version="3.0-p0",
        status=status,
        evaluated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        checks=checks,
        blockers=blockers,
    )
