"""MAFS v3.0-P0 — Executable Plan Foundation.

Bounded package. See SKILL.md and docs/P0_SUMMARY.md for scope.

Version note: the in-package `__version__` uses PEP 440 (3.0.0.post0) for
`pip install -e ".[test]"` compliance. The schema_version constant
(``3.0-p0``) is a separate namespace and is preserved as-is across the
JSON Schemas and the runtime fingerprint.
"""
__version__ = "3.0.0.post0"
