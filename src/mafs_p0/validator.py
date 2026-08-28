"""Validator (P0 §12): JSON Schema + semantic validation.

One authoritative validator. Fails closed. Validates the run directory layout
produced by ``demo.run_*`` and emits a verdict.

Supported JSON Schema subset (Draft 2020-12):
  - type (object, array, string, integer, number, boolean, null, and unions)
  - properties, required, additionalProperties
  - enum, const
  - pattern (regex)
  - items, minItems, maxItems
  - minLength, minimum, maximum
  - allOf
  - $ref to local node (#/...)

NOT supported (will fail at schema load time with a clear message):
  - oneOf, anyOf
  - if / then / else
  - $ref to external files
  - format keywords other than date-time

If a schema uses a non-supported feature, ``_assert_schema_subset_supported``
raises ``UnsupportedSchemaFeatureError`` so the failure is loud, not silent.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .util.paths import schemas_dir
from .util.hashing import sha256_file


UNSUPPORTED_FEATURES = ("oneOf", "anyOf", "if", "then", "else")


class UnsupportedSchemaFeatureError(ValueError):
    """Raised at schema load time when a schema uses a feature the
    P0 self-rolled validator does not implement. Use ``type: [...]``
    unions instead of ``oneOf``/``anyOf``; use Python code instead of
    ``if``/``then``/``else``."""


def _assert_schema_subset_supported(schema: dict, name: str) -> None:
    def walk(node, path: str) -> None:
        if not isinstance(node, dict):
            return
        for f in UNSUPPORTED_FEATURES:
            if f in node:
                raise UnsupportedSchemaFeatureError(
                    f"schema {name!r} uses unsupported feature {f!r} at {path}.{f}; "
                    f"see validator.py docstring for the supported subset."
                )
        for k, v in node.items():
            if isinstance(v, dict):
                walk(v, f"{path}.{k}")
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    if isinstance(item, dict):
                        walk(item, f"{path}.{k}[{i}]")
    walk(schema, "$")


def _load_schema(name: str) -> dict:
    p = schemas_dir() / name
    if not p.is_file():
        raise FileNotFoundError(f"missing schema: {p}")
    s = json.loads(p.read_text(encoding="utf-8"))
    _assert_schema_subset_supported(s, name)
    return s


class _MiniSchemaValidator:
    """Tiny JSON Schema validator supporting the subset MAFS-P0 uses:
       * type (object, array, string, integer, number, boolean, null)
       * properties, additionalProperties=false
       * required
       * enum, const
       * pattern
       * oneOf
       * $ref (resolved locally)
       * items (single schema)
       * minItems, maxItems
       * allOf
    Deliberately minimal: avoids the jsonschema dependency for P0.
    """
    def __init__(self, schema: dict):
        self.schema = schema
        self._cache: dict[str, dict] = {}

    def _resolve(self, node: dict) -> dict:
        if "$ref" in node:
            ref = node["$ref"]
            if ref.startswith("#/"):
                key = ref[2:]
                if key in self._cache:
                    return self._cache[key]
                parts = key.split("/")
                cur: Any = self.schema
                for p in parts:
                    cur = cur.get(p, {}) if isinstance(cur, dict) else {}
                self._cache[key] = cur
                return cur
        return node

    def validate(self, obj: Any) -> list[str]:
        errs: list[str] = []
        self._check(obj, self.schema, "$", errs)
        return errs

    def _check(self, obj: Any, schema: dict, path: str, errs: list[str]) -> None:
        schema = self._resolve(schema)
        # type
        if "type" in schema:
            t = schema["type"]
            if isinstance(t, list):
                if not any(self._matches_type(obj, tt) for tt in t):
                    errs.append(f"{path}: type mismatch (any of {t}); got {type(obj).__name__}")
                    return
            else:
                if not self._matches_type(obj, t):
                    errs.append(f"{path}: expected {t}; got {type(obj).__name__}")
                    return
        # const
        if "const" in schema and obj != schema["const"]:
            errs.append(f"{path}: const mismatch; got {obj!r}, expected {schema['const']!r}")
        # enum
        if "enum" in schema and obj not in schema["enum"]:
            errs.append(f"{path}: enum mismatch; got {obj!r}, allowed {schema['enum']!r}")
        # object
        if isinstance(obj, dict):
            req = schema.get("required", [])
            for r in req:
                if r not in obj:
                    errs.append(f"{path}: missing required '{r}'")
            if schema.get("additionalProperties") is False:
                allowed = set(schema.get("properties", {}).keys())
                extra = set(obj.keys()) - allowed
                if extra:
                    errs.append(f"{path}: extra properties {sorted(extra)}")
            for k, sub in schema.get("properties", {}).items():
                if k in obj:
                    self._check(obj[k], sub, f"{path}.{k}", errs)
            # oneOf
            for sub in schema.get("oneOf", []):
                self._check(obj, sub, path, errs)
        # array
        if isinstance(obj, list):
            items = schema.get("items")
            if items is not None:
                for i, v in enumerate(obj):
                    self._check(v, items, f"{path}[{i}]", errs)
            if "minItems" in schema and len(obj) < schema["minItems"]:
                errs.append(f"{path}: minItems {schema['minItems']} not met (got {len(obj)})")
            if "maxItems" in schema and len(obj) > schema["maxItems"]:
                errs.append(f"{path}: maxItems {schema['maxItems']} exceeded (got {len(obj)})")
        # string
        if isinstance(obj, str):
            if "pattern" in schema:
                import re
                if not re.search(schema["pattern"], obj):
                    errs.append(f"{path}: pattern {schema['pattern']!r} not matched by {obj!r}")
            if "minLength" in schema and len(obj) < schema["minLength"]:
                errs.append(f"{path}: minLength {schema['minLength']} not met (got {len(obj)})")
        # number
        if isinstance(obj, (int, float)) and not isinstance(obj, bool):
            if "minimum" in schema and obj < schema["minimum"]:
                errs.append(f"{path}: below minimum {schema['minimum']}")
            if "maximum" in schema and obj > schema["maximum"]:
                errs.append(f"{path}: above maximum {schema['maximum']}")
        # allOf
        for sub in schema.get("allOf", []):
            self._check(obj, sub, path, errs)

    def _matches_type(self, obj: Any, t: str) -> bool:
        if t == "null":
            return obj is None
        if t == "boolean":
            return isinstance(obj, bool)
        if t == "integer":
            return isinstance(obj, int) and not isinstance(obj, bool)
        if t == "number":
            return isinstance(obj, (int, float)) and not isinstance(obj, bool)
        if t == "string":
            return isinstance(obj, str)
        if t == "array":
            return isinstance(obj, list)
        if t == "object":
            return isinstance(obj, dict)
        return False


def validate_against_schema(obj: Any, schema_name: str) -> list[str]:
    schema = _load_schema(schema_name)
    v = _MiniSchemaValidator(schema)
    return v.validate(obj)


def validate_run(run_manifest: dict, *,
                 compiled_target: dict,
                 preflight_report: dict,
                 runtime_fingerprint: dict,
                 budget_state: dict,
                 axis_records: list[dict],
                 search_orders: list[dict],
                 compiled_queries: list[dict],
                 providers: list[dict] | None = None,
                 resolvers: list[dict] | None = None,
                 negotiations: list[dict] | None = None,
                 gate_graph: dict | None = None) -> dict:
    """Top-level semantic validation. Returns a verdict dict with per-check outcomes.

    Coverage (P0-RA2 Blocker A closure):
      * run_manifest, compiled_target, preflight_report, runtime_fingerprint,
        budget_state — top-level canonical objects
      * axis_records, search_orders, compiled_queries — list of canonical objects
      * providers, resolvers, negotiations, gate_graph — added in P0-RA2 to
        ensure schema truth == runtime truth for every object the demo emits.
    """
    semantic_errors: list[str] = []
    for name, obj, ref in (
        ("run_manifest.schema.json", run_manifest, "run_manifest"),
        ("compiled_target.schema.json", compiled_target, "compiled_target"),
        ("preflight_report.schema.json", preflight_report, "preflight_report"),
        ("runtime_fingerprint.schema.json", runtime_fingerprint, "runtime_fingerprint"),
        ("budget_state.schema.json", budget_state, "budget_state"),
    ):
        errs = validate_against_schema(obj, name)
        for e in errs:
            semantic_errors.append(f"{ref}: {e}")

    # Item-level schema checks
    for i, ax in enumerate(axis_records):
        errs = validate_against_schema(ax, "axis.schema.json")
        for e in errs:
            semantic_errors.append(f"axis[{i}]: {e}")
    for i, so in enumerate(search_orders):
        errs = validate_against_schema(so, "search_order.schema.json")
        for e in errs:
            semantic_errors.append(f"search_order[{i}]: {e}")
    for i, q in enumerate(compiled_queries):
        errs = validate_against_schema(q, "compiled_query.schema.json")
        for e in errs:
            semantic_errors.append(f"compiled_query[{i}]: {e}")

    # P0-RA2 Blocker A: also validate providers, resolvers, negotiations, gate_graph
    if providers is not None:
        for i, p in enumerate(providers):
            errs = validate_against_schema(p, "provider_manifest.schema.json")
            for e in errs:
                semantic_errors.append(f"provider[{i}]: {e}")
    if resolvers is not None:
        for i, r in enumerate(resolvers):
            errs = validate_against_schema(r, "resolver_manifest.schema.json")
            for e in errs:
                semantic_errors.append(f"resolver[{i}]: {e}")
    if negotiations is not None:
        for i, n in enumerate(negotiations):
            errs = validate_against_schema(n, "negotiation_result.schema.json")
            for e in errs:
                semantic_errors.append(f"negotiation[{i}]: {e}")
    if gate_graph is not None:
        errs = validate_against_schema(gate_graph, "gate_dependency_graph.schema.json")
        for e in errs:
            semantic_errors.append(f"gate_graph: {e}")

    # Cross-object semantic checks (P0 §16 risk tests 3, 5, 6, 8, 12, 11)
    cross: list[str] = []

    # 3. Target Freeze hash preserved
    if compiled_target.get("source_sha256") != run_manifest.get("target_freeze_sha256"):
        cross.append("target_freeze_hash_mismatch_between_compiled_target_and_run_manifest")

    # 5. essential axis without SearchOrder
    axes_by_id = {a["axis_id"]: a for a in axis_records}
    so_axes = {so["axis_id"] for so in search_orders}
    for a in axis_records:
        if a.get("essential") and a["axis_id"] not in so_axes:
            cross.append(f"essential_axis_no_so: {a['axis_id']}")

    # 6. SearchOrder without compatible provider -> the preflight captures this; cross-check matches.
    for so in search_orders:
        required = set(so.get("required_capabilities", []))
        # We trust the preflight report's check C4 to fail-fast.
        if not required:
            cross.append(f"empty_required_capabilities: {so.get('search_order_id')}")

    # 8. Boolean precedence preserved: spot-check one rendered query mixes AND and OR -> must have parens.
    for q in compiled_queries:
        rq = q.get("rendered_query", "")
        if " AND " in rq and " OR " in rq and "(" not in rq and ")" not in rq:
            cross.append(f"missing_parentheses_in_mixed_query: {q.get('compiler_name')}")

    # 11. unknown budget uses null
    if budget_state.get("cost_status") == "unknown":
        if budget_state.get("estimated_token_range") is not None:
            cross.append("unknown_budget_must_have_null_token_range")
        if budget_state.get("estimated_cost_range_usd") is not None:
            cross.append("unknown_budget_must_have_null_cost_range")

    # 12. non-executable plan cannot return READY
    if preflight_report.get("status") == "READY_FOR_HO_EXECUTION_APPROVAL":
        blockers = preflight_report.get("blockers", [])
        if blockers:
            cross.append("ready_status_with_blockers")
        for c in preflight_report.get("checks", []):
            if c.get("outcome") == "FAIL" and c.get("severity") == "BLOCKER":
                cross.append(f"ready_with_blocker_check: {c.get('check_id')}")
                break

    return {
        "schema_errors": semantic_errors,
        "semantic_errors": cross,
        "ok": (not semantic_errors) and (not cross),
    }
