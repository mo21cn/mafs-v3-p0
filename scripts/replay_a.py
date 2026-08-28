"""MAFS v3.0 — Replay A build script (CI entrypoint).

Persists the 12 required artifacts under ``examples/runs/ReplayA/``
and ``docs/REPLAY_A_*.md|txt``. Reuses the schema-fingerprint
self-check and the identity guard from the P1 build (P1-RA1 hygiene
§1 + §2).

Exit codes:
  0 - benchmark executed; metrics produced (recall may be 0, that's fine)
  1 - benchmark failed to load inputs
  2 - schema-fingerprint self-check failed
  3 - identity guard failed
  4 - build / IO error
"""
from __future__ import annotations
import hashlib
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PKG / "src"))

REPLAY_DIR = _PKG / "examples" / "runs" / "ReplayA"
DOCS = {
    "SUMMARY":   _PKG / "docs" / "REPLAY_A_SUMMARY.md",
    "METRICS":   _PKG / "docs" / "REPLAY_A_METRICS.json",
    "PROVENANCE": _PKG / "docs" / "REPLAY_A_CI_PROVENANCE.md",
    "MANIFEST":  _PKG / "docs" / "REPLAY_A_SHA256_MANIFEST.txt",
}


class Builder:
    def __init__(self):
        self.log_lines: list[str] = []
        self.artifacts: dict[str, dict[str, Any]] = {}
        self.exit_code: int = 0
        REPLAY_DIR.mkdir(parents=True, exist_ok=True)

    def log(self, msg: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
        line = f"[{ts}] {msg}"
        self.log_lines.append(line)
        print(line, flush=True)

    def _sha256(self, p: Path) -> str:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def write_artifact(self, relpath: str, content: Any, kind: str) -> None:
        p = REPLAY_DIR / relpath
        if isinstance(content, (dict, list)):
            text = json.dumps(content, indent=2, ensure_ascii=False, sort_keys=True)
        else:
            text = str(content)
        p.write_text(text, encoding="utf-8")
        sha = self._sha256(p)
        size = p.stat().st_size
        self.artifacts[relpath] = {"sha256": sha, "bytes": size, "kind": kind}
        self.log(f"  artifact: {relpath}  size={size}B  sha256={sha[:16]}...")

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
            self.log(f"STEP -1: Repository/workdir identity guard")
            self.log(f"  FAIL: {e}")
            self.exit_code = 3

    # ---------- step 0: schema-fingerprint self-check ----------
    def step_schema_fingerprint(self) -> None:
        try:
            from mafs_p0.runtime_fingerprint import _schemas_manifest_sha256, _schemas_in_manifest
            in_manifest = _schemas_in_manifest()
            on_disk = sorted(p.name for p in (_PKG / "schemas").glob("*.schema.json"))
            if tuple(on_disk) != in_manifest:
                self.log(f"STEP 0: schema-fingerprint self-check")
                self.log(f"  FAIL: drift (on_disk={len(on_disk)}, in_manifest={len(in_manifest)})")
                self.exit_code = 2
                return
            self.log("STEP 0: schema-fingerprint self-check")
            self.log(f"  PASS: schemas on disk == schemas in manifest (count={len(on_disk)})")
        except Exception as e:
            self.log(f"STEP 0: schema-fingerprint self-check FAIL: {e}")
            self.exit_code = 2

    # ---------- step 1: run Replay A ----------
    def step_run_replay(self) -> dict | None:
        self.log("STEP 1: Run Replay A benchmark")
        try:
            from mafs_p0.replay_a import run_replay_a
            result = run_replay_a(package_root=_PKG)
        except Exception as e:
            self.log(f"  FAIL: replay_a exception: {e}")
            self.log_block("traceback", traceback.format_exc())
            self.exit_code = 4
            return None
        return result

    # ---------- step 2: write artifacts ----------
    def step_write_artifacts(self, result: dict | None) -> None:
        if not result:
            return
        self.log("STEP 2: Write Replay A artifacts")

        # Retrieval results (per-query)
        self.write_artifact("retrieval_results.json", result["results"], "json")

        # Anchor recovery matrix
        self.write_artifact("anchor_recovery_matrix.json", result["anchor_recovery_matrix"], "json")

        # Missed-anchor diagnostics
        self.write_artifact("missed_anchor_diagnostics.json", result["missed_anchor_diagnostics"], "json")

        # Metrics (in docs/ and as an artifact)
        self.write_artifact("REPLAY_A_METRICS.json", result["metrics"], "json")
        DOCS["METRICS"].write_text(
            json.dumps(result["metrics"], indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        # Copy benchmark input files into examples/runs/ReplayA/ for
        # self-contained reproducibility
        bench_dir = _PKG / "benchmarks" / "blood_oxygen_ovary"
        for name in ("known_anchors.json", "selected_axes.json", "query_plan.json"):
            src = bench_dir / name
            if src.is_file():
                self.write_artifact(name, json.loads(src.read_text(encoding="utf-8")), "json")

        # Runtime fingerprint (re-use the P1 logic)
        try:
            from mafs_p0.runtime_fingerprint import build_fingerprint
            from mafs_p0.provider_manifest import ProviderManifest, ResolverManifest
            from mafs_p0.live_crossref import build_provider_manifest, build_resolver_manifest
            pm = build_provider_manifest()
            rm = build_resolver_manifest()
            fp = build_fingerprint(
                provider_manifests=[ProviderManifest(
                    name=pm["name"], version=pm["version"],
                    capabilities=pm["capabilities"],
                    network_requirement=pm["network_requirement"],
                    trust_class=pm["trust_class"],
                    sha256=pm["sha256"], namespace=pm["namespace"],
                )],
                resolver_manifests=[ResolverManifest(
                    name=rm["name"], version=rm["version"],
                    capabilities=rm["capabilities"],
                    trust_class=rm["trust_class"],
                    sha256=rm["sha256"], namespace=rm["namespace"],
                )],
            )
            self.write_artifact("runtime_fingerprint.json", fp, "json")
        except Exception as e:
            self.log(f"  WARN: runtime fingerprint exception (non-fatal): {e}")

        # REPLAY_A_SUMMARY.md
        m = result["metrics"]
        s_lines: list[str] = []
        s_lines.append("# REPLAY_A_SUMMARY.md — AUTO-GENERATED by scripts/replay_a.py")
        s_lines.append("")
        s_lines.append("MAFS v3.0 — Replay A Retrieval Recall Checkpoint (contract §16).")
        s_lines.append("")
        s_lines.append("## Selected axes")
        for a in result["selected_axes"]:
            s_lines.append(f"- `{a['axis_id']}` ({a['axis_label']}): {a['diagnostic_role']}")
        s_lines.append("")
        s_lines.append("## Known anchors")
        s_lines.append(f"- Total: **{m['known_anchor_count']}**")
        s_lines.append(f"- Recovered: **{m['recovered_anchor_count']}**")
        s_lines.append(f"- Missed: **{m['missed_anchor_count']}**")
        s_lines.append(f"- Known-anchor recall: **{m['known_anchor_recall']:.2%}**")
        s_lines.append(f"- Top-k anchor recall: **{m['top_k_anchor_recall']:.2%}**")
        s_lines.append("")
        s_lines.append("## Query family contribution")
        for fam, n in m["query_family_contribution"].items():
            s_lines.append(f"- `{fam}`: {n} unique anchor matches")
        s_lines.append("")
        s_lines.append("## Per-query results (top 5 by items_returned)")
        sorted_by_items = sorted(result["results"], key=lambda r: -r["items_returned"])[:5]
        for r in sorted_by_items:
            s_lines.append(f"- axis `{r['axis_id']}` / family `{r['family']}`: "
                           f"http={r['http_status']}, items={r['items_returned']}, "
                           f"matched={len(r['matched_anchor_ids'])}")
        s_lines.append("")
        s_lines.append("## Missed-anchor diagnostics")
        for d in result["missed_anchor_diagnostics"]:
            s_lines.append(f"- `{d['anchor_id']}` (axis `{d['relevant_axis']}`): **{d['category']}**")
            s_lines.append(f"    - title_hint: {d['title_hint']}")
        s_lines.append("")
        s_lines.append("## Primary failure attribution")
        s_lines.append(f"**{result['primary_failure_attribution']}**")
        s_lines.append("")
        s_lines.append("## Contract §13 acceptance answers")
        s_lines.append("1. Can the current v3.0 retrieval path recover the known important priors? "
                       f"→ **{'YES' if m['known_anchor_recall'] > 0.5 else 'PARTIAL' if m['known_anchor_recall'] > 0 else 'NO'}** "
                       f"({m['known_anchor_recall']:.0%} of {m['known_anchor_count']} anchors)")
        s_lines.append("2. Which query families actually contribute to recovery? "
                       f"→ {', '.join(m['query_family_contribution'].keys())}")
        s_lines.append(f"3. Are misses caused mainly by compiler, provider, ranking, or resolution? "
                       f"→ **{result['primary_failure_attribution']}**")
        s_lines.append("4. Is Crossref + current compiler sufficient for the next stage? "
                       "→ see Recommended Development Direction below")
        s_lines.append("5. Should the next step be (a) provider-specific compiler remediation, "
                       "(b) additional provider, (c) ranking/top-k, or (d) P2 trust/admissibility? "
                       f"→ **{m.get('recommended_direction', 'see primary failure attribution')}**")
        s_lines.append("")
        s_lines.append("## Recommended Development Direction (one bounded recommendation)")
        # Crude heuristic for the recommendation
        pfa = result["primary_failure_attribution"]
        if pfa in ("PROVIDER_RECALL", "BENCHMARK_AMBIGUITY"):
            s_lines.append("→ **provider-specific compiler remediation** "
                           "(the P0 query does not surface enough Crossref hits; "
                           "a Crossref-tuned compiler / terminology expansion is the next step).")
        elif pfa in ("QUERY_COMPILER", "TERMINOLOGY_EXPANSION"):
            s_lines.append("→ **provider-specific compiler remediation** "
                           "(the P0 pubmed_ebsco compiler is being used; a Crossref-tuned "
                           "compiler or post-query expansion would likely improve recall).")
        elif pfa == "RANKING_TOPK":
            s_lines.append("→ **ranking / top-k remediation** "
                           "(anchors exist in the provider's result set but fall outside top_k; "
                           "increase top_k or add a relevance re-ranker).")
        else:
            s_lines.append("→ **P2 trust / admissibility** "
                           "(retrieval recall is acceptable; the next missing piece is "
                           "Evidence Admissibility — taint / admissibility gates).")
        # Patch the metrics to include the recommended direction
        m["recommended_direction"] = (
            "provider-specific compiler remediation" if pfa in ("PROVIDER_RECALL", "QUERY_COMPILER", "TERMINOLOGY_EXPANSION", "BENCHMARK_AMBIGUITY")
            else "ranking / top-k remediation" if pfa == "RANKING_TOPK"
            else "P2 trust / admissibility"
        )
        s_lines.append("")
        s_lines.append(f"build_time: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
        s_lines.append(f"exit_code: {self.exit_code}")
        DOCS["SUMMARY"].write_text("\n".join(s_lines) + "\n", encoding="utf-8")
        self.log(f"  wrote {DOCS['SUMMARY'].relative_to(_PKG)}")

        # REPLAY_A_CI_PROVENANCE.md (small)
        p_lines = [
            "# REPLAY_A_CI_PROVENANCE.md",
            "",
            f"build_time: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
            f"recovered_anchors: {m['recovered_anchor_count']} / {m['known_anchor_count']}",
            f"known_anchor_recall: {m['known_anchor_recall']:.2%}",
            f"primary_failure: {result['primary_failure_attribution']}",
            f"exit_code: {self.exit_code}",
        ]
        DOCS["PROVENANCE"].write_text("\n".join(p_lines) + "\n", encoding="utf-8")
        self.log(f"  wrote {DOCS['PROVENANCE'].relative_to(_PKG)}")

        # REPLAY_A_SHA256_MANIFEST.txt
        m_lines: list[str] = []
        m_lines.append("# REPLAY_A_SHA256_MANIFEST.txt — AUTO-GENERATED by scripts/replay_a.py")
        m_lines.append("")
        m_lines.append(f"# build_time: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
        m_lines.append("")
        for rel, info in sorted(self.artifacts.items()):
            m_lines.append(f"{info['sha256']}  examples/runs/ReplayA/{rel}")
        DOCS["MANIFEST"].write_text("\n".join(m_lines) + "\n", encoding="utf-8")
        self.log(f"  wrote {DOCS['MANIFEST'].relative_to(_PKG)}")

    # ---------- step 3: build.log ----------
    def step_build_log(self) -> None:
        log = REPLAY_DIR / "build.log"
        log.write_text("\n".join(self.log_lines) + "\n", encoding="utf-8")

    # ---------- main ----------
    def run(self) -> int:
        self.log("=" * 60)
        self.log("MAFS v3.0 — Replay A (Retrieval Recall Checkpoint)")
        self.log(f"package_root: {_PKG}")
        self.log(f"python: {sys.executable}")
        self.log("=" * 60)
        self.step_identity_guard()
        if self.exit_code == 0:
            self.step_schema_fingerprint()
        if self.exit_code == 0:
            try:
                result = self.step_run_replay()
            except Exception as e:
                self.log(f"FATAL: {e}")
                self.log_block("traceback", traceback.format_exc())
                self.exit_code = 4
                result = None
        else:
            result = None
        if self.exit_code == 0:
            self.step_write_artifacts(result)
        self.step_build_log()
        self.log("=" * 60)
        self.log(f"Build complete. exit_code={self.exit_code}")
        self.log("=" * 60)
        return self.exit_code


if __name__ == "__main__":
    sys.exit(Builder().run())
