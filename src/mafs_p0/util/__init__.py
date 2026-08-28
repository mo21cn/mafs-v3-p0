"""Utility modules: paths and hashing."""
from .paths import package_root, schemas_dir, src_dir, tests_dir, examples_dir, fixtures_dir, docs_dir, scripts_dir
from .hashing import sha256_file, sha256_bytes, sha256_json, write_sidecar, read_sidecar_strict

__all__ = [
    "package_root", "schemas_dir", "src_dir", "tests_dir", "examples_dir", "fixtures_dir", "docs_dir", "scripts_dir",
    "sha256_file", "sha256_bytes", "sha256_json", "write_sidecar", "read_sidecar_strict",
]
