from __future__ import annotations

import json
import importlib.util
from pathlib import Path


def _load_script():
    path = Path("scripts/run_package_a_vertical_slice.py")
    spec = importlib.util.spec_from_file_location("run_package_a_vertical_slice", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_demo_input_prepares_without_target_identity_leakage():
    module = _load_script()
    with open("examples/package_a_vertical_slice_input.json", encoding="utf-8") as handle:
        document = json.load(handle)
    prepared = module._prepare(document)
    assert prepared.route.origin_requirement_id == "SRP-DEMO-001"
    assert prepared.fidelity_review.execution_allowed is True
    assert prepared.portfolio.uncovered_obligations == ("SRP-DEMO-001",)
    assert prepared.search_order.compiled_query
    serialized = json.dumps(prepared.search_order.to_dict()).lower()
    assert "expected_doi" not in serialized
    assert "exact_target_title" not in serialized


def test_cli_has_no_one_shot_command():
    source = open("scripts/run_package_a_vertical_slice.py", encoding="utf-8").read()
    assert 'add_parser("discover")' in source
    assert 'add_parser("select-resolve")' in source
    assert 'add_parser("ground")' in source
    assert 'add_parser("run")' not in source
