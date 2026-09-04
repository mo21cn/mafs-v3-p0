# Package A R2 Summary — Governed Search and Selection

R2 introduces a minimal `SearchPortfolio`, route-native `RouteSearchOrder`,
and explicit `SelectionArtifact`. The portfolio records active routes,
authorized/used budget, coverage obligations, and uncovered obligations; it
does not implement saturation scores, reserved slots, route splitting, an RL
allocator, or a provider platform.

`RouteSearchOrder` compiles semantic, disciplinary, mechanism, measurement,
and evidence-type intent into the generic query interface already consumed by
the P1.5 `LiveChain`. It never receives an expected DOI or target paper.

The preserved P1.5 boundary remains authoritative:

1. live discovery emits CandidatePointers and stops;
2. a separately persisted `SelectionArtifact` names one observed pointer;
3. the resolver receives exactly that pointer;
4. CandidatePointer, selection, resolver invocation, and canonical evidence
   provenance remain continuous.

R2 checkpoint status: `COMPLETE_FOR_PACKAGE_A_CANDIDATE`.

