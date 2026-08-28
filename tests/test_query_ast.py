"""§16 risk test 7: malformed Query AST fails."""
from __future__ import annotations
import pytest
from mafs_p0.query_ast import from_dict, validate, QueryASTError


def test_and_requires_two_children():
    with pytest.raises(QueryASTError):
        from_dict({"op": "AND", "children": [{"op": "PHRASE", "phrase": "x"}]})


def test_not_requires_exactly_one_child():
    with pytest.raises(QueryASTError):
        from_dict({"op": "NOT", "children": [{"op": "PHRASE", "phrase": "x"}, {"op": "PHRASE", "phrase": "y"}]})


def test_unknown_op_rejected():
    with pytest.raises(QueryASTError):
        from_dict({"op": "NOPE"})


def test_field_must_be_known():
    with pytest.raises(QueryASTError):
        from_dict({"op": "FIELD", "field": "NOPE", "value": "x"})


def test_phrase_must_be_nonempty():
    with pytest.raises(QueryASTError):
        from_dict({"op": "PHRASE", "phrase": ""})


def test_valid_ast_roundtrip():
    ast = {
        "op": "AND", "children": [
            {"op": "OR", "children": [
                {"op": "PHRASE", "phrase": "a"},
                {"op": "PHRASE", "phrase": "b"},
            ]},
            {"op": "NOT", "children": [{"op": "PHRASE", "phrase": "c"}]},
        ]
    }
    validate(ast)
    n = from_dict(ast)
    assert n is not None
