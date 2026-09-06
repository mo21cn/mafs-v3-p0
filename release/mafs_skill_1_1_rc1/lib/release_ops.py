#!/usr/bin/env python3
"""Offline release operations for MAFS Skill 1.1 RC1 (stdlib only)."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

PRODUCT_DIR = "MAFS_Skill_1.1.0-rc1"
EXPECTED_C1 = "a20377dfa447f1bd6008c6d84764b1c2544c665b"
EXPECTED_CQC = "c5c00a19f9812058050ba16ad61b717a1c1f1ca2"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def package_root(value: str | None) -> Path:
    return Path(value).resolve() if value else Path(__file__).resolve().parents[1]


def manifest_entries(root: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    manifest = root / "manifests" / "SHA256_MANIFEST.txt"
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        rows[rel] = digest
    return rows


def verify_package(root: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    manifest_path = root / "manifests" / "SHA256_MANIFEST.txt"
    if not manifest_path.is_file():
        return False, ["MANIFEST_MISSING"]
    expected = manifest_entries(root)
    actual_files = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p != manifest_path
    }
    for rel, digest in expected.items():
        path = root / rel
        if not path.is_file():
            errors.append(f"MISSING:{rel}")
        elif sha256(path) != digest:
            errors.append(f"MISMATCH:{rel}")
    for rel in sorted(actual_files - set(expected)):
        errors.append(f"EXTRA:{rel}")
    return not errors, errors


def verify_identities(root: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    release = read_json(root / "manifests" / "RELEASE_MANIFEST.json")
    dep = read_json(root / "manifests" / "DEPENDENCY_MANIFEST.json")
    if release.get("c1_accepted_sha") != EXPECTED_C1:
        errors.append("RELEASE_IDENTITY_BLOCKED")
    if dep.get("cqc_source_sha") != EXPECTED_CQC:
        errors.append("COMPATIBILITY_BLOCKED")
    artifact = root / "dependencies" / dep.get("dependency_artifact_name", "")
    if not artifact.is_file() or sha256(artifact) != dep.get("dependency_artifact_sha256"):
        errors.append("DEPENDENCY_INTEGRITY_BLOCKED")
    return not errors, errors


def operation(command: str, target: Path) -> dict:
    return {
        "operation_id": f"RE-{command.upper()}-{uuid.uuid4().hex[:12]}",
        "timestamp": now(),
        "product_version": "1.1",
        "source_sha": "",
        "target_path": str(target),
        "pre_state": {},
        "actions": [],
        "post_state": {},
        "status": "STARTED",
        "warnings": [],
        "errors": [],
    }


def emit(record: dict, log: str | None = None) -> int:
    if log:
        write_json(Path(log), record)
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0 if record["status"] in {"PASS", "READY", "DEGRADED", "ALREADY_INSTALLED", "ALREADY_MIGRATED", "ALREADY_ROLLED_BACK", "UNINSTALLED"} else 2


def validate(root: Path) -> tuple[bool, list[str]]:
    ok_manifest, manifest_errors = verify_package(root)
    if not ok_manifest:
        return False, ["INSTALL_BLOCKED", *manifest_errors]
    ok_identity, identity_errors = verify_identities(root)
    return ok_identity, identity_errors


def install(args: argparse.Namespace) -> int:
    root = package_root(args.package_root)
    install_root = Path(args.install_root).resolve()
    target = install_root / PRODUCT_DIR
    record = operation("install", target)
    release = read_json(root / "manifests" / "RELEASE_MANIFEST.json")
    record["source_sha"] = release.get("release_evaluated_source_sha", "")
    record["pre_state"] = {"target_exists": target.exists(), "registration_exists": Path(args.registration_file).exists()}
    ok, errors = validate(root)
    if not ok:
        record["status"] = errors[0]
        record["errors"] = errors
        return emit(record, args.operation_log)
    if target.exists():
        existing_ok, _ = verify_package(target)
        record["status"] = "ALREADY_INSTALLED" if existing_ok else "INSTALL_BLOCKED"
        if not existing_ok:
            record["errors"].append("EXISTING_TARGET_INTEGRITY_FAILURE")
        return emit(record, args.operation_log)
    install_root.mkdir(parents=True, exist_ok=True)
    # Keep the same-volume staging name deliberately short. Windows remains a
    # first-class target and deeply nested rehearsal roots can otherwise hit
    # legacy MAX_PATH behavior during copytree.
    staging = install_root / ".rc1-stage"
    if staging.exists():
        record["status"] = "INSTALL_BLOCKED"
        record["errors"].append("STALE_INSTALL_STAGING_PRESENT")
        return emit(record, args.operation_log)
    reg = Path(args.registration_file).resolve()
    previous = reg.read_text(encoding="utf-8") if reg.is_file() else None
    try:
        shutil.copytree(root, staging)
        copied_ok, copied_errors = verify_package(staging)
        if not copied_ok:
            raise RuntimeError("COPIED_PACKAGE_INTEGRITY_FAILURE:" + ",".join(copied_errors))
        staging.rename(target)
        config = install_root / "mafs-skill-1.1-configuration.json"
        write_json(config, {"provider_network_required_for_install": False, "provider_network_required_for_live_search": True, "credentials_embedded": False})
        reg.parent.mkdir(parents=True, exist_ok=True)
        tmp_reg = reg.with_suffix(reg.suffix + ".tmp")
        write_json(tmp_reg, {"product": "MAFS Skill", "version": "1.1", "release": "1.1.0-rc1", "path": str(target), "active": False, "stage": "STAGING"})
        os.replace(tmp_reg, reg)
        record["actions"] = ["package_verified", "dependency_verified", "versioned_install", "configuration_bootstrap", "staging_registration"]
        record["post_state"] = {"target_exists": target.exists(), "registration_path": str(reg), "configuration_path": str(config), "production_active": False}
        record["status"] = "PASS"
    except Exception as exc:
        if staging.exists():
            shutil.rmtree(staging)
        if target.exists():
            shutil.rmtree(target)
        if previous is None and reg.exists():
            reg.unlink()
        elif previous is not None:
            reg.write_text(previous, encoding="utf-8")
        record["status"] = "INSTALL_BLOCKED"
        record["errors"].append(str(exc))
    return emit(record, args.operation_log)


def doctor(args: argparse.Namespace) -> int:
    root = Path(args.install_path).resolve()
    record = operation("doctor", root)
    reasons: list[str] = []
    warnings: list[str] = []
    ok, errors = validate(root)
    if not ok:
        reasons.extend(errors)
    product = read_json(root / "manifests" / "PRODUCT_VERSION.json") if (root / "manifests" / "PRODUCT_VERSION.json").is_file() else {}
    if product.get("product_version") != "1.1" or product.get("release_stage") != "RELEASE_CANDIDATE":
        reasons.append("PRODUCT_VERSION_BLOCKED")
    schemas = list((root / "schemas").glob("*.schema.json")) if (root / "schemas").is_dir() else []
    if not schemas:
        reasons.append("SCHEMAS_MISSING")
    runtime = root / "runtime"
    sys.path.insert(0, str(runtime))
    try:
        import mafs_p0  # noqa: F401
    except Exception as exc:
        reasons.append(f"RUNTIME_IMPORT_BLOCKED:{exc}")
    cqc_adapter = root / "dependencies" / "cqc_runtime" / "integration" / "mafs_v3" / "adapter.py"
    if not cqc_adapter.is_file():
        reasons.append("CQC_RUNTIME_IMPORT_BLOCKED")
    else:
        spec = importlib.util.spec_from_file_location("mafs_cqc_adapter_probe", cqc_adapter)
        try:
            module = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
        except Exception as exc:
            reasons.append(f"CQC_RUNTIME_IMPORT_BLOCKED:{exc}")
    try:
        with tempfile.NamedTemporaryFile(dir=root, delete=True):
            pass
    except Exception as exc:
        reasons.append(f"WRITE_PERMISSION_BLOCKED:{exc}")
    if args.provider_network_status != "online":
        warnings.append("PROVIDER_NETWORK_NOT_CONFIRMED")
    record["checks"] = {
        "product_version": product.get("product_version"),
        "release_package_integrity": ok,
        "c1_accepted_sha": product.get("c1_accepted_sha"),
        "cqc_dependency_pin": EXPECTED_CQC,
        "runtime_importability": not any(x.startswith("RUNTIME_IMPORT") for x in reasons),
        "schema_count": len(schemas),
        "provider_adapter_installed": (runtime / "mafs_p0" / "live_crossref.py").is_file(),
        "provider_configuration_present": bool(os.environ.get("MAILTO") or os.environ.get("CROSSREF_MAILTO")),
        "provider_network_reachable": args.provider_network_status == "online",
        "stop_capability": (runtime / "mafs_p0" / "live_chain.py").is_file(),
        "selection_artifact_capability": (runtime / "mafs_p0" / "search_portfolio.py").is_file(),
    }
    record["warnings"] = warnings
    record["errors"] = reasons
    record["status"] = "BLOCKED" if reasons else ("DEGRADED" if warnings else "READY")
    return emit(record, args.operation_log)


def uninstall(args: argparse.Namespace) -> int:
    install_root = Path(args.install_root).resolve()
    target = install_root / PRODUCT_DIR
    record = operation("uninstall", target)
    reg = Path(args.registration_file).resolve()
    if target.exists():
        shutil.rmtree(target)
    if reg.is_file():
        data = read_json(reg)
        if Path(data.get("path", "")).resolve() == target:
            reg.unlink()
    record["status"] = "UNINSTALLED"
    record["actions"] = ["removed_rc_owned_files", "removed_rc_staging_registration"]
    record["post_state"] = {"target_exists": target.exists(), "legacy_touched": False}
    return emit(record, args.operation_log)


def migrate(args: argparse.Namespace) -> int:
    legacy = Path(args.legacy_root).resolve()
    root = package_root(args.package_root)
    install_root = Path(args.install_root).resolve()
    anchor = Path(args.rollback_anchor).resolve()
    record = operation("migrate", install_root / PRODUCT_DIR)
    if anchor.exists():
        record["status"] = "ALREADY_MIGRATED"
        return emit(record, args.operation_log)
    if not legacy.is_dir():
        record["status"] = "INSTALL_BLOCKED"
        record["errors"].append("LEGACY_ROOT_MISSING")
        return emit(record, args.operation_log)
    reg = Path(args.registration_file).resolve()
    anchor_payload = {
        "legacy_root": str(legacy),
        "legacy_manifest": str(Path(args.legacy_manifest).resolve()),
        "registration_existed": reg.is_file(),
        "registration_content": reg.read_text(encoding="utf-8") if reg.is_file() else "",
        "configuration_migration": "STATE_MIGRATION_NOT_REQUIRED",
        "created_at": now(),
    }
    write_json(anchor, anchor_payload)
    install_args = argparse.Namespace(package_root=str(root), install_root=str(install_root), registration_file=str(reg), operation_log=None)
    rc = install(install_args)
    if rc != 0:
        anchor.unlink(missing_ok=True)
        record["status"] = "INSTALL_BLOCKED"
        record["errors"].append("RC_INSTALL_FAILED")
    else:
        record["status"] = "PASS"
        record["actions"] = ["legacy_preserved", "rollback_anchor_created", "rc_installed_separately"]
        record["post_state"] = {"legacy_exists": legacy.exists(), "rc_exists": (install_root / PRODUCT_DIR).exists()}
    return emit(record, args.operation_log)


def verify_legacy(root: Path, manifest_path: Path) -> list[str]:
    errors: list[str] = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        digest, rel = line.split("  ", 1)
        path = root / Path(rel)
        if not path.is_file() or sha256(path) != digest:
            errors.append(rel)
    return errors


def rollback(args: argparse.Namespace) -> int:
    anchor = Path(args.rollback_anchor).resolve()
    install_root = Path(args.install_root).resolve()
    record = operation("rollback", install_root / PRODUCT_DIR)
    if not anchor.is_file():
        if not (install_root / PRODUCT_DIR).exists():
            record["status"] = "ALREADY_ROLLED_BACK"
        else:
            record["status"] = "ROLLBACK_BLOCKED"
            record["errors"].append("ROLLBACK_ANCHOR_MISSING")
        return emit(record, args.operation_log)
    data = read_json(anchor)
    legacy = Path(data["legacy_root"])
    mismatches = verify_legacy(legacy, Path(data["legacy_manifest"]))
    if mismatches:
        record["status"] = "ROLLBACK_BLOCKED"
        record["errors"] = [f"LEGACY_MISMATCH:{x}" for x in mismatches]
        return emit(record, args.operation_log)
    target = install_root / PRODUCT_DIR
    if target.exists():
        shutil.rmtree(target)
    reg = Path(args.registration_file).resolve()
    if data["registration_existed"]:
        reg.parent.mkdir(parents=True, exist_ok=True)
        reg.write_text(data["registration_content"], encoding="utf-8")
    elif reg.exists():
        reg.unlink()
    record["status"] = "PASS"
    record["actions"] = ["rc_removed", "legacy_registration_restored", "legacy_manifest_verified"]
    record["post_state"] = {"legacy_mismatch_count": 0, "legacy_exists": legacy.exists(), "rc_exists": target.exists()}
    return emit(record, args.operation_log)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    v = sub.add_parser("verify-package"); v.add_argument("--package-root"); v.add_argument("--operation-log")
    i = sub.add_parser("install"); i.add_argument("--package-root"); i.add_argument("--install-root", required=True); i.add_argument("--registration-file", required=True); i.add_argument("--operation-log")
    d = sub.add_parser("doctor"); d.add_argument("--install-path", required=True); d.add_argument("--provider-network-status", choices=("unknown", "offline", "online"), default="unknown"); d.add_argument("--operation-log")
    u = sub.add_parser("uninstall"); u.add_argument("--install-root", required=True); u.add_argument("--registration-file", required=True); u.add_argument("--operation-log")
    m = sub.add_parser("migrate"); m.add_argument("--package-root"); m.add_argument("--legacy-root", required=True); m.add_argument("--legacy-manifest", required=True); m.add_argument("--install-root", required=True); m.add_argument("--registration-file", required=True); m.add_argument("--rollback-anchor", required=True); m.add_argument("--operation-log")
    r = sub.add_parser("rollback"); r.add_argument("--install-root", required=True); r.add_argument("--registration-file", required=True); r.add_argument("--rollback-anchor", required=True); r.add_argument("--operation-log")
    return p


def main() -> int:
    args = parser().parse_args()
    if args.command == "verify-package":
        root = package_root(args.package_root)
        record = operation("verify", root)
        ok, errors = validate(root)
        record["status"] = "PASS" if ok else errors[0]
        record["errors"] = errors
        return emit(record, args.operation_log)
    return {"install": install, "doctor": doctor, "uninstall": uninstall, "migrate": migrate, "rollback": rollback}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
