"""Query compiler subsystem: AST -> backend-valid query text.

The compiler is responsible for:
  * preserving Boolean precedence (AND binds tighter than OR; NOT is unary)
  * emitting correct parentheses when mixing AND and OR
  * rejecting unsupported syntax
  * producing deterministic output
  * recording backend/compiler identity
"""
from .base import QueryCompiler, CompilationError
from .pubmed_ebsco import PubMedEbscoCompiler, compiler_name, compiler_version, compiler_sha256

__all__ = [
    "QueryCompiler", "CompilationError",
    "PubMedEbscoCompiler", "compiler_name", "compiler_version", "compiler_sha256",
]
