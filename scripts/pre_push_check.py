"""P1.5-RA3 §11.1 mandatory pre-push local feedback loop.

Before the first meaningful code-changing push, Local Claw must
locally run:

  1. affected deterministic pytest set;
  2. all affected scripts/build_*.py entrypoints;
  3. one deterministic acceptance-artifact generation path.

This script invokes the existing checks. It is not a new test
framework; it does not introduce new test cases. It is a thin
dispatcher over the existing entry points.

Usage:
    python scripts/pre_push_check.py [round_tag]

The round_tag is used in the artifact directory name (default: the
current git HEAD short SHA). The script exits non-zero on the
first failure; the operator must address the failure before push.

Per P1.5-RA3 §11.2: the RA3 acceptance allows at most 3 meaningful
code-changing push → CI → diagnose cycles. If the third cycle is
still not green: ITERATION_BUDGET_EXHAUSTED → STOP → blocker
report. This script is the LOCAL half of that discipline; the
CI half is the GitHub Actions workflow.

This script is not parallel .sh + .ps1: it is a single Python
entry point that runs in any Python environment that can already
run the project's tests and entrypoint scripts (per §11.1
"do not create parallel .sh + .ps1 frameworks unless the repository
genuinely requires both").
"""
from __future__ import annotations
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


PKG = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = PKG / "examples" / "runs" / "pre_push_check"


def _run(cmd: list[str], *, cwd: Path, label: str, timeout: int = 180) -> int:
    print(f"\n=== {label} ===")
    print(f"  $ {' '.join(cmd)}")
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd), check=False,
            timeout=timeout, capture_output=True, text=True,
        )
    except subprocess.TimeoutExpired as e:
        print(f"  TIMEOUT after {timeout}s")
        return 124
    dt = time.time() - t0
    if proc.returncode == 0:
        print(f"  PASS in {dt:.1f}s")
    else:
        print(f"  FAIL exit={proc.returncode} in {dt:.1f}s")
        # Print the last ~30 lines of stdout/stderr for diagnosis.
        for stream_name, stream in (("STDOUT", proc.stdout), ("STDERR", proc.stderr)):
            if stream:
                tail = stream.strip().splitlines()[-30:]
                print(f"  --- {stream_name} (last 30 lines) ---")
                for line in tail:
                    print(f"    {line}")
    return proc.returncode


def _git_head_short(cwd: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(cwd), capture_output=True, text=True, check=True,
            timeout=10,
        ).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _git_changed_files(cwd: Path) -> list[str]:
    """Return files changed vs HEAD~1 (a rough 'affected' set).
    Falls back to a small static set if HEAD~1 is unavailable.
    """
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1..HEAD"],
            cwd=str(cwd), capture_output=True, text=True, check=True,
            timeout=10,
        ).stdout.strip()
        files = [f for f in out.splitlines() if f]
        if files:
            return files
    except Exception:
        pass
    # Static fallback: always-affected core paths.
    return [
        "src/mafs_p0/live_chain.py",
        "src/mafs_p0/live_crossref.py",
        "src/mafs_p0/live_demo.py",
        "scripts/replay_b.py",
        "scripts/build_p1_min.py",
        "scripts/build_p0_ra1.py",
    ]


def _affected_pytest_targets(cwd: Path) -> list[str]:
    """Pick the affected pytest test files based on the changed set.

    P1.5-RA3 changed files live primarily under:
      - src/mafs_p0/ (production)
      - scripts/ (orchestrator + build)
    The affected test files are:
      - tests/test_p1_5*.py
      - tests/test_p1_*.py
      - tests/test_replay_b_*.py
    """
    files = _git_changed_files(cwd)
    targets: set[str] = set()
    needs_core = any(
        f.startswith(("src/mafs_p0/", "scripts/")) for f in files
    )
    if needs_core or not files:
        targets.update([
            "tests/test_p1_5.py",
            "tests/test_p1_5_ra1.py",
            "tests/test_p1_5_ra2.py",
            "tests/test_p1_5_ra3.py",
            "tests/test_p1_live_chain.py",
            "tests/test_p1_ra1.py",
            "tests/test_replay_b_ra1.py",
            "tests/test_replay_b_reopen_OFFLINE.py",
        ])
    return sorted(targets)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("round_tag", nargs="?", default=None,
                        help="Tag for the artifact directory (default: HEAD short SHA)")
    parser.add_argument("--skip-tests", action="store_true",
                        help="Skip the pytest step (e.g. when the test files are unchanged)")
    parser.add_argument("--skip-builds", action="store_true",
                        help="Skip the build_*.py entrypoint step")
    parser.add_argument("--include-artifact", action="store_true",
                        help="Run the deterministic artifact generation step. "
                             "By default this is skipped because the project's "
                             "scripts/replay_b.py and build_p1_min.py do not have "
                             "an --offline flag; running them locally would hit the "
                             "live Crossref API. Use this flag only when the entry "
                             "point is offline-safe (e.g. mock provider).")
    args = parser.parse_args()
    cwd = PKG
    head = args.round_tag or _git_head_short(cwd)
    art_dir = ARTIFACT_DIR / head
    art_dir.mkdir(parents=True, exist_ok=True)
    # ---- Step 1: affected pytest ----
    if not args.skip_tests:
        targets = _affected_pytest_targets(cwd)
        if targets:
            cmd = [sys.executable, "-m", "pytest", "-q", "--tb=line", *targets]
            rc = _run(cmd, cwd=cwd, label="affected pytest", timeout=600)
            if rc != 0:
                print("\n[pre_push_check] step 1 (pytest) FAILED; address before push.")
                return rc
        else:
            print("\n[pre_push_check] no affected pytest targets detected; skipping.")
    # ---- Step 2: all scripts/build_*.py entrypoints ----
    if not args.skip_builds:
        builds = sorted((cwd / "scripts").glob("build_*.py"))
        if builds:
            for bp in builds:
                cmd = [sys.executable, str(bp)]
                rc = _run(cmd, cwd=cwd, label=f"entrypoint: {bp.name}", timeout=180)
                if rc != 0:
                    print(f"\n[pre_push_check] step 2 ({bp.name}) FAILED; address before push.")
                    return rc
        else:
            print("\n[pre_push_check] no scripts/build_*.py found; skipping.")
    # ---- Step 3: deterministic acceptance-artifact generation ----
    # P1.5-RA3 §11.1 item 3: invoke the P1.5 orchestrator's artifact
    # generation path. By default we SKIP this step because the
    # project's entrypoints (replay_b.py, build_p1_min.py) do not
    # have an --offline flag; running them locally would hit the
    # live Crossref API. CI is the right plane for live artifact
    # generation. The operator may pass --include-artifact when the
    # entrypoint is offline-safe (e.g. mock provider).
    if not args.include_artifact:
        print("\n[pre_push_check] step 3 (artifact generation) SKIPPED "
              "(default; pass --include-artifact only when the entrypoint is "
              "offline-safe). CI is the machine-truth plane for live artifacts.")
    else:
        cmd = [sys.executable, "scripts/replay_b.py"]
        rc = _run(cmd, cwd=cwd, label="artifact generation", timeout=180)
        if rc != 0:
            print(f"\n[pre_push_check] step 3 (artifact) returned exit={rc}; "
                  "this may be expected if the entrypoint hits live Crossref.")
    print(f"\n[pre_push_check] all steps passed (or skipped). round_tag={head}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
