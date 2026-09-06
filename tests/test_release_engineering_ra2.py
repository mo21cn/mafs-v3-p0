"""RA2 portable-runtime topology and installed-artifact closure tests."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts" / "build_mafs_skill_1_1_rc1.py"
OPS_PATH = ROOT / "release" / "mafs_skill_1_1_rc1" / "lib" / "release_ops.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


builder = load(BUILDER_PATH, "mafs_ra2_builder")
ops = load(OPS_PATH, "mafs_ra2_ops")


@pytest.fixture()
def cqc_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "cqc"
    for rel in builder.CQC_ALLOWLIST:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        source = ROOT.parent / "mafs-cqc-package-c-readonly" / rel
        if source.is_file():
            shutil.copy2(source, target)
        elif rel.endswith("adapter.py"):
            target.write_text("CQC_RUNTIME_FIXTURE = True\n", encoding="utf-8")
        elif rel.endswith(".json"):
            target.write_text("{}\n", encoding="utf-8")
        else:
            target.write_text("# test fixture\n", encoding="utf-8")
    return root


@pytest.fixture()
def package(tmp_path: Path, cqc_fixture: Path) -> Path:
    output = tmp_path / "build"
    builder.build_release(
        output,
        cqc_fixture,
        "2" * 40,
        "2026-09-06T00:00:00Z",
        verify_cqc=False,
    )
    return output / builder.PRODUCT_DIR


def refresh_manifest(root: Path) -> None:
    manifest = root / "manifests" / "SHA256_MANIFEST.txt"
    rows = [
        f"{ops.sha256(path)}  {path.relative_to(root).as_posix()}"
        for path in sorted(p for p in root.rglob("*") if p.is_file() and p != manifest)
    ]
    manifest.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")


def run_ops(package: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    return subprocess.run(
        [sys.executable, str(package / "lib" / "release_ops.py"), *args],
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
    )


def test_installed_rc_critical_import_closure(package: Path):
    payload, errors = ops.installed_runtime_probe(package)
    assert errors == []
    matrix = payload["critical_import_matrix"]
    assert len(matrix) == len(ops.CRITICAL_MODULES)
    assert all(item["installed_import_status"] == "PASS" for item in matrix)
    assert all(item["execution_origin"] == "INSTALLED_RC" for item in matrix)
    assert all(Path(item["resolved_file"]).is_relative_to(package / "runtime") for item in matrix)


def test_installed_package_c_consumer_constructs_binding(package: Path):
    payload, errors = ops.installed_runtime_probe(package)
    assert errors == []
    probe = payload["package_c_functional_probe"]
    assert probe["status"] == "PASS"
    assert probe["consumer_binding_constructed"] is True
    assert probe["requirement_count"] >= 1
    assert probe["search_performed"] is False


def test_installed_preflight_uses_release_topology(package: Path):
    payload, errors = ops.installed_runtime_probe(package)
    assert errors == []
    topology = payload["runtime_topology"]
    assert topology["execution_mode"] == "INSTALLED_RELEASE"
    assert Path(topology["product_root"]) == package.resolve()
    preflight = next(item for item in payload["critical_import_matrix"] if item["module"] == "mafs_p0.preflight")
    assert Path(preflight["resolved_file"]).is_relative_to(package / "runtime")


def test_installed_validator_resolves_release_schemas(package: Path):
    payload, errors = ops.installed_runtime_probe(package)
    assert errors == []
    assert payload["package_c_functional_probe"]["schema_errors"] == []
    assert Path(payload["runtime_topology"]["schemas_root"]) == (package / "schemas").resolve()


def test_installed_runtime_fingerprint_builds(package: Path):
    payload, errors = ops.installed_runtime_probe(package)
    assert errors == []
    fingerprint = payload["runtime_fingerprint"]
    assert fingerprint["status"] == "PASS"
    assert fingerprint["execution_mode"] == "INSTALLED_RELEASE"
    assert fingerprint["release_evaluated_source_sha"] == "2" * 40
    assert fingerprint["c1_accepted_sha"] == builder.C1_SHA
    assert fingerprint["cqc_source_sha"] == builder.CQC_SHA


def test_release_doctor_blocks_on_critical_import_failure(package: Path):
    (package / "runtime" / "mafs_p0" / "cqc_integration.py").unlink()
    refresh_manifest(package)
    result = run_ops(
        package,
        "doctor",
        "--install-path",
        str(package),
        "--provider-network-status",
        "offline",
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload["status"] == "BLOCKED"
    assert any("CRITICAL_IMPORT_BLOCKED:mafs_p0.cqc_integration" in item for item in payload["errors"])


def test_release_doctor_passes_installed_functional_probe(package: Path):
    result = run_ops(
        package,
        "doctor",
        "--install-path",
        str(package),
        "--provider-network-status",
        "online",
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload["status"] == "READY"
    assert payload["checks"]["critical_runtime_imports"]["failed"] == 0
    assert payload["checks"]["package_c_functional_probe"]["status"] == "PASS"


def test_release_doctor_is_ready_offline_with_network_degraded(package: Path):
    result = run_ops(
        package,
        "doctor",
        "--install-path",
        str(package),
        "--provider-network-status",
        "offline",
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload["status"] == "READY"
    assert payload["checks"]["provider_network_status"] == "DEGRADED"
    assert "PROVIDER_NETWORK_NOT_CONFIRMED" in payload["warnings"]


def test_canonical_release_smoke_reaches_stop_from_installed_rc(package: Path, tmp_path: Path):
    output = tmp_path / "smoke.json"
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(package / "examples" / "canonical_release_smoke.py"),
            "--output",
            str(output),
            "--discovery-mode",
            "hermetic",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=180,
        env={key: value for key, value in os.environ.items() if key not in {"PYTHONPATH", "PYTHONHOME"}},
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert payload["status"] == "PASS_STOP_REACHED"
    assert payload["execution_origin"] == "INSTALLED_RC"
    assert payload["cqc_handoff_status"] == "INTEGRATION_ACCEPTED"
    assert payload["mafs_requirement_constructed"] is True
    assert payload["route_constructed"] is True
    assert payload["candidate_count"] >= 1
    assert payload["stop_status"] == "STOP_AWAITING_SELECTION_ARTIFACT"
    assert payload["selection_performed"] is False
    assert payload["resolve_performed"] is False


def test_installed_release_needs_no_pyproject_or_repo_source(package: Path, tmp_path: Path):
    isolated = tmp_path / "portable-only" / builder.PRODUCT_DIR
    isolated.parent.mkdir(parents=True)
    shutil.copytree(package, isolated)
    assert not any((parent / "pyproject.toml").exists() for parent in [isolated, *isolated.parents[:3]])
    payload, errors = ops.installed_runtime_probe(isolated)
    assert errors == []
    assert payload["runtime_topology"]["execution_mode"] == "INSTALLED_RELEASE"
    assert all(item["execution_origin"] == "INSTALLED_RC" for item in payload["critical_import_matrix"])


def test_uninstall_removes_rc_owned_configuration(package: Path, tmp_path: Path):
    install_root = tmp_path / "install"
    registration = install_root / "registration.json"
    installed = run_ops(
        package,
        "install",
        "--package-root",
        str(package),
        "--install-root",
        str(install_root),
        "--registration-file",
        str(registration),
    )
    assert installed.returncode == 0
    configuration = install_root / ops.CONFIGURATION_FILE
    assert configuration.is_file()
    removed = run_ops(
        install_root / builder.PRODUCT_DIR,
        "uninstall",
        "--install-root",
        str(install_root),
        "--registration-file",
        str(registration),
    )
    assert removed.returncode == 0
    assert not configuration.exists()
