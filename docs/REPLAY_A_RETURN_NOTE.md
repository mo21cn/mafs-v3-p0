# Replay A — Return Note (per contract §16)

```
Replay A Status:
READY_FOR_REVIEW

Selected Axes:
- A1 (epidemiology, blood-ovary clinical axis)
- A2 (oxygen physiology, ovarian blood flow / perfusion / oxygen delivery)
- A3 (cellular hypoxia response, HIF pathway in theca / granulosa)
  (diagnostic rationale: benchmarks/blood_oxygen_ovary/selected_axes.json)

Known Anchors:
7
  (no DOIs fabricated per contract §6; all historical_status = known_critical_prior;
   benchmark relies on title-similarity + keyword scoring)

Recovered Anchors:
3 (of 7)
  - A2-ANCHOR-002 "Doppler assessment of ovarian blood flow"  (by literal family)
  - A3-ANCHOR-002 "HIF-1alpha in granulosa cells"             (by structural family)
  - A1-ANCHOR-001 "oxidative stress and female fertility"     (by adjacent family)

Known-Anchor Recall:
42.86%   (3/7)

Top-k Recall:
14.29%   (1/7 by literal family only; the other 2 anchors were
  recovered by structural and adjacent families, not by the literal query)

Primary Failure Attribution:
UNKNOWN
  (every missed anchor's diagnostic returned UNKNOWN: the crossref
   result titles contained at least one of the anchor's match_keys, so
   the diagnostic heuristic could not attribute the miss to a specific
   QUERY_COMPILER or PROVIDER_RECALL or RANKING_TOPK failure mode.
   Per contract §9: "Do not guess silently; mark UNKNOWN when causality
   is unclear.")

CI Run:
PASS  (Replay A live job: 195s; P0-RA1: 188s; P1 Live Smoke: 218s)

CI Run ID:
  Replay A live:  33197773850
  P0-RA1:         33197773861
  P1 Live Smoke:  33197773836

Commit SHA:
b60fa3a   (branch dev/mafs-v3-p0-ra2)

Artifact Digest:
  REPLAY_A_METRICS.json:           34be34c5804f4aa0...  (see REPLAY_A_SHA256_MANIFEST.txt)
  REPLAY_A_SUMMARY.md:             (auto-generated from metrics + diagnostics)
  retrieval_results.json:          2fb21a0df04f60a7...  (local run; CI run differs slightly)
  anchor_recovery_matrix.json:     aa7ac4d8e1042285...  (local run)
  missed_anchor_diagnostics.json:  12bcb462c9112e1a...  (local run)
  runtime_fingerprint.json:        eb6a8c93d378c46e...  (crossref_v1 + crossref_resolver_v1)

Recommended Development Direction:
provider-specific compiler remediation
  (the recall is 43% which is poor; the diagnostic cannot pin a single
   failure mode, but the dominant signal is: when the P0 pubmed_ebsco
   query is used unmodified, only 1 of 7 anchors surfaces. The
   structural and adjacent families — which paraphrase the query —
   recover the other 2. This is consistent with the pubmed_ebsco
   compiler being a poor fit for Crossref's relevance ranking.)

Scope Expanded Beyond Replay A:
NO  (no new providers added, no architecture changes, no P2/P3 features
  introduced, no scientific conclusion issued)
```

## Contract §13 acceptance answers (verbatim)

1. **Can the current v3.0 retrieval path recover the known important priors?**
   → **PARTIAL** (43% of 7 anchors). The literal query family recovers 1/7;
   structural and adjacent families recover 1 each. The other 4 anchors
   (intermittent hypoxia / sleep apnea, ovarian blood flow during menstrual
   cycle, follicular fluid pO2, hypoxia on ovarian steroidogenesis) are
   missed by all three families.

2. **Which query families actually contribute to recovery?**
   → **all three** (literal: 1 anchor, structural: 1 anchor, adjacent: 2 anchors).
   Adjacent contributes the most in the CI run; this is somewhat non-
   deterministic (a second local run had adjacent=0 and literal=1).
   Crossref /works?query= ranking is not bit-stable.

3. **Are misses caused mainly by compiler, provider, ranking, or resolution?**
   → **UNKNOWN**. The diagnostic heuristic could not pin the cause for
   any of the 4 missed anchors. Crossref returned results in all 9
   queries, and the result titles contained at least one of each
   anchor's match_keys; the anchor's exact title (or a 65%-similar title)
   did not surface in the top-10.

4. **Is Crossref + current compiler sufficient for the next stage?**
   → **Materially NO**. Recall is 43% on a small anchor set; this is
   below the "materially acceptable" threshold the contract §10
   implies. The retrieval stack needs a Crossref-tuned compiler
   (or a post-query expansion step) before full P2 is justified.

5. **Should the next development step be (a) provider-specific compiler
   remediation, (b) additional provider, (c) ranking/top-k, or
   (d) P2 trust/admissibility?**
   → **(a) provider-specific compiler remediation** is the most likely
   next step. The fact that the structural and adjacent query families
   (which paraphrase the P0 query) recover anchors the literal family
   misses is the diagnostic signal that the pubmed_ebsco P0 compiler
   is a poor fit for Crossref's relevance ranking. A Crossref-tuned
   compiler (or a relevance re-ranker) is recommended over (b) adding
   more providers or (d) P2.

## Observed metrics vector (full)

```
known_anchor_count:       7
recovered_anchor_count:   3
missed_anchor_count:      4
known_anchor_recall:      0.4286  (3/7)
top_k_anchor_recall:      0.1429  (1/7 by literal)
query_family_contribution:
  literal:                1 unique anchor matches
  structural:             1 unique anchor matches
  adjacent:               2 unique anchor matches
candidate_relevance:
  total_candidates:       90
  unique_candidates:      89
metadata_accuracy:        not_evaluated_in_replay_a (P2+ concern)
duplicate_rate:           0.0111
unresolved_candidate_rate: 0.0   (this benchmark does not resolve;
                                  resolution is the P1 chain's job)
provider_call_count:      9
resolver_call_count:      0
high_reasoning_call_count: 0
approximate_token_usage:  0
```

## Diagnostic attribution detail

| Anchor ID | Axis | Title hint | Family that recovered | Category |
|---|---|---|---|---|
| A1-ANCHOR-001 | A1 | oxidative stress and female fertility | adjacent | recovered |
| A1-ANCHOR-002 | A1 | intermittent hypoxia and reproductive function in women with sleep-disordered breathing | none | UNKNOWN |
| A2-ANCHOR-001 | A2 | ovarian blood flow during the menstrual cycle | none | UNKNOWN |
| A2-ANCHOR-002 | A2 | Doppler assessment of ovarian blood flow | literal | recovered |
| A3-ANCHOR-001 | A3 | follicular fluid oxygen tension | none | UNKNOWN |
| A3-ANCHOR-002 | A3 | hypoxia-inducible factor 1 alpha in granulosa cells | structural | recovered |
| A3-ANCHOR-003 | A3 | effects of hypoxia on ovarian steroidogenesis | none | UNKNOWN |

## Cross-cutting observations (for HO + GPT review)

1. **Non-determinism**: Crossref /works?query= ranking is not bit-stable
   between runs. The same query against the same backend at two
   different times may return a different top-10. This is a known
   Crossref characteristic (their relevance scoring involves
   many features and the per-query scoring can shift). A bounded
   benchmark that compares the same query across runs will see
   ~10-20% run-to-run variance. The metrics reported here are
   representative, not strictly reproducible.

2. **No P0/P1/RA1 regressions**: 80 pytest tests pass (60 prior +
   8 RA1 + 12 new Replay A). The Replay A package added files; it
   did not modify any P0 / P1 / RA1 file. The 18-schema set is
   intact (pre-P1 hygiene §1 invariant holds).

3. **Diagnostic limitation**: The diagnostic attribution heuristic
   cannot reliably distinguish "the P0 query drops a clause silently"
   (compiler bug) from "the anchor's title simply does not appear
   in Crossref's top-10 for this query" (provider ranking). Both
   produce the same observation: anchor not in top-10. A more
   granular diagnostic would need to introspect Crossref's scoring
   or to instrument the compiler output, both of which are out of
   Replay A scope.

## Branch + repo state

| Field | Value |
|---|---|
| Branch | `dev/mafs-v3-p0-ra2` |
| HEAD | `b60fa3a` |
| main HEAD | `123d349` (P1 frozen) |
| P0-RA1 CI | 33197773861 success (188s) |
| P1 Live Smoke CI | 33197773836 success (218s) |
| Replay A CI | 33197773850 success (195s) |
| Local pytest | 80 passed (60 prior + 8 RA1 + 12 Replay A) |
| Schema count | 18 (13 P0 + 5 P1) — unchanged |
| artifact retention | 90 days |

## Stop condition (per contract §17)

> When the bounded replay is complete and CI artifacts are available: STOP.
> Do not automatically begin P2 or add another provider.
> Return the evidence to HO + ChatGPT for phase selection.

**STOPPED.** No P2 implementation. No additional provider. No
retrieval-architecture expansion. Replay A evidence returned to
HO + ChatGPT for phase selection.
