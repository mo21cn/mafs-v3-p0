"""Runtime Fingerprint (P0 §11).

Identifies the actual runtime that produced a plan. SHA-256s of:
  * SKILL.md
  * all 12 schemas concatenated (the schemas manifest hash)
  * validator.py
  * query compiler source
  * provider and resolver manifests (declared; for P0 we use the source files)
  * python runtime version
"""
from __future__ import annotations
import hashlib
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from .util.paths import (
    package_root, schemas_dir,
)
from .util.hashing import sha256_file, sha256_bytes
from .query_compiler import (
    compiler_name as _qc_name,
    compiler_version as _qc_version,
    compiler_sha256 as _qc_sha256,
)


SCHEMAS_ORDER: tuple[str, ...] = (
    "runtime_fingerprint.schema.json",
    "compiled_target.schema.json",
    "axis.schema.json",
    "gate_dependency_graph.schema.json",
    "search_order.schema.json",
    "provider_manifest.schema.json",
    "resolver_manifest.schema.json",
    "query_ast.schema.json",
    "compiled_query.schema.json",
    "budget_state.schema.json",
    "preflight_report.schema.json",
    "run_manifest.schema.json",
)


def _schemas_manifest_sha256() -> str:
    h = hashlib.sha256()
    for name in SCHEMAS_ORDER:
        path = schemas_dir() / name
        if not path.is_file():
            raise FileNotFoundError(f"missing schema: {path}")
        h.update(name.encode("utf-8") + b"\0")
        h.update(path.read_bytes())
    return h.hexdigest()


def _file_sha256_if_exists(rel_path: str) -> str:
    p = package_root() / rel_path
    if not p.is_file():
        return ""
    return sha256_file(p)


def build_fingerprint(
    provider_manifests: list | None = None,
    resolver_manifests: list | None = None,
) -> dict:
    skill_sha = _file_sha256_if_exists("SKILL.md")
    validator_sha = _file_sha256_if_exists("src/mafs_p0/validator.py")

    providers = []
    for pm in (provider_manifests or []):
        d = pm.to_dict() if hasattr(pm, "to_dict") else dict(pm)
        # ensure sha256 field is present; if not, compute from raw manifest
        if not d.get("sha256"):
            import json
            d["sha256"] = hashlib.sha256(
                json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
        providers.append({
            "name": d["name"],
            "version": d["version"],
            "sha256": d["sha256"],
            "trust_class": d.get("trust_class", "synthetic_test"),
            "namespace": d.get("namespace") or d.get("name"),
        })
    resolvers = []
    for rm in (resolver_manifests or []):
        d = rm.to_dict() if hasattr(rm, "to_dict") else dict(rm)
        if not d.get("sha256"):
            import json
            d["sha256"] = hashlib.sha256(
                json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
        resolvers.append({
            "name": d["name"],
            "version": d["version"],
            "sha256": d["sha256"],
            "trust_class": d.get("trust_class", "synthetic_test"),
            "namespace": d.get("namespace") or d.get("name"),
        })

    py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    return {
        "schema_version": "3.0-p0",
        "skill": {"name": "multi-axis-falsification-search-v3-p0", "version": "3.0.0-p0", "sha256": skill_sha},
        "schemas_manifest_sha256": _schemas_manifest_sha256(),
        "validator_sha256": validator_sha,
        "query_compiler": {"name": _qc_name, "version": _qc_version, "sha256": _qc_sha256},
        "providers": providers,
        "resolvers": resolvers,
        "runtime_python": py,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def fingerprint_self_sha256(fp: dict) -> str:
    """SHA-256 of the canonical JSON serialization of the fingerprint itself."""
    import json
    return sha256_bytes(json.dumps(fp, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
