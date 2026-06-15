import json
import logging
from uuid import UUID

from app.contracts.backend_lifecycle import (
    BackendDesiredState,
    BackendLifecycleCapabilities,
    BackendObservedState,
    LifecycleActionResult,
)
from app.services.admin_model_management import (
    _ALLOWED_DOCKER_SERVICES,
    parse_metadata,
    run_backend_docker_command,
)
from app.services.backend_lifecycle.providers.base import (
    BaseLifecycleProvider,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)


class DockerProvider(BaseLifecycleProvider):
    def capabilities(self) -> BackendLifecycleCapabilities:
        return BackendLifecycleCapabilities(
            can_start=True,
            can_stop=True,
            can_restart=True,
            can_observe=True,
            provider_type="docker",
        )

    async def get_observed_state(
        self, backend_id: UUID, desired: BackendDesiredState
    ) -> BackendObservedState:
        try:
            caps = self._get_capabilities(desired)
            if not caps["docker_actions_allowed"]:
                return BackendObservedState(
                    backend_id=backend_id,
                    provider=desired.provider,
                    running=False,
                    healthy=False,
                    error="docker actions not allowed",
                )
            service_name = caps["service_name"]
            if not service_name:
                return BackendObservedState(
                    backend_id=backend_id,
                    provider=desired.provider,
                    running=False,
                    healthy=False,
                    error="no service name mapped",
                )
            result = run_backend_docker_command(
                self._mock_backend(desired, service_name),
                "ps",
                "--format",
                "json",
                timeout_seconds=15,
            )
            if not result.ok:
                return BackendObservedState(
                    backend_id=backend_id,
                    provider=desired.provider,
                    running=False,
                    healthy=False,
                    error=result.detail or result.stderr or "docker ps failed",
                )
            raw = result.stdout.strip()
            if not raw:
                return BackendObservedState(
                    backend_id=backend_id,
                    provider=desired.provider,
                    running=False,
                    healthy=False,
                    error="no containers found",
                )
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = []
            services = (
                [parsed]
                if isinstance(parsed, dict)
                else (parsed if isinstance(parsed, list) else [])
            )
            match = next(
                (
                    s
                    for s in services
                    if str(s.get("Service") or s.get("Name") or "").strip() == service_name
                ),
                None,
            )
            if match is None:
                return BackendObservedState(
                    backend_id=backend_id,
                    provider=desired.provider,
                    running=False,
                    healthy=False,
                    error="service not found in compose ps",
                )
            status = str(match.get("State") or match.get("Status") or "").lower()
            running = "running" in status or "up" in status
            container_id = str(match.get("ID", ""))
            return BackendObservedState(
                backend_id=backend_id,
                provider=desired.provider,
                running=running,
                healthy=running,
                container_id=container_id,
                container_status=status,
                url=desired.backend_url,
            )
        except Exception as exc:
            logger.error("docker observe failed: %s", exc)
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
        return await self._docker_action(backend_id, desired, "start")

    async def stop_backend(
        self, backend_id: UUID, desired: BackendDesiredState
    ) -> LifecycleActionResult:
        return await self._docker_action(backend_id, desired, "stop")

    async def restart_backend(
        self, backend_id: UUID, desired: BackendDesiredState
    ) -> LifecycleActionResult:
        return await self._docker_action(backend_id, desired, "restart")

    async def _docker_action(
        self, backend_id: UUID, desired: BackendDesiredState, action: str
    ) -> LifecycleActionResult:
        try:
            caps = self._get_capabilities(desired)
            if not caps["docker_actions_allowed"]:
                raise ProviderUnavailableError(
                    "docker", "docker actions not allowed for this backend"
                )
            service_name = caps["service_name"]
            if not service_name:
                raise ProviderUnavailableError("docker", "no service name mapped")
            command_map = {
                "start": ("up", "-d", service_name),
                "stop": ("stop", service_name),
                "restart": ("restart", service_name),
            }
            result = run_backend_docker_command(
                self._mock_backend(desired, service_name),
                *command_map[action],
                timeout_seconds=120,
            )
            if not result.ok:
                return LifecycleActionResult(
                    success=False,
                    action=action,
                    backend_id=backend_id,
                    message=result.detail or result.stderr or "docker action failed",
                    error=result.stderr or result.detail,
                )
            return LifecycleActionResult(
                success=True,
                action=action,
                backend_id=backend_id,
                message=f"docker {action} succeeded",
            )
        except ProviderUnavailableError:
            raise
        except Exception as exc:
            logger.error("docker action failed: %s", exc)
            return LifecycleActionResult(
                success=False,
                action=action,
                backend_id=backend_id,
                message=str(exc),
                error=str(exc),
            )

    def _get_capabilities(self, desired: BackendDesiredState) -> dict:
        metadata = parse_metadata(desired.metadata_json)
        service_name = (metadata.get("service_name") or "").strip()
        allowed = service_name in _ALLOWED_DOCKER_SERVICES
        return {
            "service_name": service_name,
            "docker_actions_allowed": allowed,
        }

    def _mock_backend(self, desired: BackendDesiredState, service_name: str) -> object:
        import uuid

        from app.models.core.inference_backend import InferenceBackend

        backend = InferenceBackend(
            id=desired.backend_id or uuid.uuid4(),
            name=desired.name,
            provider=desired.provider,
            backend_url=desired.backend_url,
            healthcheck_path="/health",
            is_active=desired.is_active,
            is_default=False,
            status=desired.status,
            max_parallel_requests=1,
            current_running=0,
            metadata_json=desired.metadata_json or "{}",
        )
        backend.metadata_json = desired.metadata_json or "{}"
        return backend
