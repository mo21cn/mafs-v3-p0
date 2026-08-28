"""Repository / workdir identity guard (pre-P1 hygiene §2).

Purpose: fail-closed check that the active git repository IS the
intended MAFS v3.0 repository. Local Claw MUST NOT mutate the
intended repo from the wrong shell workdir, and MUST NOT confuse
the v3.0 P0 worktree with v0.1 / v0.2 / v0.3 historical worktrees.

Pre-P1 hygiene §2 invariant: before any repository mutation or
CI-artifact handling, the executing code path verifies
  - git rev-parse --show-toplevel
  - git remote get-url origin
  - git rev-parse --abbrev-ref HEAD
and aborts if any of those does not match the expected MAFS v3.0
repository identity.

The expected identity is hard-coded here (it is the same
information the GitHub App uses to provision the repo). The
guard is fail-closed: missing git, missing remote, or any
mismatch raises ``IdentityGuardError`` and prevents any further
action. The exception message is explicit about the actual vs
expected values, so a wrong-workdir mistake produces a loud,
actionable error rather than a silent mutation of the wrong repo.
"""
from __future__ import annotations
import re
import subprocess
from pathlib import Path
from typing import Sequence


# Expected identity for the MAFS v3.0-P0+ development repo.
# The substring is checked as a `Path` part to tolerate Windows
# backslash / forward-slash differences.
EXPECTED_TOPLEVEL_SUBSTR: str = "multi_axis_falsification_search_v3_p0"
EXPECTED_REMOTE_URL: str = "https://github.com/mo21cn/mafs-v3-p0.git"
EXPECTED_BRANCHES: tuple[str, ...] = (
    # Pre-P1 acceptance (P0-RA2 work branch)
    "dev/mafs-v3-p0-ra2",
    # Post-P1 hygiene §4: accepted P0 state on main
    "main",
)


class IdentityGuardError(RuntimeError):
    """Raised when the active git repository does not match the
    expected MAFS v3.0 repository identity. Fail-closed."""


def _run_git(*args: str, cwd: Path) -> str:
    """Run a git subcommand and return stdout, or raise."""
    try:
        out = subprocess.run(
            ("git",) + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError as e:
        raise IdentityGuardError(f"git not found on PATH: {e}") from e
    except subprocess.TimeoutExpired as e:
        raise IdentityGuardError(f"git {args!r} timed out: {e}") from e
    if out.returncode != 0:
        raise IdentityGuardError(
            f"git {args!r} failed in {cwd}: rc={out.returncode}, "
            f"stderr={out.stderr.strip()!r}"
        )
    return out.stdout.rstrip("\n")


def check_repo_identity(cwd: Path | None = None) -> dict:
    """Verify the active repository IS the intended MAFS v3.0 repo.

    Returns a dict with the verified identity fields. Raises
    ``IdentityGuardError`` on any mismatch or git failure.
    """
    cwd = Path(cwd) if cwd is not None else Path.cwd()
    toplevel = _run_git("rev-parse", "--show-toplevel", cwd=cwd)
    remote = _run_git("remote", "get-url", "origin", cwd=cwd)
    branch = _run_git("rev-parse", "--abbrev-ref", "HEAD", cwd=cwd)

    # Toplevel must contain the expected package name as a path part.
    # Normalize backslashes to forward slashes for cross-platform check.
    norm = toplevel.replace("\\", "/")
    if EXPECTED_TOPLEVEL_SUBSTR not in norm:
        raise IdentityGuardError(
            f"identity guard: wrong repo toplevel.\n"
            f"  expected path contains: {EXPECTED_TOPLEVEL_SUBSTR!r}\n"
            f"  actual toplevel:        {toplevel!r}\n"
            f"  cwd:                    {cwd}\n"
            f"  action: refuse to proceed."
        )

    # Remote must match the expected GitHub repository.
    if remote != EXPECTED_REMOTE_URL:
        raise IdentityGuardError(
            f"identity guard: wrong remote URL.\n"
            f"  expected: {EXPECTED_REMOTE_URL!r}\n"
            f"  actual:   {remote!r}\n"
            f"  cwd:      {cwd}\n"
            f"  action: refuse to proceed."
        )

    # Branch must be one of the expected acceptance branches.
    if branch not in EXPECTED_BRANCHES:
        raise IdentityGuardError(
            f"identity guard: wrong branch.\n"
            f"  expected one of: {list(EXPECTED_BRANCHES)}\n"
            f"  actual:          {branch!r}\n"
            f"  cwd:             {cwd}\n"
            f"  action: refuse to proceed."
        )

    return {
        "toplevel": toplevel,
        "remote": remote,
        "branch": branch,
        "expected_toplevel_substr": EXPECTED_TOPLEVEL_SUBSTR,
        "expected_remote_url": EXPECTED_REMOTE_URL,
        "expected_branches": list(EXPECTED_BRANCHES),
    }
