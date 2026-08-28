"""SHA-256 utilities. No BOM (P0 §2).

The sidecar format is a single 64-hex-char line, optional trailing newline.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any


_HEX_RE = __import__("re").compile(r"^[a-f0-9]{64}$")


def sha256_file(path: Path) -> str:
    p = Path(path)
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(obj: Any) -> str:
    """Deterministic SHA-256 of a JSON object (sorted keys, no extra whitespace)."""
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def write_sidecar(path: Path, hex_hash: str) -> None:
    """Write a 64-hex SHA-256 sidecar without BOM."""
    p = Path(path)
    if not _HEX_RE.match(hex_hash or ""):
        raise ValueError(f"write_sidecar: not a 64-hex SHA-256: {hex_hash!r}")
    import io
    with open(p, "wb") as fh:
        fh.write((hex_hash + "\n").encode("utf-8"))


def read_sidecar_strict(path: Path) -> str:
    """Read a SHA-256 sidecar; return the 64-hex token. Strictly: file must be exactly 64 or 65 bytes
    (64 hex + LF), no BOM, no extra content.

    Raises:
        ValueError: if the sidecar does not strictly match the expected format.
    """
    p = Path(path)
    raw = p.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"sidecar has UTF-8 BOM: {p}")
    text = raw.decode("utf-8").rstrip("\n")
    if not _HEX_RE.match(text):
        raise ValueError(f"sidecar content is not a 64-hex SHA-256: {p} -> {text!r}")
    return text
