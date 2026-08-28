"""Target Compiler (P0 §3).

Reads an immutable HO Target Freeze (markdown or yaml) and produces a CompiledTarget
JSON object. The original artifact is preserved byte-for-byte; only the compiled view
is generated.

Behavior:
  * All 11 required sections are extracted. If any required section cannot be extracted
    safely, ``status = TARGET_COMPILE_PARTIAL`` and the missing section is listed in
    ``missing_sections``. We never silently drop or reinterpret content.
  * Section extraction is rule-based on the source markdown structure. The compiler
    is intentionally narrow: it knows the contract's section names and the shape of
    the source Target Freeze. It is not a general markdown parser.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .util.hashing import sha256_file


# Map from compiled_target field -> markdown heading used in the canonical Target Freeze.
# Multiple acceptable headings per field (fallback). Headings are matched case-insensitive
# after stripping leading "#"s and surrounding whitespace.
SECTION_HEADINGS: dict[str, tuple[str, ...]] = {
    "root_question": ("Frozen Root Question", "Root Question"),
    "claims": ("Atomic Claims", "Claims"),
    "explicit_non_claims": ("Claims Explicitly Not Frozen as True", "Explicit Non-Claims"),
    "assumptions": ("Assumptions to Stress-Test", "Assumptions", "Known Assumptions"),
    "scope": ("Scope Boundaries", "Scope"),
    "required_search_axes": ("Required Candidate Search Axes", "Required Search Axes"),
    "high_risk_semantic_neighborhoods": ("High-Risk Semantic Neighborhoods",),
    "collision_gate_semantics": ("Gate Decision Semantics",),
    "downstream_permission": ("Downstream Permission Matrix",),
    "freeze_invariants": ("Freeze Invariants",),
}


def _split_by_h2(text: str) -> list[tuple[str, str]]:
    """Split markdown by '## N. Heading' or '## Heading' boundaries.

    Returns list of (heading, body) pairs in document order. The body of one section
    is the text between its heading line and the next heading line of the same or
    higher level.
    """
    lines = text.splitlines()
    out: list[tuple[str, str]] = []
    cur_heading: str | None = None
    cur_body: list[str] = []
    for line in lines:
        m = re.match(r"^##\s+(.*)$", line)
        if m:
            if cur_heading is not None:
                out.append((cur_heading, "\n".join(cur_body).rstrip("\n")))
            cur_heading = m.group(1).strip()
            cur_body = []
        else:
            if cur_heading is not None:
                cur_body.append(line)
    if cur_heading is not None:
        out.append((cur_heading, "\n".join(cur_body).rstrip("\n")))
    return out


def _match_heading(heading: str, candidates: tuple[str, ...]) -> bool:
    norm = heading.strip().lower()
    # Strip leading "N. " or "N.M. " section-number prefix common in canonical
    # Target Freeze documents (e.g. "2. Frozen Root Question" -> "frozen root question").
    norm = re.sub(r"^\d+(\.\d+)*\.\s*", "", norm)
    for c in candidates:
        c = c.lower()
        if norm == c or norm == c.rstrip("."):
            return True
    return False


def _extract_root_question(body: str) -> str:
    m = re.search(r"^>\s*(.+)$", body, flags=re.MULTILINE)
    if not m:
        raise ValueError("root question: no '> ...' line found in section body")
    return m.group(1).strip()


def _extract_claims(body: str) -> list[dict[str, str]]:
    """Parse claims block. Each claim starts with '### C{N} — <title>' followed by
    lines like '**Type:**', '**Proposition:**', '**Evidence that would change the framing:**'.
    """
    claims: list[dict[str, str]] = []
    blocks = re.split(r"^###\s+", body, flags=re.MULTILINE)
    for blk in blocks:
        blk = blk.strip()
        if not blk:
            continue
        head, *rest_lines = blk.splitlines()
        m = re.match(r"^(C\d+)\s*[—\-]\s*(.*)$", head.strip())
        if not m:
            continue
        cid = m.group(1)
        body_text = "\n".join(rest_lines)
        ctype = _grab_field(body_text, "Type")
        cprop = _grab_field(body_text, "Proposition")
        cevid = _grab_field(body_text, "Evidence that would change the framing")
        if cprop is None or cevid is None:
            raise ValueError(f"claim {cid}: missing 'Proposition' or 'Evidence that would change the framing'")
        claims.append({
            "id": cid,
            "proposition": cprop,
            "claim_type": ctype or "unspecified",
            "failure_condition": cevid,
        })
    if not claims:
        raise ValueError("claims section: no '### CN — ...' blocks found")
    return claims


def _grab_field(text: str, name: str) -> str | None:
    """Grab the value of a ``**Field:** value`` line.

    Accepts an optional leading bullet (``- ``) since the canonical Target Freeze
    formats fields as ``- **Type:** value`` inside each claim block.
    """
    m = re.search(rf"^[\-\*]?\s*\*\*{re.escape(name)}:\*\*\s*(.+?)\s*$", text, flags=re.MULTILINE)
    if not m:
        return None
    return m.group(1).strip()


def _extract_assumptions(body: str) -> list[str]:
    """Accept three common forms:

    1. Pipe-table rows:   ``| A1 | description | ... |``
    2. Bulleted lines:    ``- A1: description``  (also ``* A1. description``)
    3. Plain text:        ``A1: description``     (no leading bullet, no pipe)
    """
    out: list[str] = []

    # Form 1: pipe-table
    for m in re.finditer(r"^\|?\s*(A\d+)\s*\|\s*([^|]+?)\s*\|", body, flags=re.MULTILINE):
        out.append(f"{m.group(1)}: {m.group(2).strip()}")

    # Form 2: bulleted
    if not out:
        for m in re.finditer(r"^[\-\*]\s+(A\d+)\s*[:.]\s*(.+)$", body, flags=re.MULTILINE):
            out.append(f"{m.group(1)}: {m.group(2).strip()}")

    # Form 3: plain text (no bullet, no pipe)
    if not out:
        for m in re.finditer(r"^(A\d+)\s*[:.]\s*(.+)$", body, flags=re.MULTILINE):
            out.append(f"{m.group(1)}: {m.group(2).strip()}")

    if not out:
        raise ValueError(
            "assumptions section: no 'A1: ...' lines found "
            "(tried pipe-table, bulleted, and plain-text forms)"
        )
    return out


def _extract_scope(body: str) -> dict[str, list[str]]:
    in_scope: list[str] = []
    out_scope: list[str] = []
    section = ""
    for line in body.splitlines():
        if re.match(r"^###\s+In scope\b", line, flags=re.IGNORECASE):
            section = "in"
            continue
        if re.match(r"^###\s+Out of scope\b", line, flags=re.IGNORECASE):
            section = "out"
            continue
        m = re.match(r"^[\-\*]\s+(.+)$", line)
        if not m:
            continue
        item = m.group(1).strip()
        if section == "in":
            in_scope.append(item)
        elif section == "out":
            out_scope.append(item)
    if not in_scope and not out_scope:
        raise ValueError("scope section: no in/out bullets parsed")
    return {"in": in_scope, "out": out_scope}


def _extract_required_axes(body: str) -> list[dict[str, str]]:
    axes: list[dict[str, str]] = []
    for m in re.finditer(r"^(\d+)\.\s+\*\*([^*]+?):\*\*\s*(.*)$", body, flags=re.MULTILINE):
        axes.append({
            "id": f"A{m.group(1)}",
            "family": m.group(2).strip(),
            "proposition": m.group(3).strip(),
        })
    if not axes:
        raise ValueError("required_search_axes section: no numbered 'N. **Family:** proposition' lines")
    return axes


def _extract_bulleted_list(body: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r"^[\-\*]\s+(.+)$", body, flags=re.MULTILINE):
        s = m.group(1).strip()
        if s:
            out.append(s)
    if not out:
        # fall back to numbered list
        for m in re.finditer(r"^\d+\.\s+(.+)$", body, flags=re.MULTILINE):
            s = m.group(1).strip()
            if s:
                out.append(s)
    if not out:
        raise ValueError("expected bulleted/numbered list; none found")
    return out


def _extract_downstream(full_text: str) -> dict[str, Any]:
    """Extract ``downstream_allowed`` and ``stop_downstream``.

    Searches two patterns across the WHOLE document (not just the section body,
    because the canonical Target Freeze places these values in the §0 front-matter
    "Frozen value" table, not in the §12 "Downstream Permission Matrix" body):

      A) Pipe-table row containing ``downstream_allowed`` / ``stop_downstream`` tokens
      B) Front-matter Frozen value rows: ``Initial downstream permission`` /
         ``Initial stop-downstream flag``
    """
    allowed = {"true": True, "false": False}
    out: dict[str, Any] = {}

    # Pattern A: explicit pipe-table rows.
    for m in re.finditer(
        r"^\|\s*`?(downstream_allowed|stop_downstream)`?\s*\|\s*`?(true|false)`?\s*\|",
        full_text,
        flags=re.MULTILINE | re.IGNORECASE,
    ):
        key = m.group(1).lower()
        val = m.group(2).lower()
        if val in allowed:
            out[key] = allowed[val]

    # Pattern B: front-matter "Initial downstream permission" / "Initial stop-downstream flag".
    if "downstream_allowed" not in out:
        m1 = re.search(
            r"Initial\s+downstream\s+permission[^\n]*\|\s*`?(true|false)`?",
            full_text,
            flags=re.IGNORECASE,
        )
        if m1:
            out["downstream_allowed"] = m1.group(1).lower() == "true"
    if "stop_downstream" not in out:
        m2 = re.search(
            r"Initial\s+stop-downstream\s+flag[^\n]*\|\s*`?(true|false)`?",
            full_text,
            flags=re.IGNORECASE,
        )
        if m2:
            out["stop_downstream"] = m2.group(1).lower() == "true"

    if "downstream_allowed" not in out or "stop_downstream" not in out:
        raise ValueError(
            "downstream_permission: must declare downstream_allowed and stop_downstream (true/false); "
            "neither pipe-table rows nor front-matter 'Initial downstream permission' / "
            "'Initial stop-downstream flag' rows were found"
        )
    return out


def _extract_freeze_invariants(body: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r"^\d+\.\s+(.+)$", body, flags=re.MULTILINE):
        s = m.group(1).strip()
        if s:
            out.append(s)
    if not out:
        raise ValueError("freeze_invariants section: no numbered invariants")
    return out


def _extract_collision_semantics(body: str) -> list[str]:
    """Each non-empty bullet becomes one line of collision/gate semantics."""
    return _extract_bulleted_list(body)


def _extract_high_risk(body: str) -> list[str]:
    return _extract_bulleted_list(body)


# Required sections for FULLY-COMPILED status.
REQUIRED_FIELDS: tuple[str, ...] = (
    "root_question", "claims", "assumptions", "scope", "required_search_axes",
    "collision_gate_semantics", "downstream_permission", "freeze_invariants",
)


def compile_target(source_artifact: Path) -> dict[str, Any]:
    """Compile a Target Freeze artifact into a CompiledTarget dict.

    Raises:
        FileNotFoundError: if ``source_artifact`` does not exist.
        ValueError: on parse / extraction errors.
    """
    src = Path(source_artifact)
    if not src.is_file():
        raise FileNotFoundError(f"Target Freeze artifact not found: {src}")
    text = src.read_text(encoding="utf-8")
    src_hash = sha256_file(src)
    src_bytes = src.stat().st_size

    sections = dict(_split_by_h2(text))
    missing: list[str] = []
    out: dict[str, Any] = {}

    for field, candidates in SECTION_HEADINGS.items():
        body = None
        for heading, b in sections.items():
            if _match_heading(heading, candidates):
                body = b
                break
        if body is None:
            if field in REQUIRED_FIELDS:
                missing.append(field)
                continue
            # optional field; leave as default
            if field == "explicit_non_claims":
                out[field] = []
            elif field == "high_risk_semantic_neighborhoods":
                out[field] = []
            continue
        try:
            if field == "root_question":
                out[field] = _extract_root_question(body)
            elif field == "claims":
                out[field] = _extract_claims(body)
            elif field == "assumptions":
                out[field] = _extract_assumptions(body)
            elif field == "scope":
                out[field] = _extract_scope(body)
            elif field == "required_search_axes":
                out[field] = _extract_required_axes(body)
            elif field == "high_risk_semantic_neighborhoods":
                out[field] = _extract_high_risk(body)
            elif field == "collision_gate_semantics":
                out[field] = _extract_collision_semantics(body)
            elif field == "downstream_permission":
                # Special case: the canonical Target Freeze places these values in
                # the §0 front-matter table. Search the whole document, not just the
                # section body.
                out[field] = _extract_downstream(text)
            elif field == "freeze_invariants":
                out[field] = _extract_freeze_invariants(body)
            elif field == "explicit_non_claims":
                out[field] = _extract_bulleted_list(body)
            else:
                raise ValueError(f"unknown compiled_target field: {field}")
        except ValueError as e:
            if field in REQUIRED_FIELDS:
                missing.append(field)
                continue
            raise

    out["schema_version"] = "3.0-p0"
    out["source_artifact"] = str(src.resolve())
    out["source_sha256"] = src_hash
    out["source_bytes"] = src_bytes
    out["compiler_version"] = "3.0.0-p0"
    out["compiled_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if missing:
        out["status"] = "TARGET_COMPILE_PARTIAL"
        out["missing_sections"] = missing
    else:
        out["status"] = "COMPILED"
        out.pop("missing_sections", None)
    return out
