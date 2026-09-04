# Package A R3 Summary — Minimal Evidence Resolution

R3 implements a small provider-aware adapter boundary, not a content
platform. `OpenAlexAbstractAdapter` demonstrates lawful source acquisition by
already-resolved DOI; `InMemorySourceAdapter` provides hermetic regression and
replay support.

The authoritative data model is paper-first:

```text
CanonicalEvidence -> SourceDocument -> EvidenceSpan -> PropositionEvidence
```

One cached `SourceDocument` can serve multiple proposition requests. Source
representation (`ABSTRACT`, `FULL_TEXT`, `INACCESSIBLE`, and related states)
is orthogonal to grounding state (`CITABLE_SPAN`, `NOT_ADDRESSED`,
`AMBIGUOUS`, and related states).

Semantic safety checks reject wrong-source material, non-exact spans,
background-only support for result claims, raw counts for statistical
significance claims, indirect inference where explicit evidence is required,
and model-prior judgments without source spans. Negative and uncertain states
are preserved as first-class non-fabricated results.

R3 checkpoint status: `COMPLETE_FOR_PACKAGE_A_CANDIDATE`.

