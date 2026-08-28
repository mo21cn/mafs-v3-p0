"""§16 risk test 10: Runtime Fingerprint resolves.

The fingerprint must include sha256 hashes for skill, schemas_manifest, validator,
query compiler, and (where present) provider and resolver manifests. All hashes
are 64-hex.

Pre-P1 hygiene §1: the schemas manifest must include EVERY schema file
on disk (no manual tuple that can silently drift). This test asserts
that the P0-RA2-era 13th schema (``negotiation_result.schema.json``) is
included, and that the on-disk set equals the manifest set.
"""
from __future__ import annotations
import re
from pathlib import Path
from mafs_p0.runtime_fingerprint import build_fingerprint, _schemas_in_manifest
from mafs_p0.util.paths import schemas_dir
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


def test_schema_manifest_includes_all_on_disk():
    """Pre-P1 hygiene §1 invariant: schemas on disk == schemas in manifest.

    Regression test for the P0-RA2 defect where the manual SCHEMAS_ORDER
    tuple did not include negotiation_result.schema.json, causing the
    manifest hash to be silently incomplete.
    """
    on_disk = tuple(sorted(p.name for p in schemas_dir().glob("*.schema.json")))
    in_manifest = _schemas_in_manifest()
    assert on_disk == in_manifest, (
        f"schema-fingerprint drift: on disk={on_disk}, in manifest={in_manifest}"
    )
    # Belt-and-suspenders: confirm the P0-RA2-era 13th schema is included.
    assert "negotiation_result.schema.json" in in_manifest
    # And the count is non-trivial (sanity check on the glob).
    assert len(in_manifest) >= 12
