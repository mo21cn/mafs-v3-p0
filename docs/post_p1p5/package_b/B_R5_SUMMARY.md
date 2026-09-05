# Package B R5 Summary

R5 introduces `EvidenceLandscapePackage` as the final MAFS-owned structured
artifact. It preserves, without flattening:

- original and re-digested route history plus parent lineage;
- search portfolio and budget history;
- CandidatePointer and explicit selection lineage;
- typed SourceDocument, EvidenceSpan, and PropositionEvidence identifiers;
- machine-readable collision identifiers and scoped claims;
- unresolved and newly created evidence obligations;
- conservative coverage accounting and provenance.

The boundary is enforced as:

```text
authority_boundary = EVIDENCE_LANDSCAPE_ONLY
```

The implementation rejects packages that claim downstream decision authority,
omit active routes, change ResearchState proposition/collision references, drop
required coverage fields, or lack provenance. Canonical JSON serialization is
deterministic.

R5 does not implement ROC, ranking, hypothesis approval, clinical/policy/
investment decisions, autonomous experiment authorization, or production
migration. Those remain outside Package B and outside current MAFS authority.
