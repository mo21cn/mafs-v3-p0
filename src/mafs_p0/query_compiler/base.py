"""Abstract base for query compilers (P0 §8)."""
from __future__ import annotations
import abc

from ..query_ast import QueryNode


class CompilationError(ValueError):
    pass


class QueryCompiler(abc.ABC):
    """Render a QueryAST into a backend-valid query string.

    Subclasses MUST preserve Boolean precedence, MUST emit parentheses when
    mixing AND and OR, MUST reject unsupported nodes with CompilationError,
    and MUST be deterministic.
    """

    backend: str
    compiler_name: str
    compiler_version: str

    @abc.abstractmethod
    def render(self, node: QueryNode) -> str: ...
