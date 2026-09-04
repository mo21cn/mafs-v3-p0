# Development Package A — R0–R3 Final Summary

Package A is complete as a development candidate and is stopped before Gate
M3. Completion is not M3 acceptance, and R4 is not authorized.

## Result

The implementation closes one governed semantic vertical slice:

```text
Requirement
-> EpistemicRoute
-> RequirementRouteFidelityReview
-> SearchPortfolio
-> RouteSearchOrder
-> live CandidatePointer discovery
-> STOP
-> SelectionArtifact
-> preserved P1.5 resolution
-> SourceDocument
-> EvidenceSpan
-> PropositionEvidence
```

The live demonstration discovered five candidates from a semantic query that
contained no target identity. It stopped before selection, then resolved an
explicitly selected rank-4 CandidatePointer. A public abstract was identity-
verified and reused for two proposition tasks: one source-span-backed
`SUPPORTS` result and one non-fabricated `NOT_ADDRESSED` result.

## Verification

- Package A targeted tests: 34 passed.
- Full offline regression: 158 passed, 15 skipped.
- Preserved P1 live chain: 11 passed against real Crossref.
- Syntax compilation: passed.
- Legacy P0/P1.5 18-schema fingerprint scope: preserved.
- Production/global installation state: unchanged.

## Evaluated source

`bbb23021755635aaeb4d9050d60d26ec1e13f4f0`

The later package-bundle commit contains acceptance-only files. Gate M3 must
pin both the evaluated source SHA and the final package-bundle SHA to avoid a
self-referential Git commit claim.

## Known limitations

- The live sample is one route, one selected paper, and an abstract source; it
  proves operability and lineage, not scientific generalization or semantic
  adjudication accuracy.
- The discovery-purity guard mechanically rejects explicit forbidden fields
  and DOI-shaped strings. Detecting a paraphrased exact target title remains
  an M3 semantic-audit responsibility.
- `OpenAlexAbstractAdapter` is deliberately narrow; full-text/PDF/OCR and a
  provider orchestration platform are outside Package A.
- SearchPortfolio is minimal and contains no optimizer, route-splitting,
  saturation, reserved-capacity, or RL mechanism.
- The live selection authority was Codex acting in a separate post-STOP stage;
  the artifact records this boundary, while M3 decides whether the evidence is
  sufficient for architecture acceptance.
- The pre-existing `tests_dir` pytest warning remains; it does not affect test
  outcomes.

## Deviations

- New schemas are under `schemas/post_p1p5/` instead of the legacy schema root.
  This intentional compatibility isolation preserves the earned P0/P1.5
  18-schema runtime fingerprint rather than weakening its regression tests.
- The first local baseline test exposed the new branch allow-list and sandbox
  temp-directory conditions; both were resolved before final verification.
  No functional baseline regression was observed.

## Stop

`PACKAGE_A_COMPLETE_AWAITING_GATE_M3`

No CollisionAssessment, ResearchState, recursive re-digestion,
EvidenceLandscapePackage, R4, or R5 code was implemented.
