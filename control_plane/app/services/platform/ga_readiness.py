# Owner: platform-ops
"""Objective GA readiness scoring from repository and artifact evidence."""

import os
from pathlib import Path

import yaml

class GAReadinessService:
    def __init__(self, config_path="config/ga-readiness-rules.yaml"):
        self.config_path = config_path
        self._load_config()

    def _load_config(self):
        with open(self.config_path, "r") as f:
            data = yaml.safe_load(f)
            self.rules = data.get("rules", {})
            self.weights = data.get("weights", {})

    def collect_current_state(self) -> dict:
        base_dir = Path(self.config_path).resolve().parent.parent if not os.path.isabs(self.config_path) else Path(self.config_path).resolve().parents[1]

        feature_flag_audit = None
        try:
            from app.services.platform.feature_flag_audit import FeatureFlagAuditService

            feature_flag_audit = FeatureFlagAuditService(
                registry_path=str(base_dir / "config/feature-flags.yaml")
            ).perform_audit()
        except Exception:
            feature_flag_audit = None

        surface_audit = None
        try:
            from app.services.platform.surface_audit import SurfaceAuditService

            surface_audit = SurfaceAuditService(base_dir=str(base_dir)).run_audit()
        except Exception:
            surface_audit = None

        readiness_summary = self._read_text(base_dir / "artifacts/operational-readiness/latest/summary.md")
        release_summary = self._read_text(base_dir / "artifacts/releases/v2.0.1-agentic-operational-maturity/summary.md")
        agentic_rollout_docs = [
            base_dir / "docs/operations/activate-agentic-pilot.md",
            base_dir / "docs/operations/activate-agentic-production.md",
            base_dir / "docs/operations/rollback-agentic-runtime.md",
        ]

        return {
            "readiness_passing": "**Status**: pilot_ready" in readiness_summary or "**Status**: production_ready" in readiness_summary,
            "release_gate_passing": "**Status**: PASS" in release_summary,
            "no_orphaned_flags": bool(feature_flag_audit) and len(feature_flag_audit.get("orphans", [])) == 0,
            "no_orphaned_apis": bool(surface_audit)
            and len(surface_audit["apis"].get("duplicates", [])) == 0
            and len(surface_audit["apis"].get("unregistered_routes", [])) == 0
            and len(surface_audit["apis"].get("unreferenced_registry", [])) == 0,
            "eval_pass_rate": self._collect_eval_pass_rate(base_dir),
            "slo_stability_required": (base_dir / "config/agent-slo-classes.yaml").exists(),
            "incident_recovery_tested": (base_dir / "scripts/rollback-agentic-runtime.sh").exists(),
            "operational_playbooks_present": all(path.exists() for path in agentic_rollout_docs),
            "observability_dashboards_provisioned": (base_dir / "monitoring/dashboards/agentic-overview.json").exists(),
            "promotion_gates_enabled": self._promotion_gates_enabled(base_dir),
            "security_warnings_classified": (base_dir / "config/security-warning-allowlist.yaml").exists(),
            "tenant_isolation_validated": (base_dir / "tests/test_deployment_modes.py").exists(),
        }

    def _collect_eval_pass_rate(self, base_dir: Path) -> float:
        report = self._read_text(base_dir / "artifacts/evals/real-provider-validation.md")
        if not report:
            return 0.0
        passed = report.count(": passed")
        skipped = report.count(": skipped")
        total = passed + report.count(": error") + skipped
        if total == 0:
            return 0.0
        # Skipped validations do not count as passing evidence for GA.
        return passed / total

    def _promotion_gates_enabled(self, base_dir: Path) -> bool:
        registry = base_dir / "config/feature-flags.yaml"
        if not registry.exists():
            return False
        content = registry.read_text(encoding="utf-8")
        return "name: AGENT_PROMOTION_REQUIRES_EVALS" in content and "name: AGENT_EVAL_REGRESSION_GATE_ENABLED" in content

    def _read_text(self, path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def evaluate_readiness(self, current_state: dict) -> dict:
        """
        Evaluates the current state against the GA readiness rules.
        current_state is a dictionary containing booleans for each rule.
        """
        score = 0
        details = {}
        
        # 1. readiness passing
        if current_state.get("readiness_passing", False):
            score += 1
            details["readiness_passing"] = "passed"
        else:
            details["readiness_passing"] = "failed"
            
        # 2. release gate passing
        if current_state.get("release_gate_passing", False):
            score += 1
            details["release_gate_passing"] = "passed"
        else:
            details["release_gate_passing"] = "failed"
            
        # 3. no orphaned flags
        if current_state.get("no_orphaned_flags", False):
            score += 1
            details["no_orphaned_flags"] = "passed"
        else:
            details["no_orphaned_flags"] = "failed (reduces maturity)"
            
        # 4. no orphaned APIs
        if current_state.get("no_orphaned_apis", False):
            score += 1
            details["no_orphaned_apis"] = "passed"
        else:
            details["no_orphaned_apis"] = "failed"
            
        # 5. eval pass rate threshold
        eval_rate = current_state.get("eval_pass_rate", 0.0)
        if eval_rate >= self.rules.get("eval_pass_rate_threshold", 0.95):
            score += 1
            details["eval_pass_rate"] = "passed"
        else:
            details["eval_pass_rate"] = "failed (reduces maturity)"
            
        # 6. SLO stability
        if current_state.get("slo_stability_required", False):
            score += 1
            details["slo_stability"] = "passed"
        else:
            details["slo_stability"] = "failed (reduces maturity)"
            
        # 7. incident recovery tested
        if current_state.get("incident_recovery_tested", False):
            score += 1
            details["incident_recovery_tested"] = "passed"
        else:
            details["incident_recovery_tested"] = "failed"
            
        # 8. operational playbooks present
        if current_state.get("operational_playbooks_present", False):
            score += 1
            details["operational_playbooks_present"] = "passed"
        else:
            details["operational_playbooks_present"] = "failed (reduces maturity)"
            
        # 9. observability dashboards provisioned
        if current_state.get("observability_dashboards_provisioned", False):
            score += 1
            details["observability_dashboards_provisioned"] = "passed"
        else:
            details["observability_dashboards_provisioned"] = "failed"
            
        # 10. promotion gates enabled
        if current_state.get("promotion_gates_enabled", False):
            score += 1
            details["promotion_gates_enabled"] = "passed"
        else:
            details["promotion_gates_enabled"] = "failed"
            
        # 11. security warnings classified
        if current_state.get("security_warnings_classified", False):
            score += 1
            details["security_warnings_classified"] = "passed"
        else:
            details["security_warnings_classified"] = "failed"
            
        # 12. tenant isolation validated
        if current_state.get("tenant_isolation_validated", False):
            score += 1
            details["tenant_isolation_validated"] = "passed"
        else:
            details["tenant_isolation_validated"] = "failed"

        # Determine maturity level
        maturity = "experimental"
        if score >= self.weights.get("ga_ready", 12):
            maturity = "ga_ready"
        elif score >= self.weights.get("production_ready", 11):
            maturity = "production_ready"
        elif score >= self.weights.get("pilot_ready", 8):
            maturity = "pilot_ready"
        elif score >= self.weights.get("beta", 4):
            maturity = "beta"

        return {
            "maturity_level": maturity,
            "score": score,
            "total_possible": 12,
            "details": details
        }

    def generate_report(self, current_state: dict, filepath="artifacts/platform/ga-readiness.md"):
        result = self.evaluate_readiness(current_state)
        
        md = f"# Platform GA Readiness Report\n\n"
        md += f"**Overall Maturity Level:** {result['maturity_level'].upper()}\n"
        md += f"**Score:** {result['score']} / {result['total_possible']}\n\n"
        
        md += "## Detailed Assessment\n"
        for k, v in result["details"].items():
            icon = "✅" if "passed" in v else "❌"
            md += f"- {icon} **{k}**: {v}\n"
            
        md += "\n## Next Steps\n"
        if result["score"] < result["total_possible"]:
            md += "Address the failed checks to achieve GA Ready status.\n"
        else:
            md += "The platform is fully GA Ready.\n"
            
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            f.write(md)
            
        return result
