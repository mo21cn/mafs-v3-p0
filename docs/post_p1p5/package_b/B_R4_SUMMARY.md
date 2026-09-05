# Package B R4 Summary

R4 implements a bounded, artifact-first transition from grounded
`PropositionEvidence` to scientific state:

```text
multiple PropositionEvidence
-> scope-aware CollisionAssessment
-> append-only ResearchState
-> explicit NewEvidenceObligation
-> budget-authorized ReDigestionRequest
-> fidelity-reviewed, purity-checked revised EpistemicRoute
-> RouteRevisionLineage
```

`CollisionAssessment` records claim scope, comparability, evidence roles,
source limitations, supporting spans, uncertainty, and external adjudication
authority. Deterministic code validates the declared semantic relationship; it
does not infer collision type through embeddings or lexical similarity.

The hard negative path is executable: `NOT_GROUNDED` / `NOT_ADDRESSED`
evidence can produce `INSUFFICIENT_EVIDENCE`, but cannot produce a direct
contradiction. Context and measurement differences are preserved as explicit
collision types. Raw counts cannot be promoted to a statistical disagreement
without `STATISTICAL_RESULT` evidence.

`ResearchState` is immutable and append-only. Re-digestion requires an
explicit state trigger, an authorized new-evidence obligation, a positive
budget, and a named authority. Revised routes cannot overwrite parent routes
and must pass the Package A fidelity and discovery-purity guards.

R4 targeted behavior is covered by the Package B suite and the positive and
negative hermetic development demos. This is implementation evidence only;
Gate M5 has not accepted the capability.
