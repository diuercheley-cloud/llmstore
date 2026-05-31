"""
Owner: platform-ops
Status: implementation
"""
import datetime
import os
from copy import deepcopy
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


def _ensure_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _merge_env(env: List[Dict[str, Any]], extra_env: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for item in env + extra_env:
        name = item.get("name")
        if name:
            merged[name] = item
    return list(merged.values())


def _build_probe(probe: Dict[str, Any] | None, default_port: int) -> Dict[str, Any] | None:
    if not probe:
        return None
    probe = deepcopy(probe)
    if "httpGet" not in probe and probe.get("path"):
        probe["httpGet"] = {
            "path": probe.pop("path"),
            "port": probe.pop("port", default_port),
        }
    return probe


def _default_probes(container_port: int) -> Dict[str, Dict[str, Any]]:
    return {
        "readinessProbe": {
            "httpGet": {"path": "/healthz", "port": container_port},
            "initialDelaySeconds": 5,
            "periodSeconds": 10,
            "timeoutSeconds": 3,
            "failureThreshold": 6,
        },
        "livenessProbe": {
            "httpGet": {"path": "/healthz", "port": container_port},
            "initialDelaySeconds": 15,
            "periodSeconds": 20,
            "timeoutSeconds": 3,
            "failureThreshold": 3,
        },
    }


def _build_persistent_volume_claim(name: str, namespace: str, claim: Dict[str, Any]) -> Dict[str, Any]:
    access_modes = claim.get("accessModes") or ["ReadWriteOnce"]
    storage_class_name = claim.get("storageClassName")
    pvc = {
        "apiVersion": "v1",
        "kind": "PersistentVolumeClaim",
        "metadata": {
            "name": claim.get("name", f"{name}-data"),
            "namespace": namespace,
            "labels": {"app": name},
        },
        "spec": {
            "accessModes": access_modes,
            "resources": {"requests": {"storage": claim.get("size", "20Gi")}},
        },
    }
    if storage_class_name:
        pvc["spec"]["storageClassName"] = storage_class_name
    return pvc


def _build_hpa_body(name: str, namespace: str, autoscaling: Dict[str, Any]) -> Dict[str, Any]:
    metrics: List[Dict[str, Any]] = []
    cpu = autoscaling.get("targetCPUUtilizationPercentage")
    memory = autoscaling.get("targetMemoryUtilizationPercentage")
    if cpu:
        metrics.append(
            {
                "type": "Resource",
                "resource": {
                    "name": "cpu",
                    "target": {"type": "Utilization", "averageUtilization": cpu},
                },
            }
        )
    if memory:
        metrics.append(
            {
                "type": "Resource",
                "resource": {
                    "name": "memory",
                    "target": {"type": "Utilization", "averageUtilization": memory},
                },
            }
        )
    return {
        "apiVersion": "autoscaling/v2",
        "kind": "HorizontalPodAutoscaler",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "labels": {"app": name},
        },
        "spec": {
            "scaleTargetRef": {"apiVersion": "apps/v1", "kind": "Deployment", "name": name},
            "minReplicas": autoscaling.get("minReplicas", 1),
            "maxReplicas": autoscaling.get("maxReplicas", 3),
            "metrics": metrics,
        },
    }


def _build_deployment_body(name: str, namespace: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    metadata = spec.get("metadata", {})
    pod_metadata = spec.get("podMetadata", {})
    labels = {"app": name, **metadata.get("labels", {})}
    pod_labels = {"app": name, **pod_metadata.get("labels", {})}
    annotations = metadata.get("annotations", {})
    pod_annotations = pod_metadata.get("annotations", {})
    container_port = int(spec.get("containerPort", 8080))
    container_ports = spec.get("ports") or [{"containerPort": container_port}]
    env = _ensure_list(spec.get("env"))
    env_from = _ensure_list(spec.get("envFrom"))
    resources = deepcopy(spec.get("resources", {}))
    security_context = deepcopy(spec.get("securityContext", {}))
    pod_security_context = deepcopy(spec.get("podSecurityContext", {}))
    volumes = _ensure_list(spec.get("volumes"))
    volume_mounts = _ensure_list(spec.get("volumeMounts"))
    persistent_volume_claim = spec.get("persistentVolumeClaim")
    service_account_name = spec.get("serviceAccountName")

    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "labels": labels,
        },
        "spec": {
            "replicas": spec.get("replicas", 1),
            "selector": {"matchLabels": {"app": name}},
            "template": {
                "metadata": {"labels": pod_labels},
                "spec": {
                    "containers": [
                        {
                            "name": "main",
                            "image": spec.get("image", "busybox"),
                            "ports": container_ports,
                            "env": env,
                            "envFrom": env_from,
                            "resources": resources,
                            "securityContext": security_context,
                            "volumeMounts": volume_mounts,
                        }
                    ],
                    "volumes": volumes,
                },
            },
        },
    }

    if annotations:
        deployment["metadata"]["annotations"] = annotations
    if pod_annotations:
        deployment["spec"]["template"]["metadata"]["annotations"] = pod_annotations
    if service_account_name:
        deployment["spec"]["template"]["spec"]["serviceAccountName"] = service_account_name
    if pod_security_context:
        deployment["spec"]["template"]["spec"]["securityContext"] = pod_security_context
    if spec.get("nodeSelector"):
        deployment["spec"]["template"]["spec"]["nodeSelector"] = spec["nodeSelector"]
    if spec.get("tolerations"):
        deployment["spec"]["template"]["spec"]["tolerations"] = spec["tolerations"]
    if spec.get("affinity"):
        deployment["spec"]["template"]["spec"]["affinity"] = spec["affinity"]

    if persistent_volume_claim:
        claim_name = persistent_volume_claim.get("name", f"{name}-data")
        deployment["spec"]["template"]["spec"].setdefault("volumes", []).append(
            {
                "name": persistent_volume_claim.get("volumeName", "data"),
                "persistentVolumeClaim": {"claimName": claim_name},
            }
        )
        mount_path = persistent_volume_claim.get("mountPath", "/data")
        deployment["spec"]["template"]["spec"]["containers"][0].setdefault("volumeMounts", []).append(
            {"name": persistent_volume_claim.get("volumeName", "data"), "mountPath": mount_path}
        )

    probes = _default_probes(container_port)
    readiness_probe = _build_probe(spec.get("readinessProbe"), container_port) or probes["readinessProbe"]
    liveness_probe = _build_probe(spec.get("livenessProbe"), container_port) or probes["livenessProbe"]
    startup_probe = _build_probe(spec.get("startupProbe"), container_port)
    deployment["spec"]["template"]["spec"]["containers"][0]["readinessProbe"] = readiness_probe
    deployment["spec"]["template"]["spec"]["containers"][0]["livenessProbe"] = liveness_probe
    if startup_probe:
        deployment["spec"]["template"]["spec"]["containers"][0]["startupProbe"] = startup_probe

    if spec.get("gpu", {}).get("enabled"):
        gpu_count = spec["gpu"].get("count", 1)
        container_resources = deployment["spec"]["template"]["spec"]["containers"][0].setdefault("resources", {})
        container_resources.setdefault("limits", {})
        container_resources["limits"]["nvidia.com/gpu"] = gpu_count

    return deployment


def _build_service_body(name: str, namespace: str, spec: Dict[str, Any] | None = None) -> Dict[str, Any]:
    spec = spec or {}
    service_spec = spec.get("service", {})
    port = int(service_spec.get("port", 80))
    target_port = int(service_spec.get("targetPort", spec.get("containerPort", 8080)))
    body = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "labels": {"app": name, **service_spec.get("labels", {})},
        },
        "spec": {
            "selector": {"app": name},
            "type": service_spec.get("type", "ClusterIP"),
            "ports": service_spec.get("ports") or [{"port": port, "targetPort": target_port}],
        },
    }
    if service_spec.get("annotations"):
        body["metadata"]["annotations"] = service_spec["annotations"]
    return body


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


def apply_service(name: str, namespace: str, spec: Dict[str, Any], owner: Dict[str, Any], logger):
    core_v1 = kubernetes.client.CoreV1Api()
    service = _build_service_body(name, namespace, spec)
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


def apply_persistent_volume_claim(name: str, namespace: str, spec: Dict[str, Any], owner: Dict[str, Any], logger):
    claim = spec.get("persistentVolumeClaim")
    if not claim:
        return
    core_v1 = kubernetes.client.CoreV1Api()
    pvc = _build_persistent_volume_claim(name, namespace, claim)
    kopf.adopt(pvc, owner)

    if not _apply_enabled():
        logger.info(f"[{_mode_log_prefix()}] Would apply PersistentVolumeClaim {pvc['metadata']['name']}")
        return

    try:
        core_v1.create_namespaced_persistent_volume_claim(namespace=namespace, body=pvc)
        logger.info(f"Created PersistentVolumeClaim {pvc['metadata']['name']}")
    except kubernetes.client.exceptions.ApiException as exc:
        if exc.status != 409:
            raise
        core_v1.patch_namespaced_persistent_volume_claim(
            name=pvc["metadata"]["name"],
            namespace=namespace,
            body=pvc,
        )
        logger.info(f"Patched PersistentVolumeClaim {pvc['metadata']['name']}")


def apply_horizontal_pod_autoscaler(name: str, namespace: str, spec: Dict[str, Any], owner: Dict[str, Any], logger):
    autoscaling = spec.get("autoscaling", {})
    if not autoscaling.get("enabled"):
        return
    autoscaling_v2 = kubernetes.client.AutoscalingV2Api()
    hpa = _build_hpa_body(name, namespace, autoscaling)
    kopf.adopt(hpa, owner)

    if not _apply_enabled():
        logger.info(f"[{_mode_log_prefix()}] Would apply HorizontalPodAutoscaler {name}")
        return

    try:
        autoscaling_v2.create_namespaced_horizontal_pod_autoscaler(namespace=namespace, body=hpa)
        logger.info(f"Created HorizontalPodAutoscaler {name}")
    except kubernetes.client.exceptions.ApiException as exc:
        if exc.status != 409:
            raise
        autoscaling_v2.patch_namespaced_horizontal_pod_autoscaler(name=name, namespace=namespace, body=hpa)
        logger.info(f"Patched HorizontalPodAutoscaler {name}")


def _resource_status_message(base: str, spec: Dict[str, Any]) -> str:
    resources = ["deployment"]
    if spec.get("service", {}).get("enabled", True):
        resources.append("service")
    if spec.get("persistentVolumeClaim"):
        resources.append("persistent_volume_claim")
    if spec.get("autoscaling", {}).get("enabled"):
        resources.append("horizontal_pod_autoscaler")
    return f"{base}: {', '.join(resources)}"


@kopf.on.create("llm.stack.local", "v1", "llmworkers")
@kopf.on.update("llm.stack.local", "v1", "llmworkers")
def reconcile_worker(spec, name, namespace, body, logger, **kwargs):
    logger.info(f"Reconciling LLMWorker {name} with Agentic Self-Healing")

    # Agentic Health Check (Semantic sanity)
    # In a real scenario, this would query Prometheus/Metrics for agent error rates
    semantic_health = spec.get("healthThreshold", 0.95)
    
    try:
        worker_spec = deepcopy(spec)
        # Injection of self-healing environment variables
        worker_spec["env"] = _merge_env(_ensure_list(worker_spec.get("env")), [
            {"name": "AGENT_SELF_HEALING_ENABLED", "value": "true"},
            {"name": "AGENT_HEALTH_THRESHOLD", "value": str(semantic_health)},
        ])

        apply_persistent_volume_claim(name, namespace, worker_spec, body, logger)
        apply_deployment(name, namespace, worker_spec, body, logger)
        apply_horizontal_pod_autoscaler(name, namespace, worker_spec, body, logger)
        update_status(
            name,
            namespace,
            "llmworkers",
            [{"type": "Ready", "status": "True", "reason": "Success", "message": _resource_status_message("Worker deployment reconciled", worker_spec)}],
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
        control_plane_spec = deepcopy(spec)
        apply_persistent_volume_claim(f"{name}-cp", namespace, control_plane_spec, body, logger)
        apply_deployment(f"{name}-cp", namespace, control_plane_spec, body, logger)
        if control_plane_spec.get("service", {}).get("enabled", True):
            apply_service(f"{name}-cp", namespace, control_plane_spec, body, logger)
        apply_horizontal_pod_autoscaler(f"{name}-cp", namespace, control_plane_spec, body, logger)
        update_status(
            name,
            namespace,
            "llminferencestacks",
            [{"type": "Ready", "status": "True", "reason": "Success", "message": _resource_status_message("All resources reconciled", control_plane_spec)}],
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
        runtime_spec = deepcopy(spec)
        apply_persistent_volume_claim(name, namespace, runtime_spec, body, logger)
        apply_deployment(name, namespace, runtime_spec, body, logger)
        if runtime_spec.get("service", {}).get("enabled", False):
            apply_service(name, namespace, runtime_spec, body, logger)
        apply_horizontal_pod_autoscaler(name, namespace, runtime_spec, body, logger)
        update_status(
            name,
            namespace,
            "llmmodelruntimes",
            [{"type": "Ready", "status": "True", "reason": "Success", "message": _resource_status_message("Runtime deployment reconciled", runtime_spec)}],
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
