"""Deterministic development and installed-release path resolution.

The runtime has two explicit layouts.  A development checkout is identified
by its project metadata and ``src/mafs_p0`` tree.  An installed release is
identified by release manifests plus ``runtime/mafs_p0``.  Installed code
never needs Git metadata, a working directory, or a fake ``pyproject.toml``.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


DEV_MODE = "DEV_MODE"
INSTALLED_RELEASE = "INSTALLED_RELEASE"


class RuntimeTopologyError(FileNotFoundError):
    """Raised when the product layout is absent or a path is mode-inapplicable."""


@dataclass(frozen=True)
class RuntimeTopology:
    mode: str
    product_root: Path
    runtime_root: Path
    schemas_root: Path
    manifests_root: Path | None
    dependencies_root: Path | None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "execution_mode": self.mode,
            "product_root": str(self.product_root),
            "runtime_root": str(self.runtime_root),
            "schemas_root": str(self.schemas_root),
            "manifests_root": str(self.manifests_root) if self.manifests_root else None,
            "dependencies_root": str(self.dependencies_root) if self.dependencies_root else None,
        }


def _valid_release_root(root: Path) -> bool:
    product = root / "manifests" / "PRODUCT_VERSION.json"
    release = root / "manifests" / "RELEASE_MANIFEST.json"
    runtime = root / "runtime" / "mafs_p0"
    schemas = root / "schemas"
    if not (product.is_file() and release.is_file() and runtime.is_dir() and schemas.is_dir()):
        return False
    try:
        product_data = json.loads(product.read_text(encoding="utf-8"))
        release_data = json.loads(release.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    return (
        product_data.get("product_name") == "MAFS Skill"
        and product_data.get("release_artifact_version")
        == release_data.get("release_artifact_version")
    )


def _valid_dev_root(root: Path) -> bool:
    return (
        (root / "pyproject.toml").is_file()
        and (root / "src" / "mafs_p0").is_dir()
        and (root / "schemas").is_dir()
    )


def detect_runtime_topology(start: Path | None = None) -> RuntimeTopology:
    """Detect an explicit product topology from a module path or test start."""

    current = (start or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent
    for _ in range(10):
        if _valid_release_root(current):
            return RuntimeTopology(
                mode=INSTALLED_RELEASE,
                product_root=current,
                runtime_root=current / "runtime",
                schemas_root=current / "schemas",
                manifests_root=current / "manifests",
                dependencies_root=current / "dependencies",
            )
        if _valid_dev_root(current):
            return RuntimeTopology(
                mode=DEV_MODE,
                product_root=current,
                runtime_root=current / "src",
                schemas_root=current / "schemas",
                manifests_root=None,
                dependencies_root=None,
            )
        parent = current.parent
        if parent == current:
            break
        current = parent
    raise RuntimeTopologyError(
        "cannot locate a MAFS development or installed-release product root "
        f"walking from {start or Path(__file__)}"
    )


_TOPOLOGY = detect_runtime_topology()


def execution_mode() -> str:
    return _TOPOLOGY.mode


def topology() -> RuntimeTopology:
    return _TOPOLOGY


def product_root() -> Path:
    return _TOPOLOGY.product_root


def package_root() -> Path:
    """Backward-compatible alias for the product root."""

    return product_root()


def runtime_root() -> Path:
    return _TOPOLOGY.runtime_root


def src_dir() -> Path:
    """Return the active Python runtime root in either supported layout."""

    return runtime_root()


def schemas_root() -> Path:
    path = _TOPOLOGY.schemas_root
    if not path.is_dir() or not any(path.glob("*.schema.json")):
        raise RuntimeTopologyError(f"schemas root is invalid: {path}")
    return path


def schemas_dir() -> Path:
    """Backward-compatible alias for ``schemas_root``."""

    return schemas_root()


def manifests_root() -> Path:
    path = _TOPOLOGY.manifests_root
    if path is None or not path.is_dir():
        raise RuntimeTopologyError("manifests_root is available only in installed release mode")
    return path


def dependencies_root() -> Path:
    path = _TOPOLOGY.dependencies_root
    if path is None or not path.is_dir():
        raise RuntimeTopologyError("dependencies_root is available only in installed release mode")
    return path


def _dev_only(name: str, relative: str) -> Path:
    if _TOPOLOGY.mode != DEV_MODE:
        raise RuntimeTopologyError(f"{name} is DEV_ONLY and unavailable in installed release mode")
    path = _TOPOLOGY.product_root / relative
    if not path.is_dir():
        raise RuntimeTopologyError(f"{name} missing: {path}")
    return path


def tests_dir() -> Path:
    return _dev_only("tests_dir", "tests")


def examples_dir() -> Path:
    return _dev_only("examples_dir", "examples")


def fixtures_dir() -> Path:
    return _dev_only("fixtures_dir", "examples/fixtures")


def docs_dir() -> Path:
    return _dev_only("docs_dir", "docs")


def scripts_dir() -> Path:
    return _dev_only("scripts_dir", "scripts")
