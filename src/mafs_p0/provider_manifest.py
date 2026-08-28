"""Provider manifest (P0 §5, §7.9, §8.8)."""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, asdict, field


def _compute_manifest_sha256(payload: dict) -> str:
    """Canonical SHA-256 over the manifest payload (sans sha256 field, deterministic)."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class ProviderManifest:
    name: str
    version: str
    capabilities: list[str]
    network_requirement: str = "offline"   # P0 default; live retrievals are P1
    trust_class: str = "synthetic_test"    # P0 default; real trust classes are P2
    sha256: str = ""
    # Extension namespace used to qualify non-core capabilities. The extension
    # ``<namespace>.<verb>`` is recognized only if ``namespace`` equals one of the
    # registered providers' ``namespace`` field (or, if unset, the provider ``name``).
    # This separates the versioned provider identity (``openalex_v1``) from the
    # extension prefix (``openalex.related_works``), per master contract §5.
    namespace: str | None = None

    def effective_namespace(self) -> str:
        return self.namespace if self.namespace else self.name

    def to_dict(self) -> dict:
        d = asdict(self)
        d["schema_version"] = "3.0-p0"
        if not d.get("sha256"):
            d_for_hash = {k: v for k, v in d.items() if k != "sha256"}
            d["sha256"] = _compute_manifest_sha256(d_for_hash)
        return d


@dataclass
class ResolverManifest:
    name: str
    version: str
    capabilities: list[str]
    trust_class: str = "synthetic_test"
    sha256: str = ""
    namespace: str | None = None

    def effective_namespace(self) -> str:
        return self.namespace if self.namespace else self.name

    def to_dict(self) -> dict:
        d = asdict(self)
        d["schema_version"] = "3.0-p0"
        if not d.get("sha256"):
            d_for_hash = {k: v for k, v in d.items() if k != "sha256"}
            d["sha256"] = _compute_manifest_sha256(d_for_hash)
        return d
