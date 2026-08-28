# Replay A-RA1 — Return Note (per contract §16)

```
Replay A-RA1 Status:
READY_FOR_REVIEW

Canonical Anchors:
7
  (benchmarks/blood_oxygen_ovary/known_anchors_canonical.json)

Identity-Resolved Anchors:
0   (Crossref top-result title similarity < 0.9 threshold for all 7
     title_hint descriptions; the contract §1 honest-exit path was taken)

Identity-Unresolved Anchors:
7   (all 7 historical anchors are marked
     ANCHOR_IDENTITY_UNRESOLVED and excluded from the recall
     denominator per contract §1)

Recovered Anchors:
0   (denominator = 0; identity_safe_recall is N/A by definition)

Identity-Safe Recall:
None  (N/A; 0 resolved anchors — see primary failure attribution)

Provider Coverage/Indexing Misses:
0   (the ladder did not reach this category; all 7 were excluded at
     the identity-resolution step)

Ranking/Top-k Misses:
0   (same)

Query/Compiler Misses:
0   (same)

Unknown Misses:
0   (same)

Production Stack Exercised:
PASS  (CrossrefRetrievalProvider + CrossrefReferenceResolver +
       pubmed_ebsco compiler all invoked via production interfaces;
       query plan supplies QueryASTs, not hard-coded compiled strings)

CI Run:
PASS  (Replay A-RA1 live job: 206s)

CI Run ID:
33202859509

Commit SHA:
db035ce  (with bug-fix follow-up for the previous 33202129716 failure)

Artifact Digest:
  REPLAY_A_RA1_METRICS.json:          42594e49a1721e64...  (local, identical to CI)
  anchor_recovery_matrix.json:       61d3142cf0d72eb8...
  miss_diagnostic_ablation.json:     9d1405651937d013...
  resolver_invocations.json:         d019594a73649f56...
  normal_retrieval_results.json:     0bf726e9e5beb114...
  runtime_fingerprint.json:         28cd736e0d92d654...
  known_anchors_canonical.json:      881cf366ecc72ceb...

Recommended Next Development Step:
P1.5 bounded remediation is NOT useful here: the canonical anchor set
has 0 identity-resolved anchors. Either supply canonical DOI/PMID/title+author/year
for the 7 historical anchors (HO + GPT curation), or expand the anchor set
to papers the provider does index, or stop measuring recall and use the
production stack directly for downstream tasks.

Primary Failure Attribution (RA1 §14.3):
BENCHMARK_BASIS_INCOMPLETE  (all 7 anchors are identity-unresolved; the
miss-attribution ladder does not apply to unresolved anchors; the
benchmark is honest about not having a measurement basis at this round)

Scope Expanded Beyond RA1:
NO  (no new providers, no architecture changes, no P2/P3, no MAFS Gate)
```

## Contract §14 Acceptance Answers

1. **What is the identity-safe known-anchor recall?**
   → **N/A** (denominator = 0; 0 of 7 anchors are identity-resolved.
      The contract §1 honest-exit path was taken: anchors whose
      identity could not be verified via Crossref /works?query=
      (top-result title similarity < 0.9) are marked
      ANCHOR_IDENTITY_UNRESOLVED and excluded from the denominator.)

2. **Which historical anchors are still identity-unresolved?**
   → **All 7** of 7 are unresolved:
   - A1-ANCHOR-001 (oxidative stress and female fertility)
   - A1-ANCHOR-002 (intermittent hypoxia and reproductive function)
   - A2-ANCHOR-001 (ovarian blood flow during menstrual cycle)
   - A2-ANCHOR-002 (Doppler assessment of ovarian blood flow)
   - A3-ANCHOR-001 (follicular fluid oxygen tension)
   - A3-ANCHOR-002 (hypoxia-inducible factor 1-alpha in granulosa)
   - A3-ANCHOR-003 (effects of hypoxia on ovarian steroidogenesis)
   The known_anchors_canonical.json records the best Crossref match
   similarity for each (range 0.516-0.891) and the rationale for
   rejection.

3. **For each miss, is the dominant failure provider coverage, ranking,
   query, resolution, benchmark ambiguity, or unknown?**
   → **BENCHMARK_BASIS_INCOMPLETE** (a meta-category added because all
   7 misses were excluded at the identity-resolution step before the
   §5 ladder could run). Of the 5 contract §5 categories:
     - provider_coverage_failures: 0
     - ranking_topk_failures: 0
     - query_formulation_or_compiler_failures: 0
     - unknown_failures: 0
     - benchmark_ambiguity: 0 (no benchmark-ambiguity cases)
   The 7 identity-unresolved anchors are recorded in
   `anchor_identity_unresolved: 7`.

4. **Did the benchmark execute through the real v3.0 stack?**
   → **YES** (verified by:
     - `tests/test_replay_a_ra1.py::test_ra1_05_replay_uses_production_retrieval_provider`
       (asserts the orchestrator imports and uses CrossrefRetrievalProvider)
     - `tests/test_replay_a_ra1.py::test_ra1_06_replay_uses_production_query_compiler`
       (asserts the orchestrator imports and uses pubmed_ebsco.compile_for_demo)
     - `query_plan.json` stores QueryASTs (`query_representation` field),
       not hard-coded `compiled_query` strings.
     - 9 normal retrieval calls and 9 selective resolution calls were
       recorded in `resolver_invocations.json`.)

5. **Is the current retrieval stack ready for the next stage, or is a
   bounded P1.5 remediation required?**
   → **P1.5 bounded remediation is NOT useful at this round.** The
   benchmark basis itself is incomplete. The retrieval stack may be
   working fine; we cannot measure that until the canonical anchor
   set is supplied or expanded.
   - If HO + GPT can supply real DOIs/canonical titles for the 7
     anchors (curation), the benchmark can be re-run and a
     measurement is possible.
   - If the 7 anchors are intended to be permanent "fuzzy"
     indicators, then per contract §1 they should be marked
     BENCHMARK_AMBIGUITY and the benchmark should switch to
     using only identity-resolved anchors going forward.
   - If the goal is to move to downstream tasks (P2 trust/
     admissibility, full replay), the production stack is ready
     to be used directly without a measurement harness.

## Cross-cutting observations (for HO + GPT review)

1. **The benchmark fidelity defects are all closed**: identity-safe
   matching, production-stack execution, and bounded miss-diagnostic
   ablation are all in place. The remaining issue is data, not
   measurement.

2. **The Crossref lookup tool is honest about its limits**: with a
   title similarity threshold of 0.9, none of the 7 paraphrase
   title_hints match a real paper. Lowering the threshold (e.g., to
   0.5 or 0.6) would accept paraphrases as identities, but that
   would re-introduce exactly the fuzzy-positive failure mode that
   the contract §2 explicitly forbids. The contract prefers
   ANCHOR_IDENTITY_UNRESOLVED over fuzzy-identity acceptance.

3. **Two self-remediations in this round**:
   - First push (commit `ed95011`) failed the CI live job with two
     bugs in the rewritten code: a NameError (referenced `m` before
     assignment) and a missing `log_block()` method.
   - Both fixed in `db035ce` and the CI re-run was green.

4. **The previous Replay A's 3/7 fuzzy-positive result is
   explicitly NOT carried forward**: per contract §7, "Do not report
   the previous fuzzy 3/7 value as the current benchmark result.
   Keep it only as historical-invalid measurement if useful."
   The current 0/0 result is identity-safe.

## Branch + repo state

| Field | Value |
|---|---|
| Branch | `dev/mafs-v3-p0-ra2` |
| HEAD | `db035ce` (with bug-fix follow-up) |
| main HEAD | `123d349` (P1 frozen; Replay A-RA1 not yet fast-forwarded) |
| Replay A-RA1 CI | 33202859509 success (206s) |
| P0-RA1 CI | 33202859597 success (175s) |
| P1 Live Smoke CI | 33202859540 success (216s) |
| Local pytest | 80 passed (60 prior + 8 RA1 + 10 RA1 + 1 stub + 1 misc) |
| Schema count | 18 (13 P0 + 5 P1) — unchanged |
| artifact retention | 90 days |

## Stop Condition (per contract §18)

> When the corrected benchmark executes successfully and CI artifacts
> are complete: STOP.
> Do not automatically remediate compiler/provider behavior.
> Return the evidence to HO + ChatGPT for phase selection.

**STOPPED.** No P1.5 implementation. No new provider. No
retrieval-architecture expansion. No P2. Replay A-RA1 evidence
returned to HO + ChatGPT for phase selection.
