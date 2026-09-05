"""Identity guard test (pre-P1 hygiene §2).

Verifies the repository/workdir identity guard:
  1. Calling it on the current (correct) MAFS v3.0 repo returns the
     expected identity and does not raise.
  2. The expected-identity constants are non-empty and parseable.
  3. The guard module exposes the documented constants and the
     ``check_repo_identity`` function.

This test is intentionally light on real-git invocations to avoid
CI flakiness from missing git on rare runner images; the
authoritative check is the in-build-script call (``STEP -1``) which
runs on every CI execution.
"""
from __future__ import annotations
from mafs_p0.identity_guard import (
    EXPECTED_PYPROJECT_NAME,
    EXPECTED_REMOTE_OWNER_REPO,
    EXPECTED_BRANCHES,
    IdentityGuardError,
    check_repo_identity,
)


def test_expected_identity_constants_are_populated():
    assert isinstance(EXPECTED_PYPROJECT_NAME, str) and len(EXPECTED_PYPROJECT_NAME) > 0
    assert EXPECTED_PYPROJECT_NAME == "multi-axis-falsification-search-v3-p0"
    assert isinstance(EXPECTED_REMOTE_OWNER_REPO, str)
    assert "/" in EXPECTED_REMOTE_OWNER_REPO
    assert EXPECTED_REMOTE_OWNER_REPO == "mo21cn/mafs-v3-p0"
    assert isinstance(EXPECTED_BRANCHES, tuple) and len(EXPECTED_BRANCHES) >= 1
    # The two expected branches are the P0 work branch and the
    # post-acceptance main branch.
    assert "main" in EXPECTED_BRANCHES
    assert any("dev/" in b for b in EXPECTED_BRANCHES)
    assert "dev/post-p1p5-semantic-r4-r5" in EXPECTED_BRANCHES


def test_identity_guard_passes_on_current_repo():
    """When invoked from the MAFS v3.0 repo, the guard must return a
    populated identity dict and not raise."""
    ident = check_repo_identity()
    assert "toplevel" in ident
    assert "remote" in ident
    assert "branch" in ident
    assert "package_name" in ident
    assert "owner_repo" in ident
    assert ident["package_name"] == EXPECTED_PYPROJECT_NAME
    assert ident["owner_repo"] == EXPECTED_REMOTE_OWNER_REPO
    assert ident["branch"] in EXPECTED_BRANCHES


def test_identity_guard_error_is_typed():
    """The guard's error class must be a RuntimeError subclass so it
    composes with the existing except-Exception handlers in the
    build script."""
    assert issubclass(IdentityGuardError, RuntimeError)
