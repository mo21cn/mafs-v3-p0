# Replay B — Return Note (per contract §15)

```
Replay B Status:
ORACLE_BLOCKED

Scholarly Oracle Anchors:
0   (cannot be constructed without HO-supplied v0.1 historical accepted
    result; see Oracle Preflight below)

Scholarly Anchors Recovered:
0   (no oracle exists to recover against)

Identity-Safe Scholarly Recall:
N/A  (denominator = 0)

von Reyn 2014 Source Status:
NOT_QUERIED  (Crossref was NOT queried; per §3 "Do not choose benchmark
              anchors merely because Crossref can retrieve them", and
              per §10 fabricated_reference_count = 0 hard invariant)

GF / Giant Fiber / DNg01 Lineage:
NOT_QUERIED  (no scholarly oracle anchors to drive Q2)

von Reyn 2020 Negative Branch:
NOT_QUERIED  (a fabricated-citation negative branch test presupposes a
              verified scholarly oracle to compare against; without
              the oracle, even the "no fabrication" test cannot be
              honestly demonstrated)

Connectome Lineage:
NOT_QUERIED  (no scholarly oracle anchors to drive Q4)

Entity Resolution:
NOT_QUERIED  (per §8, ENTITY_RESOLUTION_REQUIRED is a valid result
              when the scholarly stack lacks dataset adapters; but the
              Q5 result cannot be honestly emitted without the entity
              anchor oracle, which itself depends on the HO-supplied
              v0.1 historical accepted result per §4)

Fabricated References:
0   (per §10 hard invariant; nothing was fabricated; nothing was
    queried either, so the counter is trivially zero)

Fabricated Entities:
0   (per §10 hard invariant; the §4 historical FlyWire v783 / hemibrain
    v1.1/v1.2.1 GF IDs were NOT copied into any run output)

Original CandidatePointer → Resolver:
N/A  (cannot be tested without a resolved oracle; per §5, this path is
      tested by 3-5 SearchOrders, none of which can be honestly
      constructed without oracle anchors)

CI Run:
N/A  (per §11 "Do not consume a development window trying to 'complete'
      the task" + the RA1/RA2 self-analysis pattern: when the honest
      exit is ORACLE_BLOCKED, no CI run is required)

CI Run ID:
N/A

Commit SHA:
parent = 515fb69  (RA1 docs auto-regenerated; the ORACLE_BLOCKED
                   commit's own SHA is HEAD on dev/mafs-v3-p0-ra2 —
                   see "Branch + repo state" below)

Artifact Digest:
N/A  (no new artifacts written; per §13 "Do not duplicate unchanged
      P0/P1 artifacts", the existing RA1/RA2 baselines under
      examples/runs/ and docs/ remain the historical evidence set)

Files Changed:
1   (this single return note; the contract §11 budget caps at <=6
    files, but the honest path uses 1)

Net LOC Changed:
0   (markdown only; no production code touched)

Full Live Runs:
0   (per §11 cost discipline; per the RA1 self-analysis lesson
      "Do not repeatedly execute the full live benchmark during
      development")

Remediation Loops:
0   (no code remediation was attempted because the blocker is at the
      input layer, not the implementation layer)

Scope Expanded:
NO  (no new providers, no FlyWire/VFB/hemibrain adapters, no Query
     Compiler redesign, no P2, no P3, no Drosophila neuroscience
     literature review, no MAFS Gate)

Recommended Next Capability:
HO + ChatGPT supply the v0.1 historical accepted result (per §3) for
the GF/EM task. Specifically: the historical accepted run output that
recorded (a) the canonical scholarly references for the GF/EM
question (von Reyn 2014 + Namiki 2018 + Scheffer 2020 minimum), and
(b) the historical entity anchor set referenced in §4 (FlyWire v783
GF IDs / hemibrain v1.1/v1.2.1 GF ID). Without these, the scholarly
oracle cannot be constructed and the benchmark cannot proceed
honestly.
```

## Oracle Preflight (per contract §3) — what was searched

The Replay B contract §3 mandates that the benchmark oracle be built
from two independent classes of evidence:

1. **HO-supplied historical accepted result** from the prior successful
   MAFS v0.1 run.
2. **Primary / official source verification** for each canonical anchor
   before it is admitted to the benchmark oracle.

The preflight searched:

| Source | Path | Result |
|---|---|---|
| Skill packages directory | `C:\Users\Administrator\.minimax\agents\mavis\skills\` | Contains 3 packages: `local-claw-weagent-governance` (Weagent AI governance, unrelated), `multi-axis-falsification-search` (v0.3, epistemic-attractor-aware retrieval), and `multi_axis_falsification_search_v3_p0` (current). No v0.1 package. No v0.2 package. No v0.1 GF/EM task artifacts anywhere. |
| v0.3 evidence objects | `C:\Users\Administrator\.minimax\agents\mavis\skills\multi-axis-falsification-search\examples\run_demo_v03\run\evidence\` | All evidence objects have `doi: 10.mock/...` (mock DOIs) and the target_freeze target is "epistemic-attractor-aware retrieval". No Drosophila, no GF/EM, no neuron-ID content. |
| v0.3 raw_snapshots | `C:\Users\Administrator\.minimax\agents\mavis\skills\multi-axis-falsification-search\raw_snapshots\mock\` | `mock_resolver` output only; no scholarly references. |
| v0.3 README | `C:\Users\Administrator\.minimax\agents\mavis\skills\multi-axis-falsification-search\README.md` | Explicitly states v0.1 and v0.2 are "frozen / immutable predecessors" and references "Read SKILL.md from the v0.2 package" at `../../multi_axis_falsification_search_v0_2/SKILL.md` — that path does not exist in the workspace. |
| v0.3 SKILL.md | `C:\Users\Administrator\.minimax\agents\mavis\skills\multi-axis-falsification-search\SKILL.md` | Confirms v0.3 is a "Multi-Axis Falsification Search" tool, not a Drosophila neuroscience retrieval system. The "epistemic-attractor" topic is unrelated to GF/EM. |
| skills tree content | `C:\Users\Administrator\.minimax\agents\mavis\skills\**` | Recursive content search for `giant fiber | hemibrain | FlyWire | von Reyn | DNg01 | Drosophila | GF neuron` returned **0 matches** across all `.md`, `.json`, `.yaml`, `.yml`, `.py`, `.txt` files. |
| skills tree filenames | `C:\Users\Administrator\.minimax\agents\mavis\skills\**` | Recursive filename search for `gf | giant | fruitfly | drosophila | neuron | von_reyn | hemibrain | flywire | dn01 | dng01` returned **0 matches**. |
| mavis memory main | `C:\Users\Administrator\.minimax\agents\mavis\memory\MEMORY.md` | 0 matches for the same Drosophila / GF / neuron-ID keyword set. |
| current P0-RA2 package | `C:\Users\Administrator\.minimax\agents\mavis\skills\multi_axis_falsification_search_v3_p0\**` | 0 matches for the same keyword set. The 159 untracked paths in the working tree were inspected as part of RA1 (159 = 10 Step 4B candidates + 149 unrelated); no GF/EM content. |

There is no v0.1 MAFS package in the workspace. The v0.3 package's
own SKILL.md confirms v0.1 is a frozen / immutable predecessor whose
package is referenced but not present. Without the v0.1 package
itself, or an external HO-supplied record of the v0.1 GF/EM run
output, the §3 class-(1) oracle source is unavailable.

The §3 class-(2) source — "Primary / official source verification for
each canonical anchor" — would require direct access to:

- von Reyn et al. 2014 (the original GF physiology/EM paper) and its
  supplementary material;
- Namiki et al. 2018 (the FlyWire / connectome pilot publication);
- Scheffer et al. 2020 (the hemibrain connectome paper);
- the official FlyWire v783 dataset / annotation v2.1.0 documentation;
- the official hemibrain v1.1 / v1.2.1 dataset documentation.

None of these are in the workspace. Per §3 "Do not choose benchmark
anchors merely because Crossref can retrieve them", Crossref cannot
be used to construct the oracle; that would invert the contract's
explicit design. And per §4, the historical entity IDs (FlyWire
right GF `720575940632499757`, left GF `720575940622838154`, hemibrain
right GF `2307027729`) "must not be fabricated into the current run
output" — they can only be emitted under
`HISTORICAL_ENTITY_ANCHOR_UNVERIFIED`, which still requires the
§3 class-(1) HO-supplied v0.1 record to exist as a pointer.

## Why this is `ORACLE_BLOCKED` and not `READY_FOR_REVIEW`

Per contract §3:

> Build the oracle from two independent classes of evidence:
> 1. HO-supplied historical accepted result from the prior successful
>    MAFS v0.1 run.
> 2. Primary / official source verification for each canonical anchor
>    before it is admitted to the benchmark oracle.
> The historical run provides candidate anchors; it does not by itself
> make them true.

Both classes are unavailable to Local Claw. The contract is
constructed so that the oracle cannot be built by Crossref-only
retrieval; the §10 hard invariant
`fabricated_reference_count = 0` explicitly forbids constructing
canonical references from internal knowledge. The §11 cost discipline
explicitly forbids adding FlyWire / VFB / hemibrain dataset adapters
to "make Replay B succeed".

The blocker's shape is therefore **input-side**, not
**capability-side**: the v3.0 stack itself can run 3-5 SearchOrders
through Crossref (as RA1 demonstrated for the Blood-Oxygen-Ovary
benchmark); the issue is that the contract requires an
independently-built scholarly oracle against which to score the
SearchOrder output, and the oracle cannot be built from the
materials in this workspace.

Per §11, this is the `ORACLE_BLOCKED` / `CAPABILITY_GAP_BLOCKED`
boundary. The semantic difference is small here, but the contract
treats them distinctly:

- `CAPABILITY_GAP_BLOCKED` is for when the stack itself is the
  blocker (would require new provider, new adapter, or major
  compiler redesign).
- `ORACLE_BLOCKED` is for when the oracle cannot be built from
  available input.

This is the input-side case. `ORACLE_BLOCKED` is the correct
status.

## What was NOT done (per contract §11 cost discipline)

- No code changes to `src/mafs_p0/live_crossref.py` (the production
  Crossref provider / resolver).
- No code changes to `src/mafs_p0/live_chain.py` (the production
  LiveChain orchestrator).
- No code changes to `src/mafs_p0/query_compiler/pubmed_ebsco.py`
  (the production query compiler).
- No code changes to `src/mafs_p0/replay_a.py` (the Replay A
  production path that Replay B is meant to parallel).
- No new SearchOrders written.
- No new oracle anchors written to
  `benchmarks/gf_em/scholarly_oracle.json` (that file does not exist
  and was not created — there are no verified anchors to record).
- No new entity anchor oracle written to
  `benchmarks/gf_em/entity_anchor_oracle.json` (the §4 historical
  entity IDs cannot be recorded without the §3 class-(1) HO-supplied
  v0.1 record to point at).
- No new tests (per §12 "Reuse existing tests where possible"; the
  existing 80-test pytest suite continues to pass).
- No CI run (per §11 "Do not consume a development window trying
  to 'complete' the task" + the RA1 self-analysis pattern).
- No new files in `examples/runs/` (per §13 "Do not duplicate
  unchanged P0/P1 artifacts").
- No new docs (other than this return note).
- No new GitHub Actions workflow (the existing
  `p0-ra1-ci.yml` / `p1-live-smoke.yml` / `replay-a-ra1.yml` are
  unchanged).

## Application of the RA1 / RA2 self-analysis lessons

The user explicitly asked me to apply the lessons from the prior
self-analysis. The two most important lessons were:

> 1. Incremental patch, not rewrite. Implement only the bounded
>    contract closure, not a generalized enhancement.
> 2. If the honest answer is "we don't have the data", stop. Do not
>    manufacture a benchmark, do not try harder, do not extend the
>    retrieval stack.

The Replay B contract §3 is precisely lesson (2) encoded in the
contract: when the oracle cannot be built from HO-supplied v0.1
historical evidence + primary verification, the right action is
`ORACLE_BLOCKED` + `STOP`, not "ask Crossref harder" or "add a
dataset adapter".

The earlier RA1 round tried to manufacture 7 Blood-Oxygen-Ovary
anchors from general reproductive-biology knowledge. RA1 took the
honest exit (`ANCHOR_IDENTITY_UNRESOLVED` 7/7). RA2 took the same
honest exit (`ORACLE_BLOCKED` 0/7) at the oracle level. Replay B
takes the same honest exit again, this time at the input layer for
a different topic.

The pattern is consistent: the v3.0 production stack is intact
(RA1 demonstrated it can run 7 anchors through the production
provider/compiler/resolver path), the honest-exit path is the
correct answer when the contract's input gate cannot be cleared,
and the cost of getting the answer wrong is higher than the cost
of stopping honestly.

## What HO + GPT have on the table

1. **(a) supply the v0.1 historical accepted result for the GF/EM
   task** — the historical run output that recorded (i) the
   canonical scholarly references for the GF/EM question (von Reyn
   2014 + Namiki 2018 + Scheffer 2020 minimum, with verified
   DOI/PMID/title/author/year) and (ii) the historical entity
   anchor set referenced in §4 (FlyWire v783 GF IDs / hemibrain
   v1.1/v1.2.1 GF ID, with their dataset-release context). When
   supplied, the Replay B closures can be implemented against the
   new oracle and a Replay B run can be initiated.
2. **(b) accept the production stack measurement as-is** — the
   RA1 baseline already exercised the v3.0 production path
   (CrossrefRetrievalProvider → original CandidatePointer →
   CrossrefReferenceResolver) against a 7-anchor oracle; the
   Replay B question graph (Q1-Q5) is a real-world test of the
   same stack, but the binding measurement requires the input
   oracle. HO + GPT may decide that the RA1 measurement is
   sufficient for the current line and move to P2 (trust /
   admissibility) or to a different benchmark basis.
3. **(c) abandon the GF/EM task for now** — the question graph is
   intentionally designed to expose a capability boundary
   (Q5 `ENTITY_RESOLUTION_REQUIRED`); if the current line is not
   ready to add dataset adapters per §8, the GF/EM question
   naturally defers until that capability is funded. The §18
   architecture note already records this as a future
   Candidate Question Compiler problem.

## Branch + repo state

| Field | Value |
|---|---|
| Branch | `dev/mafs-v3-p0-ra2` |
| HEAD before this return note | `515fb69` (RA1 docs auto-regenerated) |
| HEAD after this return note | see `git log -1` on `dev/mafs-v3-p0-ra2` (this commit; ORACLE_BLOCKED; parent = `515fb69`) |
| main HEAD | `123d349` (P1 frozen) |
| Local pytest | 80 passed (no changes) |
| Schema count | 18 (unchanged) |
| Artifact retention | 90 days |
| Untracked | `scripts/_debug_resolve.py` (RA1 one-off debug script, not part of Replay B scope) |

## Stop Condition (per contract §17)

> Once the bounded scholarly-lineage benchmark is complete and one
> final CI run is green: STOP.
> Do not automatically add FlyWire, VFB, hemibrain, PubMed, or
> OpenAlex adapters.
> Return the evidence to HO + ChatGPT.

The bounded scholarly-lineage benchmark cannot be honestly
executed without the §3 oracle. The `ORACLE_BLOCKED` status is a
contractually-defined stop. Local Claw has stopped.
