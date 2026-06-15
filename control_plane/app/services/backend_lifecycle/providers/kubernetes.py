import logging
from uuid import UUID

from app.contracts.backend_lifecycle import (
    BackendDesiredState,
    BackendLifecycleCapabilities,
    BackendObservedState,
    LifecycleActionResult,
)
from app.services.backend_lifecycle.providers.base import (
    BaseLifecycleProvider,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)


class KubernetesProvider(BaseLifecycleProvider):
    def __init__(self) -> None:
        self._client = None
        self._initialized = False
        self._namespace = "default"

    def _ensure_client(self) -> None:
        if self._initialized:
            return
        try:
            from kubernetes import client, config

            try:
                config.load_incluster_config()
            except Exception:
                config.load_kube_config()
            self._client = client.AppsV1Api()
            self._namespace = "default"
            self._initialized = True
        except ImportError:
            logger.warning("kubernetes library not installed, provider unavailable")
        except Exception as exc:
            logger.warning("kubernetes init failed: %s", exc)

    def capabilities(self) -> BackendLifecycleCapabilities:
        self._ensure_client()
        if self._client is None:
            return BackendLifecycleCapabilities(
                can_start=False,
                can_stop=False,
                can_restart=False,
                can_observe=False,
                provider_type="kubernetes_unavailable",
            )
        return BackendLifecycleCapabilities(
            can_start=True,
            can_stop=True,
            can_restart=True,
            can_observe=True,
            provider_type="kubernetes",
        )

    async def get_observed_state(
        self, backend_id: UUID, desired: BackendDesiredState
    ) -> BackendObservedState:
        self._ensure_client()
        if self._client is None:
            return BackendObservedState(
                backend_id=backend_id,
                provider=desired.provider,
                running=False,
                healthy=False,
                error="kubernetes client unavailable",
            )
        try:
            name = self._deployment_name(desired)
            dep = self._client.read_namespaced_deployment(name, self._namespace)
            available = dep.status.ready_replicas or 0
            desired_replicas = dep.spec.replicas or 0
            running = available > 0
            return BackendObservedState(
                backend_id=backend_id,
                provider=desired.provider,
                running=running,
                healthy=running,
                pod_name=name,
                pod_phase="Running" if running else "Pending",
                url=desired.backend_url,
            )
        except Exception as exc:
            return BackendObservedState(
                backend_id=backend_id,
                provider=desired.provider,
                running=False,
                healthy=False,
                error=str(exc),
            )

    async def start_backend(
        self, backend_id: UUID, desired: BackendDesiredState
    ) -> LifecycleActionResult:
        self._ensure_client()
        if self._client is None:
            raise ProviderUnavailableError("kubernetes", "kubernetes client unavailable")
        try:
            name = self._deployment_name(desired)
            body = {"spec": {"replicas": 1}}
            self._client.patch_namespaced_deployment_scale(name, self._namespace, body)
            return LifecycleActionResult(
                success=True,
                action="start",
                backend_id=backend_id,
                message=f"scaled up {name}",
            )
        except Exception as exc:
            logger.error("k8s start failed: %s", exc)
            return LifecycleActionResult(
                success=False,
                action="start",
                backend_id=backend_id,
                message=str(exc),
                error=str(exc),
            )

    async def stop_backend(
        self, backend_id: UUID, desired: BackendDesiredState
    ) -> LifecycleActionResult:
        self._ensure_client()
        if self._client is None:
            raise ProviderUnavailableError("kubernetes", "kubernetes client unavailable")
        try:
            name = self._deployment_name(desired)
            body = {"spec": {"replicas": 0}}
            self._client.patch_namespaced_deployment_scale(name, self._namespace, body)
            return LifecycleActionResult(
                success=True,
                action="stop",
                backend_id=backend_id,
                message=f"scaled down {name}",
            )
        except Exception as exc:
            logger.error("k8s stop failed: %s", exc)
            return LifecycleActionResult(
                success=False,
                action="stop",
                backend_id=backend_id,
                message=str(exc),
                error=str(exc),
            )

    async def restart_backend(
        self, backend_id: UUID, desired: BackendDesiredState
    ) -> LifecycleActionResult:
        self._ensure_client()
        if self._client is None:
            raise ProviderUnavailableError("kubernetes", "kubernetes client unavailable")
        stop = await self.stop_backend(backend_id, desired)
        if not stop.success:
            return stop
        return await self.start_backend(backend_id, desired)

    def _deployment_name(self, desired: BackendDesiredState) -> str:
        return f"backend-{desired.name}"
