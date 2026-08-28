"""One-time anchor identity resolution (RA1 §1).

For each anchor in ``benchmarks/blood_oxygen_ovary/known_anchors.json``,
attempt to resolve a stable scholarly identifier by querying
Crossref's /works?query.biblio API with the title_hint. If the
top-ranked Crossref result has a SequenceMatcher ratio >= 0.9 against
the title_hint, accept its DOI; otherwise mark the anchor
``ANCHOR_IDENTITY_UNRESOLVED``.

This is a GROUND TRUTH generation step, not part of the benchmark
itself. The benchmark reads the resulting canonical anchors.

The contract is explicit:
  - never fabricate DOI/PMID/authors/year
  - if DOI/PMID is unavailable, verified canonical title + author/year
    may serve as fallback identity
  - ``title_hint`` and ``match_keys`` may remain for query generation only
  - unresolved anchors are excluded from denominator-based recall
"""
from __future__ import annotations
import difflib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


USER_AGENT = "MAFS-v3.0-Replay-A-RA1/0.1 (Local-Claw; mailto:mo21cn@example.invalid)"
TITLE_SIM_THRESHOLD = 0.9
HTTP_TIMEOUT = 30


def _normalize(t: str | None) -> str:
    if not t:
        return ""
    t = t.lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _title_similarity(a: str | None, b: str | None) -> float:
    a, b = _normalize(a), _normalize(b)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _http_get_json(url: str) -> dict | None:
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, Exception):
        return None


def _resolve_one_anchor(anc: dict) -> dict:
    """Return the canonical-fields dict for one anchor.

    Adds / replaces:
      - canonical_title (string, may equal title_hint if already canonical)
      - authors (list of strings, may be empty if Crossref did not return authors)
      - year (int or null)
      - doi (string or null)
      - pmid (string or null) — Crossref does not return PMID; we leave null
      - stable_source_locator (string or null)
      - identity_status (RESOLVED or ANCHOR_IDENTITY_UNRESOLVED)
    """
    title_hint = anc.get("title_hint") or ""
    year_approx = anc.get("year_approx")
    out: dict[str, Any] = dict(anc)
    out["doi"] = None
    out["pmid"] = None
    out["canonical_title"] = title_hint
    out["authors"] = []
    out["year"] = None
    out["stable_source_locator"] = None
    out["identity_status"] = "ANCHOR_IDENTITY_UNRESOLVED"
    out["identity_resolution_note"] = None

    # Two-pass strategy:
    # 1. Query Crossref with the title_hint using the regular full-text
    #    ``query=`` parameter (not ``query.biblio=``, which has strict
    #    field-prefix parsing and rejects our plain title strings).
    # 2. If the top-ranked result has a SequenceMatcher title similarity
    #    >= TITLE_SIM_THRESHOLD, accept its DOI and metadata.
    quoted = urllib.parse.quote(title_hint, safe="")
    url = f"https://api.crossref.org/works?query={quoted}&rows=5"
    payload = _http_get_json(url)
    if not payload:
        out["identity_resolution_note"] = "crossref lookup failed (network/parse)"
        return out
    msg = payload.get("message") or {}
    items = msg.get("items") or []
    if not items:
        out["identity_resolution_note"] = "no Crossref item returned"
        return out
    # Pick the item with the highest title similarity.
    best = None
    best_sim = 0.0
    best_title = None
    for it in items:
        tlist = it.get("title") or []
        t = tlist[0] if tlist else None
        s = _title_similarity(title_hint, t)
        if s > best_sim:
            best_sim = s
            best = it
            best_title = t
    if best is None or best_title is None:
        out["identity_resolution_note"] = "no usable Crossref item"
        return out
    # Always record the best similarity for diagnostic purposes, even
    # if it doesn't meet the threshold.
    if best_sim < TITLE_SIM_THRESHOLD:
        out["identity_resolution_note"] = (
            f"best Crossref match similarity {best_sim:.3f} below threshold "
            f"{TITLE_SIM_THRESHOLD}; top title was {best_title!r}"
        )
        return out
    # Accept
    out["canonical_title"] = best_title
    out["doi"] = (best.get("DOI") or "").lower() or None
    out["stable_source_locator"] = best.get("URL") or (f"https://doi.org/{out['doi']}" if out["doi"] else None)
    # Authors
    authors: list[str] = []
    for a in (best.get("author") or []):
        given = a.get("given") or ""
        family = a.get("family") or ""
        full = (given + " " + family).strip()
        if full:
            authors.append(full)
    out["authors"] = authors
    # Year
    yr = None
    for date_field in ("issued", "published-print", "published-online", "created"):
        d = best.get(date_field) or {}
        parts = (d.get("date-parts") or [[None]])[0]
        if parts and parts[0] is not None:
            try:
                yr = int(parts[0])
                break
            except (TypeError, ValueError):
                yr = None
    if yr is None and year_approx is not None:
        # Fallback: if the Crossref record has no parseable year but
        # the user said "year_approx" is the year, accept it as a
        # weakly-supported year.
        yr = int(year_approx)
    out["year"] = yr
    out["identity_status"] = "RESOLVED"
    out["identity_resolution_note"] = (
        f"title_similarity={best_sim:.3f}; Crossref item accepted"
    )
    return out


def main() -> int:
    pkg = Path(__file__).resolve().parent.parent
    bench_dir = pkg / "benchmarks" / "blood_oxygen_ovary"
    src = bench_dir / "known_anchors.json"
    out_path = bench_dir / "known_anchors_canonical.json"

    if not src.is_file():
        print(f"FATAL: {src} not found", file=sys.stderr)
        return 1
    doc = json.loads(src.read_text(encoding="utf-8"))
    anchors_in = doc.get("anchors", [])
    if not anchors_in:
        print("FATAL: no anchors in known_anchors.json", file=sys.stderr)
        return 1

    print(f"Resolving identity for {len(anchors_in)} anchors via Crossref...")
    resolved_count = 0
    out_anchors: list[dict] = []
    for anc in anchors_in:
        out = _resolve_one_anchor(anc)
        out_anchors.append(out)
        status = out["identity_status"]
        doi = out["doi"]
        print(f"  {anc['anchor_id']}: {status}"
              f"  doi={doi or '-'}")
        if status == "RESOLVED":
            resolved_count += 1

    out_doc = {
        "schema_version": "3.0-replay-a-ra1",
        "benchmark_id": doc.get("benchmark_id", "MAFS-v3.0-Replay-A-blood_oxygen_ovary"),
        "resolution_threshold": TITLE_SIM_THRESHOLD,
        "anchor_count": len(out_anchors),
        "resolved_count": resolved_count,
        "unresolved_count": len(out_anchors) - resolved_count,
        "anchors": out_anchors,
    }
    out_path.write_text(
        json.dumps(out_doc, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {out_path.relative_to(pkg)}: "
          f"{resolved_count}/{len(out_anchors)} resolved, "
          f"{len(out_anchors) - resolved_count} ANCHOR_IDENTITY_UNRESOLVED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
