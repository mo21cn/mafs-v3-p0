"""PubMed ESearch URL-syntax query compiler.

Maps QueryAST -> a single query string that can be passed to PubMed ESearch
``term`` parameter (or, equivalently, a literal boolean expression that
PubMed's term parser understands).

Field tags:
  TI   -> [Title]
  AB   -> [Title/Abstract]   (we approximate to Title/Abstract because ESearch
                              does not have a standalone AB tag; TW also covers this)
  AU   -> [Author]
  TW   -> [Text Word]
  ALL  -> [All Fields]
  MESH -> [MeSH Terms]
  DP   -> [Date - Publication]
  LA   -> [Language]

Boolean operators: AND, OR, NOT (PubMed requires uppercase).
Parentheses are emitted when an AND has an OR child, or vice versa.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Callable

from ..query_ast import (
    AndNode, OrNode, NotNode, PhraseNode, FieldNode, QueryNode,
    QueryASTError,
)
from ..util.hashing import sha256_bytes
from .base import QueryCompiler, CompilationError


COMPILER_NAME = "pubmed_ebsco"
COMPILER_VERSION = "3.0.0-p0"


# Compute a stable SHA-256 of the compiler's own source. Used for runtime fingerprint
# (P0 §11). We hash the file once and cache it at import time.
def _compiler_self_sha256() -> str:
    import pathlib
    here = pathlib.Path(__file__).resolve()
    return sha256_bytes(here.read_bytes())


compiler_name = COMPILER_NAME
compiler_version = COMPILER_VERSION
compiler_sha256 = _compiler_self_sha256()


# Map our internal field names to PubMed ESearch tag names.
FIELD_TAGS: dict[str, str] = {
    "TI": "[Title]",
    "AB": "[Title/Abstract]",   # nearest valid ESearch tag
    "AU": "[Author]",
    "TW": "[Text Word]",
    "ALL": "[All Fields]",
    "MESH": "[MeSH Terms]",
    "DP": "[Date - Publication]",
    "LA": "[Language]",
}


class PubMedEbscoCompiler(QueryCompiler):
    backend = "pubmed_esearch"
    compiler_name = COMPILER_NAME
    compiler_version = COMPILER_VERSION

    def render(self, node: QueryNode) -> str:
        try:
            return _render(node)
        except QueryASTError as e:
            raise CompilationError(str(e)) from e


def _needs_parens(child: QueryNode, parent_op: str) -> bool:
    """Decide whether child of an AND/OR needs parentheses.

    Rules:
      * Parent is AND: OR child must be parenthesized; NOT child must be parenthesized.
      * Parent is OR:  AND child must be parenthesized; NOT child must be parenthesized.
    """
    if isinstance(child, (AndNode, OrNode, NotNode)) and not isinstance(child, type(node_for_op(parent_op))):
        return True
    return False


def node_for_op(op: str):
    return {"AND": AndNode, "OR": OrNode}[op]


def _render(n: QueryNode) -> str:
    if isinstance(n, AndNode):
        return _render_n_ary(n.children, "AND")
    if isinstance(n, OrNode):
        return _render_n_ary(n.children, "OR")
    if isinstance(n, NotNode):
        inner = _render(n.child)
        # If child is binary (AND/OR), always parenthesize.
        if isinstance(n.child, (AndNode, OrNode)):
            inner = f"({inner})"
        return f"NOT {inner}"
    if isinstance(n, PhraseNode):
        return _escape_phrase(n.phrase)
    if isinstance(n, FieldNode):
        return _render_field(n)
    raise QueryASTError(f"unknown AST node type: {type(n).__name__}")


def _render_n_ary(children: list[QueryNode], op: str) -> str:
    if len(children) < 2:
        raise QueryASTError(f"{op} requires at least 2 children")
    rendered: list[str] = []
    for c in children:
        piece = _render(c)
        if isinstance(c, (OrNode, AndNode)) and _op_of(c) != op:
            piece = f"({piece})"
        elif isinstance(c, NotNode):
            piece = f"({piece})"
        rendered.append(piece)
    return f" {op} ".join(rendered)


def _op_of(n: QueryNode) -> str:
    if isinstance(n, AndNode): return "AND"
    if isinstance(n, OrNode): return "OR"
    if isinstance(n, NotNode): return "NOT"
    return ""


def _escape_phrase(s: str) -> str:
    # PubMed ESearch term requires double-quoted phrases; escape embedded quotes.
    s = s.strip()
    if not s:
        raise QueryASTError("PHRASE value is empty")
    if '"' in s:
        s = s.replace('"', '\\"')
    return f'"{s}"'


def _render_field(f: FieldNode) -> str:
    tag = FIELD_TAGS.get(f.field)
    if tag is None:
        raise CompilationError(f"unsupported field for PubMed: {f.field!r}")
    val = f.value.strip()
    if not val:
        raise CompilationError(f"FIELD value is empty for {f.field!r}")
    if any(ch in val for ch in ['"', '[', ']']):
        # Already-tagged values are passed through with explicit quotes.
        return f'{val}{tag}'
    return f'"{val}"{tag}'


def compile_for_demo(ast_dict: dict) -> dict:
    """Convenience: validate AST, compile, return CompiledQuery JSON dict (P0 §8.11)."""
    from ..query_ast import from_dict, validate as validate_ast, QueryASTError
    from ..util.hashing import sha256_json
    try:
        validate_ast(ast_dict)
        node = from_dict(ast_dict)
    except QueryASTError as e:
        # Surface AST errors as CompilationError so callers have a single error type.
        raise CompilationError(f"AST validation failed: {e}") from e
    c = PubMedEbscoCompiler()
    try:
        rendered = c.render(node)
    except QueryASTError as e:
        raise CompilationError(str(e)) from e
    cq = {
        "schema_version": "3.0-p0",
        "query_ast_sha256": sha256_json(ast_dict),
        "backend": c.backend,
        "rendered_query": rendered,
        "compiler_name": c.compiler_name,
        "compiler_version": c.compiler_version,
        "validation_status": "valid",
    }
    return cq
