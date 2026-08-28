"""§16 risk test 10: Runtime Fingerprint resolves.

The fingerprint must include sha256 hashes for skill, schemas_manifest, validator,
query compiler, and (where present) provider and resolver manifests. All hashes
are 64-hex.
"""
from __future__ import annotations
import re
from mafs_p0.runtime_fingerprint import build_fingerprint
from mafs_p0.provider_manifest import ProviderManifest, ResolverManifest


_HEX = re.compile(r"^[a-f0-9]{64}$")


def test_fingerprint_has_required_sha256s():
    fp = build_fingerprint(
        provider_manifests=[ProviderManifest(
            name="pubmed_mock_v1", version="3.0.0-p0",
            capabilities=["search.query", "search.pagination", "result.ranked"],
            network_requirement="offline", trust_class="synthetic_test",
        )],
        resolver_manifests=[ResolverManifest(
            name="crossref_mock_v1", version="3.0.0-p0",
            capabilities=["resolve.doi", "resolve.pmid", "metadata.snapshot"],
            trust_class="synthetic_test",
        )],
    )
    assert _HEX.match(fp["schemas_manifest_sha256"])
    assert _HEX.match(fp["validator_sha256"])
    assert _HEX.match(fp["query_compiler"]["sha256"])
    assert _HEX.match(fp["skill"]["sha256"])
    for p in fp["providers"]:
        assert _HEX.match(p["sha256"])
        assert p["namespace"]  # namespace defaults to name when unset
    for r in fp["resolvers"]:
        assert _HEX.match(r["sha256"])
        assert r["namespace"]
    # Runtime python
    import sys
    assert fp["runtime_python"].startswith(f"{sys.version_info.major}.")
    # Schema version
    assert fp["schema_version"] == "3.0-p0"
    # Created at present
    assert "T" in fp["created_at"]
