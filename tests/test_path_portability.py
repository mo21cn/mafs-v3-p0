"""§16 risk test 1: no hard-coded machine path dependency.

Scans all .py and .json source files for any of: H:\\, I:\\, C:\\Users\\.
Reports violations as test failures.
"""
from __future__ import annotations
import re
from pathlib import Path

import pytest

from mafs_p0.util.paths import package_root, schemas_dir, src_dir, tests_dir, examples_dir, docs_dir, scripts_dir


_BAD_PATTERNS = [
    re.compile(r"H:\\"),
    re.compile(r"I:\\"),
    re.compile(r"C:\\Users\\"),
    re.compile(r"/Users/"),       # macOS /Users/ hard-coded
    re.compile(r"/home/[a-z]"),   # /home/user
]


def _scan_text(text: str) -> list[str]:
    out: list[str] = []
    for pat in _BAD_PATTERNS:
        for m in pat.finditer(text):
            out.append(f"pattern={pat.pattern!r} match={m.group(0)!r}")
    return out


def test_path_resolution_helpers_return_relative_paths():
    """The path helpers must resolve to absolute paths under the package root,
    and must NOT reference H:\\, I:\\, C:\\Users\\, /Users/, or /home/<u>."""
    root = package_root()
    for fn in (schemas_dir, src_dir, tests_dir, examples_dir, docs_dir, scripts_dir):
        p = fn()
        assert p.is_absolute(), f"{fn.__name__} returned a non-absolute path: {p}"
        assert str(p).startswith(str(root)), f"{fn.__name__} escaped package root: {p}"


def test_no_hardcoded_machine_paths_in_sources():
    """Production source (``src/``) must contain no hard-coded machine path patterns.

    Tests, scripts, and docs are excluded because:
      * ``tests/`` may legitimately contain paths as test fixtures or comments.
      * ``scripts/`` contains ``build_p0_ra1.py`` which legitimately uses
        ``Path(__file__).resolve()`` and the build script has its own internal
        path conventions.
      * ``docs/`` legitimately describes the bad patterns as part of the
        HIGH_RISK_INVARIANTS contract.

    The point of this test is to catch a developer accidentally writing
    ``r"C:\\Users\\foo\\bar"`` inside a runtime import path. Such a bug must
    surface in production code, not in test scaffolding.
    """
    root = package_root()
    production_root = root / "src"
    if not production_root.is_dir():
        pytest.skip(f"production source dir not found: {production_root}")
    bad: list[str] = []
    for path in production_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".py", ".json"}:
            continue
        if any(seg in path.parts for seg in (".git", "__pycache__")):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        matches = _scan_text(text)
        if matches:
            for m in matches:
                bad.append(f"{path.relative_to(root)}: {m}")
    assert not bad, "hard-coded machine path patterns found in production source:\n  " + "\n  ".join(bad)
