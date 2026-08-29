# P1_5_CI_PROVENANCE.md

contract_id: MAFS-v3.0-P1.5-CROSSREF-QUERY-RENDERING-ANCHOR-RECOVERY
build_id: ci-live
source: live
build_time: 2026-08-29T09:39:11Z
baseline_recall: 0/3
final_recall: 1/3
scholarly_anchor_count: 3
scholarly_anchor_recovered: 1
scholarly_identity_safe_recall: 0.3333333333333333
per_anchor_recovery: {"S1-vonReyn-2014": "RECOVERED", "S2-Namiki-2018": "NOT_RECOVERED", "S3-Scheffer-2020": "NOT_RECOVERED"}
per_anchor_rank: {"S1-vonReyn-2014": 1, "S2-Namiki-2018": null, "S3-Scheffer-2020": null}
rendering_path_used: {"Q1": "A_author_year_bibliographic", "Q2": "C_title_exact", "Q4": ""}
query_renderer_type: CROSSREF_SPECIFIC_THIN_RENDERER
architecture_drift_detected: False
crossref_specific_renderer: PASS
pubmed_specific_syntax_leakage_removed: PASS
provider_call_count: 16
resolver_call_count: 2
candidate_pointer_to_resolver_status: PASS
fabricated_reference_count: 0
fabricated_entity_count: 0
fabrication_hard_invariant_holds: True
Q1.paper_identity_status: RECOVERED
Q1.source_content_status: SOURCE_CONTENT_NOT_ACCESSIBLE
Q2.paper_identity_status: NOT_RECOVERED
Q2.proposition_status: ORACLE_VERIFIED_BUT_NOT_REPRODUCED_BY_PRODUCTION_STACK
Q3.negative_branch_status: COVERAGE_INSUFFICIENT
Q4.paper_identity_status: NOT_RECOVERED
Q5.entity_resolution_status: ENTITY_RESOLUTION_REQUIRED
exit_code: 0
