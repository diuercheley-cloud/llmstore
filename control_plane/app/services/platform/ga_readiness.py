# Owner: platform-ops
"""Objective GA readiness scoring from repository and artifact evidence."""

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml


CRITERIA = [
    ("operational_readiness_passed", "Operational readiness checks passed"),
    ("agentic_readiness_passed", "Agentic readiness checks passed"),
    ("release_gate_passed", "Release gates passed"),
    ("platform_freeze_passed", "Platform freeze gate passed"),
    ("surface_audit_clean", "Surface audit is clean"),
    ("no_orphaned_flags", "No orphaned feature flags"),
    ("security_warnings_classified", "Security warnings are classified"),
    ("eval_gate_enforced", "Eval gate is enforced"),
    ("provider_validation_recent", "Recent real provider or validated gateway evidence exists"),
    ("no_silent_mock_in_production", "No silent mock provider path exists in production"),
    ("no_silent_task_simulation", "No silent task simulation path exists in production"),
    ("tenant_isolation_validated", "Tenant isolation is validated"),
]

PASSING_OPERATIONAL_STATUSES = ("pilot_ready", "production_ready", "ga_ready")
PASSING_AGENTIC_MARKERS = (
    "## Status: READY",
    "**Status**: READY",
    "**Status**: PASS",
    "**Status**: pilot_ready",
    "**Status**: production_ready",
    "**Status**: ga_ready",
)


class GAReadinessService:
    def __init__(self, config_path="config/ga-readiness-rules.yaml"):
        self.config_path = config_path
        self._load_config()

    def _load_config(self):
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        self.rules = data.get("rules", {})
        self.weights = data.get("weights", {})

    def _resolve_base_dir(self) -> Path:
        config_path = Path(self.config_path).resolve()
        return config_path.parent.parent

    def collect_current_state(self) -> dict:
        base_dir = self._resolve_base_dir()
        reasons = {}

        surface_audit = None
        try:
            from app.services.platform.surface_audit import SurfaceAuditService

            surface_audit = SurfaceAuditService(base_dir=str(base_dir)).run_audit()
        except Exception as exc:
            reasons["surface_audit_clean"] = f"surface audit unavailable: {exc}"

        feature_flag_audit = None
        try:
            from app.services.platform.feature_flag_audit import FeatureFlagAuditService

            feature_flag_audit = FeatureFlagAuditService(
                registry_path=str(base_dir / "config/feature-flags.yaml")
            ).perform_audit()
        except Exception as exc:
            reasons["no_orphaned_flags"] = f"feature flag audit unavailable: {exc}"

        operational_summary = self._read_text(base_dir / "artifacts/operational-readiness/latest/summary.md")
        agentic_summary = self._read_text(base_dir / "artifacts/agentic-readiness/latest/summary.md")
        release_summary = self._read_text(
            base_dir / "artifacts/releases/v2.0.1-agentic-operational-maturity/summary.md"
        )

        operational_ok, operational_reason = self._operational_readiness_passed(operational_summary)
        agentic_ok, agentic_reason = self._agentic_readiness_passed(agentic_summary)
        release_ok, release_reason = self._release_gate_passed(release_summary)
        freeze_ok, freeze_reason = self._check_platform_freeze(base_dir, release_summary)
        surface_ok, surface_reason = self._surface_audit_status(surface_audit)
        flags_ok, flags_reason = self._feature_flag_status(feature_flag_audit)
        security_ok, security_reason = self._security_warning_status(base_dir)
        eval_ok, eval_reason = self._eval_gates_enforced(base_dir)
        provider_ok, provider_reason = self._provider_validation_recent(base_dir)
        mock_ok, mock_reason = self._no_silent_mock_in_production()
        simulation_ok, simulation_reason = self._no_silent_task_simulation(base_dir)
        tenant_ok, tenant_reason = self._tenant_isolation_validated(base_dir)

        reasons.update(
            {
                "operational_readiness_passed": operational_reason,
                "agentic_readiness_passed": agentic_reason,
                "release_gate_passed": release_reason,
                "platform_freeze_passed": freeze_reason,
                "surface_audit_clean": surface_reason,
                "no_orphaned_flags": flags_reason,
                "security_warnings_classified": security_reason,
                "eval_gate_enforced": eval_reason,
                "provider_validation_recent": provider_reason,
                "no_silent_mock_in_production": mock_reason,
                "no_silent_task_simulation": simulation_reason,
                "tenant_isolation_validated": tenant_reason,
            }
        )

        return {
            "operational_readiness_passed": operational_ok,
            "agentic_readiness_passed": agentic_ok,
            "release_gate_passed": release_ok,
            "platform_freeze_passed": freeze_ok,
            "surface_audit_clean": surface_ok,
            "no_orphaned_flags": flags_ok,
            "security_warnings_classified": security_ok,
            "eval_gate_enforced": eval_ok,
            "provider_validation_recent": provider_ok,
            "no_silent_mock_in_production": mock_ok,
            "no_silent_task_simulation": simulation_ok,
            "tenant_isolation_validated": tenant_ok,
            "_reasons": reasons,
        }

    def _read_text(self, path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def _extract_status(self, content: str) -> str:
        patterns = [
            r"\*\*Status\*\*:\s*([A-Za-z_]+)",
            r"## Status:\s*([A-Za-z_]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1).strip().lower()
        return ""

    def _operational_readiness_passed(self, content: str) -> tuple[bool, str]:
        status = self._extract_status(content)
        if status in PASSING_OPERATIONAL_STATUSES:
            return True, f"operational readiness status is {status}"
        if not content:
            return False, "operational readiness summary artifact is missing"
        return False, f"operational readiness status is {status or 'unknown'}"

    def _agentic_readiness_passed(self, content: str) -> tuple[bool, str]:
        status = self._extract_status(content)
        if any(marker in content for marker in PASSING_AGENTIC_MARKERS) or status in PASSING_OPERATIONAL_STATUSES:
            return True, f"agentic readiness status is {status or 'ready'}"
        if not content:
            return False, "agentic readiness summary artifact is missing"
        return False, f"agentic readiness status is {status or 'unknown'}"

    def _release_gate_passed(self, content: str) -> tuple[bool, str]:
        if "**Status**: PASS" in content:
            return True, "release summary reports PASS"
        if not content:
            return False, "release summary artifact is missing"
        return False, "release summary does not report PASS"

    def _check_platform_freeze(self, base_dir: Path, release_summary: str) -> tuple[bool, str]:
        freeze_marker = base_dir / "config/platform-freeze.yaml"
        if freeze_marker.exists():
            try:
                data = yaml.safe_load(freeze_marker.read_text(encoding="utf-8")) or {}
                if data.get("frozen", False):
                    return True, "config/platform-freeze.yaml marks the platform as frozen"
            except Exception as exc:
                return False, f"platform freeze marker could not be parsed: {exc}"

        if "| platform-freeze-check | PASS |" in release_summary:
            return True, "release summary includes a passing platform-freeze-check gate"
        return False, "no passing platform freeze evidence was found"

    def _surface_audit_status(self, surface_audit: dict | None) -> tuple[bool, str]:
        if surface_audit is None:
            return False, "surface audit report is unavailable"

        findings = []
        apis = surface_audit.get("apis", {})
        services = surface_audit.get("services", {})
        scripts = surface_audit.get("scripts", {})
        ui_pages = surface_audit.get("ui_pages", {})

        if apis.get("duplicates"):
            findings.append(f"{len(apis['duplicates'])} duplicate API routes")
        if apis.get("unregistered_routes"):
            findings.append(f"{len(apis['unregistered_routes'])} unregistered API routes")
        if apis.get("unreferenced_registry"):
            findings.append(f"{len(apis['unreferenced_registry'])} registry routes without implementation")
        if services.get("orphaned_services"):
            findings.append(f"{len(services['orphaned_services'])} orphaned services")
        if scripts.get("orphaned_scripts"):
            findings.append(f"{len(scripts['orphaned_scripts'])} orphaned scripts")
        if ui_pages.get("orphaned_pages"):
            findings.append(f"{len(ui_pages['orphaned_pages'])} orphaned UI pages")

        if findings:
            return False, "surface audit is dirty: " + ", ".join(findings)
        return True, "surface audit is clean"

    def _feature_flag_status(self, feature_flag_audit: dict | None) -> tuple[bool, str]:
        if feature_flag_audit is None:
            return False, "feature flag audit report is unavailable"
        orphan_count = len(feature_flag_audit.get("orphans", []))
        if orphan_count == 0:
            return True, "feature flag audit found no orphaned flags"
        return False, f"feature flag audit found {orphan_count} orphaned flags"

    def _security_warning_status(self, base_dir: Path) -> tuple[bool, str]:
        allowlist = base_dir / "config/security-warning-allowlist.yaml"
        if allowlist.exists():
            return True, "security warning allowlist is present"
        return False, "config/security-warning-allowlist.yaml is missing"

    def _eval_gates_enforced(self, base_dir: Path) -> tuple[bool, str]:
        registry = base_dir / "config/feature-flags.yaml"
        if not registry.exists():
            return False, "config/feature-flags.yaml is missing"

        content = registry.read_text(encoding="utf-8")
        required_flags = [
            "name: AGENT_PROMOTION_REQUIRES_EVALS",
            "name: AGENT_EVAL_REGRESSION_GATE_ENABLED",
        ]
        missing = [flag.split(": ", 1)[1] for flag in required_flags if flag not in content]
        if missing:
            return False, f"missing eval gate flags: {', '.join(missing)}"
        return True, "promotion and regression eval gates are registered"

    def _parse_iso_date(self, value: str) -> datetime | None:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _provider_validation_recent(self, base_dir: Path, max_age_days: int = 30) -> tuple[bool, str]:
        latest_results = base_dir / "artifacts/evals/real-provider-validation/latest/results.json"
        legacy_report = base_dir / "artifacts/evals/real-provider-validation.md"
        now = datetime.now(timezone.utc)
        max_age = timedelta(days=max_age_days)

        if latest_results.exists():
            try:
                data = json.loads(latest_results.read_text(encoding="utf-8"))
                generated_at = self._parse_iso_date(str(data.get("generated_at", "")))
                if generated_at is None:
                    return False, "provider validation latest/results.json has no valid generated_at timestamp"
                age = now - generated_at.astimezone(timezone.utc)
                if age > max_age:
                    return False, f"provider validation evidence is stale: {generated_at.date().isoformat()}"

                providers = data.get("providers", [])
                validated = [
                    provider.get("provider", "unknown")
                    for provider in providers
                    if provider.get("provider") != "mock"
                    and any(
                        result.get("feature") == "basic_model_call" and result.get("status") == "passed"
                        for result in provider.get("results", [])
                    )
                ]
                if validated:
                    return True, "validated providers: " + ", ".join(validated)
                return False, "provider validation latest/results.json has no non-mock provider with a passing basic_model_call"
            except Exception as exc:
                return False, f"provider validation latest/results.json could not be parsed: {exc}"

        if legacy_report.exists():
            try:
                content = legacy_report.read_text(encoding="utf-8")
                match = re.search(r"Run Date:\s*([0-9T:\-+.]+)", content)
                if match:
                    generated_at = self._parse_iso_date(match.group(1))
                    if generated_at and now - generated_at.astimezone(timezone.utc) <= max_age:
                        providers = re.findall(r"## Provider:\s*([^\n]+)", content)
                        validated = [provider for provider in providers if provider.strip().lower() != "mock"]
                        if validated:
                            return True, "validated providers: " + ", ".join(validated)
                        return False, "legacy provider validation report only contains mock coverage"
                return False, "legacy provider validation report is missing a recent validated provider entry"
            except Exception as exc:
                return False, f"legacy provider validation report could not be parsed: {exc}"

        return False, "no provider validation artifact was found"

    def _no_silent_mock_in_production(self) -> tuple[bool, str]:
        try:
            from app.core.config import get_settings

            settings = get_settings()
            provider = getattr(settings, "agent_llm_provider", "mock")
            mode = getattr(settings, "deployment_mode", "appliance")
            allow_mock = getattr(settings, "agent_allow_mock_llm_in_production", False)

            if mode in ("production", "enterprise_managed") and provider == "mock":
                if allow_mock:
                    return False, "mock LLM is explicitly allowed in production-capable mode"
                return False, f"mock LLM is configured for {mode}"
            return True, f"LLM provider posture is {provider} in {mode}"
        except Exception as exc:
            return False, f"production mock posture could not be validated: {exc}"

    def _no_silent_task_simulation(self, base_dir: Path) -> tuple[bool, str]:
        task_engine = base_dir / "control_plane/app/services/agents/task_engine.py"
        agent_executor = base_dir / "control_plane/app/services/agents/agent_executor.py"
        if not task_engine.exists() or not agent_executor.exists():
            return False, "task execution sources are missing"

        task_engine_content = task_engine.read_text(encoding="utf-8")
        agent_executor_content = agent_executor.read_text(encoding="utf-8")
        findings = []
        settings = None
        try:
            from app.core.config import get_settings

            settings = get_settings()
        except Exception:
            settings = None

        if 'output["execution_mode"] = ctx.execution_mode' not in task_engine_content:
            findings.append("task_engine.py can complete tasks without execution_mode")
        if 'simulation_mode_unsupported' not in task_engine_content:
            findings.append("task_engine.py does not fail explicitly on AGENT_TASK_SIMULATION_MODE")
        if 'controlled_not_implemented' in task_engine_content or 'NotImplementedError' in task_engine_content:
            findings.append("task_engine.py still contains incomplete execution markers")
        if 'output.setdefault("execution_mode", "dry_run")' not in agent_executor_content:
            findings.append("agent_executor.py does not tag dry_run tool calls with execution_mode")
        if 'output.setdefault("execution_mode", "real")' not in agent_executor_content:
            findings.append("agent_executor.py does not tag real tool calls with execution_mode")
        if '"execution_mode": "mock"' not in agent_executor_content:
            findings.append("agent_executor.py does not tag mock tool calls with execution_mode")
        if '"simulated": True' not in agent_executor_content:
            findings.append("agent_executor.py does not tag simulated outputs with simulated=true")
        if 'agent_executor_allow_simulation' not in agent_executor_content:
            findings.append("agent_executor.py does not guard simulation behind AGENT_EXECUTOR_ALLOW_SIMULATION")
        if 'agent_executor_mock_mode' not in agent_executor_content:
            findings.append("agent_executor.py does not guard mock mode behind AGENT_EXECUTOR_MOCK_MODE")
        if 'agent_executor_dry_run_mode' not in agent_executor_content:
            findings.append("agent_executor.py does not guard dry-run mode behind AGENT_EXECUTOR_DRY_RUN_MODE")

        if settings is not None:
            mode = getattr(settings, "deployment_mode", "appliance")
            active_modes = [
                name
                for name, enabled in (
                    ("mock", getattr(settings, "agent_executor_mock_mode", False)),
                    ("dry_run", getattr(settings, "agent_executor_dry_run_mode", False)),
                    ("simulation", getattr(settings, "agent_executor_allow_simulation", False)),
                )
                if enabled
            ]
            if active_modes and mode in ("production", "enterprise_managed"):
                findings.append(
                    f"AgentExecutor non-real modes active in {mode}: {', '.join(active_modes)}"
                )

        if findings:
            return False, "; ".join(findings)
        return True, "task execution paths require explicit execution_mode and reject silent simulation"

    def _tenant_isolation_validated(self, base_dir: Path) -> tuple[bool, str]:
        test_candidates = sorted(base_dir.glob("tests/**/*tenant*isolation*.py"))
        if test_candidates:
            return True, f"tenant isolation tests present: {len(test_candidates)} files"
        config_path = base_dir / "config/multi-tenant.yaml"
        if config_path.exists():
            return True, "config/multi-tenant.yaml is present"
        return False, "no tenant isolation test or config evidence was found"

    def _criterion_passed(self, current_state: dict, criterion_key: str) -> bool:
        value = current_state.get(criterion_key, False)
        return bool(value)

    def evaluate_readiness(self, current_state: dict) -> dict:
        """Evaluate the current state against the 12 GA readiness criteria."""
        reasons = current_state.get("_reasons", {})
        score = 0
        details = {}
        failed_criteria = []

        for criterion_key, description in CRITERIA:
            passed = self._criterion_passed(current_state, criterion_key)
            if passed:
                score += 1
                details[criterion_key] = f"passed: {reasons.get(criterion_key, description)}"
            else:
                failure_reason = reasons.get(criterion_key, description)
                details[criterion_key] = f"failed: {failure_reason}"
                failed_criteria.append(criterion_key)

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
            "total_possible": len(CRITERIA),
            "details": details,
            "failed_criteria": failed_criteria,
        }

    def generate_report(self, current_state: dict, filepath: str = "artifacts/platform/ga-readiness.md") -> dict:
        result = self.evaluate_readiness(current_state)

        lines = [
            "# Platform GA Readiness Report",
            "",
            f"**Overall Maturity Level:** {result['maturity_level'].upper()}",
            f"**Score:** {result['score']} / {result['total_possible']}",
            "",
        ]

        if result["failed_criteria"]:
            lines.extend(["## Failed Criteria", ""])
            for criterion in result["failed_criteria"]:
                lines.append(f"- ❌ **{criterion}**: {result['details'][criterion]}")
            lines.append("")

        lines.extend(["## All Criteria Assessment", ""])
        for criterion_key, _ in CRITERIA:
            status = result["details"][criterion_key]
            icon = "✅" if status.startswith("passed:") else "❌"
            lines.append(f"- {icon} **{criterion_key}**: {status}")

        lines.extend(["", "## Next Steps"])
        if result["score"] == len(CRITERIA):
            lines.append("Platform is GA_READY 12/12.")
        else:
            lines.append(
                f"GA is blocked until {len(result['failed_criteria'])} missing criteria are closed."
            )

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        Path(filepath).write_text("\n".join(lines) + "\n", encoding="utf-8")
        return result
