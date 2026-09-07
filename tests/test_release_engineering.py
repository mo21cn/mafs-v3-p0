"""Release-engineering contract tests for MAFS Skill 1.1 RC1."""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import zipfile
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


builder = load(BUILDER_PATH, "mafs_rc1_builder")
ops = load(OPS_PATH, "mafs_rc1_ops")


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
    out = tmp_path / "build"
    builder.build_release(out, cqc_fixture, "1" * 40, "2026-09-06T00:00:00Z", verify_cqc=False)
    return out / builder.PRODUCT_DIR


def refresh_manifest(root: Path) -> None:
    manifest = root / "manifests" / "SHA256_MANIFEST.txt"
    rows = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p != manifest):
        rows.append(f"{ops.sha256(path)}  {path.relative_to(root).as_posix()}")
    manifest.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")


def run_ops(package: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(package / "lib" / "release_ops.py"), *args], capture_output=True, text=True, timeout=60)


def test_builder_is_byte_reproducible(tmp_path: Path, cqc_fixture: Path):
    a = tmp_path / "a"; b = tmp_path / "b"
    zip_a, _, sha_a = builder.build_release(a, cqc_fixture, "1" * 40, "2026-09-06T00:00:00Z", verify_cqc=False)
    zip_b, _, sha_b = builder.build_release(b, cqc_fixture, "1" * 40, "2026-09-06T00:00:00Z", verify_cqc=False)
    assert sha_a == sha_b
    assert zip_a.read_bytes() == zip_b.read_bytes()


def test_portable_zip_has_one_product_root_and_no_git(package: Path):
    zip_path = package.parent / f"{builder.PRODUCT_DIR}_portable.zip"
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
    assert names and all(name.startswith(builder.PRODUCT_DIR + "/") for name in names)
    assert not any("/.git/" in name or "__pycache__" in name for name in names)


def test_manifest_and_frozen_identity_pass(package: Path):
    assert ops.verify_package(package) == (True, [])
    assert ops.verify_identities(package) == (True, [])


def test_manifest_tamper_blocks_install(package: Path, tmp_path: Path):
    (package / "runtime" / "mafs_p0" / "__init__.py").write_text("tampered\n", encoding="utf-8")
    result = run_ops(package, "install", "--package-root", str(package), "--install-root", str(tmp_path / "install"), "--registration-file", str(tmp_path / "reg.json"))
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "INSTALL_BLOCKED"


def test_wrong_cqc_identity_is_compatibility_blocked(package: Path):
    path = package / "manifests" / "DEPENDENCY_MANIFEST.json"
    data = json.loads(path.read_text(encoding="utf-8")); data["cqc_source_sha"] = "0" * 40
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    refresh_manifest(package)
    ok, errors = ops.validate(package)
    assert not ok and "COMPATIBILITY_BLOCKED" in errors


def test_wrong_mafs_source_identity_is_release_blocked(package: Path):
    path = package / "manifests" / "RELEASE_MANIFEST.json"
    data = json.loads(path.read_text(encoding="utf-8")); data["c1_accepted_sha"] = "0" * 40
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    refresh_manifest(package)
    ok, errors = ops.validate(package)
    assert not ok and "RELEASE_IDENTITY_BLOCKED" in errors


def test_fresh_install_doctor_idempotent_and_uninstall(package: Path, tmp_path: Path):
    install_root = tmp_path / "install path with spaces"; reg = install_root / "registration.json"
    first = run_ops(package, "install", "--package-root", str(package), "--install-root", str(install_root), "--registration-file", str(reg))
    assert first.returncode == 0 and json.loads(first.stdout)["status"] == "PASS"
    installed = install_root / builder.PRODUCT_DIR
    doctor = run_ops(installed, "doctor", "--install-path", str(installed), "--provider-network-status", "offline")
    assert doctor.returncode == 0 and json.loads(doctor.stdout)["status"] == "READY"
    second = run_ops(package, "install", "--package-root", str(package), "--install-root", str(install_root), "--registration-file", str(reg))
    assert second.returncode == 0 and json.loads(second.stdout)["status"] == "ALREADY_INSTALLED"
    removed = run_ops(installed, "uninstall", "--install-root", str(install_root), "--registration-file", str(reg))
    assert removed.returncode == 0 and json.loads(removed.stdout)["status"] == "UNINSTALLED"


def test_existing_target_wrong_identity_blocks_reinstall(package: Path, tmp_path: Path):
    install_root = tmp_path / "identity mismatch"; reg = install_root / "registration.json"
    first = run_ops(package, "install", "--package-root", str(package), "--install-root", str(install_root), "--registration-file", str(reg))
    assert first.returncode == 0 and json.loads(first.stdout)["status"] == "PASS"
    installed = install_root / builder.PRODUCT_DIR
    release_manifest = installed / "manifests" / "RELEASE_MANIFEST.json"
    release = json.loads(release_manifest.read_text(encoding="utf-8"))
    release["release_evaluated_source_sha"] = "2" * 40
    release_manifest.write_text(json.dumps(release, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    refresh_manifest(installed)
    assert ops.verify_package(installed) == (True, [])

    second = run_ops(package, "install", "--package-root", str(package), "--install-root", str(install_root), "--registration-file", str(reg))
    result = json.loads(second.stdout)
    assert second.returncode == 2
    assert result["status"] == "INSTALL_BLOCKED"
    assert "EXISTING_TARGET_RELEASE_MISMATCH" in result["errors"]
    assert json.loads(release_manifest.read_text(encoding="utf-8"))["release_evaluated_source_sha"] == "2" * 40


def test_failed_install_removes_new_rc_owned_configuration(package: Path, tmp_path: Path):
    install_root = tmp_path / "partial"; blocker = tmp_path / "not-a-directory"
    blocker.write_text("block", encoding="utf-8")
    result = run_ops(package, "install", "--package-root", str(package), "--install-root", str(install_root), "--registration-file", str(blocker / "registration.json"))
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "INSTALL_BLOCKED"
    assert not (install_root / builder.PRODUCT_DIR).exists()
    assert not (install_root / ops.CONFIGURATION_FILE).exists()
    assert payload["failure_stage"] == "registration_write"
    assert payload["config_created_by_operation"] is True
    assert payload["config_removed"] is True
    assert payload["registration_restored"] is True
    assert payload["target_removed"] is True
    assert payload["staging_removed"] is True
    assert payload["partial_state_cleaned"] is True
    assert payload["cleanup_errors"] == []
    assert payload["residual_artifacts"] == []

    doctor = run_ops(package, "doctor", "--install-path", str(install_root / builder.PRODUCT_DIR), "--provider-network-status", "offline")
    assert doctor.returncode == 2
    assert json.loads(doctor.stdout)["status"] == "BLOCKED"


def test_failed_install_restores_preexisting_configuration_exactly(package: Path, tmp_path: Path):
    install_root = tmp_path / "preexisting"; install_root.mkdir()
    config = install_root / ops.CONFIGURATION_FILE
    before = b'{\r\n  "operator_setting": "preserve exact bytes"\r\n}\r\n'
    config.write_bytes(before)
    before_sha = ops.sha256(config)
    blocker = tmp_path / "preexisting-not-a-directory"
    blocker.write_text("block", encoding="utf-8")

    result = run_ops(package, "install", "--package-root", str(package), "--install-root", str(install_root), "--registration-file", str(blocker / "registration.json"))
    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload["status"] == "INSTALL_BLOCKED"
    assert payload["config_preexisted"] is True
    assert payload["config_backup_sha256"] == before_sha
    assert payload["config_restored"] is True
    assert payload["partial_state_cleaned"] is True
    assert config.read_bytes() == before
    assert ops.sha256(config) == before_sha


def test_failed_install_reports_cleanup_incomplete_if_config_restore_fails(package: Path, tmp_path: Path, monkeypatch, capsys):
    install_root = tmp_path / "restore-failure"; install_root.mkdir()
    config = install_root / ops.CONFIGURATION_FILE
    config.write_bytes(b'old exact bytes\r\n')
    blocker = tmp_path / "restore-failure-not-a-directory"
    blocker.write_text("block", encoding="utf-8")
    original_restore = ops._restore_exact_file

    def injected_restore(path: Path, before: bytes | None, temporary: Path) -> None:
        if path == config:
            raise PermissionError("injected config restore failure")
        original_restore(path, before, temporary)

    monkeypatch.setattr(ops, "_restore_exact_file", injected_restore)
    args = type("Args", (), {
        "package_root": str(package),
        "install_root": str(install_root),
        "registration_file": str(blocker / "registration.json"),
        "operation_log": None,
    })()
    returncode = ops.install(args)
    payload = json.loads(capsys.readouterr().out)
    assert returncode == 2
    assert payload["status"] == "INSTALL_BLOCKED"
    assert payload["partial_state_cleaned"] is False
    assert "ROLLBACK_INCOMPLETE" in payload["errors"]
    assert any(item.startswith("configuration_restore:PermissionError") for item in payload["cleanup_errors"])
    assert {item["artifact"] for item in payload["residual_artifacts"]} == {"configuration_pre_state_mismatch"}


def test_migrate_and_rollback_restore_legacy_manifest(package: Path, tmp_path: Path):
    legacy = tmp_path / "legacy"; legacy.mkdir(); (legacy / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    manifest = tmp_path / "legacy-manifest.txt"
    manifest.write_text(f"{ops.sha256(legacy / 'VERSION')}  VERSION\n", encoding="utf-8")
    install_root = tmp_path / "upgrade"; reg = install_root / "registration.json"; anchor = install_root / "anchor.json"
    migrated = run_ops(package, "migrate", "--package-root", str(package), "--legacy-root", str(legacy), "--legacy-manifest", str(manifest), "--install-root", str(install_root), "--registration-file", str(reg), "--rollback-anchor", str(anchor))
    assert migrated.returncode == 0 and '"status": "PASS"' in migrated.stdout
    rolled = run_ops(package, "rollback", "--install-root", str(install_root), "--registration-file", str(reg), "--rollback-anchor", str(anchor))
    assert rolled.returncode == 0 and json.loads(rolled.stdout)["status"] == "PASS"
    assert (legacy / "VERSION").read_text(encoding="utf-8") == "1.0.0\n"
    again = run_ops(package, "rollback", "--install-root", str(install_root), "--registration-file", str(reg), "--rollback-anchor", str(anchor))
    assert again.returncode == 0 and json.loads(again.stdout)["status"] == "PASS"


def test_stale_migration_anchor_blocks_false_already_migrated(package: Path, tmp_path: Path):
    legacy = tmp_path / "legacy"; legacy.mkdir(); (legacy / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    manifest = tmp_path / "legacy-manifest.txt"
    manifest.write_text(f"{ops.sha256(legacy / 'VERSION')}  VERSION\n", encoding="utf-8")

    missing_root = tmp_path / "missing target"; missing_reg = missing_root / "registration.json"; missing_anchor = missing_root / "anchor.json"
    migrated = run_ops(package, "migrate", "--package-root", str(package), "--legacy-root", str(legacy), "--legacy-manifest", str(manifest), "--install-root", str(missing_root), "--registration-file", str(missing_reg), "--rollback-anchor", str(missing_anchor))
    assert migrated.returncode == 0 and '"status": "PASS"' in migrated.stdout
    shutil.rmtree(missing_root / builder.PRODUCT_DIR)
    stale_target = run_ops(package, "migrate", "--package-root", str(package), "--legacy-root", str(legacy), "--legacy-manifest", str(manifest), "--install-root", str(missing_root), "--registration-file", str(missing_reg), "--rollback-anchor", str(missing_anchor))
    missing_result = json.loads(stale_target.stdout)
    assert stale_target.returncode == 2
    assert missing_result["status"] == "MIGRATION_STATE_INCONSISTENT"
    assert "RC_TARGET_MISSING" in missing_result["errors"]

    bad_reg_root = tmp_path / "bad registration"; bad_reg = bad_reg_root / "registration.json"; bad_reg_anchor = bad_reg_root / "anchor.json"
    migrated = run_ops(package, "migrate", "--package-root", str(package), "--legacy-root", str(legacy), "--legacy-manifest", str(manifest), "--install-root", str(bad_reg_root), "--registration-file", str(bad_reg), "--rollback-anchor", str(bad_reg_anchor))
    assert migrated.returncode == 0 and '"status": "PASS"' in migrated.stdout
    registration = json.loads(bad_reg.read_text(encoding="utf-8")); registration["path"] = str(tmp_path / "wrong-target")
    bad_reg.write_text(json.dumps(registration, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    stale_registration = run_ops(package, "migrate", "--package-root", str(package), "--legacy-root", str(legacy), "--legacy-manifest", str(manifest), "--install-root", str(bad_reg_root), "--registration-file", str(bad_reg), "--rollback-anchor", str(bad_reg_anchor))
    registration_result = json.loads(stale_registration.stdout)
    assert stale_registration.returncode == 2
    assert registration_result["status"] == "MIGRATION_STATE_INCONSISTENT"
    assert "MIGRATION_REGISTRATION_MISMATCH:path" in registration_result["errors"]


def test_release_skill_truth_and_stop_non_capability(package: Path):
    skill = (package / "SKILL.md").read_text(encoding="utf-8")
    capabilities = json.loads((package / "manifests" / "CAPABILITY_MANIFEST.json").read_text(encoding="utf-8"))
    assert "CandidatePointer → STOP →" in skill
    assert capabilities["stop_boundary_mandatory"] is True
    assert "automatic top-1 selection" in capabilities["non_capabilities"]


def test_bounded_smoke_constructs_valid_governed_execution(package: Path):
    smoke = load(package / "examples" / "bounded_smoke.py", "mafs_rc1_smoke")
    execution = smoke.build_execution()
    assert execution.route.route_id == "ER-9901"
    assert execution.fidelity_review.review_id == "RFR-9901"
    assert execution.portfolio.portfolio_id == "SP-9901"
    rendered = json.dumps(execution.search_order.to_dict()).lower()
    assert "expected_doi" not in rendered
    assert "target_paper_identity" not in rendered
