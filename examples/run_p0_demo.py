"""Run the P0 positive + negative demos and emit the run JSON to examples/runs/.

Usage:
    python examples/run_p0_demo.py

Required env var: MAFS_P0_TF_PATH must point to the source Target Freeze artifact.
The source is NEVER modified.
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

_PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PKG / "src"))

from mafs_p0.demo import run_positive_demo, run_negative_demo
from mafs_p0.validator import validate_run


def main() -> int:
    tf_path = os.environ.get("MAFS_P0_TF_PATH")
    if not tf_path:
        print("ERROR: MAFS_P0_TF_PATH environment variable is not set.")
        print("Set it to the absolute path of the source Target Freeze artifact,")
        print("for example:")
        print('  $env:MAFS_P0_TF_PATH = "C:\\path\\to\\target_freeze.md"')
        return 2
    tf_p = Path(tf_path)
    if not tf_p.is_file():
        print(f"ERROR: MAFS_P0_TF_PATH does not point to a file: {tf_p}")
        return 2

    out_dir = _PKG / "examples" / "runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    pos_path = out_dir / "positive_run.json"
    neg_path = out_dir / "negative_run.json"

    pos = run_positive_demo(tf_path=tf_p, out_path=pos_path)
    neg = run_negative_demo(tf_path=tf_p, out_path=neg_path)

    pos_verdict = validate_run(
        pos["run_manifest"],
        compiled_target=pos["compiled_target"],
        preflight_report=pos["preflight"],
        runtime_fingerprint=pos["runtime_fingerprint"],
        budget_state=pos["budget"],
        axis_records=pos["axes"],
        search_orders=pos["search_orders"],
        compiled_queries=pos["compiled_queries"],
    )
    neg_verdict = validate_run(
        neg["run_manifest"],
        compiled_target=neg["compiled_target"],
        preflight_report=neg["preflight"],
        runtime_fingerprint=neg["runtime_fingerprint"],
        budget_state=neg["budget"],
        axis_records=neg["axes"],
        search_orders=neg["search_orders"],
        compiled_queries=neg["compiled_queries"],
    )

    print("=== POSITIVE DEMO ===")
    print(f"  preflight_status: {pos['preflight']['status']}")
    print(f"  validators: ok={pos_verdict['ok']}")
    if not pos_verdict["ok"]:
        print(f"  schema_errors: {pos_verdict['schema_errors']}")
        print(f"  semantic_errors: {pos_verdict['semantic_errors']}")
    print(f"  written: {pos_path}")

    print("=== NEGATIVE DEMO ===")
    print(f"  preflight_status: {neg['preflight']['status']}")
    print(f"  validators: ok={neg_verdict['ok']}")
    if not neg_verdict["ok"]:
        print(f"  schema_errors: {neg_verdict['schema_errors']}")
        print(f"  semantic_errors: {neg_verdict['semantic_errors']}")
    print(f"  written: {neg_path}")

    # Acceptance: positive must be READY + validators ok; negative must be BLOCKED + validators ok.
    if pos["preflight"]["status"] != "READY_FOR_HO_EXECUTION_APPROVAL":
        print("FAIL: positive demo not READY")
        return 1
    if neg["preflight"]["status"] != "PLANNING_BLOCKED":
        print("FAIL: negative demo not BLOCKED")
        return 1
    if not pos_verdict["ok"]:
        print("FAIL: positive demo failed validation")
        return 1
    if not neg_verdict["ok"]:
        print("FAIL: negative demo failed validation")
        return 1
    print("OK: both demos passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
