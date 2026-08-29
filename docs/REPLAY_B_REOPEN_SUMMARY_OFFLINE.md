# REPLAY_B_REOPEN_SUMMARY.md

MAFS v3.0 — Replay B Reopen (GF/EM Scholarly Lineage & Boundary-Aware Identity Retrieval).

## Oracle provider-independence
- Scholarly oracle: 3 anchors, all `VERIFIED` against external primary sources
  (PubMed, PMC, eLife DOI, FlyBase, Virtual Fly Brain, Monarch Initiative, Janelia bibliography).
- Entity anchor oracle: 3 historical candidate IDs, all `HISTORICAL_ENTITY_ANCHOR_UNVERIFIED`
  (format consistent with FlyWire v783 / hemibrain v1.2.1; specific body ID ↔ DNp01 mapping
  not independently confirmed without programmatic Codex / neuPrint access).

## Nomenclature correction
- Q2 question text updated to reflect the verified modern mapping:
  **GF / Giant Fiber == DNp01** (per Namiki et al. 2018 and Virtual Fly Brain FBbt:00004020).
  The historical predecessor label 'DNg01' is recorded as a synonym, not the current canonical name.

## Question outcomes
- Q1: **OFFLINE_MODE** (no oracle anchor matched; Offline test mode; production chain not executed.)
- Q2: **OFFLINE_MODE** (no oracle anchor matched; Offline test mode; production chain not executed.)
- Q3: **OFFLINE_MODE** (no oracle anchor matched; Offline test mode; production chain not executed.)
- Q4: **OFFLINE_MODE** (no oracle anchor matched; Offline test mode; production chain not executed.)
- Q5: **ENTITY_RESOLUTION_REQUIRED** (no oracle anchor matched; Production scholarly stack (Crossref + pubmed_ebsco) does not include FlyWire / VFB / hemibrain adapters. Per Reopen Prompt §6 and original Replay B contract §8, this is a contract-designed legitimate)

## §10 metrics vector
- scholarly_anchor_count: 3
- scholarly_anchor_recovered: 0
- scholarly_identity_safe_recall: 0.0
- negative_anchor_result: OFFLINE_MODE
- naming_lineage_status: OFFLINE_MODE
- connectome_lineage_status: OFFLINE_MODE
- source_content_status: OFFLINE_MODE
- entity_resolution_status: ENTITY_RESOLUTION_REQUIRED
- provider_call_count: 0
- resolver_call_count: 0
- fabricated_reference_count: 0
- fabricated_entity_count: 0
- fabrication_hard_invariant_holds: True
- original_candidate_pointer_to_resolver: PASS
- scholarly_oracle_provider_independent: PASS
- entity_anchor_oracle_verification_status_documented: True
- dnp01_correction_applied: True
- von_reyn_2020_negative_branch_no_fabrication: False

## Recommended Next Capability (one bounded recommendation)
- Add a verified FlyWire / hemibrain adapter for the historical entity IDs in entity_anchor_oracle.json,
  so the Q5 ENTITY_RESOLUTION_REQUIRED boundary can be promoted to a genuine Q5 outcome
  with independent programmatic verification of the three root_id / body_id values.

build_time: 2026-08-29T05:23:32Z
exit_code: 0
