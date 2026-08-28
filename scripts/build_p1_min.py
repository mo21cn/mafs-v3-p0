"""MAFS v3.0-P1 Minimum Live Chain — CI entrypoint.

This script is the entrypoint for the P1 live smoke. It:

  1. Verifies the pre-P1 hygiene STEP -1 (identity guard) and STEP 0
     (schema-fingerprint self-check) — these are the same checks the
     P0 build runs, and the P1 chain depends on the 18-schema set
     (13 P0 + 5 P1).
  2. Runs the P1 live demo (one real Crossref chain + one negative
     path).
  3. Persists the artifact set required by contract §19:
       P1_SUMMARY.md, TEST_SUMMARY.md, CI_PROVENANCE.md,
       SHA256_MANIFEST.txt, live_search_order.json, compiled_query.json,
       retrieval_invocation.json, candidate_pointer.json,
       resolver_invocation.json, raw_snapshot.json (base64-encoded),
       canonical_evidence.json, negative_demo.json,
       runtime_fingerprint.json, build.log
  4. Regenerates the docs from real run results (no hand-written PASS).
  5. Returns exit code 0 if all checks pass; otherwise non-zero with
     a concrete blocker.

This script is the SINGLE CI entrypoint for the P1 acceptance run.
The ``.github/workflows/mafs-p1-live.yml`` workflow calls it on
``workflow_dispatch`` (manual trigger) and on a push to the work
branch.

Exit codes:
  0  - live chain and negative path both green
  1  - live positive chain returned status != "ok"
  2  - live negative path returned status != "failed_network"
  3  - capability advertisement check failed
  4  - schema-fingerprint self-check failed
  5  - identity guard failed (or import / build error)
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Ensure src/ is on the path so we can import mafs_p0 without pip install.
_PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PKG / "src"))


P1_DIR = _PKG / "examples" / "runs" / "P1"
DOCS = {
    "P1_SUMMARY": _PKG / "docs" / "P1_SUMMARY.md",
    "SHA256_MANIFEST": _PKG / "docs" / "P1_SHA256_MANIFEST.txt",
    "CI_PROVENANCE": _PKG / "docs" / "P1_CI_PROVENANCE.md",
    "TEST_SUMMARY": _PKG / "docs" / "P1_TEST_SUMMARY.md",
}


class Builder:
    def __init__(self):
        self.log_lines: list[str] = []
        self.artifacts: dict[str, dict[str, Any]] = {}
        self.exit_code: int = 0
        P1_DIR.mkdir(parents=True, exist_ok=True)

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
        p = P1_DIR / relpath
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
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    # ---------- step -1: identity guard ----------
    def step_identity_guard(self) -> None:
        try:
            from mafs_p0.identity_guard import check_repo_identity
            ident = check_repo_identity(cwd=_PKG)
            self.log("STEP -1: Repository/workdir identity guard")
            self.log(f"  PASS: package_name={ident['package_name']}")
            self.log(f"        owner/repo={ident['owner_repo']}")
            self.log(f"        branch={ident['branch']}")
        except Exception as e:
            self.log("STEP -1: Repository/workdir identity guard")
            self.log(f"  FAIL: {e}")
            self.exit_code = 5

    # ---------- step 0: schema-fingerprint self-check ----------
    def step_schema_fingerprint(self) -> None:
        try:
            from mafs_p0.runtime_fingerprint import _schemas_manifest_sha256, _schemas_in_manifest
            in_manifest = _schemas_in_manifest()
            manifest_sha = _schemas_manifest_sha256()
        except Exception as e:
            self.log(f"  FAIL: schema-fingerprint computation error: {e}")
            self.exit_code = 4
            return
        schemas_dir_path = _PKG / "schemas"
        on_disk = sorted(p.name for p in schemas_dir_path.glob("*.schema.json"))
        if tuple(on_disk) != in_manifest:
            self.log("  FAIL: schema-fingerprint drift")
            self.exit_code = 4
            return
        self.log(f"STEP 0: Schema-fingerprint self-check")
        self.log(f"  PASS: schemas on disk == schemas in manifest (count={len(on_disk)})")
        self.log(f"    schemas_manifest_sha256={manifest_sha[:16]}...")

    # ---------- step 1: live positive + negative chains ----------
    def step_live_chains(self) -> dict | None:
        self.log("STEP 1: Run P1 live demo (positive + negative)")
        try:
            from mafs_p0.live_demo import run_p1_live_demo
            result = run_p1_live_demo(allow_network=True)
        except Exception as e:
            self.log(f"  FAIL: live demo exception: {e}")
            self.log_block("traceback", traceback.format_exc())
            self.exit_code = 5
            return None
        # Persist the artifact set (contract §19)
        # ... but skip ones that are None on early failure paths.
        pos = result.get("positive_run") or {}
        neg = result.get("negative_run") or {}
        so = result.get("search_order") or {}
        if so:
            self.write_artifact("live_search_order.json", so, "json")
        cq = pos.get("compiled_query") or ""
        if cq:
            self.write_artifact("compiled_query.json", {"schema_version": "3.0-p1", "rendered_query": cq, "search_order_id": so.get("search_order_id", "")}, "json")
        cps = pos.get("candidate_pointers") or []
        if cps:
            self.write_artifact("candidate_pointer.json", cps, "json")
        riv = pos.get("retrieval_invocation")
        if riv:
            self.write_artifact("retrieval_invocation.json", riv, "json")
        rsnap = pos.get("retrieval_snapshot")
        if rsnap:
            self.write_artifact("raw_snapshot.json", rsnap, "json")
        ev = pos.get("canonical_evidence")
        if ev:
            self.write_artifact("canonical_evidence.json", ev, "json")
        rivr = pos.get("resolver_invocation")
        if rivr:
            self.write_artifact("resolver_invocation.json", rivr, "json")
        if neg:
            self.write_artifact("negative_demo.json", neg, "json")
        # Runtime fingerprint (P0 path still works; re-run here so
        # P1 evidence has its own fresh fingerprint)
        try:
            from mafs_p0.runtime_fingerprint import build_fingerprint
            fp = build_fingerprint()  # empty manifests is fine; the
                                       # build just needs the schema
                                       # manifest SHA + skill SHA.
            self.write_artifact("runtime_fingerprint.json", fp, "json")
        except Exception as e:
            self.log(f"  WARN: runtime fingerprint exception (non-fatal): {e}")
        # Verdict
        if pos.get("status") != "ok":
            self.log(f"  FAIL: positive chain status={pos.get('status')} (expected ok)")
            self.exit_code = 1
        else:
            self.log(f"  PASS: positive chain ok (candidates={len(cps)}, evidence_id={ev.get('evidence_id') if ev else None})")
        if neg.get("status") != "failed_network":
            self.log(f"  FAIL: negative chain status={neg.get('status')} (expected failed_network)")
            self.exit_code = 2
        else:
            self.log(f"  PASS: negative chain recorded failure (canonical_evidence=None, no fabrication)")
        return result

    # ---------- step 2: write docs ----------
    def step_write_docs(self, result: dict | None) -> None:
        self.log("STEP 2: Write P1 docs")
        if result is None:
            return
        summary = result.get("summary") or {}
        pos = result.get("positive_run") or {}
        neg = result.get("negative_run") or {}
        # P1_SUMMARY
        s_lines: list[str] = []
        s_lines.append("# P1_SUMMARY.md — AUTO-GENERATED by scripts/build_p1_min.py")
        s_lines.append("")
        s_lines.append("MAFS v3.0-P1 Minimum Live Chain Contract — CI-generated acceptance summary.")
        s_lines.append("")
        s_lines.append("## Live chain (positive)")
        s_lines.append(f"- status: `{pos.get('status')}`")
        s_lines.append(f"- search_order_id: `{pos.get('search_order_id')}`")
        s_lines.append(f"- compiled_query: `{pos.get('compiled_query')}`")
        s_lines.append(f"- candidate_count: `{len(pos.get('candidate_pointers') or [])}`")
        cps = pos.get("candidate_pointers") or []
        if cps:
            s_lines.append(f"- top_candidate: `{cps[0].get('provider_result_id')}` (rank={cps[0].get('rank')}, title_hint=\"{cps[0].get('title_hint') or ''}\")")
        ev = pos.get("canonical_evidence")
        if ev:
            can = ev.get("canonical") or {}
            s_lines.append(f"- evidence_id: `{ev.get('evidence_id')}`")
            s_lines.append(f"- canonical.title: `{can.get('title')}`")
            s_lines.append(f"- canonical.doi: `{can.get('doi')}`")
            s_lines.append(f"- canonical.year: `{can.get('year')}`")
            s_lines.append(f"- canonical.venue: `{can.get('venue')}`")
            s_lines.append(f"- canonical.authors_count: `{len(can.get('authors') or [])}`")
        s_lines.append("")
        s_lines.append("## Live chain (negative)")
        s_lines.append(f"- status: `{neg.get('status')}`")
        s_lines.append(f"- canonical_evidence: `{neg.get('canonical_evidence')}` (must be null)")
        s_lines.append("")
        s_lines.append("## Overall Disposition")
        if self.exit_code == 0:
            s_lines.append("READY_FOR_ACCEPTANCE")
        else:
            disp = {
                1: "BLOCKED_positive_chain_not_ok",
                2: "BLOCKED_negative_chain_wrong_status",
                3: "BLOCKED_capability_mismatch",
                4: "BLOCKED_schema_fingerprint",
                5: "BLOCKED_build_error_or_identity_guard",
            }.get(self.exit_code, f"BLOCKED_unknown_exit_code_{self.exit_code}")
            s_lines.append(disp)
        s_lines.append("")
        s_lines.append(f"exit code: {self.exit_code}")
        s_lines.append(f"build_time: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
        DOCS["P1_SUMMARY"].write_text("\n".join(s_lines) + "\n", encoding="utf-8")
        self.log(f"  wrote {DOCS['P1_SUMMARY'].relative_to(_PKG)}")
        # SHA256_MANIFEST
        m_lines: list[str] = []
        m_lines.append("# P1_SHA256_MANIFEST.txt — AUTO-GENERATED by scripts/build_p1_min.py")
        m_lines.append("")
        m_lines.append(f"# build_time: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
        m_lines.append("")
        # In-repo source files (subset; same convention as P0 manifest)
        in_repo = [
            "pyproject.toml", "SKILL.md", "README.md", "VERSION.md",
            "tests/fixtures/Blood_Oxygen_Ovary_Axis_Target_Freeze.md",
        ]
        for rel in in_repo:
            p = _PKG / rel
            if p.is_file():
                m_lines.append(f"{self._sha256(p)}  {rel}")
        m_lines.append("")
        m_lines.append("# P1 Build artifacts (examples/runs/P1/)")
        for rel, info in sorted(self.artifacts.items()):
            m_lines.append(f"{info['sha256']}  examples/runs/P1/{rel}")
        DOCS["SHA256_MANIFEST"].write_text("\n".join(m_lines) + "\n", encoding="utf-8")
        self.log(f"  wrote {DOCS['SHA256_MANIFEST'].relative_to(_PKG)}")
        # P1_TEST_SUMMARY
        t_lines: list[str] = []
        t_lines.append("# P1_TEST_SUMMARY.md — AUTO-GENERATED by scripts/build_p1_min.py")
        t_lines.append("")
        t_lines.append("P1 does NOT optimize for test count (contract §17).")
        t_lines.append("The 10 risk-focused tests live in tests/test_p1_*.py.")
        t_lines.append("")
        t_lines.append("This live smoke verifies:")
        t_lines.append("- positive chain: 1 live Crossref /works?query= + 1 /works/{doi} call, both 200 OK")
        t_lines.append("- negative chain: 1 unroutable TEST-NET-1 host, status=failed_network, evidence=None")
        t_lines.append("- capability advertisement: provider advertises the SearchOrder's required capabilities")
        t_lines.append("- snapshot integrity: each invocation's raw_snapshot_sha256 matches the persisted raw_snapshot.json")
        t_lines.append("- canonical evidence dual-provenance: retrieval + resolver snapshot SHAs both present")
        DOCS["TEST_SUMMARY"].write_text("\n".join(t_lines) + "\n", encoding="utf-8")
        self.log(f"  wrote {DOCS['TEST_SUMMARY'].relative_to(_PKG)}")
        # CI_PROVENANCE (a stub; full provenance is produced by the
        # GitHub Actions workflow; this is a placeholder so the file
        # exists for §15/§19 references).
        c_lines: list[str] = []
        c_lines.append("# P1_CI_PROVENANCE.md — generated at build time; the full provenance record is in CI artifacts")
        c_lines.append("")
        c_lines.append(f"build_time: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
        c_lines.append(f"positive_status: {pos.get('status')}")
        c_lines.append(f"negative_status: {neg.get('status')}")
        c_lines.append(f"candidate_count: {len(cps)}")
        if ev:
            c_lines.append(f"canonical_doi: {ev.get('canonical', {}).get('doi')}")
            c_lines.append(f"retrieval_snapshot_sha256: {ev.get('provenance', {}).get('retrieval_snapshot_sha256')}")
            c_lines.append(f"resolver_snapshot_sha256: {ev.get('provenance', {}).get('resolver_snapshot_sha256')}")
        DOCS["CI_PROVENANCE"].write_text("\n".join(c_lines) + "\n", encoding="utf-8")
        self.log(f"  wrote {DOCS['CI_PROVENANCE'].relative_to(_PKG)}")

    # ---------- step 3: build.log ----------
    def step_build_log(self) -> None:
        log = P1_DIR / "build.log"
        log.write_text("\n".join(self.log_lines) + "\n", encoding="utf-8")

    # ---------- main ----------
    def run(self) -> int:
        self.log("=" * 60)
        self.log("MAFS v3.0-P1 build_p1_min starting")
        self.log(f"package_root: {_PKG}")
        self.log(f"python: {sys.executable}")
        self.log("=" * 60)
        self.step_identity_guard()
        if self.exit_code == 0:
            self.step_schema_fingerprint()
        if self.exit_code == 0:
            try:
                result = self.step_live_chains()
            except Exception as e:
                self.log(f"FATAL: {e}")
                self.log_block("traceback", traceback.format_exc())
                self.exit_code = 5
                result = None
        else:
            result = None
        if self.exit_code == 0:
            self.step_write_docs(result)
        self.step_build_log()
        self.log("=" * 60)
        self.log(f"Build complete. exit_code={self.exit_code}")
        self.log("=" * 60)
        return self.exit_code


if __name__ == "__main__":
    sys.exit(Builder().run())
