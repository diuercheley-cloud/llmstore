"""
Owner: platform-ops
Status: implementation
"""
import datetime
import os
from typing import Any, Dict, List

import kopf
import kubernetes

DRY_RUN = os.environ.get("OPERATOR_DRY_RUN", "false").lower() == "true"


def get_operator_mode() -> str:
    mode = os.environ.get("OPERATOR_MODE")
    if mode:
        normalized = mode.strip().lower()
        if normalized in {"real", "mock", "dry_run"}:
            return normalized
    return "dry_run" if DRY_RUN else "real"


def _apply_enabled() -> bool:
    return get_operator_mode() == "real"


def _mode_log_prefix() -> str:
    mode = get_operator_mode()
    if mode == "dry_run":
        return "DRY-RUN"
    return mode.upper()


def get_api_client():
    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        kubernetes.config.load_incluster_config()
    else:
        kubernetes.config.load_kube_config()
    return kubernetes.client.ApiClient()


def update_status(name: str, namespace: str, plural: str, conditions: List[Dict[str, Any]], logger):
    if not _apply_enabled():
        logger.info(f"[{_mode_log_prefix()}] Would update status for {plural}/{name} in {namespace}")
        return

    api = kubernetes.client.CustomObjectsApi()
    group = "llm.stack.local"
    version = "v1"

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for condition in conditions:
        condition.setdefault("lastTransitionTime", now)

    status = {"conditions": conditions}
    api.patch_namespaced_custom_object_status(group, version, namespace, plural, name, {"status": status})


def _build_deployment_body(name: str, namespace: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "labels": {"app": name},
        },
        "spec": {
            "replicas": spec.get("replicas", 1),
            "selector": {"matchLabels": {"app": name}},
            "template": {
                "metadata": {"labels": {"app": name}},
                "spec": {
                    "containers": [
                        {
                            "name": "main",
                            "image": spec.get("image", "busybox"),
                            "ports": [{"containerPort": 8080}],
                        }
                    ]
                },
            },
        },
    }

    if spec.get("gpu", {}).get("enabled"):
        gpu_count = spec["gpu"].get("count", 1)
        deployment["spec"]["template"]["spec"]["containers"][0]["resources"] = {
            "limits": {"nvidia.com/gpu": gpu_count}
        }

    return deployment


def _build_service_body(name: str, namespace: str) -> Dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "labels": {"app": name},
        },
        "spec": {
            "selector": {"app": name},
            "ports": [{"port": 80, "targetPort": 8080}],
        },
    }


def apply_deployment(name: str, namespace: str, spec: Dict[str, Any], owner: Dict[str, Any], logger):
    apps_v1 = kubernetes.client.AppsV1Api()
    deployment = _build_deployment_body(name, namespace, spec)
    kopf.adopt(deployment, owner)

    if not _apply_enabled():
        logger.info(f"[{_mode_log_prefix()}] Would apply Deployment {name}")
        return

    try:
        apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)
        logger.info(f"Created Deployment {name}")
    except kubernetes.client.exceptions.ApiException as exc:
        if exc.status != 409:
            raise
        apps_v1.replace_namespaced_deployment(name=name, namespace=namespace, body=deployment)
        logger.info(f"Updated Deployment {name}")


def apply_service(name: str, namespace: str, owner: Dict[str, Any], logger):
    core_v1 = kubernetes.client.CoreV1Api()
    service = _build_service_body(name, namespace)
    kopf.adopt(service, owner)

    if not _apply_enabled():
        logger.info(f"[{_mode_log_prefix()}] Would apply Service {name}")
        return

    try:
        core_v1.create_namespaced_service(namespace=namespace, body=service)
        logger.info(f"Created Service {name}")
    except kubernetes.client.exceptions.ApiException as exc:
        if exc.status != 409:
            raise
        core_v1.patch_namespaced_service(name=name, namespace=namespace, body=service)
        logger.info(f"Patched Service {name}")


@kopf.on.create("llm.stack.local", "v1", "llmworkers")
@kopf.on.update("llm.stack.local", "v1", "llmworkers")
def reconcile_worker(spec, name, namespace, body, logger, **kwargs):
    logger.info(f"Reconciling LLMWorker {name} in mode={get_operator_mode()}")

    try:
        # Agent Worker specific environment
        spec["env"] = spec.get("env", []) + [
            {"name": "AGENT_WORKER_ENABLED", "value": "true"},
            {"name": "AGENT_EXECUTION_PLANE_ENABLED", "value": "true"},
        ]
        
        apply_deployment(name, namespace, spec, body, logger)
        update_status(
            name,
            namespace,
            "llmworkers",
            [{"type": "Ready", "status": "True", "reason": "Success", "message": "Worker deployment reconciled"}],
            logger,
        )
    except Exception as exc:
        logger.error(f"Worker reconciliation failed: {exc}")
        update_status(
            name,
            namespace,
            "llmworkers",
            [{"type": "Ready", "status": "False", "reason": "Error", "message": str(exc)}],
            logger,
        )


@kopf.on.create("llm.stack.local", "v1", "llminferencestacks")
@kopf.on.update("llm.stack.local", "v1", "llminferencestacks")
def reconcile_inference_stack(spec, name, namespace, body, logger, **kwargs):
    logger.info(f"Reconciling LLMInferenceStack {name} in mode={get_operator_mode()}")

    try:
        apply_deployment(f"{name}-cp", namespace, spec, body, logger)
        apply_service(f"{name}-cp", namespace, body, logger)
        update_status(
            name,
            namespace,
            "llminferencestacks",
            [{"type": "Ready", "status": "True", "reason": "Success", "message": "All resources reconciled"}],
            logger,
        )
    except Exception as exc:
        logger.error(f"Reconciliation failed: {exc}")
        update_status(
            name,
            namespace,
            "llminferencestacks",
            [{"type": "Ready", "status": "False", "reason": "Error", "message": str(exc)}],
            logger,
        )


@kopf.on.create("llm.stack.local", "v1", "llmmodelruntimes")
@kopf.on.update("llm.stack.local", "v1", "llmmodelruntimes")
def reconcile_model_runtime(spec, name, namespace, body, logger, **kwargs):
    logger.info(f"Reconciling LLMModelRuntime {name} in mode={get_operator_mode()}")

    try:
        apply_deployment(name, namespace, spec, body, logger)
        update_status(
            name,
            namespace,
            "llmmodelruntimes",
            [{"type": "Ready", "status": "True", "reason": "Success", "message": "Runtime deployment reconciled"}],
            logger,
        )
    except Exception as exc:
        update_status(
            name,
            namespace,
            "llmmodelruntimes",
            [{"type": "Ready", "status": "False", "reason": "Error", "message": str(exc)}],
            logger,
        )


@kopf.on.create("llm.stack.local", "v1", "llmproviders")
@kopf.on.update("llm.stack.local", "v1", "llmproviders")
def reconcile_provider(spec, name, namespace, logger, **kwargs):
    logger.info(f"Reconciling LLMProvider {name} in mode={get_operator_mode()}")

    secret_ref = spec.get("apiKeySecretRef")
    if not secret_ref:
        update_status(
            name,
            namespace,
            "llmproviders",
            [{"type": "Degraded", "status": "True", "reason": "MissingSecret", "message": "apiKeySecretRef is required"}],
            logger,
        )
        return

    if not _apply_enabled():
        update_status(
            name,
            namespace,
            "llmproviders",
            [{"type": "Ready", "status": "True", "reason": "MockValidated", "message": f"Validated provider secret reference {secret_ref} in {get_operator_mode()} mode"}],
            logger,
        )
        return

    core_v1 = kubernetes.client.CoreV1Api()
    try:
        core_v1.read_namespaced_secret(name=secret_ref, namespace=namespace)
        update_status(
            name,
            namespace,
            "llmproviders",
            [{"type": "Ready", "status": "True", "reason": "SecretFound", "message": "API key secret found"}],
            logger,
        )
    except kubernetes.client.exceptions.ApiException as exc:
        if exc.status != 404:
            raise
        update_status(
            name,
            namespace,
            "llmproviders",
            [{"type": "Degraded", "status": "True", "reason": "SecretNotFound", "message": f"Secret {secret_ref} not found"}],
            logger,
        )


@kopf.on.create("llm.stack.local", "v1", "llmtenants")
@kopf.on.update("llm.stack.local", "v1", "llmtenants")
def reconcile_tenant(spec, name, namespace, logger, **kwargs):
    logger.info(f"Reconciling LLMTenant {name} in mode={get_operator_mode()}")
    update_status(
        name,
        namespace,
        "llmtenants",
        [{"type": "Ready", "status": "True", "reason": "Success", "message": "Tenant registered"}],
        logger,
    )
