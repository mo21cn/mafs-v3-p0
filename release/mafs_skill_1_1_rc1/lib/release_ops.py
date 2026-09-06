#!/usr/bin/env python3
"""Offline release operations for MAFS Skill 1.1 RC1 (stdlib only)."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

PRODUCT_DIR = "MAFS_Skill_1.1.0-rc1"
EXPECTED_C1 = "a20377dfa447f1bd6008c6d84764b1c2544c665b"
EXPECTED_CQC = "c5c00a19f9812058050ba16ad61b717a1c1f1ca2"
RELEASE_IDENTITY_FIELDS = (
    "product_name",
    "product_version",
    "release_artifact_version",
    "release_stage",
    "release_evaluated_source_sha",
    "c1_accepted_sha",
    "cqc_source_sha",
    "dependency_artifact_name",
    "dependency_artifact_sha256",
)
CRITICAL_MODULES = (
    "mafs_p0.cqc_integration",
    "mafs_p0.preflight",
    "mafs_p0.validator",
    "mafs_p0.target_compiler",
    "mafs_p0.runtime_fingerprint",
    "mafs_p0.epistemic_route",
    "mafs_p0.search_portfolio",
    "mafs_p0.package_a",
    "mafs_p0.live_chain",
    "mafs_p0.live_crossref",
)
CONFIGURATION_FILE = "mafs-skill-1.1-configuration.json"


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


def release_identity(root: Path) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    try:
        release = read_json(root / "manifests" / "RELEASE_MANIFEST.json")
        product = read_json(root / "manifests" / "PRODUCT_VERSION.json")
        dep = read_json(root / "manifests" / "DEPENDENCY_MANIFEST.json")
    except (OSError, ValueError, TypeError) as exc:
        return {}, [f"RELEASE_IDENTITY_BLOCKED:{type(exc).__name__}"]
    identity = {
        "product_name": str(release.get("product_name", "")),
        "product_version": str(release.get("product_version", "")),
        "release_artifact_version": str(release.get("release_artifact_version", "")),
        "release_stage": str(release.get("release_stage", "")),
        "release_evaluated_source_sha": str(release.get("release_evaluated_source_sha", "")),
        "c1_accepted_sha": str(release.get("c1_accepted_sha", "")),
        "cqc_source_sha": str(dep.get("cqc_source_sha", "")),
        "dependency_artifact_name": str(dep.get("dependency_artifact_name", "")),
        "dependency_artifact_sha256": str(dep.get("dependency_artifact_sha256", "")),
    }
    if identity["product_name"] != "MAFS Skill":
        errors.append("PRODUCT_IDENTITY_BLOCKED")
    if product.get("product_name") != identity["product_name"]:
        errors.append("PRODUCT_IDENTITY_INCONSISTENT")
    if product.get("product_version") != identity["product_version"]:
        errors.append("PRODUCT_VERSION_INCONSISTENT")
    if product.get("release_artifact_version") != identity["release_artifact_version"]:
        errors.append("RELEASE_ARTIFACT_VERSION_INCONSISTENT")
    if product.get("release_stage") != identity["release_stage"]:
        errors.append("RELEASE_STAGE_INCONSISTENT")
    if product.get("c1_accepted_sha") != identity["c1_accepted_sha"]:
        errors.append("C1_IDENTITY_INCONSISTENT")
    if product.get("cqc_frozen_producer_sha") != identity["cqc_source_sha"]:
        errors.append("CQC_IDENTITY_INCONSISTENT")
    return identity, errors


def verify_identities(root: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    identity, identity_errors = release_identity(root)
    if not identity:
        return False, identity_errors
    if identity["c1_accepted_sha"] != EXPECTED_C1:
        errors.append("RELEASE_IDENTITY_BLOCKED")
    if identity["cqc_source_sha"] != EXPECTED_CQC:
        errors.append("COMPATIBILITY_BLOCKED")
    errors.extend(identity_errors)
    artifact = root / "dependencies" / identity["dependency_artifact_name"]
    if not artifact.is_file() or sha256(artifact) != identity["dependency_artifact_sha256"]:
        errors.append("DEPENDENCY_INTEGRITY_BLOCKED")
    return not errors, errors


def identity_mismatches(existing: dict[str, str], incoming: dict[str, str]) -> list[str]:
    return [field for field in RELEASE_IDENTITY_FIELDS if existing.get(field) != incoming.get(field)]


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


def installed_runtime_probe(root: Path) -> tuple[dict, list[str]]:
    """Probe only the installed runtime in an isolated Python process."""

    script = textwrap.dedent(
        """
        import importlib
        import json
        from pathlib import Path
        import sys
        import tempfile

        root = Path(sys.argv[1]).resolve()
        runtime = (root / "runtime").resolve()
        sys.path.insert(0, str(runtime))
        critical = json.loads(sys.argv[2])
        matrix = []
        for name in critical:
            try:
                module = importlib.import_module(name)
                resolved = Path(module.__file__).resolve()
                installed = resolved.is_relative_to(runtime)
                matrix.append({
                    "module": name,
                    "installed_import_status": "PASS" if installed else "FAIL",
                    "resolved_file": str(resolved),
                    "execution_origin": "INSTALLED_RC" if installed else "REPOSITORY_OR_OTHER",
                    "release_mode": "INSTALLED_RELEASE",
                    "error": "" if installed else "MODULE_ORIGIN_OUTSIDE_INSTALLED_RUNTIME",
                })
            except Exception as exc:
                matrix.append({
                    "module": name,
                    "installed_import_status": "FAIL",
                    "resolved_file": "",
                    "execution_origin": "UNRESOLVED",
                    "release_mode": "INSTALLED_RELEASE",
                    "error": f"{type(exc).__name__}: {exc}",
                })

        payload = {"critical_import_matrix": matrix}
        try:
            from mafs_p0.util.paths import (
                INSTALLED_RELEASE,
                dependencies_root,
                execution_mode,
                manifests_root,
                product_root,
                runtime_root,
                schemas_root,
            )
            payload["runtime_topology"] = {
                "execution_mode": execution_mode(),
                "product_root": str(product_root()),
                "runtime_root": str(runtime_root()),
                "schemas_root": str(schemas_root()),
                "manifests_root": str(manifests_root()),
                "dependencies_root": str(dependencies_root()),
                "valid": execution_mode() == INSTALLED_RELEASE and product_root() == root,
            }
        except Exception as exc:
            payload["runtime_topology"] = {"valid": False, "error": f"{type(exc).__name__}: {exc}"}

        try:
            from mafs_p0.runtime_fingerprint import build_fingerprint
            fingerprint = build_fingerprint()
            identity = fingerprint.get("runtime_topology", {}).get("release_identity", {})
            payload["runtime_fingerprint"] = {
                "status": "PASS",
                "execution_mode": fingerprint.get("runtime_topology", {}).get("execution_mode"),
                "product_root": fingerprint.get("runtime_topology", {}).get("product_root"),
                "product_version": identity.get("product_version"),
                "release_artifact_version": identity.get("release_artifact_version"),
                "release_evaluated_source_sha": identity.get("release_evaluated_source_sha"),
                "c1_accepted_sha": identity.get("c1_accepted_sha"),
                "cqc_source_sha": identity.get("cqc_source_sha"),
            }
        except Exception as exc:
            payload["runtime_fingerprint"] = {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}

        try:
            from mafs_p0.package_c_demo import consume, write_hermetic_cqc_fixture
            from mafs_p0.validator import validate_against_schema
            with tempfile.TemporaryDirectory(prefix="mafs-ra2-doctor-") as temp_name:
                result = consume(write_hermetic_cqc_fixture(Path(temp_name)))
            binding_errors = (
                validate_against_schema(
                    result.consumer_binding,
                    "post_p1p5/cqc_mafs_consumer_binding.schema.json",
                )
                if result.consumer_binding else ["consumer binding missing"]
            )
            payload["package_c_functional_probe"] = {
                "status": "PASS" if result.accepted and not binding_errors and result.mafs_requirements else "FAIL",
                "integration_status": result.integration_status,
                "compatibility_status": result.compatibility_status,
                "consumer_binding_constructed": result.consumer_binding is not None,
                "requirement_count": len(result.mafs_requirements),
                "schema_errors": binding_errors,
                "search_performed": False,
                "selection_performed": False,
                "resolve_performed": False,
            }
        except Exception as exc:
            payload["package_c_functional_probe"] = {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
        print(json.dumps(payload, sort_keys=True))
        """
    )
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    with tempfile.TemporaryDirectory(prefix="mafs-ra2-isolated-cwd-") as isolated_cwd:
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-c", script, str(root), json.dumps(CRITICAL_MODULES)],
            cwd=isolated_cwd,
            env=environment,
            capture_output=True,
            text=True,
            timeout=120,
        )
    if result.returncode != 0:
        return {}, [f"INSTALLED_PROBE_PROCESS_BLOCKED:{result.stderr.strip() or result.stdout.strip()}"]
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {}, [f"INSTALLED_PROBE_OUTPUT_BLOCKED:{exc}"]
    errors = [
        f"CRITICAL_IMPORT_BLOCKED:{item['module']}:{item['error']}"
        for item in payload.get("critical_import_matrix", [])
        if item.get("installed_import_status") != "PASS"
    ]
    if not payload.get("runtime_topology", {}).get("valid"):
        errors.append("RELEASE_TOPOLOGY_BLOCKED")
    if payload.get("runtime_fingerprint", {}).get("status") != "PASS":
        errors.append("RUNTIME_FINGERPRINT_BLOCKED")
    if payload.get("package_c_functional_probe", {}).get("status") != "PASS":
        errors.append("PACKAGE_C_FUNCTIONAL_PROBE_BLOCKED")
    return payload, errors


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
        existing_ok, existing_errors = validate(target)
        existing_identity, identity_errors = release_identity(target)
        incoming_identity, incoming_errors = release_identity(root)
        mismatches = identity_mismatches(existing_identity, incoming_identity) if existing_identity and incoming_identity else []
        if existing_ok and not identity_errors and not incoming_errors and not mismatches:
            record["status"] = "ALREADY_INSTALLED"
        else:
            record["status"] = "INSTALL_BLOCKED"
            record["errors"].append("EXISTING_TARGET_IDENTITY_MISMATCH")
            record["errors"].extend(f"EXISTING_TARGET_VALIDATION:{error}" for error in existing_errors)
            record["errors"].extend(f"EXISTING_TARGET_IDENTITY:{error}" for error in identity_errors)
            record["errors"].extend(f"INCOMING_IDENTITY:{error}" for error in incoming_errors)
            if any(field.startswith("dependency_") or field == "cqc_source_sha" for field in mismatches):
                record["errors"].append("EXISTING_TARGET_DEPENDENCY_MISMATCH")
            if mismatches:
                record["errors"].append("EXISTING_TARGET_RELEASE_MISMATCH")
                record["errors"].extend(f"IDENTITY_FIELD_MISMATCH:{field}" for field in mismatches)
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
    probe, probe_errors = installed_runtime_probe(root)
    reasons.extend(probe_errors)
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
    matrix = probe.get("critical_import_matrix", [])
    record["checks"] = {
        "product_version": product.get("product_version"),
        "release_package_integrity": ok,
        "c1_accepted_sha": product.get("c1_accepted_sha"),
        "cqc_dependency_pin": EXPECTED_CQC,
        "release_mode_detected": probe.get("runtime_topology", {}).get("execution_mode"),
        "product_root_valid": probe.get("runtime_topology", {}).get("valid", False),
        "critical_runtime_imports": {
            "total": len(CRITICAL_MODULES),
            "passed": sum(item.get("installed_import_status") == "PASS" for item in matrix),
            "failed": sum(item.get("installed_import_status") != "PASS" for item in matrix),
            "matrix": matrix,
        },
        "package_c_consumer_importable": any(item.get("module") == "mafs_p0.cqc_integration" and item.get("installed_import_status") == "PASS" for item in matrix),
        "preflight_importable": any(item.get("module") == "mafs_p0.preflight" and item.get("installed_import_status") == "PASS" for item in matrix),
        "validator_importable": any(item.get("module") == "mafs_p0.validator" and item.get("installed_import_status") == "PASS" for item in matrix),
        "target_compiler_importable": any(item.get("module") == "mafs_p0.target_compiler" and item.get("installed_import_status") == "PASS" for item in matrix),
        "runtime_fingerprint_buildable": probe.get("runtime_fingerprint", {}).get("status") == "PASS",
        "runtime_fingerprint": probe.get("runtime_fingerprint", {}),
        "package_c_functional_probe": probe.get("package_c_functional_probe", {}),
        "runtime_importability": not probe_errors,
        "schema_count": len(schemas),
        "provider_adapter_installed": (runtime / "mafs_p0" / "live_crossref.py").is_file(),
        "provider_configuration_present": bool(os.environ.get("MAILTO") or os.environ.get("CROSSREF_MAILTO")),
        "provider_network_reachable": args.provider_network_status == "online",
        "provider_network_status": "READY" if args.provider_network_status == "online" else "DEGRADED",
        "stop_capability": (runtime / "mafs_p0" / "live_chain.py").is_file(),
        "selection_artifact_capability": (runtime / "mafs_p0" / "search_portfolio.py").is_file(),
    }
    record["warnings"] = warnings
    record["errors"] = reasons
    # Provider reachability is a scientific-operation concern, not installed
    # runtime integrity. Preserve it as a warning/check without downgrading an
    # otherwise complete offline product.
    record["status"] = "BLOCKED" if reasons else "READY"
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
    config = install_root / CONFIGURATION_FILE
    if config.is_file():
        config.unlink()
    record["status"] = "UNINSTALLED"
    record["actions"] = ["removed_rc_owned_files", "removed_rc_staging_registration", "removed_rc_owned_configuration"]
    record["post_state"] = {"target_exists": target.exists(), "configuration_exists": config.exists(), "legacy_touched": False}
    return emit(record, args.operation_log)


def migrate(args: argparse.Namespace) -> int:
    legacy = Path(args.legacy_root).resolve()
    root = package_root(args.package_root)
    install_root = Path(args.install_root).resolve()
    anchor = Path(args.rollback_anchor).resolve()
    record = operation("migrate", install_root / PRODUCT_DIR)
    if anchor.exists():
        state_errors = verify_migrated_state(args, root, install_root, anchor)
        if state_errors:
            record["status"] = "MIGRATION_STATE_INCONSISTENT"
            record["errors"] = state_errors
        else:
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


def verify_migrated_state(
    args: argparse.Namespace,
    incoming_root: Path,
    install_root: Path,
    anchor: Path,
) -> list[str]:
    errors: list[str] = []
    try:
        data = read_json(anchor)
    except (OSError, ValueError, TypeError) as exc:
        return [f"ROLLBACK_ANCHOR_INVALID:{type(exc).__name__}"]
    required = {"legacy_root", "legacy_manifest", "registration_existed", "registration_content"}
    if not required.issubset(data):
        errors.append("ROLLBACK_ANCHOR_FIELDS_MISSING")
        return errors

    legacy = Path(args.legacy_root).resolve()
    legacy_manifest = Path(args.legacy_manifest).resolve()
    if Path(data["legacy_root"]).resolve() != legacy:
        errors.append("ROLLBACK_ANCHOR_LEGACY_ROOT_MISMATCH")
    if Path(data["legacy_manifest"]).resolve() != legacy_manifest:
        errors.append("ROLLBACK_ANCHOR_LEGACY_MANIFEST_MISMATCH")
    if not legacy.is_dir():
        errors.append("LEGACY_ROOT_MISSING")
    if not legacy_manifest.is_file():
        errors.append("LEGACY_MANIFEST_MISSING")
    elif legacy.is_dir():
        try:
            errors.extend(f"LEGACY_MISMATCH:{rel}" for rel in verify_legacy(legacy, legacy_manifest))
        except (OSError, ValueError) as exc:
            errors.append(f"LEGACY_MANIFEST_INVALID:{type(exc).__name__}")

    target = install_root / PRODUCT_DIR
    if not target.is_dir():
        errors.append("RC_TARGET_MISSING")
    else:
        target_ok, target_errors = validate(target)
        if not target_ok:
            errors.extend(f"RC_TARGET_INVALID:{error}" for error in target_errors)
        target_identity, target_identity_errors = release_identity(target)
        incoming_ok, incoming_errors = validate(incoming_root)
        incoming_identity, incoming_identity_errors = release_identity(incoming_root)
        if not incoming_ok:
            errors.extend(f"INCOMING_PACKAGE_INVALID:{error}" for error in incoming_errors)
        errors.extend(f"RC_TARGET_IDENTITY:{error}" for error in target_identity_errors)
        errors.extend(f"INCOMING_IDENTITY:{error}" for error in incoming_identity_errors)
        for field in identity_mismatches(target_identity, incoming_identity):
            errors.append(f"RC_TARGET_IDENTITY_MISMATCH:{field}")

    reg = Path(args.registration_file).resolve()
    if not reg.is_file():
        errors.append("MIGRATION_REGISTRATION_MISSING")
    else:
        try:
            registration = read_json(reg)
        except (OSError, ValueError, TypeError) as exc:
            errors.append(f"MIGRATION_REGISTRATION_INVALID:{type(exc).__name__}")
        else:
            expected_registration = {
                "product": "MAFS Skill",
                "version": "1.1",
                "release": "1.1.0-rc1",
                "stage": "STAGING",
                "active": False,
            }
            for field, expected in expected_registration.items():
                if registration.get(field) != expected:
                    errors.append(f"MIGRATION_REGISTRATION_MISMATCH:{field}")
            registered_path = registration.get("path")
            if not isinstance(registered_path, str) or Path(registered_path).resolve() != target.resolve():
                errors.append("MIGRATION_REGISTRATION_MISMATCH:path")
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
    config = install_root / CONFIGURATION_FILE
    if config.is_file():
        config.unlink()
    reg = Path(args.registration_file).resolve()
    if data["registration_existed"]:
        reg.parent.mkdir(parents=True, exist_ok=True)
        reg.write_text(data["registration_content"], encoding="utf-8")
    elif reg.exists():
        reg.unlink()
    record["status"] = "PASS"
    record["actions"] = ["rc_removed", "rc_owned_configuration_removed", "legacy_registration_restored", "legacy_manifest_verified"]
    record["post_state"] = {"legacy_mismatch_count": 0, "legacy_exists": legacy.exists(), "rc_exists": target.exists(), "configuration_exists": config.exists()}
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
