"""§16 risk test 8: Boolean precedence preserved.

When a query mixes AND and OR, the rendered output MUST parenthesize the OR
subexpression. Without parentheses, PubMed ESearch would parse "A AND B OR C" as
"(A AND B) OR C" (left-to-right), which is a different query.

The contract requirement is that the operator precedence is encoded structurally
in the AST, and the compiler emits parentheses when needed.
"""
from __future__ import annotations
import pytest
from mafs_p0.query_compiler.pubmed_ebsco import PubMedEbscoCompiler, compile_for_demo
from mafs_p0.query_compiler.base import CompilationError
from mafs_p0.query_ast import from_dict


def _render(ast: dict) -> str:
    return compile_for_demo(ast)["rendered_query"]


def test_or_only_no_parens_needed():
    r = _render({"op": "OR", "children": [
        {"op": "PHRASE", "phrase": "a"},
        {"op": "PHRASE", "phrase": "b"},
    ]})
    assert r == '"a" OR "b"'


def test_and_only_no_parens_needed():
    r = _render({"op": "AND", "children": [
        {"op": "PHRASE", "phrase": "a"},
        {"op": "PHRASE", "phrase": "b"},
    ]})
    assert r == '"a" AND "b"'


def test_mixed_and_or_emits_parens_around_or():
    r = _render({"op": "AND", "children": [
        {"op": "PHRASE", "phrase": "a"},
        {"op": "OR", "children": [
            {"op": "PHRASE", "phrase": "b"},
            {"op": "PHRASE", "phrase": "c"},
        ]},
    ]})
    # The OR child of AND must be parenthesized.
    assert r == '"a" AND ("b" OR "c")'


def test_mixed_or_and_emits_parens_around_and():
    r = _render({"op": "OR", "children": [
        {"op": "PHRASE", "phrase": "a"},
        {"op": "AND", "children": [
            {"op": "PHRASE", "phrase": "b"},
            {"op": "PHRASE", "phrase": "c"},
        ]},
    ]})
    assert r == '"a" OR ("b" AND "c")'


def test_not_parenthesizes_binary_child():
    r = _render({"op": "NOT", "children": [
        {"op": "AND", "children": [
            {"op": "PHRASE", "phrase": "a"},
            {"op": "PHRASE", "phrase": "b"},
        ]},
    ]})
    assert r == 'NOT ("a" AND "b")'


def test_field_tag_appended():
    r = _render({"op": "FIELD", "field": "TI", "value": "oxygen"})
    assert r == '"oxygen"[Title]'


def test_deterministic_output():
    ast = {
        "op": "AND", "children": [
            {"op": "OR", "children": [
                {"op": "PHRASE", "phrase": "a"},
                {"op": "PHRASE", "phrase": "b"},
            ]},
            {"op": "PHRASE", "phrase": "c"},
        ]
    }
    r1 = _render(ast)
    r2 = _render(ast)
    assert r1 == r2


def test_unsupported_field_rejected():
    with pytest.raises(CompilationError):
        compile_for_demo({"op": "FIELD", "field": "NOPE", "value": "x"})
