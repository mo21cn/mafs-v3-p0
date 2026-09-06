#!/usr/bin/env python3
"""Build the deterministic, offline MAFS Skill 1.1.0-rc1 package."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "release" / "mafs_skill_1_1_rc1"
PRODUCT_DIR = "MAFS_Skill_1.1.0-rc1"
C1_SHA = "a20377dfa447f1bd6008c6d84764b1c2544c665b"
PACKAGE_C_SOURCE = "5ab44da280bf873d9e0f326f7e81c58c49da9fe9"
PACKAGE_C_BUNDLE = "1a3d65cd8d057549c4c4dae0860f739f3e2fd414"
M5_SHA = "ecfa39e9fdeced45848c643544477e408e872d60"
CQC_SHA = "c5c00a19f9812058050ba16ad61b717a1c1f1ca2"
ZIP_TIME = (2026, 9, 6, 0, 0, 0)

CQC_ALLOWLIST = (
    "integration/mafs_v3/adapter.py",
    "integration/mafs_v3/render.py",
    "integration/mafs_v3/validator.py",
    "schemas/budget_envelope.v0.1.schema.json",
    "schemas/candidate_question_set.v0.1.schema.json",
    "schemas/cqc_mafs_integration_binding.v0.1.schema.json",
    "schemas/search_requirement_profile.v0.1.schema.json",
    "scripts/mini_jsonschema.py",
    "scripts/render_budget_envelope.py",
    "scripts/render_cqs.py",
    "scripts/render_srp.py",
    "scripts/validate_cqs.py",
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_tree(source: Path, target: Path) -> None:
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))


def deterministic_zip(source: Path, output: Path, prefix: str | None = None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(p for p in source.rglob("*") if p.is_file()):
            rel = path.relative_to(source).as_posix()
            name = f"{prefix}/{rel}" if prefix else rel
            info = zipfile.ZipInfo(name, ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())


def verify_cqc_checkout(cqc_source: Path) -> None:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={cqc_source.as_posix()}", "-C", str(cqc_source), "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=20,
    )
    if result.returncode != 0 or result.stdout.strip() != CQC_SHA:
        raise RuntimeError(f"wrong CQC source identity: {result.stdout.strip()!r} {result.stderr.strip()!r}")
    status = subprocess.run(
        ["git", "-c", f"safe.directory={cqc_source.as_posix()}", "-C", str(cqc_source), "status", "--short"],
        capture_output=True, text=True, timeout=20,
    )
    if status.returncode != 0 or status.stdout.strip():
        raise RuntimeError("CQC checkout is not clean")


def build_cqc_dependency(cqc_source: Path, dependency_root: Path) -> tuple[str, str]:
    runtime_root = dependency_root / "cqc_runtime"
    for rel in CQC_ALLOWLIST:
        source = cqc_source / rel
        if not source.is_file():
            raise FileNotFoundError(source)
        target = runtime_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    identity = {
        "product": "mafs-cqc-runtime-protocol-subset",
        "source_sha": CQC_SHA,
        "allowlisted_files": list(CQC_ALLOWLIST),
        "repository_history_included": False,
        "offline_complete": True,
    }
    write_json(runtime_root / "CQC_DEPENDENCY_IDENTITY.json", identity)
    name = f"mafs-cqc-{CQC_SHA}-runtime.zip"
    artifact = dependency_root / name
    deterministic_zip(runtime_root, artifact, prefix="cqc_runtime")
    return name, sha256(artifact)


def build_release(output_dir: Path, cqc_source: Path, source_sha: str, build_timestamp: str, *, verify_cqc: bool = True) -> tuple[Path, Path, str]:
    if len(source_sha) != 40:
        raise ValueError("release evaluated source SHA must be 40 hex characters")
    if verify_cqc:
        verify_cqc_checkout(cqc_source)
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mafs-rc1-build-") as temp_name:
        stage = Path(temp_name) / PRODUCT_DIR
        copy_tree(TEMPLATE, stage)
        copy_tree(ROOT / "src" / "mafs_p0", stage / "runtime" / "mafs_p0")
        copy_tree(ROOT / "schemas", stage / "schemas")
        dep_name, dep_sha = build_cqc_dependency(cqc_source, stage / "dependencies")
        manifests = stage / "manifests"
        manifests.mkdir(parents=True, exist_ok=True)
        write_json(manifests / "PRODUCT_VERSION.json", {
            "product_name": "MAFS Skill", "product_version": "1.1",
            "release_artifact_version": "1.1.0-rc1", "release_stage": "RELEASE_CANDIDATE",
            "engine_lineage": "MAFS v3 / Post-P1.5 semantic engine",
            "c1_accepted_sha": C1_SHA, "package_c_evaluated_source_sha": PACKAGE_C_SOURCE,
            "package_c_bundle_sha": PACKAGE_C_BUNDLE, "cqc_frozen_producer_sha": CQC_SHA,
            "legacy_product_version": "1.0.0", "legacy_product_status": "PRESERVED",
            "build_timestamp": build_timestamp, "builder": "Codex release engineering",
            "production_active": False,
        })
        write_json(manifests / "CAPABILITY_MANIFEST.json", {
            "schema_version": "mafs-skill-capabilities.v1", "product_version": "1.1",
            "accepted_path": ["Research Narrative", "CQC", "CQS", "SRP", "BudgetEnvelope", "Package C ConsumerBinding", "MAFS Requirement", "EpistemicRoute", "live discovery", "CandidatePointer", "STOP", "explicit selection", "SourceDocument", "EvidenceSpan", "PropositionEvidence", "CollisionAssessment where applicable", "ResearchState", "governed re-digestion where applicable", "EvidenceLandscapePackage"],
            "non_capabilities": ["automatic top-1 selection", "unbounded autonomous recursion", "automatic truth arbitration", "research-opportunity ranking", "ROC", "clinical decision support", "autonomous experiment authorization", "production decision authority"],
            "stop_boundary_mandatory": True, "model_prior_is_evidence": False,
        })
        write_json(manifests / "RELEASE_MANIFEST.json", {
            "schema_version": "mafs-skill-release.v1", "product_name": "MAFS Skill",
            "product_version": "1.1", "release_artifact_version": "1.1.0-rc1",
            "release_stage": "RELEASE_CANDIDATE", "c1_accepted_sha": C1_SHA,
            "package_c_evaluated_source_sha": PACKAGE_C_SOURCE, "package_c_bundle_sha": PACKAGE_C_BUNDLE,
            "m5_accepted_sha": M5_SHA, "release_evaluated_source_sha": source_sha,
            "gate_r1_accepted": False, "production_active": False, "legacy_replaced": False,
        })
        write_json(manifests / "DEPENDENCY_MANIFEST.json", {
            "schema_version": "mafs-skill-dependencies.v1", "model": "offline_allowlisted_runtime_protocol_bundle",
            "offline_install_supported": True, "cqc_source_sha": CQC_SHA,
            "dependency_artifact_name": dep_name, "dependency_artifact_sha256": dep_sha,
            "dependency_build_method": "deterministic ZIP from explicit CQC runtime/protocol allowlist",
            "runtime_import_identity": "dependencies/cqc_runtime/integration/mafs_v3/adapter.py",
            "compatibility_status": "COMPATIBLE_WITH_PACKAGE_C_C1_ACCEPTED",
            "floating_dependency": False,
        })
        write_json(manifests / "COMPATIBILITY_MANIFEST.json", {
            "schema_version": "mafs-skill-compatibility.v1", "python": ">=3.10",
            "operating_systems": ["Windows 10/11", "portable stdlib-compatible systems"],
            "powershell_target": "5.1+", "cqc_source_sha": CQC_SHA,
            "mafs_c1_accepted_sha": C1_SHA, "offline_code_install": True,
            "provider_network_required_for_install": False,
            "provider_network_required_for_live_search": True,
        })
        manifest_path = manifests / "SHA256_MANIFEST.txt"
        rows = []
        for path in sorted(p for p in stage.rglob("*") if p.is_file() and p != manifest_path):
            rows.append(f"{sha256(path)}  {path.relative_to(stage).as_posix()}")
        manifest_path.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
        zip_path = output_dir / f"{PRODUCT_DIR}_portable.zip"
        deterministic_zip(stage, zip_path, prefix=PRODUCT_DIR)
        package_sha = sha256(zip_path)
        sha_path = zip_path.with_suffix(zip_path.suffix + ".sha256")
        sha_path.write_text(f"{package_sha}  {zip_path.name}\n", encoding="utf-8", newline="\n")
        unpacked = output_dir / PRODUCT_DIR
        if unpacked.exists():
            shutil.rmtree(unpacked)
        shutil.copytree(stage, unpacked)
    return zip_path, sha_path, package_sha


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cqc-source", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--build-timestamp", required=True)
    args = parser.parse_args()
    zip_path, sha_path, package_sha = build_release(args.output_dir.resolve(), args.cqc_source.resolve(), args.source_sha, args.build_timestamp)
    print(json.dumps({"zip_path": str(zip_path), "sha256_path": str(sha_path), "sha256": package_sha}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
