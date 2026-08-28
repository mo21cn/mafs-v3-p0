"""Runtime Fingerprint (P0 §11).

Identifies the actual runtime that produced a plan. SHA-256s of:
  * SKILL.md
  * all schemas concatenated (the schemas manifest hash)
  * validator.py
  * query compiler source
  * provider and resolver manifests (declared; for P0 we use the source files)
  * python runtime version

The schemas manifest hash is derived from the on-disk schema set
(sorted glob of ``schemas/*.schema.json``), NOT from a manually
maintained list. This eliminates the prior silent-drift failure
mode where a newly added schema (e.g. ``negotiation_result.schema.json``
in P0-RA2) was not included in the manifest hash.

Pre-P1 Hygiene §1 invariant: ``schemas present on disk == schemas
included in runtime fingerprint manifest`` — satisfied by construction.
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


def _schemas_manifest_sha256() -> str:
    """Compute the canonical manifest hash from the on-disk schema set.

    The schema set is derived from the filesystem (sorted glob of
    ``schemas/*.schema.json``) so adding or removing a schema file
    automatically updates the manifest. By construction,
    ``schemas in manifest == schemas present on disk``.

    Fail-closed semantics: an empty or missing schemas directory
    raises ``FileNotFoundError`` rather than producing a
    silently-incorrect hash.
    """
    h = hashlib.sha256()
    schemas_path = schemas_dir()
    if not schemas_path.is_dir():
        raise FileNotFoundError(f"missing schemas directory: {schemas_path}")
    names = sorted(p.name for p in schemas_path.glob("*.schema.json"))
    if not names:
        raise FileNotFoundError(f"no schemas found in: {schemas_path}")
    for name in names:
        path = schemas_path / name
        h.update(name.encode("utf-8") + b"\0")
        h.update(path.read_bytes())
    return h.hexdigest()


def _schemas_in_manifest() -> tuple[str, ...]:
    """Return the canonical sorted list of schema filenames included in the
    manifest hash. Exposed for tests and for the pre-P1 hygiene §1
    disk-vs-manifest equality assertion."""
    schemas_path = schemas_dir()
    return tuple(sorted(p.name for p in schemas_path.glob("*.schema.json")))


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
