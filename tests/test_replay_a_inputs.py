"""Stub for the original Replay A input-structure tests.

The original Replay A implementation in ``mafs_p0.replay_a`` was
replaced in Replay A-RA1 (Benchmark Fidelity & Stack-Path Closure).
The tests in this file were the Replay A input-structure tests; they
have been superseded by ``tests/test_replay_a_ra1.py`` (10 risk-focused
tests per the RA1 contract §12).

This stub remains only so that pytest collection does not fail on
import errors from the old test file (e.g., references to
``_keyword_score`` which is no longer in ``mafs_p0.replay_a``).
"""
from __future__ import annotations


def test_placeholder_replay_a_ra1_supersedes_this_module():
    """The Replay A input-structure tests have moved to
    ``test_replay_a_ra1.py``. This placeholder exists only so
    pytest collection does not fail.
    """
    pass
