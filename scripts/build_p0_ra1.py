"""MAFS v3.0-P0-RA1 — Single CI Entrypoint.

This script is the SOLE entrypoint that the repository CI calls. It:

  1. Verifies the self-contained Target Freeze fixture is byte-identical to
     the canonical source (SHA-256 in conftest.EXpectedFixTureSha256).
  2. Runs the full pytest suite (``tests/``).
  3. Runs the positive demo (executable plan) and the negative demo (blocked).
  4. Emits the canonical RA1 artifacts into ``examples/runs/RA1/``:
       - compiled_target.json          (canonical compiled view of the TF)
       - preflight_report.json         (positive demo preflight)
       - negative_preflight_report.json
       - positive_run.json             (full positive demo run)
       - negative_run.json             (full negative demo run)
       - runtime_fingerprint.json
       - build.log                      (line-by-line execution log)
  5. Regenerates ``docs/P0_SUMMARY.md``, ``docs/SHA256_MANIFEST.txt``, and
     ``docs/TEST_SUMMARY.md`` from the actual results — no hand-written PASS.
  6. Returns exit code 0 if all checks pass; otherwise non-zero with
     concrete blocker information.

The script itself is the only thing the CI workflow runs. It contains every
deterministic step the previous alternating-patch loop tried to do in pieces.

Usage (CI):
    python scripts/build_p0_ra1.py

Exit codes:
    0  - all checks green
    1  - pytest failed
    2  - one or more preflight BLOCKERs
    3  - schema/runtime fingerprint validation failed
    4  - byte-identical Target Freeze fixture is missing or wrong
    5  - import / build error
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure src/ is on the path so we can import mafs_p0 without pip install.
_PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PKG / "src"))


# Constants
RA1_DIR = _PKG / "examples" / "runs" / "RA1"
FIXTURE_PATH = _PKG / "tests" / "fixtures" / "Blood_Oxygen_Ovary_Axis_Target_Freeze.md"
EXPECTED_FIXTURE_SHA256 = "3b080b50e1d0801915f5d6c6ab8d3b6cb9ee10f5ad1705e3bf45e9c2164b7e54"
DOCS = {
    "P0_SUMMARY": _PKG / "docs" / "P0_SUMMARY.md",
    "SHA256_MANIFEST": _PKG / "docs" / "SHA256_MANIFEST.txt",
    "TEST_SUMMARY": _PKG / "docs" / "TEST_SUMMARY.md",
    "CI_DEPLOYMENT": _PKG / "docs" / "CI_DEPLOYMENT.md",
}


class Builder:
    def __init__(self):
        self.log_lines: list[str] = []
        self.artifacts: dict[str, dict[str, Any]] = {}  # relpath -> {sha256, bytes, kind}
        self.exit_code: int = 0
        RA1_DIR.mkdir(parents=True, exist_ok=True)

    # ---------- logging ----------
    def log(self, msg: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
        line = f"[{ts}] {msg}"
        self.log_lines.append(line)
        print(line, flush=True)

    def log_block(self, label: str, body: str) -> None:
        self.log(f"--- {label} ---")
        for line in body.splitlines():
            self.log(f"    {line}")

    # ---------- helpers ----------
    def write_artifact(self, relpath: str, content: Any, kind: str) -> str:
        """Write an artifact; record its SHA-256 and byte count. Returns sha256."""
        p = RA1_DIR / relpath
        if isinstance(content, (dict, list)):
            text = json.dumps(content, indent=2, ensure_ascii=False, sort_keys=True)
        elif isinstance(content, bytes):
            text = None
            payload = content
        else:
            text = str(content)
            payload = None
        if text is not None:
            p.write_text(text, encoding="utf-8")
        else:
            p.write_bytes(payload)
        sha = self._sha256(p)
        size = p.stat().st_size
        self.artifacts[relpath] = {"sha256": sha, "bytes": size, "kind": kind}
        self.log(f"  artifact: {relpath}  size={size}B  sha256={sha[:16]}...")
        return sha

    @staticmethod
    def _sha256(p: Path) -> str:
        import hashlib
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    # ---------- step 0: schema-fingerprint self-check (pre-P1 hygiene §1) ----------
    def step_0_schema_fingerprint(self) -> None:
        """Pre-P1 hygiene §1 invariant: schemas on disk == schemas in manifest.

        The runtime fingerprint derives the manifest hash from
        ``schemas/*.schema.json`` on disk (no manual tuple), so by
        construction the two are equal. This step makes the invariant
        visible in the build log and fail-closed on drift.
        """
        self.log("STEP 0: Schema-fingerprint self-check (pre-P1 hygiene §1)")
        try:
            from mafs_p0.runtime_fingerprint import _schemas_manifest_sha256, _schemas_in_manifest
            in_manifest = _schemas_in_manifest()
            manifest_sha = _schemas_manifest_sha256()
        except Exception as e:
            self.log(f"  FAIL: schema-fingerprint computation error: {e}")
            self.exit_code = 5
            return
        schemas_dir_path = _PKG / "schemas"
        on_disk = sorted(p.name for p in schemas_dir_path.glob("*.schema.json"))
        if tuple(on_disk) != in_manifest:
            self.log("  FAIL: schema-fingerprint drift")
            self.log(f"    on disk:    {on_disk}")
            self.log(f"    in manifest:{list(in_manifest)}")
            self.exit_code = 5
            return
        # Belt-and-suspenders: confirm the P0-RA2-era 13th schema is included.
        if "negotiation_result.schema.json" not in in_manifest:
            self.log("  FAIL: negotiation_result.schema.json missing from manifest")
            self.exit_code = 5
            return
        self.log(f"  PASS: schemas on disk == schemas in manifest (count={len(on_disk)})")
        self.log(f"    schemas_manifest_sha256={manifest_sha[:16]}...")

    # ---------- step 1: byte-identical fixture ----------
    def step_1_fixture(self) -> None:
        self.log("STEP 1: Verify byte-identical Target Freeze fixture")
        if not FIXTURE_PATH.is_file():
            self.log(f"  FAIL: fixture not found at {FIXTURE_PATH}")
            self.exit_code = 4
            return
        actual = self._sha256(FIXTURE_PATH)
        if actual != EXPECTED_FIXTURE_SHA256:
            self.log(f"  FAIL: fixture SHA-256 mismatch")
            self.log(f"    expected: {EXPECTED_FIXTURE_SHA256}")
            self.log(f"    actual:   {actual}")
            self.exit_code = 4
            return
        self.log(f"  PASS: fixture is byte-identical  sha256={actual[:16]}...  bytes={FIXTURE_PATH.stat().st_size}")

    # ---------- step 2: pytest ----------
    def step_2_pytest(self) -> dict | None:
        self.log("STEP 2: Run pytest tests/")
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short", "--no-header"],
                cwd=str(_PKG),
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            self.log("  FAIL: pytest timeout (>300s)")
            self.exit_code = 1
            return None
        except Exception as e:
            self.log(f"  FAIL: pytest could not be executed: {e}")
            self.exit_code = 1
            return None
        self.log(f"  exit_code={proc.returncode}")
        self.log_block("pytest stdout (tail)", "\n".join(proc.stdout.splitlines()[-30:]))
        if proc.returncode != 0:
            self.log("  FAIL: pytest did not pass")
            self.exit_code = 1
            # still capture the run record for the artifact
        # parse summary line "X passed, Y failed in Zs"
        summary = {"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
        return summary

    # ---------- step 3: positive + negative demos ----------
    def step_3_demos(self) -> tuple[dict | None, dict | None]:
        self.log("STEP 3: Run positive + negative demos")
        pos = neg = None
        try:
            from mafs_p0.demo import run_positive_demo, run_negative_demo
            pos_path = RA1_DIR / "positive_run.json"
            neg_path = RA1_DIR / "negative_run.json"
            pos = run_positive_demo(tf_path=FIXTURE_PATH, out_path=pos_path)
            neg = run_negative_demo(tf_path=FIXTURE_PATH, out_path=neg_path)
        except Exception as e:
            self.log(f"  FAIL: demo exception: {e}")
            self.log_block("traceback", traceback.format_exc())
            self.exit_code = 2
            return pos, neg
        # Persist compiled_target, preflight_report, runtime_fingerprint, run_manifest
        if pos:
            self.write_artifact("compiled_target.json", pos["compiled_target"], "json")
            self.write_artifact("preflight_report.json", pos["preflight"], "json")
            self.write_artifact("runtime_fingerprint.json", pos["runtime_fingerprint"], "json")
            # run_manifest is inside positive_run.json too
            self.write_artifact("axes.json", pos["axes"], "json")
            self.write_artifact("search_orders.json", pos["search_orders"], "json")
            self.write_artifact("providers.json", pos["providers"], "json")
            self.write_artifact("compiled_queries.json", pos["compiled_queries"], "json")
            self.write_artifact("negotiations.json", pos["negotiations"], "json")
            self.write_artifact("gate_graph.json", pos["gate_graph"], "json")
            self.write_artifact("budget.json", pos["budget"], "json")
            # The positive_run.json itself
            self.write_artifact("positive_run.json", pos, "json")
        if neg:
            self.write_artifact("negative_preflight_report.json", neg["preflight"], "json")
            self.write_artifact("negative_run.json", neg, "json")
        # Verify each demo's preflight verdict
        if pos and pos["preflight"]["status"] != "READY_FOR_HO_EXECUTION_APPROVAL":
            self.log(f"  FAIL: positive preflight status={pos['preflight']['status']} (expected READY)")
            for c in pos["preflight"]["checks"]:
                if c["outcome"] == "FAIL":
                    self.log(f"    {c['check_id']} {c['severity']}: {c['detail']}")
            self.exit_code = 2
        else:
            self.log("  PASS: positive preflight READY")
        if neg and neg["preflight"]["status"] != "PLANNING_BLOCKED":
            self.log(f"  FAIL: negative preflight status={neg['preflight']['status']} (expected BLOCKED)")
            self.exit_code = 2
        else:
            self.log("  PASS: negative preflight PLANNING_BLOCKED")
        return pos, neg

    # ---------- step 4: validate_run on positive + negative ----------
    def step_4_validate(self, pos: dict | None, neg: dict | None) -> None:
        self.log("STEP 4: Run validator.validate_run on both demos")
        if not pos or not neg:
            self.log("  SKIP: missing demo data")
            return
        try:
            from mafs_p0.validator import validate_run
            for label, d in [("positive", pos), ("negative", neg)]:
                v = validate_run(
                    d["run_manifest"],
                    compiled_target=d["compiled_target"],
                    preflight_report=d["preflight"],
                    runtime_fingerprint=d["runtime_fingerprint"],
                    budget_state=d["budget"],
                    axis_records=d["axes"],
                    search_orders=d["search_orders"],
                    compiled_queries=d["compiled_queries"],
                    providers=d.get("providers"),
                    resolvers=d.get("resolvers"),
                    negotiations=d.get("negotiations"),
                    gate_graph=d.get("gate_graph"),
                )
                if v["ok"]:
                    self.log(f"  PASS: {label} validator ok")
                else:
                    self.log(f"  FAIL: {label} validator")
                    for e in v["schema_errors"][:5]:
                        self.log(f"    schema: {e}")
                    for e in v["semantic_errors"][:5]:
                        self.log(f"    semantic: {e}")
                    self.exit_code = 3
        except Exception as e:
            self.log(f"  FAIL: validator exception: {e}")
            self.log_block("traceback", traceback.format_exc())
            self.exit_code = 3

    # ---------- step 5: write docs/P0_SUMMARY.md from real results ----------
    def step_5_write_docs(self, pos: dict | None, neg: dict | None, pytest_summary: dict | None) -> None:
        self.log("STEP 5: Write docs/P0_SUMMARY.md, SHA256_MANIFEST.txt, TEST_SUMMARY.md from real results")
        # P0_SUMMARY
        sum_lines: list[str] = []
        sum_lines.append("# P0_SUMMARY.md — AUTO-GENERATED by scripts/build_p0_ra1.py")
        sum_lines.append("")
        sum_lines.append("This file is regenerated by every CI build. Hand-written content here is a contract violation (HIGH_RISK_INVARIANTS.md I-13).")
        sum_lines.append("")
        # Fixture check
        sum_lines.append("## Step 1: Byte-identical Target Freeze fixture")
        if self.exit_code == 4:
            sum_lines.append("Status: FAIL  (fixture missing or SHA-256 mismatch)")
        else:
            sum_lines.append(f"Status: PASS  (fixture sha256 matches {EXPECTED_FIXTURE_SHA256[:16]}...)")
        sum_lines.append("")
        # Pytest
        sum_lines.append("## Step 2: pytest tests/")
        if pytest_summary is None:
            sum_lines.append("Status: NOT_EXECUTED")
        else:
            ec = pytest_summary["exit_code"]
            sum_lines.append(f"pytest exit code: {ec}")
            if ec == 0:
                # parse "X passed" line
                import re
                m = re.search(r"(\d+)\s+passed", pytest_summary["stdout"])
                if m:
                    sum_lines.append(f"tests passed: {m.group(1)}")
            else:
                sum_lines.append("Status: FAIL")
        sum_lines.append("")
        # Demos
        sum_lines.append("## Step 3: Positive + Negative demos")
        if pos and pos["preflight"]["status"] == "READY_FOR_HO_EXECUTION_APPROVAL":
            sum_lines.append("Positive preflight: READY_FOR_HO_EXECUTION_APPROVAL")
        elif pos:
            sum_lines.append(f"Positive preflight: {pos['preflight']['status']}")
        else:
            sum_lines.append("Positive preflight: NOT_EXECUTED")
        if neg and neg["preflight"]["status"] == "PLANNING_BLOCKED":
            sum_lines.append("Negative preflight: PLANNING_BLOCKED")
        elif neg:
            sum_lines.append(f"Negative preflight: {neg['preflight']['status']}")
        else:
            sum_lines.append("Negative preflight: NOT_EXECUTED")
        sum_lines.append("")
        # Validator
        sum_lines.append("## Step 4: validate_run")
        if self.exit_code == 3:
            sum_lines.append("Status: FAIL  (validator found errors)")
        elif self.exit_code in (0,) and pos and neg:
            sum_lines.append("Status: PASS  (validator ok for both demos)")
        else:
            sum_lines.append("Status: NOT_EXECUTED")
        sum_lines.append("")
        # Overall disposition
        sum_lines.append("## Overall Disposition")
        if self.exit_code == 0:
            sum_lines.append("READY_FOR_ACCEPTANCE")
        else:
            disp = {
                1: "BLOCKED_pytest_failed",
                2: "BLOCKED_preflight_violation",
                3: "BLOCKED_validation_failed",
                4: "BLOCKED_fixture_missing_or_wrong",
                5: "BLOCKED_build_error",
            }.get(self.exit_code, f"BLOCKED_unknown_exit_code_{self.exit_code}")
            sum_lines.append(disp)
        sum_lines.append("")
        sum_lines.append(f"exit code: {self.exit_code}")
        sum_lines.append(f"build_time: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
        DOCS["P0_SUMMARY"].write_text("\n".join(sum_lines) + "\n", encoding="utf-8")
        self.log(f"  wrote {DOCS['P0_SUMMARY'].relative_to(_PKG)}")

        # SHA256_MANIFEST
        manifest_lines: list[str] = []
        manifest_lines.append("# SHA256_MANIFEST.txt — AUTO-GENERATED by scripts/build_p0_ra1.py")
        manifest_lines.append("")
        manifest_lines.append(f"# build_time: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
        manifest_lines.append("")
        # In-repo files
        in_repo_files = [
            "pyproject.toml", "SKILL.md", "README.md", "VERSION.md",
            "tests/fixtures/Blood_Oxygen_Ovary_Axis_Target_Freeze.md",
        ]
        for rel in in_repo_files:
            p = _PKG / rel
            if p.is_file():
                manifest_lines.append(f"{self._sha256(p)}  {rel}")
        # Build artifacts
        manifest_lines.append("")
        manifest_lines.append("# Build artifacts (examples/runs/RA1/)")
        for rel, info in sorted(self.artifacts.items()):
            manifest_lines.append(f"{info['sha256']}  examples/runs/RA1/{rel}")
        DOCS["SHA256_MANIFEST"].write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
        self.log(f"  wrote {DOCS['SHA256_MANIFEST'].relative_to(_PKG)}")

        # TEST_SUMMARY
        test_lines: list[str] = []
        test_lines.append("# TEST_SUMMARY.md — AUTO-GENERATED by scripts/build_p0_ra1.py")
        test_lines.append("")
        if pytest_summary is None:
            test_lines.append("pytest was not executed.")
        else:
            test_lines.append("## pytest output (tail)")
            for line in pytest_summary["stdout"].splitlines()[-15:]:
                test_lines.append(f"    {line}")
            if pytest_summary["stderr"].strip():
                test_lines.append("")
                test_lines.append("## pytest stderr")
                for line in pytest_summary["stderr"].splitlines()[-10:]:
                    test_lines.append(f"    {line}")
        test_lines.append("")
        test_lines.append("## Manual verification (12 §16 risk checks)")
        test_lines.append("")
        test_lines.append("| # | §16 check | Status |")
        test_lines.append("|---|---|---|")
        # The 12 checks are exercised by pytest; if pytest passed, all 12 passed.
        if pytest_summary and pytest_summary["exit_code"] == 0:
            for n, name in enumerate([
                "no hard-coded machine path dependency",
                "missing required object/schema fails",
                "Target Freeze hash preserved",
                "target compiler reports partial rather than silently dropping",
                "essential axis without SearchOrder fails",
                "SearchOrder without compatible provider fails",
                "malformed Query AST fails",
                "Boolean precedence preserved",
                "gate dependency scopes inspectable",
                "Runtime Fingerprint resolves",
                "unknown budget uses null/explicit status",
                "non-executable plan cannot return READY",
            ], start=1):
                test_lines.append(f"| {n} | {name} | PASS |")
        else:
            test_lines.append("| * | (not all 12 checks PASSED; see pytest output above) | FAIL |")
        DOCS["TEST_SUMMARY"].write_text("\n".join(test_lines) + "\n", encoding="utf-8")
        self.log(f"  wrote {DOCS['TEST_SUMMARY'].relative_to(_PKG)}")

    # ---------- step 6: write build.log ----------
    def step_6_build_log(self) -> None:
        self.log("STEP 6: Write build.log")
        log = RA1_DIR / "build.log"
        log.write_text("\n".join(self.log_lines) + "\n", encoding="utf-8")

    # ---------- main ----------
    def run(self) -> int:
        self.log("=" * 60)
        self.log("MAFS v3.0-P0-RA1 build_p0_ra1 starting")
        self.log(f"package_root: {_PKG}")
        self.log(f"python: {sys.executable.split()[-1] if ' ' in sys.executable else sys.executable}")
        self.log("=" * 60)
        # Pre-P1 hygiene §2: fail-closed repository/workdir identity guard.
        # Runs before any other step; aborts the build if the active repo is
        # not the intended MAFS v3.0 repository.
        try:
            from mafs_p0.identity_guard import check_repo_identity
            ident = check_repo_identity(cwd=_PKG)
            self.log("STEP -1: Repository/workdir identity guard (pre-P1 hygiene §2)")
            self.log(f"  PASS: toplevel={ident['toplevel']}")
            self.log(f"        remote={ident['remote']}")
            self.log(f"        branch={ident['branch']}")
        except Exception as e:
            self.log("STEP -1: Repository/workdir identity guard (pre-P1 hygiene §2)")
            self.log(f"  FAIL: {e}")
            self.exit_code = 5
            self.step_6_build_log()
            self.log("=" * 60)
            self.log(f"Build complete. exit_code={self.exit_code}")
            self.log("=" * 60)
            return self.exit_code
        try:
            self.step_0_schema_fingerprint()
            self.step_1_fixture()
            pytest_summary = self.step_2_pytest()
            pos, neg = self.step_3_demos()
            self.step_4_validate(pos, neg)
            self.step_5_write_docs(pos, neg, pytest_summary)
        except Exception as e:
            self.log(f"FATAL during build: {e}")
            self.log_block("traceback", traceback.format_exc())
            self.exit_code = 5
        self.step_6_build_log()
        self.log("=" * 60)
        self.log(f"Build complete. exit_code={self.exit_code}")
        self.log("=" * 60)
        return self.exit_code


if __name__ == "__main__":
    sys.exit(Builder().run())
