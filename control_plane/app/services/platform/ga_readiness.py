# Owner: platform-ops
"""Objective GA readiness scoring from repository and artifact evidence."""

import asyncio
import json
import os
from datetime import timedelta
from pathlib import Path

import yaml
from app.core.config import get_settings
from app.services.platform.current_release_context import get_current_tag
from app.services.platform.release_artifact_resolver import ReleaseArtifactResolver

CRITERIA = [
    ("runtime_enabled", "Agent runtime is enabled in config"),
    ("worker_heartbeat_active", "Active worker heartbeat registered"),
    ("real_execution_readiness_passed", "real-execution-readiness passed"),
    ("production_agentic_e2e_passed", "production-agentic-e2e passed"),
    ("plugin_runtime_verified", "Plugin runtime verified and sandbox active"),
    ("cryptographic_receipts_real", "Cryptographic receipts are signed and real"),
    ("observability_real_data", "Observability collects real event and metric data"),
    ("profile_validation_strict", "Strict profile resolver validation with no conflicts"),
    ("no_placeholder_production_surface", "No placeholders in production surface"),
    ("clean_working_tree", "Clean working tree certified"),
    ("supported_surface_no_production_beta_stub", "No production feature depends on beta/stub/mock"),
    ("release_gate_passed", "Unified release gate passed for current release"),
]

class GAReadinessService:
    def __init__(self, config_path="config/ga-readiness-rules.yaml"):
        self.config_path = config_path
        self.settings = get_settings()
        self._load_config()

    def _load_config(self):
        # Allow default rules if config is missing
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self.rules = data.get("rules", {})
            self.weights = data.get("weights", {})
        else:
            self.rules = {}
            self.weights = {"ga_ready": 12, "production_ready": 11, "pilot_ready": 8, "beta": 4}

    def _resolve_base_dir(self) -> Path:
        config_path = Path(self.config_path).resolve()
        return config_path.parent.parent

    def _run_sync(self, coro):
        from concurrent.futures import ThreadPoolExecutor
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(lambda: asyncio.run(coro))
                return future.result()
        else:
            return loop.run_until_complete(coro)

    def _production_surface_dependencies_ok(self, base_dir: Path) -> tuple[bool, str]:
        supported_surface_yaml = base_dir / "config/supported-surface.yaml"
        if not supported_surface_yaml.exists():
            return False, "config/supported-surface.yaml is missing"

        try:
            data = yaml.safe_load(supported_surface_yaml.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            return False, f"Failed to parse supported-surface.yaml: {exc}"

        capabilities = data.get("capabilities", [])
        production_core_ids = {
            item.get("id")
            for item in capabilities
            if isinstance(item, dict) and item.get("status") == "production_core"
        }
        blockers = []

        if "billing" in production_core_ids:
            provider = str(getattr(self.settings, "payment_provider", "mock")).strip().lower()
            if provider in {"mock", "disabled", ""}:
                blockers.append(f"billing requires PAYMENT_PROVIDER real, found '{provider}'")

        if "rag" in production_core_ids:
            embeddings = str(getattr(self.settings, "embeddings_backend", "mock")).strip().lower()
            if embeddings == "mock":
                blockers.append("rag requires EMBEDDINGS_BACKEND real, found 'mock'")

        if "multi-provider-routing" in production_core_ids:
            if bool(getattr(self.settings, "mock_backend_enabled", False)):
                blockers.append("multi-provider-routing requires MOCK_BACKEND_ENABLED=false")

        if "agentic-runtime" in production_core_ids:
            llm_provider = str(getattr(self.settings, "agent_llm_provider", "mock")).strip().lower()
            if llm_provider == "mock":
                blockers.append("agentic-runtime requires AGENT_LLM_PROVIDER not mock")
            non_real_modes = [
                mode
                for mode, enabled in (
                    ("mock", bool(getattr(self.settings, "agent_executor_mock_mode", False))),
                    ("dry_run", bool(getattr(self.settings, "agent_executor_dry_run_mode", False))),
                    ("simulation", bool(getattr(self.settings, "agent_executor_allow_simulation", False))),
                )
                if enabled
            ]
            if non_real_modes:
                blockers.append(
                    "agentic-runtime requires real executor modes only; found "
                    + ", ".join(non_real_modes)
                )

        if "agent-worker-operations" in production_core_ids:
            if not bool(getattr(self.settings, "agent_worker_enabled", False)):
                blockers.append("agent-worker-operations requires AGENT_WORKER_ENABLED=true")

        if "agent-readiness" in production_core_ids:
            readiness_artifact = base_dir / "artifacts/runtime/real-execution-readiness.json"
            if not readiness_artifact.exists():
                blockers.append("agent-readiness requires artifacts/runtime/real-execution-readiness.json")

        if blockers:
            return False, "; ".join(blockers)
        return True, "Supported surface validated with production dependencies hardened"

    async def _check_active_workers_db(self) -> bool:
        try:
            from app.core.time import utc_now
            from app.db.session import SessionLocal
            from app.models.agents.agent_execution import AgentWorkerHeartbeat
            from sqlalchemy import func
            from sqlalchemy.future import select
            
            async with SessionLocal() as db:
                res = await db.execute(
                    select(func.count(AgentWorkerHeartbeat.worker_id))
                    .where(AgentWorkerHeartbeat.last_heartbeat >= utc_now() - timedelta(minutes=2))
                )
                count = res.scalar() or 0
                return count > 0
        except Exception:
            return False

    def collect_current_state(self) -> dict:
        base_dir = self._resolve_base_dir()
        tag = get_current_tag()
        resolver = ReleaseArtifactResolver(base_dir)
        reasons = {}

        # 1. runtime_enabled
        runtime_ok = bool(self.settings.agent_runtime_enabled)
        reasons["runtime_enabled"] = "Agent runtime is enabled" if runtime_ok else "Agent runtime is disabled"

        # 2. worker_heartbeat_active
        worker_ok = self._run_sync(self._check_active_workers_db())
        reasons["worker_heartbeat_active"] = "Active workers found in database" if worker_ok else "No active worker heartbeats found in DB"

        # 3. real_execution_readiness_passed
        real_readiness_file = base_dir / "artifacts/runtime/real-execution-readiness.json"
        real_execution_ok = False
        if real_readiness_file.exists():
            try:
                data = json.loads(real_readiness_file.read_text(encoding="utf-8"))
                if data.get("status") == "ready" or data.get("status") == "success":
                    real_execution_ok = True
                    reasons["real_execution_readiness_passed"] = "Real execution readiness reports status=ready"
                else:
                    reasons["real_execution_readiness_passed"] = f"Real execution readiness status is: {data.get('status')}"
            except Exception as e:
                reasons["real_execution_readiness_passed"] = f"Failed to parse real-execution-readiness.json: {e}"
        else:
            reasons["real_execution_readiness_passed"] = "real-execution-readiness.json artifact is missing"

        # 4. production_agentic_e2e_passed
        e2e_summary_file = base_dir / "artifacts/e2e/production-agentic/summary.md"
        e2e_ok = False
        if e2e_summary_file.exists():
            content = e2e_summary_file.read_text(encoding="utf-8")
            if "Result: PASS" in content or "Status: PASS" in content:
                e2e_ok = True
                reasons["production_agentic_e2e_passed"] = "production-agentic-e2e passed"
            else:
                reasons["production_agentic_e2e_passed"] = "production-agentic-e2e summary does not report PASS"
        else:
            reasons["production_agentic_e2e_passed"] = "production-agentic-e2e summary.md artifact is missing"

        # 5. plugin_runtime_verified
        plugin_artifact = resolver.get_validation_path(tag).parent / "plugin-runtime.md"
        plugin_ok = False
        if plugin_artifact.exists():
            content = plugin_artifact.read_text(encoding="utf-8")
            if "Result: PASS" in content or "Status: PASS" in content:
                plugin_ok = True
                reasons["plugin_runtime_verified"] = "Plugin runtime verified and sandbox active"
            else:
                reasons["plugin_runtime_verified"] = "Plugin runtime validation does not report PASS"
        else:
            reasons["plugin_runtime_verified"] = f"plugin-runtime.md artifact is missing for tag {tag}"

        # 6. cryptographic_receipts_real
        receipts_artifact = resolver.get_validation_path(tag).parent / "cryptographic-receipts.md"
        receipts_ok = False
        if receipts_artifact.exists():
            content = receipts_artifact.read_text(encoding="utf-8")
            if "Result: PASS" in content or "Status: PASS" in content:
                receipts_ok = True
                reasons["cryptographic_receipts_real"] = "Cryptographic receipts verified and real"
            else:
                reasons["cryptographic_receipts_real"] = "Cryptographic receipts verification does not report PASS"
        else:
            reasons["cryptographic_receipts_real"] = f"cryptographic-receipts.md artifact is missing for tag {tag}"

        # 7. observability_real_data
        observability_artifact = resolver.get_validation_path(tag).parent / "observability.md"
        observability_ok = False
        if observability_artifact.exists():
            content = observability_artifact.read_text(encoding="utf-8")
            if "Result: PASS" in content or "Status: PASS" in content:
                observability_ok = True
                reasons["observability_real_data"] = "Observability collects real event and metric data"
            else:
                reasons["observability_real_data"] = "Observability validation does not report PASS"
        else:
            reasons["observability_real_data"] = f"observability.md artifact is missing for tag {tag}"

        # 8. profile_validation_strict
        profile_artifact = resolver.get_validation_path(tag).parent / "profile-resolver.md"
        profile_ok = False
        if profile_artifact.exists():
            content = profile_artifact.read_text(encoding="utf-8")
            if "Result: PASS" in content or "Status: PASS" in content:
                profile_ok = True
                reasons["profile_validation_strict"] = "Strict profile resolver validation passes"
            else:
                reasons["profile_validation_strict"] = "Profile resolver validation does not report PASS"
        else:
            reasons["profile_validation_strict"] = f"profile-resolver.md artifact is missing for tag {tag}"

        # 9. no_placeholder_production_surface
        placeholder_artifact = base_dir / "artifacts/audit/production-placeholders.md"
        placeholder_ok = False
        if placeholder_artifact.exists():
            content = placeholder_artifact.read_text(encoding="utf-8")
            if "Result: PASS" in content and "production_blocker" not in content.lower():
                placeholder_ok = True
                reasons["no_placeholder_production_surface"] = "No placeholders in production surface"
            else:
                reasons["no_placeholder_production_surface"] = "Placeholder audit reports failures or production_blockers"
        else:
            reasons["no_placeholder_production_surface"] = "production-placeholders.md artifact is missing"

        # 10. clean_working_tree
        working_tree_artifact = resolver.get_validation_path(tag).parent / "working-tree-certification.md"
        working_tree_ok = False
        if working_tree_artifact.exists():
            content = working_tree_artifact.read_text(encoding="utf-8")
            if "Status: PASS" in content or "Result: PASS" in content:
                working_tree_ok = True
                reasons["clean_working_tree"] = "Clean working tree certified"
            else:
                reasons["clean_working_tree"] = "Working tree certification status is not PASS"
        else:
            reasons["clean_working_tree"] = f"working-tree-certification.md artifact is missing for tag {tag}"

        # 11. supported_surface_no_production_beta_stub
        surface_ok, surface_reason = self._production_surface_dependencies_ok(base_dir)
        reasons["supported_surface_no_production_beta_stub"] = surface_reason

        # 12. release_gate_passed
        release_gate_artifact = resolver.get_production_gate_path(tag)
        release_gate_ok = False
        if release_gate_artifact.exists():
            content = release_gate_artifact.read_text(encoding="utf-8")
            if "Overall Status: PASS" in content or "Result: PASS" in content:
                release_gate_ok = True
                reasons["release_gate_passed"] = "Unified release gate passed for current release"
            else:
                reasons["release_gate_passed"] = "Unified release gate status is not PASS"
        else:
            # Fallback to summary.md
            summary_artifact = resolver.get_summary_path(tag)
            if summary_artifact.exists():
                content = summary_artifact.read_text(encoding="utf-8")
                if "**Status**: PASS" in content:
                    release_gate_ok = True
                    reasons["release_gate_passed"] = "Release summary reports PASS for current release"
                else:
                    reasons["release_gate_passed"] = "Release summary status is not PASS"
            else:
                reasons["release_gate_passed"] = f"No release gate or summary artifact found for tag {tag}"

        return {
            "runtime_enabled": runtime_ok,
            "worker_heartbeat_active": worker_ok,
            "real_execution_readiness_passed": real_execution_ok,
            "production_agentic_e2e_passed": e2e_ok,
            "plugin_runtime_verified": plugin_ok,
            "cryptographic_receipts_real": receipts_ok,
            "observability_real_data": observability_ok,
            "profile_validation_strict": profile_ok,
            "no_placeholder_production_surface": placeholder_ok,
            "clean_working_tree": working_tree_ok,
            "supported_surface_no_production_beta_stub": surface_ok,
            "release_gate_passed": release_gate_ok,
            "_reasons": reasons,
        }

    def evaluate_readiness(self, current_state: dict) -> dict:
        """Evaluate the current state against the 12 GA readiness criteria."""
        reasons = current_state.get("_reasons", {})
        score = 0
        details = {}
        failed_criteria = []

        # GA readiness requires:
        # 1. runtime enabled
        # 2. GA is forbidden if runtime disabled, even if other things pass
        # 3. GA is forbidden if artifacts are from another release (which is handled by resolving using current tag/release)
        # 4. GA is forbidden if production E2E did not run (production_agentic_e2e_passed must be True)

        for criterion_key, description in CRITERIA:
            passed = bool(current_state.get(criterion_key, False))
            if passed:
                score += 1
                details[criterion_key] = f"passed: {reasons.get(criterion_key, description)}"
            else:
                failure_reason = reasons.get(criterion_key, description)
                details[criterion_key] = f"failed: {failure_reason}"
                failed_criteria.append(criterion_key)

        maturity = "experimental"
        # Strict enforcement: if runtime is disabled or production E2E failed/didn't run, status cannot be GA_READY
        runtime_disabled = not current_state.get("runtime_enabled", False)
        e2e_failed = not current_state.get("production_agentic_e2e_passed", False)
        
        if score >= self.weights.get("ga_ready", 12) and not runtime_disabled and not e2e_failed:
            maturity = "ga_ready"
        elif score >= self.weights.get("production_ready", 11) and not runtime_disabled:
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
        if result["maturity_level"] == "ga_ready":
            lines.append("Platform is GA_READY 12/12.")
        else:
            lines.append(
                f"GA is blocked until {len(result['failed_criteria'])} missing criteria are closed."
            )

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        Path(filepath).write_text("\n".join(lines) + "\n", encoding="utf-8")
        return result
