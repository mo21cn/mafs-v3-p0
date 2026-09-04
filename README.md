# MAFS v3.0-P0 — Executable Plan Foundation

Bounded P0 implementation of MAFS v3.0. Goal: prove a planned search is executable
before HO is asked to authorize live retrieval.

## Install (development only — not globally installed)

```text
pip install -e .[test]
```

## Run

```text
python examples/run_p0_demo.py
pytest tests/ -q
```

## Post-P1.5 Package A (R0-R3)

Package A adds a governed semantic vertical slice around the preserved P1.5
retrieval and resolver spine:

```text
upstream requirement
-> EpistemicRoute
-> RequirementRouteFidelityReview
-> SearchPortfolio / RouteSearchOrder
-> CandidatePointer
-> STOP
-> SelectionArtifact
-> canonical resolution
-> SourceDocument
-> EvidenceSpan
-> PropositionEvidence
```

The live demonstration is deliberately staged; there is no one-shot command
that can auto-select a CandidatePointer:

```text
python scripts/run_package_a_vertical_slice.py --input examples/package_a_vertical_slice_input.json --output-dir <dir> discover
python scripts/run_package_a_vertical_slice.py --input examples/package_a_vertical_slice_input.json --output-dir <dir> select-resolve --rendering-path <path> --candidate-pointer-id <id> --selection-authority <authority> --selection-reason <reason>
python scripts/run_package_a_vertical_slice.py --input examples/package_a_vertical_slice_input.json --output-dir <dir> ground --adjudication <semantic-adjudication.json>
```

Package A stops before Gate M3. It does not implement CollisionAssessment,
ResearchState, recursive re-digestion, or EvidenceLandscapePackage.

## Status of this package

- v0.1 / v0.2 / v0.3 packages are immutable and untouched
- This package is a sibling skill at `multi_axis_falsification_search_v3_p0/`
- Not globally installed; not auto-loaded by the Mavis skill loader (directory name differs from v0.3)
- v3.0 master contract and v3.0-P0 contract are documents of record, not code
- Post-P1.5 Package A is a development candidate only; it is not globally
  installed or production-migrated before independent Gate M3 acceptance.
