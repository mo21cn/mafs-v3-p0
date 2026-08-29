"""MAFS v3.0-P1.5 — Thin Crossref-Specific Query Renderer.

This is a thin provider-specific rendering layer. It does NOT
replace the model's scientific search reasoning with a deterministic
planner. Its sole responsibility is to map a compact search intent
(author, year, title clue, concepts) into Crossref-native URL
parameters, and to expose a small bounded fallback ladder when one
exact rendering is too restrictive.

The renderer is governed by P1.5 contract sections §3 (What the
Model Owns), §4 (What the Crossref Renderer Owns), §5 (Minimal
Fallback Ladder), and §10 (No Generic Query Intelligence Layer):

  - the model / MAFS cognitive layer remains responsible for
    scientific intent, query concepts, author / year / title clues,
    and structural search reasoning;
  - the renderer accepts a compact intent such as
        intent:
          author: "von Reyn"
          year: 2014
          concepts: ["Drosophila", "Giant Fiber", "action selection"]
    and produces a small list of Crossref URL-param dicts, one per
    fallback rung;
  - each rung preserves the same original search intent; the ladder
    is bounded (3 rungs max);
  - the renderer is not an autonomous research planner.

Each rendering is recorded with a stable ``rendering_path`` label
so the orchestrator can audit which rung produced each recovered
candidate.
"""
from __future__ import annotations
import json
import urllib.parse
from dataclasses import dataclass, field
from typing import Any


# ---- Bounded ladder rung definitions --------------------------------------

LADDER_RUNG_A = "A_author_year_bibliographic"  # query.author + year + title/concept
LADDER_RUNG_B = "B_author_year_strongest"      # author + year + single strongest phrase
LADDER_RUNG_C = "C_title_exact"                # exact / near-exact title lookup
LADDER_RUNG_LEGACY = "legacy_pubmed_ebsco_query"  # pre-P1.5 path (for comparison / fallback)

LADDER_RUNG_ORDER = (LADDER_RUNG_A, LADDER_RUNG_B, LADDER_RUNG_C)


@dataclass
class RenderedQuery:
    """One rung of the Crossref fallback ladder."""
    rendering_path: str
    url_params: dict[str, str]
    notes: str = ""


@dataclass
class SearchIntent:
    """Compact search intent (P1.5 contract §3)."""
    author: str | None = None
    year: int | None = None
    title: str | None = None       # primary title phrase (single phrase)
    concepts: list[str] = field(default_factory=list)  # additional concept terms

    def has_structured_signal(self) -> bool:
        return bool(self.author or self.year or self.title or self.concepts)


# ---- Heuristic extraction from QueryAST -----------------------------------

def extract_intent_from_query_representation(
    qre: dict, *, fallback_author: str | None = None, fallback_year: int | None = None,
    fallback_title: str | None = None, fallback_concepts: list[str] | None = None,
) -> SearchIntent:
    """Extract a compact SearchIntent from a legacy QueryAST.

    The QueryAST (op: AND/OR/PHRASE/FIELD) is the pre-P1.5 representation.
    For P1.5 we add a structured intent field to each SearchOrder, but
    the orchestrator also wants to derive an intent heuristically from
    the AST so that the renderer can be tested without requiring
    SearchOrder authors to manually populate the intent for every
    future Q.

    The heuristic walks the AST and looks for:
      - a 4-digit year token (used for the year field);
      - a PHRASE node that looks like a person name (CamelCase,
        multi-word) or that is explicitly named via the SearchOrder
        fallback_author arg;
      - PHRASE nodes that contain "giant fiber", "hemibrain",
        "connectome", "spike", "action selection", etc. — these are
        treated as concept terms;
      - any remaining PHRASE becomes part of the title hint (the
        longest one).

    The SearchOrder-level fallback args (fallback_author, etc.) take
    precedence over the AST heuristic; this lets the orchestrator
    pass verified metadata that the AST may not contain.
    """
    phrases: list[str] = []
    if isinstance(qre, dict):
        op = qre.get("op")
        if op == "PHRASE":
            phrase = qre.get("phrase")
            if isinstance(phrase, str):
                phrases.append(phrase)
        for child in qre.get("children", []) or []:
            phrases.extend(extract_intent_from_query_representation(child).concepts)
            # also collect titles / years / authors if the child
            # recurses (handled by the parent below)
    # Year detection
    year = fallback_year
    title_hint = fallback_title
    author = fallback_author
    concept_terms: list[str] = list(fallback_concepts or [])
    for p in phrases:
        if p.isdigit() and len(p) == 4 and 1900 <= int(p) <= 2100 and year is None:
            year = int(p)
        elif any(t in p.lower() for t in ("giant fiber", "hemibrain", "connectome",
                                            "spike-timing", "action selection",
                                            "descending", "sensory-motor")):
            if p not in concept_terms:
                concept_terms.append(p)
        else:
            if title_hint is None and len(p.split()) <= 6:
                title_hint = p
            elif p not in concept_terms and len(p.split()) <= 4:
                concept_terms.append(p)
    return SearchIntent(
        author=author,
        year=year,
        title=title_hint,
        concepts=concept_terms,
    )


# ---- Thin Crossref-native rendering ----------------------------------------

def _date_filter(year: int | None) -> str | None:
    """Build Crossref `filter=from-pub-date:...,until-pub-date:...` from a year."""
    if year is None:
        return None
    return f"from-pub-date:{year:04d}-01-01,until-pub-date:{year:04d}-12-31"


def _join_phrases(phrases: list[str]) -> str:
    """Join a list of concept phrases into a Crossref `query.title` value
    (space-separated; Crossref splits on whitespace)."""
    return " ".join(p for p in phrases if p)


def _rung_A(intent: SearchIntent) -> RenderedQuery | None:
    """Rung A: query.author + year date filter + query.title with concept terms."""
    if not (intent.author and intent.year is not None):
        return None
    title_parts: list[str] = []
    if intent.title:
        title_parts.append(intent.title)
    title_parts.extend(intent.concepts[:3])  # cap concept terms
    params: dict[str, str] = {
        "query.author": intent.author,
        "query.title": _join_phrases(title_parts) if title_parts else "",
    }
    date_f = _date_filter(intent.year)
    if date_f:
        params["filter"] = date_f
    return RenderedQuery(
        rendering_path=LADDER_RUNG_A,
        url_params=params,
        notes=f"author={intent.author!r} year={intent.year} title={_join_phrases(title_parts)!r}",
    )


def _rung_B(intent: SearchIntent) -> RenderedQuery | None:
    """Rung B: author + year + single strongest phrase (no broad title
    multi-phrase). Used when rung A's multi-phrase title is too
    restrictive."""
    if not (intent.author and intent.year is not None):
        return None
    strongest = intent.title or (intent.concepts[0] if intent.concepts else None)
    if not strongest:
        return None
    params = {
        "query.author": intent.author,
        "query.title": strongest,
    }
    date_f = _date_filter(intent.year)
    if date_f:
        params["filter"] = date_f
    return RenderedQuery(
        rendering_path=LADDER_RUNG_B,
        url_params=params,
        notes=f"author={intent.author!r} year={intent.year} strongest_phrase={strongest!r}",
    )


def _rung_C(intent: SearchIntent) -> RenderedQuery | None:
    """Rung C: exact / near-exact title lookup when a title clue exists.
    Uses query.bibliographic with the title only (no author/year filter);
    Crossref's bibliographic field tolerates quoted phrases well."""
    if not intent.title:
        return None
    return RenderedQuery(
        rendering_path=LADDER_RUNG_C,
        url_params={"query.bibliographic": intent.title},
        notes=f"title={intent.title!r} (exact bibliographic lookup)",
    )


def _rung_legacy(intent: SearchIntent, compiled_query: str) -> RenderedQuery:
    """Legacy pre-P1.5 path: the full-text `query=` parameter. Always
    included as the last rung so the regression-prevention test can
    verify the ladder still works when the new rungs fail."""
    return RenderedQuery(
        rendering_path=LADDER_RUNG_LEGACY,
        url_params={"query": compiled_query},
        notes="legacy pubmed_ebsco-style query (preserved for audit)",
    )


def render_intent(intent: SearchIntent, *, compiled_query: str = "", top_k: int = 5,
                  include_legacy: bool = True) -> list[RenderedQuery]:
    """Render a compact SearchIntent into a bounded list of
    Crossref-native URL-param dicts, plus optionally the legacy
    full-text query as the final rung.

    The returned list is the fallback ladder; the orchestrator
    should try each rung in order, recording which one produced the
    recovered candidate.

    The ladder is bounded:
      rung A: author + year + title/concept
      rung B: author + year + single strongest phrase
      rung C: exact title bibliographic lookup
      rung LEGACY: (optional) pubmed_ebsco-style query

    Rungs are only included when they can be constructed from the
    intent. If a rung is None, it is skipped silently.
    """
    ladder: list[RenderedQuery] = []
    for rung_fn in (_rung_A, _rung_B, _rung_C):
        r = rung_fn(intent)
        if r is not None:
            # top_k shared across all rungs; the orchestrator can override.
            r.url_params = {**r.url_params, "rows": str(top_k)}
            ladder.append(r)
    if include_legacy and compiled_query:
        legacy = _rung_legacy(intent, compiled_query)
        legacy.url_params = {**legacy.url_params, "rows": str(top_k)}
        ladder.append(legacy)
    return ladder


def render_query_url(base_url: str, rendered: RenderedQuery) -> str:
    """Build a Crossref REST URL from a RenderedQuery."""
    params = dict(rendered.url_params)
    return f"{base_url.rstrip('/')}/works?{urllib.parse.urlencode(params)}"


# ---- Audit persistence -----------------------------------------------------

def rendered_query_to_audit_dict(rendered: RenderedQuery) -> dict:
    """Serialize a RenderedQuery for the rendered_queries.json artifact."""
    return {
        "rendering_path": rendered.rendering_path,
        "url_params": dict(rendered.url_params),
        "notes": rendered.notes,
        "url": render_query_url("https://api.crossref.org", rendered),
    }
