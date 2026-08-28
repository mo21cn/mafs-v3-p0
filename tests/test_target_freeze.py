"""§16 risk test 3: Target Freeze hash preserved.

The compiled target carries the source SHA-256; we re-verify it byte-for-byte.
"""
from __future__ import annotations
from mafs_p0.target_compiler import compile_target
from mafs_p0.util.hashing import sha256_file


def test_target_freeze_hash_preserved_minimal(minimal_tf_path):
    compiled = compile_target(minimal_tf_path)
    actual = sha256_file(minimal_tf_path)
    assert compiled["source_sha256"] == actual


def test_target_freeze_hash_preserved_real(real_tf_path):
    compiled = compile_target(real_tf_path)
    actual = sha256_file(real_tf_path)
    assert compiled["source_sha256"] == actual


def test_compiled_target_status_full(minimal_tf_path):
    compiled = compile_target(minimal_tf_path)
    assert compiled["status"] == "COMPILED", f"expected COMPILED; got {compiled['status']}; missing={compiled.get('missing_sections')}"
