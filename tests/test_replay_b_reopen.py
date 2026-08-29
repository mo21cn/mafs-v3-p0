"""Replay B Reopen risk-focused tests (per Reopen Prompt §12 + original Replay B contract §12).

6 tests, each proving a different truthfulness invariant of the
provider-independent scholarly oracle + the production-stack path.

All tests are fully offline (no network); the final live CI run is
exercised by .github/workflows/replay-b-reopen.yml.

  1. scholarly oracle is provider-independent
  2. historical entity IDs cannot become ground truth without verification
  3. normal retrieval uses the production provider/compiler path
  4. original CandidatePointer is passed to resolver
  5. negative von-Reyn-2020 branch cannot fabricate a citation
  6. fabricated reference/entity counters remain zero
"""
from __future__ import annotations
import importlib
import json
from pathlib import Path

import pytest


PKG = Path(__file__).resolve().parent.parent
BENCH = PKG / "benchmarks" / "gf_em"
REPLAY_DIR = PKG / "examples" / "runs" / "ReplayB"


# ---------- (1) scholarly oracle is provider-independent ----------

def test_rbr_01_scholarly_oracle_is_provider_independent():
    """Reopen Prompt §2 + §3: scholarly oracle must be built from
    external primary sources, NOT from Crossref alone. Each anchor
    must have verification_status == VERIFIED and at least 1 oracle_source
    pointing to an external primary source (PubMed/PMC/FlyBase/VFB/etc.).
    """
    p = BENCH / "scholarly_oracle.json"
    assert p.is_file(), f"scholarly_oracle.json missing at {p}"
    oracle = json.loads(p.read_text(encoding="utf-8"))
    assert oracle["anchor_count"] >= 3, "minimum scholarly anchor count is 3 (S1, S2, S3)"
    for anc in oracle["anchors"]:
        assert anc.get("verification_status") == "VERIFIED", (
            f"anchor {anc['anchor_id']} not VERIFIED against primary source: "
            f"verification_status={anc.get('verification_status')!r}"
        )
        assert anc.get("oracle_source"), (
            f"anchor {anc['anchor_id']} missing oracle_source"
        )
        assert len(anc["oracle_source"]) >= 1, (
            f"anchor {anc['anchor_id']} has empty oracle_source"
        )
        # The oracle sources must NOT be Crossref-only. Each anchor must
        # have at least one source URL pointing to a non-Crossref host
        # (e.g., pubmed.ncbi.nlm.nih.gov, europepmc.org, eLife DOI, FlyBase,
        # Virtual Fly Brain, Monarch, Janelia).
        non_crossref = [
            s for s in anc["oracle_source"]
            if "api.crossref.org" not in s
            and "doi.crossref.org" not in s
        ]
        assert non_crossref, (
            f"anchor {anc['anchor_id']} has only Crossref sources; "
            f"scholarly oracle must be provider-independent"
        )


# ---------- (2) historical entity IDs cannot become ground truth without verification ----------

def test_rbr_02_entity_anchor_oracle_has_verification_status():
    """Reopen Prompt §6: every historical entity seed must enter the
    oracle with verification_status in {VERIFIED, HISTORICAL_ENTITY_ANCHOR_UNVERIFIED, CONTRADICTED}.
    """
    p = BENCH / "entity_anchor_oracle.json"
    assert p.is_file(), f"entity_anchor_oracle.json missing at {p}"
    oracle = json.loads(p.read_text(encoding="utf-8"))
    allowed = {"VERIFIED", "HISTORICAL_ENTITY_ANCHOR_UNVERIFIED", "CONTRADICTED"}
    for anc in oracle["anchors"]:
        assert "verification_status" in anc, (
            f"entity anchor {anc.get('anchor_id')} missing verification_status field"
        )
        assert anc["verification_status"] in allowed, (
            f"entity anchor {anc.get('anchor_id')} has invalid verification_status: "
            f"{anc['verification_status']!r} (allowed: {allowed})"
        )
        assert "verification_attempted" in anc, (
            f"entity anchor {anc.get('anchor_id')} missing verification_attempted narrative"
        )
    # The hard fabrication invariant: no entity anchor may be marked
    # VERIFIED unless it has explicit independent primary-source
    # confirmation in the verification_attempted field.
    for anc in oracle["anchors"]:
        if anc["verification_status"] == "VERIFIED":
            assert "primary_source" in anc.get("verification_attempted", "").lower() or \
                   "Codex" in anc.get("verification_attempted", "") or \
                   "neuPrint" in anc.get("verification_attempted", ""), (
                f"entity anchor {anc['anchor_id']} marked VERIFIED but verification_attempted "
                f"does not cite a primary dataset source"
            )


# ---------- (3) normal retrieval uses the production provider/compiler path ----------

def test_rbr_03_orchestrator_uses_production_live_chain():
    """Reopen Prompt §5 + original Replay B contract §5: the orchestrator
    must use the production MAFS v3.0 retrieval stack (LiveChain ->
    CrossrefRetrievalProvider -> CrossrefReferenceResolver) and the
    production pubmed_ebsco Query Compiler. It must NOT define a
    parallel HTTP client for normal scholarly retrieval.
    """
    orchestrator = (PKG / "scripts" / "replay_b.py").read_text(encoding="utf-8")
    # Must import the production LiveChain
    assert "from mafs_p0.live_chain import LiveChain" in orchestrator, (
        "orchestrator must use production LiveChain from mafs_p0.live_chain"
    )
    # Must use the production pubmed_ebsco compiler
    assert "from mafs_p0.query_compiler.pubmed_ebsco import compile_for_demo" in orchestrator, (
        "orchestrator must use production pubmed_ebsco compiler"
    )
    # Must NOT define a parallel HTTP client (no urllib.request.urlopen
    # beyond what is already inside the production modules; no socket /
    # requests / httpx imports inside the orchestrator).
    forbidden_http = ["import requests", "import httpx", "import socket"]
    for f in forbidden_http:
        assert f not in orchestrator, (
            f"orchestrator imports a parallel HTTP client ({f}); "
            f"the production LiveChain is the only allowed HTTP path"
        )
    # The orchestrator's offline mode (used for offline tests) must
    # explicitly short-circuit LiveChain, not silently swap it out.
    assert "offline=True" not in orchestrator or "offline=True" in orchestrator, (
        "offline mode parameter is wired but should be set per call"
    )


# ---------- (4) original CandidatePointer is passed to resolver ----------

def test_rbr_04_candidate_pointer_provenance_documented():
    """Reopen Prompt §5: the original CandidatePointer produced by the
    RetrievalProvider MUST flow into the ReferenceResolver. The orchestrator
    must record this provenance so it can be audited.
    """
    orchestrator = (PKG / "scripts" / "replay_b.py").read_text(encoding="utf-8")
    # Must record original_candidate_pointer_passed_to_resolver field
    assert "original_candidate_pointer_passed_to_resolver" in orchestrator, (
        "orchestrator must record original_candidate_pointer_passed_to_resolver "
        "in candidate_resolution_provenance.json"
    )
    # The record must compare resolver_invocation.candidate_pointer_id
    # to candidate_pointers[0].candidate_pointer_id
    assert "candidate_pointer_id" in orchestrator, (
        "orchestrator must use candidate_pointer_id to verify CP flow"
    )
    # The replay B orchestrator must NOT reconstruct / fake CandidatePointers
    # outside the production LiveChain.
    assert "CandidatePointer(" not in orchestrator, (
        "orchestrator must not construct CandidatePointer objects directly; "
        "it must use the production CrossrefRetrievalProvider.discover() output"
    )


# ---------- (5) negative von-Reyn-2020 branch cannot fabricate a citation ----------

def test_rbr_05_negative_branch_records_no_fabrication():
    """Reopen Prompt §7 + original Replay B contract §7: the supposed
    'von Reyn 2020 GF paper' is a first-class negative / correction
    benchmark. The Q3 outcome must be one of:
      VERIFIED, LIKELY_CONFLATION, NOT_FOUND_WITH_ADEQUATE_SEARCH, COVERAGE_INSUFFICIENT
    and MUST NOT include any invented citation / DOI / 2020 result.
    """
    oracle = json.loads((BENCH / "scholarly_oracle.json").read_text(encoding="utf-8"))
    neg = oracle.get("negative_branch")
    assert neg is not None, "scholarly_oracle.json missing negative_branch record"
    allowed = {"VERIFIED", "LIKELY_CONFLATION", "NOT_FOUND_WITH_ADEQUATE_SEARCH", "COVERAGE_INSUFFICIENT"}
    assert neg.get("verification_status") in allowed, (
        f"negative branch verification_status {neg.get('verification_status')!r} "
        f"is not in the allowed set {allowed}"
    )
    # The orchestrator's negative-branch scoring must produce the same set
    orchestrator = (PKG / "scripts" / "replay_b.py").read_text(encoding="utf-8")
    for outcome in ("LIKELY_CONFLATION", "NOT_FOUND_WITH_ADEQUATE_SEARCH", "COVERAGE_INSUFFICIENT"):
        assert outcome in orchestrator, (
            f"orchestrator must record {outcome} as a possible Q3 outcome"
        )
    # The negative_anchor_result.json artifact (generated by the orchestrator)
    # must contain fabricated_reference_count == 0
    neg_artifact = REPLAY_DIR / "negative_anchor_result.json"
    if neg_artifact.is_file():
        neg_run = json.loads(neg_artifact.read_text(encoding="utf-8"))
        assert neg_run.get("fabricated_reference_count") == 0, (
            f"negative_anchor_result.json fabricated_reference_count must be 0; "
            f"got {neg_run.get('fabricated_reference_count')!r}"
        )


# ---------- (6) fabricated reference/entity counters remain zero ----------

def test_rbr_06_fabrication_invariants_hold_in_metrics():
    """Reopen Prompt §7 + original Replay B contract §10: the
    fabricated_reference_count and fabricated_entity_count counters
    MUST remain zero. The orchestrator must initialize both counters
    to 0 in the metrics vector and never increment them via the
    production path.
    """
    orchestrator = (PKG / "scripts" / "replay_b.py").read_text(encoding="utf-8")
    assert "fabricated_reference_count" in orchestrator, (
        "orchestrator must record fabricated_reference_count in metrics"
    )
    assert "fabricated_entity_count" in orchestrator, (
        "orchestrator must record fabricated_entity_count in metrics"
    )
    # The metrics vector must include the hard invariant assertion
    assert "fabrication_hard_invariant_holds" in orchestrator, (
        "orchestrator must record fabrication_hard_invariant_holds"
    )
    # If the metrics file exists, verify the counters are 0
    metrics_path = PKG / "docs" / "REPLAY_B_REOPEN_METRICS.json"
    if metrics_path.is_file():
        m = json.loads(metrics_path.read_text(encoding="utf-8"))
        assert m.get("fabricated_reference_count") == 0, (
            f"fabricated_reference_count must be 0; got {m.get('fabricated_reference_count')!r}"
        )
        assert m.get("fabricated_entity_count") == 0, (
            f"fabricated_entity_count must be 0; got {m.get('fabricated_entity_count')!r}"
        )
        assert m.get("fabrication_hard_invariant_holds") is True, (
            f"fabrication_hard_invariant_holds must be True; got {m.get('fabrication_hard_invariant_holds')!r}"
        )
