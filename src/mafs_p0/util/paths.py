"""Package-relative path resolution. No hard-coded machine paths (P0 §2).

The package root is found by walking up from this file until ``pyproject.toml``
is encountered. This is robust against:
  * differences in how the package is laid out (src/ vs flat layout)
  * stale __pycache__ (which can mask the wrong number of .parent calls)
  * symlink resolution

Every helper that returns a subdirectory asserts that a known sentinel file
exists in that directory; otherwise it raises (P0 §16 risk test 2: missing
required object fails closed rather than silently).
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional


_SENTINEL = "pyproject.toml"


def _find_pkg_root(start: Path, sentinel: str = _SENTINEL) -> Path:
    cur: Path = start.resolve()
    for _ in range(8):  # bound the walk to avoid infinite loops on weird FS
        if (cur / sentinel).is_file():
            return cur
        parent = cur.parent
        if parent == cur:
            raise FileNotFoundError(
                f"cannot locate package root (sentinel '{sentinel}') "
                f"walking up from {start}"
            )
        cur = parent
    raise FileNotFoundError(
        f"walked 8 levels from {start} without finding sentinel '{sentinel}'"
    )


# This file is at <pkg_root>/src/mafs_p0/util/paths.py — sentinel-walk gives pkg_root.
_PKG_ROOT: Path = _find_pkg_root(Path(__file__))


def package_root() -> Path:
    if not (_PKG_ROOT / _SENTINEL).is_file():
        raise FileNotFoundError(
            f"package_root sentinel missing: {_PKG_ROOT / _SENTINEL}"
        )
    return _PKG_ROOT


def src_dir() -> Path:
    p = _PKG_ROOT / "src"
    if not p.is_dir():
        raise FileNotFoundError(f"src_dir missing: {p}")
    return p


def schemas_dir() -> Path:
    p = _PKG_ROOT / "schemas"
    if not p.is_dir():
        raise FileNotFoundError(f"schemas_dir missing: {p}")
    if not any(p.glob("*.schema.json")):
        raise FileNotFoundError(f"schemas_dir has no .schema.json files: {p}")
    return p


def tests_dir() -> Path:
    p = _PKG_ROOT / "tests"
    if not p.is_dir():
        raise FileNotFoundError(f"tests_dir missing: {p}")
    return p


def examples_dir() -> Path:
    p = _PKG_ROOT / "examples"
    if not p.is_dir():
        raise FileNotFoundError(f"examples_dir missing: {p}")
    return p


def fixtures_dir() -> Path:
    p = _PKG_ROOT / "examples" / "fixtures"
    if not p.is_dir():
        raise FileNotFoundError(f"fixtures_dir missing: {p}")
    return p


def docs_dir() -> Path:
    p = _PKG_ROOT / "docs"
    if not p.is_dir():
        raise FileNotFoundError(f"docs_dir missing: {p}")
    return p


def scripts_dir() -> Path:
    p = _PKG_ROOT / "scripts"
    if not p.is_dir():
        raise FileNotFoundError(f"scripts_dir missing: {p}")
    return p
