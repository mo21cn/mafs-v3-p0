"""§16 risk test 6: SearchOrder without compatible provider fails (preflight C4)."""
from __future__ import annotations
from mafs_p0.demo import run_positive_demo, run_negative_demo


def test_positive_demo_negotiates_all_so(real_tf_path):
    out = run_positive_demo(tf_path=real_tf_path)
    for n in out["negotiations"]:
        assert n["executable"], f"SO {n['search_order_id']} not executable: {n['blocker']}"


def test_negative_demo_negotiation_fails(real_tf_path):
    out = run_negative_demo(tf_path=real_tf_path)
    # The negative demo uses a provider missing search.pagination, so all 10 SOs fail.
    non_exec = [n for n in out["negotiations"] if not n["executable"]]
    assert len(non_exec) >= 1
    # preflight C4 should be FAIL
    c4 = next(c for c in out["preflight"]["checks"] if c["check_id"] == "C4")
    assert c4["outcome"] == "FAIL"
    # overall status must be PLANNING_BLOCKED
    assert out["preflight"]["status"] == "PLANNING_BLOCKED"


def test_unknown_capability_rejected():
    from mafs_p0.capability_vocabulary import validate_capabilities, CapabilityVocabularyError
    import pytest
    with pytest.raises(CapabilityVocabularyError):
        validate_capabilities(["search.query", "invented.fake_capability"], registered_providers=["pubmed_mock_v1"])
    with pytest.raises(CapabilityVocabularyError):
        # empty list is not allowed
        validate_capabilities([], registered_providers=["pubmed_mock_v1"])


def test_extension_capability_requires_known_provider():
    from mafs_p0.capability_vocabulary import is_known
    # registered namespace
    assert is_known("openalex.related_works", registered_providers=["openalex"])
    # unregistered namespace -> not a known capability
    assert not is_known("invented.thing", registered_providers=["openalex"])
    # core
    assert is_known("search.query", registered_providers=[])
