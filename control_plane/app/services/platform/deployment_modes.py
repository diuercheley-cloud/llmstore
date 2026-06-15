# Owner: platform-ops
"""Governed deployment mode resolution for operational activation postures."""

import logging
import os
from typing import Any

import yaml

from .profile_resolver import ProfileResolver

logger = logging.getLogger(__name__)


class DeploymentModeService:
    _modes_config: dict[str, Any] | None = None

    def __init__(self, config_path: str | None = None):
        self.profile_resolver = ProfileResolver()
        if config_path is None:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
            config_path = os.path.join(base_dir, "config/deployment-modes.yaml")
        self.config_path = config_path
        if DeploymentModeService._modes_config is None:
            self._load_config()

    def _load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, encoding="utf-8") as f:
                    DeploymentModeService._modes_config = yaml.safe_load(f)
            else:
                logger.warning(
                    f"Deployment modes config not found at {self.config_path}. Using fallback defaults."
                )
                DeploymentModeService._modes_config = self._get_fallback_defaults()
        except Exception as e:
            logger.error(f"Failed to load deployment modes config: {e}. Using fallback defaults.")
            DeploymentModeService._modes_config = self._get_fallback_defaults()

    def _get_fallback_defaults(self) -> dict[str, Any]:
        return {
            "appliance": {
                "name": "Appliance Mode",
                "description": "Fallback Appliance Mode Configuration",
                "features": {
                    "AGENT_RUNTIME_ENABLED": False,
                    "AGENT_EXECUTION_ENABLED": False,
                    "AGENT_ASYNC_EXECUTION_ENABLED": False,
                    "AGENT_WORKER_ENABLED": False,
                    "AGENT_EMBEDDED_WORKER_ENABLED": False,
                    "AGENT_SAAS_CONNECTORS_ENABLED": False,
                    "AGENT_CONNECTOR_WRITE_ENABLED": False,
                    "AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED": False,
                    "AGENT_MULTI_AGENT_ENABLED": False,
                    "AGENT_STATEFUL_WORKFLOWS_ENABLED": False,
                    "AGENT_STUDIO_ENABLED": False,
                },
                "governance": {
                    "posture": "Strict Air-gapped / Local Only",
                    "readiness_constraints": [
                        {"flag": "AGENT_RUNTIME_ENABLED", "expected": False, "severity": "blocker"},
                        {
                            "flag": "AGENT_SAAS_CONNECTORS_ENABLED",
                            "expected": False,
                            "severity": "blocker",
                        },
                        {
                            "flag": "AGENT_MULTI_AGENT_ENABLED",
                            "expected": False,
                            "severity": "blocker",
                        },
                        {
                            "flag": "AGENT_STATEFUL_WORKFLOWS_ENABLED",
                            "expected": False,
                            "severity": "blocker",
                        },
                    ],
                },
            },
            "pilot": {
                "name": "Pilot Mode",
                "description": "Fallback Pilot Mode Configuration",
                "features": {
                    "AGENT_RUNTIME_ENABLED": True,
                    "AGENT_EXECUTION_ENABLED": True,
                    "AGENT_ASYNC_EXECUTION_ENABLED": True,
                    "AGENT_WORKER_ENABLED": True,
                    "AGENT_EMBEDDED_WORKER_ENABLED": True,
                    "AGENT_SAAS_CONNECTORS_ENABLED": True,
                    "AGENT_CONNECTOR_WRITE_ENABLED": False,
                    "AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED": True,
                    "AGENT_HUMAN_APPROVAL_ENABLED": True,
                    "AGENT_APPROVAL_REQUIRED_FOR_HIGH_RISK": True,
                    "AGENT_MULTI_AGENT_ENABLED": False,
                    "AGENT_STATEFUL_WORKFLOWS_ENABLED": True,
                    "AGENT_STUDIO_ENABLED": True,
                    "AGENT_STRICT_BUDGETS": True,
                },
                "governance": {
                    "posture": "Governed Testing / Human-in-the-loop",
                    "readiness_constraints": [
                        {"flag": "AGENT_RUNTIME_ENABLED", "expected": True, "severity": "blocker"},
                        {
                            "flag": "AGENT_CONNECTOR_WRITE_ENABLED",
                            "expected": False,
                            "severity": "blocker",
                        },
                        {
                            "flag": "AGENT_HUMAN_APPROVAL_ENABLED",
                            "expected": True,
                            "severity": "blocker",
                        },
                        {
                            "flag": "AGENT_MULTI_AGENT_ENABLED",
                            "expected": False,
                            "severity": "warning",
                        },
                    ],
                },
            },
            "production": {
                "name": "Production Mode",
                "description": "Fallback Production Mode Configuration",
                "features": {
                    "AGENT_RUNTIME_ENABLED": True,
                    "AGENT_EXECUTION_ENABLED": True,
                    "AGENT_ASYNC_EXECUTION_ENABLED": True,
                    "AGENT_WORKER_ENABLED": True,
                    "AGENT_SAAS_CONNECTORS_ENABLED": True,
                    "AGENT_CONNECTOR_WRITE_ENABLED": True,
                    "AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED": True,
                    "AGENT_PROMOTION_REQUIRES_EVALS": True,
                    "AGENT_EVAL_REGRESSION_GATE_ENABLED": True,
                    "AGENT_STATEFUL_WORKFLOWS_ENABLED": True,
                    "AGENT_WORKER_AUTOSCALING_ENABLED": True,
                    "AGENT_SLO_ENFORCEMENT_ENABLED": True,
                },
                "governance": {
                    "posture": "Production Grade / Automatic Evals & SLOs",
                    "readiness_constraints": [
                        {"flag": "AGENT_RUNTIME_ENABLED", "expected": True, "severity": "blocker"},
                        {
                            "flag": "AGENT_PROMOTION_REQUIRES_EVALS",
                            "expected": True,
                            "severity": "blocker",
                        },
                        {
                            "flag": "AGENT_EVAL_REGRESSION_GATE_ENABLED",
                            "expected": True,
                            "severity": "blocker",
                        },
                    ],
                },
            },
            "enterprise_managed": {
                "name": "Enterprise Managed Mode",
                "description": "Fallback Enterprise Managed Mode Configuration",
                "features": {
                    "AGENT_RUNTIME_ENABLED": True,
                    "AGENT_EXECUTION_ENABLED": True,
                    "AGENT_ASYNC_EXECUTION_ENABLED": True,
                    "AGENT_WORKER_ENABLED": True,
                    "AGENT_SAAS_CONNECTORS_ENABLED": True,
                    "AGENT_CONNECTOR_WRITE_ENABLED": True,
                    "AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED": True,
                    "AGENT_PROMOTION_REQUIRES_EVALS": True,
                    "AGENT_EVAL_REGRESSION_GATE_ENABLED": True,
                    "AGENT_STATEFUL_WORKFLOWS_ENABLED": True,
                    "AGENT_WORKER_AUTOSCALING_ENABLED": True,
                    "AGENT_SLO_ENFORCEMENT_ENABLED": True,
                    "COMMERCIAL_FEDERATION_ENABLED": True,
                    "COMMERCIAL_GOVERNANCE_FEDERATION_ENABLED": True,
                    "MANAGED_CONTROL_PLANE_ENABLED": True,
                    "AGENT_ENTERPRISE_OBSERVABILITY_ENABLED": True,
                    "AGENT_TENANT_ISOLATION_STRICT": True,
                },
                "governance": {
                    "posture": "Enterprise Managed / Federated & Strict Isolation",
                    "readiness_constraints": [
                        {"flag": "AGENT_RUNTIME_ENABLED", "expected": True, "severity": "blocker"},
                        {
                            "flag": "AGENT_TENANT_ISOLATION_STRICT",
                            "expected": True,
                            "severity": "blocker",
                        },
                        {
                            "flag": "MANAGED_CONTROL_PLANE_ENABLED",
                            "expected": True,
                            "severity": "blocker",
                        },
                    ],
                },
            },
        }

    def get_mode_config(self, mode: str) -> dict[str, Any]:
        if not DeploymentModeService._modes_config:
            self._load_config()
        return DeploymentModeService._modes_config.get(mode) or self._get_fallback_defaults().get(
            "appliance"
        )

    def get_mode_defaults(self, mode: str) -> dict[str, Any]:
        return self.get_mode_config(mode).get("features", {})

    def get_governance_posture(self, mode: str) -> str:
        return self.get_mode_config(mode).get("governance", {}).get("posture", "Unknown")

    def validate_coherence(self, settings: Any) -> tuple[bool, list[str], list[str]]:
        """
        Validates if manually set settings are coherent with the chosen deployment mode constraints.
        Returns:
            (is_coherent, blockers, warnings)
        """
        mode = getattr(settings, "deployment_mode", "appliance")
        mode_cfg = self.get_mode_config(mode)
        constraints = mode_cfg.get("governance", {}).get("readiness_constraints", [])

        blockers = []
        warnings = []

        for constraint in constraints:
            flag_name = constraint.get("flag")
            expected_val = constraint.get("expected")
            severity = constraint.get("severity", "blocker")

            attr_name = flag_name.lower()
            if hasattr(settings, attr_name):
                current_val = getattr(settings, attr_name)
                if current_val != expected_val:
                    msg = f"Deployment Mode '{mode}' expects feature flag '{flag_name}' to be {expected_val}, but it is currently set to {current_val}."
                    if severity == "blocker":
                        blockers.append(msg)
                    else:
                        warnings.append(msg)
            else:
                if expected_val:
                    msg = f"Deployment Mode '{mode}' expects feature flag '{flag_name}' to be {expected_val}, but this feature flag is undefined."
                    if severity == "blocker":
                        blockers.append(msg)
                    else:
                        warnings.append(msg)

        valid_modes = {"appliance", "pilot", "production", "enterprise_managed"}
        if mode not in valid_modes:
            blockers.append(
                f"Invalid DEPLOYMENT_MODE '{mode}'. Allowed modes are: {', '.join(valid_modes)}"
            )

        return len(blockers) == 0, blockers, warnings

    def print_startup_banner(self, settings: Any):
        """
        Logs a detailed startup banner to standard loggers with information about the deployment mode.
        """
        mode = getattr(settings, "deployment_mode", "appliance")
        profile = getattr(settings, "platform_profile", "appliance")
        posture = self.get_governance_posture(mode)
        mode_cfg = self.get_mode_config(mode)
        name = mode_cfg.get("name", mode)

        # Detect features enabled
        enabled_features = []
        for key in sorted(mode_cfg.get("features", {}).keys()):
            attr_name = key.lower()
            if hasattr(settings, attr_name) and getattr(settings, attr_name) is True:
                enabled_features.append(key)

        banner = f"""
======================================================================
                  AGENTIC AI PLATFORM INITIALIZATION
======================================================================
  [Deployment Mode]    {name} ({mode})
  [Platform Profile]   {profile}
  [Governance Posture] {posture}
  
  [Enabled Feature Flags]
"""
        if enabled_features:
            for feat in enabled_features:
                banner += f"    - {feat}\n"
        else:
            banner += "    (None)\n"

        banner += "======================================================================"
        logger.info(banner)
