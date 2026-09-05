from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_package_b_demo_cli_writes_positive_and_negative_flows(tmp_path: Path):
    output = tmp_path / "package_b_demo"
    completed = subprocess.run(
        [sys.executable, "scripts/run_package_b_vertical_slice.py", "--output", str(output)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    summary = json.loads((output / "demo_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["m5_accepted"] is False
    assert (output / "positive" / "landscape.json").is_file()
    negative = json.loads((output / "negative" / "collision.json").read_text(encoding="utf-8"))
    assert negative["collision_type"] == "INSUFFICIENT_EVIDENCE"

