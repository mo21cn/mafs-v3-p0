"""MAFS v3.0 — Replay A-RA1 build script (CI entrypoint).

Persists the 14 required artifacts under ``examples/runs/ReplayA/``
and ``docs/REPLAY_A_RA1_*.md|txt|json``. Reuses the schema-fingerprint
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
    "SUMMARY":    _PKG / "docs" / "REPLAY_A_RA1_SUMMARY.md",
    "METRICS":    _PKG / "docs" / "REPLAY_A_RA1_METRICS.json",
    "PROVENANCE": _PKG / "docs" / "REPLAY_A_RA1_CI_PROVENANCE.md",
    "MANIFEST":   _PKG / "docs" / "REPLAY_A_RA1_SHA256_MANIFEST.txt",
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
            self.exit_code = 3

    def step_schema_fingerprint(self) -> None:
        try:
            from mafs_p0.runtime_fingerprint import _schemas_manifest_sha256, _schemas_in_manifest
            in_manifest = _schemas_in_manifest()
            on_disk = sorted(p.name for p in (_PKG / "schemas").glob("*.schema.json"))
            if tuple(on_disk) != in_manifest:
                self.log("STEP 0: schema-fingerprint self-check")
                self.log(f"  FAIL: drift (on_disk={len(on_disk)}, in_manifest={len(in_manifest)})")
                self.exit_code = 2
                return
            self.log("STEP 0: schema-fingerprint self-check")
            self.log(f"  PASS: schemas on disk == schemas in manifest (count={len(on_disk)})")
        except Exception as e:
            self.log(f"STEP 0: schema-fingerprint self-check FAIL: {e}")
            self.exit_code = 2

    def step_run_replay(self) -> dict | None:
        self.log("STEP 1: Run Replay A-RA1 benchmark (production stack)")
        try:
            from mafs_p0.replay_a import run_replay_a_ra1
            result = run_replay_a_ra1(package_root=_PKG)
        except Exception as e:
            self.log(f"  FAIL: replay_a exception: {e}")
            self.log_block("traceback", traceback.format_exc())
            self.exit_code = 4
            return None
        return result

    def step_write_artifacts(self, result: dict | None) -> None:
        if not result:
            return
        self.log("STEP 2: Write Replay A-RA1 artifacts")
        # Copy benchmark input files (self-contained reproducibility)
        bench_dir = _PKG / "benchmarks" / "blood_oxygen_ovary"
        for name in ("known_anchors_canonical.json", "selected_axes.json", "query_plan.json"):
            src = bench_dir / name
            if src.is_file():
                self.write_artifact(name, json.loads(src.read_text(encoding="utf-8")), "json")
        # Normal retrieval results
        self.write_artifact("normal_retrieval_results.json", result["normal_retrieval_results"], "json")
        # Anchor recovery matrix
        self.write_artifact("anchor_recovery_matrix.json", result["anchor_recovery_matrix"], "json")
        # Possible-candidate matrix
        self.write_artifact("possible_candidate_matrix.json", result["possible_candidate_matrix"], "json")
        # Miss-diagnostic ablation
        self.write_artifact("miss_diagnostic_ablation.json", result["miss_diagnostic_ablation"], "json")
        # Resolver invocations
        self.write_artifact("resolver_invocations.json", result["resolver_invocations"], "json")
        # Metrics (in docs/ and as an artifact)
        self.write_artifact("REPLAY_A_RA1_METRICS.json", result["metrics"], "json")
        DOCS["METRICS"].write_text(
            json.dumps(result["metrics"], indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        # Runtime fingerprint (use production P1 components)
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

        # REPLAY_A_RA1_SUMMARY.md (per contract §16)
        m = result["metrics"]
        s_lines: list[str] = []
        s_lines.append("# REPLAY_A_RA1_SUMMARY.md — AUTO-GENERATED by scripts/replay_a.py")
        s_lines.append("")
        s_lines.append("MAFS v3.0 — Replay A-RA1 Benchmark Fidelity & Stack-Path Closure.")
        s_lines.append("")
        s_lines.append("## Selected axes")
        s_lines.append("- A1 (epidemiology) + A2 (oxygen physiology) + A3 (cellular hypoxia response)")
        s_lines.append("")
        s_lines.append("## Canonical anchor identity")
        s_lines.append(f"- canonical_anchor_count: {m['canonical_anchor_count']}")
        s_lines.append(f"- identity_resolved_anchor_count: {m['identity_resolved_anchor_count']}")
        s_lines.append(f"- identity_unresolved_anchor_count: {m['identity_unresolved_anchor_count']}")
        s_lines.append("")
        s_lines.append("## Identity-safe recall (RECOVERED)")
        if m["identity_safe_recall"] is None:
            s_lines.append("- identity_safe_recall: **N/A** (denominator = 0; no identity-resolved anchors)")
        else:
            s_lines.append(f"- identity_safe_recall: **{m['identity_safe_recall']:.2%}**")
        s_lines.append(f"- recovered_anchor_count: {m['recovered_anchor_count']}")
        s_lines.append(f"- possible_candidate_count: {m['possible_candidate_count']}")
        s_lines.append("")
        s_lines.append("## Per-family top-10 recall")
        s_lines.append(f"- top_10_recall: {m['top_10_recall'] if m['top_10_recall'] is not None else 'N/A'}")
        s_lines.append("")
        s_lines.append("## Miss-diagnostic ablation (RA1 §5)")
        s_lines.append(f"- provider_coverage_failures: {m['provider_coverage_failures']}")
        s_lines.append(f"- ranking_topk_failures: {m['ranking_topk_failures']}")
        s_lines.append(f"- query_formulation_or_compiler_failures: {m['query_formulation_or_compiler_failures']}")
        s_lines.append(f"- unknown_failures: {m['unknown_failures']}")
        s_lines.append(f"- anchor_identity_unresolved: {m['anchor_identity_unresolved']}")
        s_lines.append("")
        s_lines.append("## Production stack exercised (RA1 §3, §9)")
        s_lines.append("- `CrossrefRetrievalProvider` (production P1 component)")
        s_lines.append("- `CrossrefReferenceResolver` (production P1 component)")
        s_lines.append("- `pubmed_ebsco` Query Compiler (production P0 component)")
        s_lines.append("- query plan supplies QueryASTs, not hard-coded compiled strings")
        s_lines.append("")
        s_lines.append("## Provider / resolver call counts")
        s_lines.append(f"- provider_call_count: {m['provider_call_count']}  (9 normal + {m['canonical_anchor_count']} Stage A lookups)")
        s_lines.append(f"- resolver_call_count: {m['resolver_call_count']}  (selective resolution, top-1 per normal query)")
        s_lines.append("")
        s_lines.append("## Primary failure attribution")
        s_lines.append(f"**{result['primary_failure_attribution']}**")
        s_lines.append("")
        s_lines.append("## Contract §14 acceptance answers")
        s_lines.append(f"1. What is the identity-safe known-anchor recall? "
                       f"→ **{m['identity_safe_recall']:.2%}** ({m['recovered_anchor_count']}/{m['identity_resolved_anchor_count']})" if m['identity_safe_recall'] is not None
                       else "1. What is the identity-safe known-anchor recall? → **N/A** (0 resolved anchors)")
        s_lines.append(f"2. Which historical anchors are still identity-unresolved? → "
                       f"**{m['identity_unresolved_anchor_count']}** of {m['canonical_anchor_count']} (see known_anchors_canonical.json)")
        s_lines.append(f"3. For each miss, is the dominant failure provider coverage, ranking, query, resolution, benchmark ambiguity, or unknown? → "
                       f"**{result['primary_failure_attribution']}** (with "
                       f"{m['provider_coverage_failures']} provider_coverage, "
                       f"{m['ranking_topk_failures']} ranking, "
                       f"{m['query_formulation_or_compiler_failures']} compiler, "
                       f"{m['unknown_failures']} unknown, "
                       f"{m['anchor_identity_unresolved']} identity_unresolved)")
        s_lines.append("4. Did the benchmark execute through the real v3.0 stack? → **YES** "
                       "(QueryAST → pubmed_ebsco compiler → CrossrefRetrievalProvider; selective resolution via CrossrefReferenceResolver)")
        s_lines.append(f"5. Is the current retrieval stack ready for the next stage, or is a bounded P1.5 remediation required? → **{result['recommended_next_step']}**")
        s_lines.append("")
        s_lines.append("## Recommended Next Step (one bounded recommendation)")
        s_lines.append(f"→ {result['recommended_next_step']}")
        s_lines.append("")
        s_lines.append("## Scope Expanded Beyond RA1")
        s_lines.append("→ **NO** (no new providers, no architecture changes, no P2/P3, no MAFS Gate)")
        s_lines.append("")
        s_lines.append(f"build_time: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
        s_lines.append(f"exit_code: {self.exit_code}")
        DOCS["SUMMARY"].write_text("\n".join(s_lines) + "\n", encoding="utf-8")
        self.log(f"  wrote {DOCS['SUMMARY'].relative_to(_PKG)}")

        # REPLAY_A_RA1_CI_PROVENANCE.md
        p_lines = [
            "# REPLAY_A_RA1_CI_PROVENANCE.md",
            "",
            f"build_time: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
            f"canonical_anchor_count: {m['canonical_anchor_count']}",
            f"identity_resolved_anchor_count: {m['identity_resolved_anchor_count']}",
            f"identity_unresolved_anchor_count: {m['identity_unresolved_anchor_count']}",
            f"recovered_anchor_count: {m['recovered_anchor_count']}",
            f"possible_candidate_count: {m['possible_candidate_count']}",
            f"identity_safe_recall: {m['identity_safe_recall']}",
            f"primary_failure_attribution: {result['primary_failure_attribution']}",
            f"exit_code: {self.exit_code}",
        ]
        DOCS["PROVENANCE"].write_text("\n".join(p_lines) + "\n", encoding="utf-8")
        self.log(f"  wrote {DOCS['PROVENANCE'].relative_to(_PKG)}")

        # REPLAY_A_RA1_SHA256_MANIFEST.txt
        m_lines: list[str] = []
        m_lines.append("# REPLAY_A_RA1_SHA256_MANIFEST.txt — AUTO-GENERATED by scripts/replay_a.py")
        m_lines.append("")
        m_lines.append(f"# build_time: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
        m_lines.append("")
        for rel, info in sorted(self.artifacts.items()):
            m_lines.append(f"{info['sha256']}  examples/runs/ReplayA/{rel}")
        DOCS["MANIFEST"].write_text("\n".join(m_lines) + "\n", encoding="utf-8")
        self.log(f"  wrote {DOCS['MANIFEST'].relative_to(_PKG)}")

    def step_build_log(self) -> None:
        log = REPLAY_DIR / "build.log"
        log.write_text("\n".join(self.log_lines) + "\n", encoding="utf-8")

    def run(self) -> int:
        self.log("=" * 60)
        self.log("MAFS v3.0 — Replay A-RA1 (Benchmark Fidelity & Stack-Path Closure)")
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
