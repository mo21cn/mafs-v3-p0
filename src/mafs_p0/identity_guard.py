"""Repository / workdir identity guard (pre-P1 hygiene §2).

Purpose: fail-closed check that the active git repository IS the
intended MAFS v3.0 repository. Local Claw MUST NOT mutate the
intended repo from the wrong shell workdir, and MUST NOT confuse
the v3.0 P0 worktree with v0.1 / v0.2 / v0.3 historical worktrees.

Pre-P1 hygiene §2 invariant: before any repository mutation or
CI-artifact handling, the executing code path verifies
  - git rev-parse --show-toplevel  (must contain pyproject.toml
                                    with the expected package name)
  - git remote get-url origin      (must match the expected URL)
  - git rev-parse --abbrev-ref HEAD (must be one of the expected
                                      branches)
and aborts if any of those does not match the expected MAFS v3.0
repository identity.

Note on toplevel check: the contract lists ``git rev-parse
--show-toplevel`` but the SEMANTIC question is "is this the MAFS
v3.0 worktree". The portable cross-platform answer is to verify
that the toplevel contains a ``pyproject.toml`` whose ``[project]
name`` field matches the expected package name. A filesystem-path
substring check would break on the CI runner, which checks out
to ``/home/runner/work/mafs-v3-p0/mafs-v3-p0`` rather than a
path containing the local skill folder name.

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
# The toplevel check is portable: it asserts the pyproject.toml
# project name, not a filesystem-path substring (which would
# differ between Windows development, macOS development, and
# the GitHub-Actions Linux runner).
EXPECTED_PYPROJECT_NAME: str = "multi-axis-falsification-search-v3-p0"
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


def _verify_pyproject_name(toplevel: Path) -> str:
    """Read ``<toplevel>/pyproject.toml`` and extract the ``[project]
    name`` value. Raises ``IdentityGuardError`` if the file is
    missing or the name does not match ``EXPECTED_PYPROJECT_NAME``.

    Portable across Python 3.10 (the CI runner version) and 3.11+:
    uses a regex on the raw text rather than ``tomllib`` to avoid
    the stdlib-version dependency. The ``[project] name = "..."``
    line is on a single line in the project's pyproject.toml.

    This is a portable cross-platform check: the toplevel path can
    differ between Windows / macOS / Linux / CI runner, but the
    package metadata is the same in every checkout of the same
    repository.
    """
    pyproject = toplevel / "pyproject.toml"
    if not pyproject.is_file():
        raise IdentityGuardError(
            f"identity guard: pyproject.toml not found at toplevel.\n"
            f"  toplevel: {toplevel}\n"
            f"  expected: {pyproject}\n"
            f"  action: refuse to proceed."
        )
    text = pyproject.read_text(encoding="utf-8")
    # Match the FIRST `name = "..."` line under [project] (or anywhere
    # in the file if the section header is missing). The pattern is
    # intentionally simple — pyproject.toml format guarantees that
    # the project's name is a quoted string on its own line.
    m = re.search(r'^name\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
    if not m:
        raise IdentityGuardError(
            f"identity guard: could not find `name = \"...\"` in pyproject.toml.\n"
            f"  toplevel: {toplevel}\n"
            f"  pyproject: {pyproject}\n"
            f"  action: refuse to proceed."
        )
    actual = m.group(1)
    if actual != EXPECTED_PYPROJECT_NAME:
        raise IdentityGuardError(
            f"identity guard: wrong package identity in pyproject.toml.\n"
            f"  expected [project].name: {EXPECTED_PYPROJECT_NAME!r}\n"
            f"  actual [project].name:   {actual!r}\n"
            f"  toplevel: {toplevel}\n"
            f"  action: refuse to proceed."
        )
    return actual


def check_repo_identity(cwd: Path | None = None) -> dict:
    """Verify the active repository IS the intended MAFS v3.0 repo.

    Returns a dict with the verified identity fields. Raises
    ``IdentityGuardError`` on any mismatch or git failure.
    """
    cwd = Path(cwd) if cwd is not None else Path.cwd()
    toplevel_str = _run_git("rev-parse", "--show-toplevel", cwd=cwd)
    toplevel = Path(toplevel_str)
    remote = _run_git("remote", "get-url", "origin", cwd=cwd)
    branch = _run_git("rev-parse", "--abbrev-ref", "HEAD", cwd=cwd)

    # Portable toplevel check: package name in pyproject.toml
    # (not a filesystem-path substring).
    package_name = _verify_pyproject_name(toplevel)

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
        "toplevel": str(toplevel),
        "remote": remote,
        "branch": branch,
        "package_name": package_name,
        "expected_remote_url": EXPECTED_REMOTE_URL,
        "expected_branches": list(EXPECTED_BRANCHES),
    }
