"""Query AST (P0 §8). Precedence is structural: AND binds tighter than OR; NOT is unary.

Parentheses are explicit children, not inferred.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any


VALID_FIELDS: frozenset[str] = frozenset({"TI", "AB", "AU", "TW", "ALL", "MESH", "DP", "LA"})


class QueryASTError(ValueError):
    pass


@dataclass
class AndNode:
    children: list["QueryNode"] = field(default_factory=list)


@dataclass
class OrNode:
    children: list["QueryNode"] = field(default_factory=list)


@dataclass
class NotNode:
    child: "QueryNode"


@dataclass
class PhraseNode:
    phrase: str


@dataclass
class FieldNode:
    field: str
    value: str


QueryNode = AndNode | OrNode | NotNode | PhraseNode | FieldNode


def _node_to_dict(n: QueryNode) -> dict[str, Any]:
    if isinstance(n, AndNode):
        return {"op": "AND", "children": [_node_to_dict(c) for c in n.children]}
    if isinstance(n, OrNode):
        return {"op": "OR", "children": [_node_to_dict(c) for c in n.children]}
    if isinstance(n, NotNode):
        return {"op": "NOT", "children": [_node_to_dict(n.child)]}
    if isinstance(n, PhraseNode):
        return {"op": "PHRASE", "phrase": n.phrase}
    if isinstance(n, FieldNode):
        return {"op": "FIELD", "field": n.field, "value": n.value}
    raise QueryASTError(f"unknown node: {n!r}")


def node_to_dict(n: QueryNode) -> dict[str, Any]:
    return _node_to_dict(n)


def from_dict(d: dict[str, Any]) -> QueryNode:
    if not isinstance(d, dict):
        raise QueryASTError(f"AST node must be a dict, got {type(d).__name__}")
    op = d.get("op")
    if op == "AND":
        ch = d.get("children") or []
        if len(ch) < 2:
            raise QueryASTError("AND requires at least 2 children")
        return AndNode(children=[from_dict(c) for c in ch])
    if op == "OR":
        ch = d.get("children") or []
        if len(ch) < 2:
            raise QueryASTError("OR requires at least 2 children")
        return OrNode(children=[from_dict(c) for c in ch])
    if op == "NOT":
        ch = d.get("children") or []
        if len(ch) != 1:
            raise QueryASTError("NOT requires exactly 1 child")
        return NotNode(child=from_dict(ch[0]))
    if op == "PHRASE":
        phrase = d.get("phrase")
        if not isinstance(phrase, str) or not phrase:
            raise QueryASTError("PHRASE requires a non-empty 'phrase' string")
        return PhraseNode(phrase=phrase)
    if op == "FIELD":
        fld = d.get("field")
        val = d.get("value")
        if fld not in VALID_FIELDS:
            raise QueryASTError(f"FIELD has invalid field tag: {fld!r}; valid: {sorted(VALID_FIELDS)}")
        if not isinstance(val, str) or not val:
            raise QueryASTError("FIELD requires non-empty 'value' string")
        return FieldNode(field=fld, value=val)
    raise QueryASTError(f"unknown AST op: {op!r}")


def validate(d: dict[str, Any]) -> None:
    """Idempotent structural validation; raises QueryASTError on first problem."""
    from_dict(d)
