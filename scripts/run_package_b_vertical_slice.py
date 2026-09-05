"""Write the hermetic Package B positive and negative development demos."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

# Permit direct execution from a clean checkout without an editable install.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from mafs_p0.package_b_demo import build_negative_demo, build_positive_demo


def _json_value(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


def _write_flow(root: Path, name: str, artifacts: dict[str, Any]) -> None:
    flow = root / name
    flow.mkdir(parents=True, exist_ok=True)
    for key, value in artifacts.items():
        (flow / f"{key}.json").write_text(
            json.dumps(_json_value(value), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/post_p1p5/package_b/B_VERTICAL_SLICE_DEMO"),
    )
    args = parser.parse_args()
    _write_flow(args.output, "positive", build_positive_demo())
    _write_flow(args.output, "negative", build_negative_demo())
    summary = {
        "status": "PASS",
        "positive_flow": "grounded collision -> RS-002 -> authorized re-digestion -> ER-102 -> RS-003 -> ELP",
        "negative_flow": "not-addressed evidence -> insufficient evidence -> unresolved state -> valid ELP",
        "m5_accepted": False,
        "production_migration_authorized": False,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "demo_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
