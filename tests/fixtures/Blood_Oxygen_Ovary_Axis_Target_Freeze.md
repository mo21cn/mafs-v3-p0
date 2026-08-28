# Systemic Oxygen-Waveform–Ovarian Microenvironment Coupling
## (“Blood-Oxygen–Ovary Axis”) — MAFS v0.1 Target Freeze

| Field | Frozen value |
|---|---|
| Document role | Immutable pre-search Gate Artifact / Target Freeze |
| Authoring actor | HO + GPT |
| Search execution actor | Codex |
| Final decision authority | HO + GPT |
| Required Skill | Globally registered `multi-axis-falsification-search` (MAFS) v0.1 |
| Primary mode | `novelty_audit` |
| Search depth | `standard` |
| Freeze date | 2026-08-26 |
| Status | `FROZEN_FOR_SEARCH` |
| Initial downstream permission | `false` |
| Initial stop-downstream flag | `true` |

## 1. Purpose of this Gate

This Gate tests whether the proposed third experimental pipeline has a defensible original scientific object before any experimental SOP, measurement stack, grant narrative, manuscript framing, patent claim, or clinical translation plan is produced.

The proposed internal shorthand is **“blood-oxygen–ovary axis.”** That term is not treated as established and is not assumed to be valid. The lower-risk starting construct is **systemic oxygen-waveform–ovarian microenvironment coupling**.

The search must attack the proposal structurally, not merely search its coined terms.

## 2. Frozen Root Question

> Is the proposal to treat programmable systemic oxygen exposure as an identifiable, stage- and compartment-dependent ovarian oxygen-transfer-and-decoding problem—centered on the mapping from arterial oxygen delivery to local ovarian and follicular `pO₂(x,t)`—a scientifically distinct contribution beyond existing work on ovarian oxygen physiology, follicular hypoxia, hyperbaric or normobaric oxygen interventions, reproductive redox signaling, tissue oxygen transport, and dynamic oxygen-response measurement?

## 3. Frozen System Boundary

The candidate causal and measurement boundary is:

\[
u(t)=[P_{amb}(t),FiO_2(t)]
\rightarrow [PaO_2(t),SaO_2(t),CaO_2(t)]
\rightarrow DO_{2,ovary}(t)
\rightarrow pO_{2,ovary}(x,t)
\rightarrow \text{oxygen/redox sensing}
\rightarrow \text{cell state}
\rightarrow \text{ovarian function}
\]

with:

\[
DO_{2,ovary}(t)=Q_{ovary}(t)\times CaO_2(t)
\]

and the proposed organ transfer object:

\[
pO_{2,ovary}(x,t)=\mathcal{H}_{ovary}
\left[CaO_2(t),Q_{ovary}(t);
\text{age, cycle stage, vascular state, follicle stage, compartment}\right].
\]

`x` may distinguish ovarian cortex, stroma, theca, granulosa layer, cumulus–oocyte complex, follicular fluid, corpus luteum, or another empirically justified compartment.

The search must not assume that peripheral `SpO₂` is an adequate representation of the input, that oxygen delivery equals local tissue oxygen tension, or that local ovarian oxygenation is spatially homogeneous.

## 4. Atomic Claims

### C1 — Organ transfer-function contribution

- **Type:** scientific hypothesis + methodological claim
- **Proposition:** Identifying the dynamic mapping from systemic/arterial oxygen input and ovarian perfusion to local ovarian or follicular `pO₂(x,t)` is a scientifically meaningful object that has not already been structurally closed by existing ovarian physiology or oxygen-transport research.
- **Evidence that would change the framing:** Prior work already formulates and empirically identifies substantially the same dynamic ovarian transfer function under controlled systemic oxygen perturbations, including input, perfusion, local oxygen tension, and relevant covariates; or credible evidence shows that the mapping is neither observable nor scientifically discriminative.

### C2 — Non-trivial ovarian filtering

- **Type:** mechanism hypothesis
- **Proposition:** The ovary does not merely mirror arterial oxygen as a scalar; vascular regulation, oxygen extraction, diffusion, consumption, and follicular geometry can impose amplitude attenuation, delay, low-pass behavior, spatial gradients, or compartment-specific waveforms.
- **Evidence that would change the framing:** Direct dynamic measurements demonstrate a trivial, homogeneous, and stage-invariant mapping across the relevant range; or existing literature has already established the same ovarian filter architecture and its governing variables.

### C3 — Temporal-structure contribution

- **Type:** scientific hypothesis + design-space claim
- **Proposition:** After appropriate matching of conventional exposure descriptors such as mean, peak, duration, or AUC, oxygen-waveform features such as slope, frequency, duty cycle, recovery interval, and ordering may retain independent explanatory or causal value for ovarian local oxygenation or downstream state.
- **Evidence that would change the framing:** Well-controlled evidence shows no independent temporal-structure effect after exposure matching; the proposed features are physiologically erased before reaching the ovary; or prior work already defines and validates the same ovarian waveform design space.

### C4 — Layered transfer-and-decoding architecture

- **Type:** architecture claim + methodological claim
- **Proposition:** Separating commanded oxygen exposure, arterial oxygen state, ovarian perfusion/delivery, local `pO₂(x,t)`, molecular decoding, cell state, and function is a necessary and potentially original research architecture; outcome-only HBOT studies do not by themselves close this architecture.
- **Evidence that would change the framing:** An existing framework already uses substantially the same system boundary, layer separation, causal rationale, and intended generalization for the ovary; or evidence shows that the proposed layers cannot be separately identified even in principle.

### C5 — State-dependent transfer-function drift

- **Type:** mechanism hypothesis
- **Proposition:** `\mathcal{H}_{ovary}` may vary materially with age, reproductive-cycle stage, vascular state, follicle stage, and tissue compartment; therefore a single universal ovarian oxygen-response curve is unlikely to be adequate.
- **Evidence that would change the framing:** Robust evidence establishes practical invariance across the frozen modifiers; or the complete state-dependent mapping is already mature prior art rather than an unresolved region.

### C6 — Functional objective conflict

- **Type:** design-space claim + translational hypothesis
- **Proposition:** Short-term ovarian response, oocyte or embryo metrics, primordial-follicle recruitment, reserve preservation, and ovarian lifespan are non-equivalent outcomes and may move in opposite directions under oxygen/redox perturbation.
- **Evidence that would change the framing:** Existing oxygen-intervention frameworks already operationalize this exact objective conflict, absorbing the proposed distinction; or strong causal evidence shows that these outcomes are reliably directionally coupled in the target context.

### C7 — Conditional category formation (“axis” threshold)

- **Type:** terminology claim + category-formation claim
- **Proposition:** “Blood-oxygen–ovary axis” becomes a defensible category only if repeatable local coupling is demonstrated and linked to causal decoding plus organ-, compartment-, stage-, or regulatory specificity. A systemic exposure followed by an ovarian outcome is insufficient by itself.
- **Evidence that would change the framing:** The same category and evidentiary threshold are already established under another vocabulary; the phrase is already used for an equivalent system; or evidence shows that the proposed threshold does not create a useful distinction from ordinary exposure–response physiology.

## 5. Claims Explicitly Not Frozen as True

The following are candidates or hype-layer statements, not premises and not protected claims:

1. A linear `ROS → NRF2 → NF-κB → ovarian rejuvenation` mechanism.
2. The claim that NRF2 activation is uniformly beneficial to the ovary.
3. The claim that NF-κB suppression is uniformly beneficial.
4. The claim that hyperoxia necessarily raises local ovarian `pO₂` in proportion to arterial oxygen because hyperoxic vasoconstriction may alter `Q_ovary`.
5. The claim that improved oocyte yield, AMH, embryo metrics, ovarian reserve, and ovarian lifespan are interchangeable endpoints.
6. The claim that HBOT, intermittent oxygen exposure, or oxygen-waveform control already has proven clinical efficacy for ovarian aging or poor ovarian response.
7. The claim that “blood-oxygen–ovary axis” is already an established physiological axis.

Candidate decoding pathways—including PHD/HIF, ROS/NRF2, ROS/NF-κB, VEGF/eNOS, mitochondrial signaling, inflammatory signaling, steroidogenic signaling, and mechanistically justified alternatives—must be searched as a conditional network rather than forced into one linear chain.

## 6. Assumptions to Stress-Test

| ID | Assumption | Required treatment |
|---|---|---|
| A1 | A systemic oxygen input can be represented as a controlled time-varying exposure rather than only a dose label. | Search for direct support and counterexamples. |
| A2 | Arterial oxygen state and ovarian perfusion can be measured or bounded sufficiently to define oxygen delivery. | Test observability and proxy validity. |
| A3 | Local ovarian or follicular oxygen tension is measurable, inferable, or experimentally identifiable at a scientifically useful resolution. | Search invasive, ex vivo, imaging, and model-based methods. |
| A4 | The local ovarian field may preserve some information about input timing. | Seek both confirming and null/attenuation evidence. |
| A5 | Cross-species evidence can inform mechanism but cannot be silently promoted to human validation. | Preserve species and preparation boundaries. |
| A6 | “Axis” is a provisional upper-level category, not a starting fact. | Search equivalent established categories and usage. |

## 7. Scope Boundaries

### In scope

- Human, non-human mammalian, ovarian tissue, follicle, organ culture, and mechanistically relevant cellular evidence, with preparation and species recorded.
- Hyperbaric hyperoxia, normobaric hyperoxia, hypoxia, intermittent oxygen protocols, oxygen challenges, and other structurally relevant dynamic perturbations.
- Ovarian blood flow, vascular resistance, perfusion, oxygen extraction, tissue oxygenation, follicular-fluid oxygen tension, diffusion/consumption models, and compartment gradients.
- Dynamic or static measurement methods that bear on observability, including direct probes, imaging, spectroscopy, photoacoustic or oxygen-sensitive approaches, and justified model-based inference.
- HIF/PHD, ROS/NRF2, NF-κB, VEGF/eNOS, mitochondrial, inflammatory, steroidogenic, follicle-activation, and reserve-related mechanisms only insofar as they alter the frozen framing.
- Older terminology and adjacent fields, including reproductive physiology, microcirculation, tissue oxygen transport, systems physiology, control engineering, oxygen-challenge testing, and organ-specific transfer-function research.
- Negative, null, contradictory, damaging, and non-generalizing evidence.
- Scientific literature from database inception through the search execution date; relevant standards, patents, device precedents, or trial records may be retained but must be classified separately from scientific novelty.

### Out of scope

- Producing an experimental SOP or choosing instruments.
- Optimizing a waveform or selecting a treatment protocol.
- Writing a manuscript Introduction, grant application, business plan, or patent application.
- Making clinical recommendations or efficacy claims.
- Treating generic antioxidant/oxidative-stress papers as collisions unless they bear materially on a frozen claim.
- Treating IVF incubator oxygen concentration as structurally identical to systemic oxygen-waveform transmission without an explicit equivalence argument.
- Assigning a scalar novelty percentage, quality score, or winning hypothesis.

## 8. Required Candidate Search Axes

Codex must evaluate the following as candidate axes using the MAFS admission rubric. They are not automatically admitted; any rejection or merger requires an epistemic rationale.

1. **Terminology and category ancestry:** alternate names for ovarian oxygenation dynamics, ovarian oxygen signaling, blood–ovary coupling, and physiological “axis” constructs.
2. **Ovarian microcirculation and oxygen delivery:** ovarian blood flow, vascular resistance, oxygen extraction, cycle-stage hemodynamics, and hyperoxic vasoconstriction.
3. **Follicular oxygen transport and spatial gradients:** follicular-fluid `pO₂`, theca-to-granulosa diffusion, consumption, follicle-size effects, and compartment models.
4. **Dynamic oxygen perturbation in reproductive systems:** intermittent hypoxia/hyperoxia, oxygen challenges, pulse structure, recovery, temporal coding, and matched-dose comparisons.
5. **HBOT/normobaric oxygen and ovarian outcomes:** ovarian aging, poor ovarian response, ischemia/reperfusion, toxic injury, fertility, oocyte and embryo outcomes, and null or adverse studies.
6. **Measurement and identifiability:** direct versus proxy measurement of ovarian perfusion, delivery, local oxygen tension, temporal resolution, spatial resolution, and confounding.
7. **Oxygen/redox sensing and ovarian decoding:** PHD/HIF, ROS/NRF2, NF-κB, VEGF/eNOS, mitochondrial and inflammatory responses, with cell-type and follicle-stage resolution.
8. **Adjacent organ and systems-engineering prior art:** dynamic tissue oxygen transfer functions, oxygen challenge tests, organ filtering, compartment modeling, and feedback/control framings outside ovarian science.
9. **Counterexample and boundary evidence:** signal attenuation, non-monotonicity, hyperoxic injury, vascular compensation, follicle over-recruitment, reserve depletion, species failures, and exposure–outcome dissociation.
10. **Translation and device precedent:** existing clinical protocols, trials, instruments, regulatory categories, or patents that validate feasibility or collide with implementation—but must not be used as substitutes for scientific novelty evidence.

## 9. High-Risk Semantic Neighborhoods

The query families must go beyond these seeds, but at minimum consider structural equivalents of:

- ovarian oxygenation dynamics;
- ovarian oxygen delivery or extraction;
- ovarian tissue oxygen tension;
- follicular-fluid oxygen tension;
- ovarian/follicular oxygen gradient or transport model;
- ovarian microcirculation oxygen;
- oxygen challenge ovary;
- intermittent hyperoxia or hypoxia ovary;
- hyperbaric oxygen ovarian reserve, ovarian aging, fertility, or poor ovarian response;
- dynamic tissue oxygen response or tissue oxygen transfer function;
- organ oxygen filtering, compartment model, or oxygen impulse response;
- ovarian BOLD, oxygen-enhanced imaging, phosphorescence quenching, EPR oximetry, photoacoustic oxygenation, or direct oxygen microsensing;
- HIF dynamics, redox dynamics, NRF2 dynamics, or NF-κB dynamics in granulosa, theca, cumulus, oocyte, stroma, endothelium, immune cells, and corpus luteum;
- primordial-follicle activation versus ovarian reserve preservation under redox or oxygen perturbation.

## 10. Structural Collision Rules Specific to This Gate

1. An HBOT study reporting ovarian outcomes is not automatically a collision with C1–C4 unless it measures or structurally formulates the intervening delivery/local-oxygen mapping.
2. A static ovarian or follicular oxygen measurement is normally component overlap, not automatic closure of a dynamic transfer-function claim.
3. An isolated culture oxygen study may attack diffusion, sensing, damage, or endpoint assumptions but does not automatically reproduce a systemic blood-to-ovary system boundary.
4. A dynamic oxygen-transfer framework in another organ may be a strong structural neighbor or architecture collision even without ovarian terminology.
5. Literal use of “blood–ovary axis” is weak evidence unless the underlying system boundary and causal abstraction match.
6. Absence of the exact phrase, absence of a single perfect study, or sparse evidence cannot establish novelty.
7. A combination of known components is not distinct merely because they have not appeared in one title; the integrated system boundary, abstraction, variables, rationale, and intended generalization must be compared.

## 11. Gate Decision Semantics

Use only the canonical MAFS outcomes:

- **PASS:** No major collision changes the core framing, and the central claims remain distinct enough to justify downstream planning.
- **PASS_WITH_NARROWING:** Important antecedents absorb part of the framing, but a specific and meaningful contribution survives. State exactly what survives and what must no longer be called novel.
- **REDESIGN:** A Level-4 collision, multiple independent Level-3 collisions, or a hidden prior absorbs or invalidates the central framing. Stop downstream work and propose only the bounded salvage framings required by MAFS.
- **ABANDON:** Prior work fully absorbs the central framing and no defensible contribution remains.

If essential structural-equivalence axes cannot be searched or the evidence cannot adjudicate the frozen claims, keep `gate.decision: null`, mark execution pending or blocked, set `downstream_allowed: false`, and provide the blocker and resumption condition.

## 12. Downstream Permission Matrix

| Gate state | Permitted next action |
|---|---|
| `PASS` | HO + GPT may decide whether to authorize experimental/measurement design. Codex must not generate it in this run. |
| `PASS_WITH_NARROWING` | Only the surviving narrowed claims may be taken to a later HO-authorized design step. |
| `REDESIGN` | No SOP or pipeline design. Return collision evidence and bounded salvage framings for HO decision. |
| `ABANDON` | Stop this framing. |
| `null`, pending, or blocked | Stop downstream work until the missing evidence or access blocker is resolved. |

## 13. Freeze Invariants

1. Do not silently revise the Root Question, claims, or scope after search begins.
2. Record any evidence-driven change as a preserved `ResearchState` transition.
3. Preserve claim-level differences; do not compress the result into “the idea is novel” or “the idea is not novel.”
4. Keep scientific novelty, mechanistic plausibility, measurement feasibility, clinical efficacy, commercial validity, regulatory precedent, and patentability separate.
5. Do not generate downstream solutions in this run.
6. Final authority over `continue`, `narrow`, `redesign`, or `abandon` remains with HO + GPT after return-package review.

