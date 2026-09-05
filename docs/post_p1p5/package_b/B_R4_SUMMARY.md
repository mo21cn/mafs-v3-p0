# Package B R4 Summary — RA1 Lineage Closure

RA1 closes the measured post-redigestion state gap while preserving original
R4 semantics. The canonical positive sequence is now:

```text
RS-002
-> ReDigestionRequest RDR-001
-> fidelity-reviewed EpistemicRoute ER-102
-> append-only ResearchState RS-003 (parent = RS-002)
-> EvidenceLandscapePackage ELP-001
```

`RS-003` owns the current route truth. Its current routes are `ER-101` and
`ER-102`; the latest status of `ER-101` is `REVISION_CANDIDATE`, while `ER-102`
is `UNDEREXPLORED` because no downstream search was executed. The authorized
obligation from `RS-002` remains unresolved and visible. No prior state is
mutated.

ResearchState construction now requires every current route to have a status
record and rejects status records for routes outside current state. The latest
append-only record is the authoritative current status.

CollisionAssessment, claim-scope semantics, Package A, P1.5, and M3 acceptance
truth were not changed. This remains implementation evidence only; Gate M5 has
not accepted the capability.

Evaluated source: `ad12444b9340439d304b50a776e1b3fa0d81aa47`.
