"""§16 risk test 12: non-executable plan cannot return READY.

If preflight identifies any BLOCKER-severity check failure, the overall status
must be PLANNING_BLOCKED. The semantic validator cross-checks this invariant.
"""
from __future__ import annotations
from mafs_p0.demo import run_positive_demo, run_negative_demo
from mafs_p0.validator import validate_run


def test_positive_demo_ready():
    out = run_positive_demo()
    assert out["preflight"]["status"] == "READY_FOR_HO_EXECUTION_APPROVAL"


def test_negative_demo_blocked():
    out = run_negative_demo()
    assert out["preflight"]["status"] == "PLANNING_BLOCKED"
    # And at least one BLOCKER check failed
    failed_blockers = [c for c in out["preflight"]["checks"] if c["outcome"] == "FAIL" and c["severity"] == "BLOCKER"]
    assert len(failed_blockers) >= 1


def test_validator_catches_ready_with_blockers_invariant():
    # Manually construct a preflight that says READY but has a failing BLOCKER check.
    # The semantic validator must flag it.
    bogus_preflight = {
        "schema_version": "3.0-p0",
        "status": "READY_FOR_HO_EXECUTION_APPROVAL",
        "evaluated_at": "2026-08-28T00:00:00Z",
        "checks": [
            {"check_id": "C4", "label": "capability", "outcome": "FAIL", "severity": "BLOCKER", "detail": "forced failure"},
        ],
        "blockers": [],
    }
    run_manifest = {
        "schema_version": "3.0-p0",
        "run_id": "P0-DEMO-POSITIVE",
        "target_freeze_sha256": "a" * 64,
        "compiled_target_sha256": "b" * 64,
        "search_order_count": 1,
        "axes_count": 1,
        "provider_count": 1,
        "fingerprint_sha256": "c" * 64,
        "preflight_status": "READY_FOR_HO_EXECUTION_APPROVAL",
        "started_at": "2026-08-28T00:00:00Z",
    }
    out = run_positive_demo()
    verdict = validate_run(
        run_manifest,
        compiled_target=out["compiled_target"],
        preflight_report=bogus_preflight,
        runtime_fingerprint=out["runtime_fingerprint"],
        budget_state=out["budget"],
        axis_records=out["axes"],
        search_orders=out["search_orders"],
        compiled_queries=out["compiled_queries"],
    )
    # The validator's semantic check #12 ("non-executable plan cannot return READY")
    # triggers when status=READY but a BLOCKER check is FAIL.
    # We expect semantic_errors to include "ready_with_blocker_check".
    assert any("ready_with_blocker_check" in e for e in verdict["semantic_errors"]), verdict
