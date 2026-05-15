import logging
import uuid
from typing import Dict, Any
from app.services.routing.infra_adapters.base import BaseInfraAdapter
from app.models.commercial_infra_simulation import CommercialInfrastructureSimulation
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class KubernetesAdapter(BaseInfraAdapter):
    def __init__(self):
        self.settings = get_settings()
        self.client = None
        self._initialized = False

    def _init_client(self):
        if self._initialized:
            return
        try:
            from kubernetes import client, config
            if self.settings.commercial_k8s_context:
                config.load_kube_config(context=self.settings.commercial_k8s_context)
            else:
                try:
                    config.load_incluster_config()
                except config.ConfigException:
                    config.load_kube_config()
            self.client = client.AppsV1Api()
            self._initialized = True
        except ImportError:
            logger.warning("kubernetes python library not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")

    def validate_connection(self) -> bool:
        if not self.settings.commercial_k8s_execution_enabled:
            return False
        self._init_client()
        return self.client is not None

    async def plan_action(self, simulation: CommercialInfrastructureSimulation) -> Dict[str, Any]:
        return {
            "adapter": "kubernetes",
            "namespace": self.settings.commercial_k8s_namespace,
            "target": simulation.target_identifier,
            "action": simulation.simulation_type,
            "dry_run": True
        }

    async def execute_action(self, simulation: CommercialInfrastructureSimulation, dry_run: bool = True) -> Dict[str, Any]:
        if not self.validate_connection():
            return {"status": "failed", "error": "Kubernetes adapter unavailable or disabled"}

        # Real dry_run check
        effective_dry_run = dry_run or self.settings.commercial_k8s_dry_run
        
        try:
            action = simulation.simulation_type
            target = simulation.target_identifier
            details = simulation.requested_action_json
            namespace = self.settings.commercial_k8s_namespace

            if action in ["scale_up", "scale_down"]:
                replicas = details.get("replicas") or details.get("nodes")
                if replicas is None:
                    return {"status": "failed", "error": "Replicas not specified for scaling"}
                
                if effective_dry_run:
                    return {
                        "status": "dry_run",
                        "external_id": f"k8s-dryrun-{uuid.uuid4()}",
                        "message": f"Dry run: Scale {target} in {namespace} to {replicas} replicas"
                    }
                
                # Real execution
                body = {"spec": {"replicas": replicas}}
                # Try Deployment first, then StatefulSet
                try:
                    self.client.patch_namespaced_deployment_scale(target, namespace, body)
                except Exception:
                    self.client.patch_namespaced_stateful_set_scale(target, namespace, body)
                
                return {
                    "status": "executed",
                    "external_id": f"k8s-{target}-{uuid.uuid4()}",
                    "message": f"Successfully scaled {target} to {replicas}"
                }
            
            return {"status": "failed", "error": f"Action {action} not supported by Kubernetes adapter"}
            
        except Exception as e:
            logger.error(f"Kubernetes execution failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def rollback_action(self, execution_record_id: str) -> Dict[str, Any]:
        # Basic rollback for scaling: we'd need to know the previous replica count
        # For Phase 22, we'll return a message that manual intervention might be needed
        # or we could store the previous state in the execution record.
        return {
            "status": "failed",
            "message": "Rollback not fully implemented for Kubernetes. Manual intervention suggested."
        }

    async def get_status(self, external_operation_id: str) -> Dict[str, Any]:
        return {"status": "unknown", "external_id": external_operation_id}
