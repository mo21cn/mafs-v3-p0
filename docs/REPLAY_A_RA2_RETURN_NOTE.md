# Replay A-RA2 — Return Note (per contract §13)

```
Replay A-RA2 Status:
ORACLE_BLOCKED

Identity-Resolved Anchors:
0   (cannot be increased without provider-independent historical evidence)

Identity-Unresolved Anchors:
7   (all 7 historical anchors carry identity_status=ANCHOR_IDENTITY_UNRESOLVED
     from the RA1 round; the RA2 Oracle Preflight confirmed that none of them
     can be promoted to RESOLVED status from the historical materials available
     in the workspace)

Oracle Provider-Independent:
FAIL  (the v0.x historical materials in this workspace do NOT contain
       Blood-Oxygen-Ovary references; see Oracle Preflight below)

Original CandidatePointer → Resolver:
N/A  (cannot be tested without a resolved oracle)

Top-50 Identity/Rank Diagnostic:
N/A  (cannot be tested without a resolved oracle)

Identity-Safe Recall:
N/A  (denominator = 0)

Primary Failure Attribution:
ORACLE_BLOCKED  (the §5 attribution ladder is moot when the oracle
                 itself is the blocker; this is a meta-category added
                 by the RA1 code path and confirmed by RA2 §3)

CI Run:
N/A  (per contract §3 "STOP" + §9 "Do not repeatedly execute the full
      live benchmark during development", and per the honest-exit
      path ORACLE_BLOCKED does not require a CI run)

CI Run ID:
N/A

Commit SHA:
N/A  (no code changes were committed for RA2; see "Scope" below)

Artifact Digest:
N/A  (no new artifacts were written; the existing RA1 artifacts under
      examples/runs/ReplayA/ and the v0.3 evidence under
      examples/run_demo_v03/run/ remain as the historical baseline)

Files Changed:
0   (the contract §1 "incremental patch" applies only to the three
    RA2 closures; since none of them can be applied without an oracle,
    no code is patched)

Approx. Net LOC Changed:
0

Full Live Benchmark Runs During RA2:
0   (per contract §3 "Do not modify the retrieval stack" + §9
    "Do not repeatedly execute the full live benchmark during
    development")

Remediation Loops:
0

Scope Expanded:
NO  (no new providers, no architecture changes, no P2/P3, no MAFS Gate)

Recommended Next Step:
HO + GPT decide between:
  (a) supply canonical references (real DOI / PMID / verified
      canonical title + author + year) for the Blood-Oxygen-Ovary
      benchmark anchors from external historical materials that are
      NOT in the workspace (e.g., a published MAFS audit, an
      accepted P0/P1 run from before this workspace was set up, a
      human-curated bibliography);
  (b) drop the Blood-Oxygen-Ovary benchmark basis and pick a
      different scientific question that DOES have historical
      materials in the workspace;
  (c) accept the honest measurement: the retrieval stack may be
      working, but we cannot measure it without an oracle, so move
      to downstream tasks (P2 trust/admissibility) on the
      production stack directly.
```

## Oracle Preflight (per contract §2) — what was searched

The RA2 contract §2 mandates that the benchmark oracle be built from
**provider-independent historical evidence** — "prior accepted MAFS
runs, historical run artifacts, previously verified citations /
candidate records, stable DOI / PMID / canonical publication metadata" —
and explicitly forbids "defining benchmark membership by asking
Crossref what it can retrieve."

The preflight searched:

| Source | Path | Result |
|---|---|---|
| v0.3 evidence objects | `C:\Users\Administrator\.minimax\agents\mavis\skills\multi-axis-falsification-search\examples\run_demo_v03\run\evidence\E5.yaml` | All 4 evidence objects (`E5`, `E17`, `E22`, `E_NEW`) have `doi: 10.mock/...` (mock DOIs) and are about "epistemic-attractor-aware retrieval" — a different scientific question from Blood-Oxygen-Ovary |
| v0.3 target_freeze | `examples/run_demo_v03/run/target_freeze/target_freeze.yaml` | Topic: "epistemic-attractor-aware retrieval"; no Blood-Oxygen-Ovary references |
| v0.3 raw_snapshots | `examples/run_demo_v03/run/raw_snapshots/` | All snapshots are `mock`/`local_cache` resolver output with mock DOIs |
| v0.3 final_gate | `examples/run_demo_v03/run/final/final_gate.yaml` | Status: PARTIAL, pending; references only E5/E17/E22/E_NEW (all mock) |
| v0.2 port | `examples/run_demo_v0_2_port/build_demo_fixture.py` | No Blood-Oxygen-Ovary references |
| v0.3 templates | `templates/*.md` (15 files) | All generic MAFS template content; no Blood-Oxygen-Ovary references |
| v0.3 raw workspace | `C:\Users\Administrator\.minimax\agents\mavis\skills\multi-axis-falsification-search` (all files) | Recursive search for `ovary|ovarian|oxygen|hypoxia|granulosa|follicular|HIF` returned **0 matches** |

The v0.3 final_gate output explicitly notes the workspace coverage
is `PARTIAL 鈥?patents inaccessible; non-English inaccessible` — the
v0.3 demo was itself a placeholder run, not a real prior MAFS audit
of Blood-Oxygen-Ovary.

There are no other MAFS run packages in the workspace. The v3.0-P0
package itself was the first Blood-Oxygen-Ovary run; there is no
"prior accepted MAFS run" to draw canonical references from.

## Why the previous Replay A / RA1 anchors were non-historical

The 7 anchors in `benchmarks/blood_oxygen_ovary/known_anchors.json`
have `title_hint` strings I (Local Claw) wrote from general
reproductive-biology knowledge, not from any historical MAFS artifact.
The `historical_status: known_critical_prior` was my own judgment
about which papers "should" be in the literature, not a verification
of which papers were actually used in a prior accepted run.

This is exactly the situation the RA2 contract §2 is designed to
catch: benchmark membership was being defined by what a researcher
*thought* the literature contained, not by what a prior MAFS run
*actually cited*. Crossref cannot rescue this — per §2, "Do not
define benchmark membership by asking Crossref what it can retrieve."

## Why this is `ORACLE_BLOCKED` and not `READY_FOR_REVIEW`

Per contract §3:

> Recommended minimum:
>   >= 4 identity-resolved anchors
>   AND coverage of >= 2 selected axes
> If this cannot be achieved from provider-independent historical
> evidence:
>   ORACLE_BLOCKED
>   STOP.
>   Do not modify the retrieval stack and do not manufacture a
>   benchmark.
>   Return the unresolved oracle evidence to HO + ChatGPT.

The recommended minimum is 4 identity-resolved anchors. The actual
count is 0. The clause "If this cannot be achieved from
provider-independent historical evidence: ORACLE_BLOCKED" applies
exactly: the v0.x historical materials do not contain Blood-Oxygen-Ovary
canonical references, so the minimum cannot be achieved from
historical evidence.

Per contract §10:

> RA2 must not:
>   - add PubMed / OpenAlex / another provider
>   - change Candidate Question / scientific framing
>   - optimize query relevance
>   - redesign Query AST
>   - enter Evidence Admissibility
>   - enter P2 / P3
>   - run the full ten-axis historical task
>   - issue a scientific Gate
>   - change P1 frozen behavior

RA2's "Three closures" all presuppose a resolved oracle. The
provenance-continuity closure needs CPs that point to oracle-
resolved DOIs. The top-50 diagnostic needs resolved anchors to
test rank against. Without an oracle, none of the three closures
can be demonstrated; the contract's honest-exit path is the
correct one.

## What was NOT done (per contract §10)

- No code changes to `src/mafs_p0/replay_a.py`
- No code changes to `scripts/replay_a.py`
- No changes to `query_plan.json` (no `query_representation` was
  hand-written for RA2; the RA1 ASTs are unchanged)
- No changes to `known_anchors_canonical.json` (the 7 RA1
  ANCHOR_IDENTITY_UNRESOLVED entries are unchanged; no
  `oracle_source` / `oracle_verification_note` fields added
  because there is no oracle source to record)
- No new tests (per §8 "Reuse existing tests where they already cover
  a requirement. Do not add tests merely to increase count.")
- No CI run (per §9 "Do not repeatedly execute the full live
  benchmark during development")
- No new files in `examples/runs/`
- No new docs (other than this return note)

## Application of the self-analysis lessons

The user asked me to apply the lessons from the prior self-analysis.
The most important lesson was:

> If the honest answer is "we don't have the data", stop. Do not
> manufacture a benchmark, do not try harder, do not extend the
> retrieval stack.

The RA2 contract §3 is precisely this lesson encoded in the
contract: when the oracle cannot be built from historical evidence,
the right action is `ORACLE_BLOCKED` + `STOP`, not "extend the
scope" or "manufacture a benchmark."

The earlier RA1 round tried to manufacture 7 anchors from general
knowledge. The RA1 contract §1 explicitly designed an exit for that
case (`ANCHOR_IDENTITY_UNRESOLVED`); RA1 took the exit. RA2 confirms
the exit is correct by checking the historical materials and finding
none.

The contract is well-designed. The honest answer is the right
answer.

## What HO + GPT have on the table

1. **(a) supply canonical references** — real DOI / PMID / verified
   canonical title + author + year for Blood-Oxygen-Ovary benchmarks
   from external sources (published MAFS audits, prior accepted runs
   outside this workspace, human-curated bibliographies). When
   supplied, the RA2 closures can be implemented against the new
   oracle and a new RA2 run can be initiated.
2. **(b) drop this benchmark basis** — pick a different scientific
   question that DOES have historical MAFS materials. (The v0.3
   epistemic-attractor-aware retrieval would be one such candidate
   if a real prior run of it exists; the v0.3 demo is itself mock.)
3. **(c) move to downstream tasks** — the production stack may be
   working; we cannot measure it from the workspace, but P2
   trust/admissibility does not require a measurement basis, only a
   working stack.

## Branch + repo state

| Field | Value |
|---|---|
| Branch | `dev/mafs-v3-p0-ra2` |
| HEAD | `3e78326` (last RA1 commit; no RA2 code changes) |
| main HEAD | `123d349` (P1 frozen) |
| Local pytest | 80 passed (no changes) |
| Schema count | 18 (unchanged) |
| Artifact retention | 90 days |

## Stop Condition (per contract §15)

> When the three closures are proven and one final CI benchmark is
> green: STOP.
> Do not automatically remediate retrieval quality.
> Return the evidence to HO + ChatGPT.

The three closures are not provable without an oracle. The
ORACLE_BLOCKED status is a contractually-defined stop. Local Claw
has stopped.
