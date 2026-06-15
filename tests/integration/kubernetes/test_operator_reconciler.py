import unittest.mock as mock
from importlib.util import module_from_spec, spec_from_file_location

import pytest


def load_operator_main():
    spec = spec_from_file_location("operator_main", "operator/main.py")
    m = module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


operator_main = load_operator_main()
reconcile_inference_stack = operator_main.reconcile_inference_stack
reconcile_provider = operator_main.reconcile_provider
reconcile_model_runtime = operator_main.reconcile_model_runtime


@pytest.fixture
def logger():
    return mock.Mock()


@pytest.fixture
def k8s_apps_v1():
    with mock.patch("kubernetes.client.AppsV1Api") as m:
        yield m.return_value


@pytest.fixture
def k8s_core_v1():
    with mock.patch("kubernetes.client.CoreV1Api") as m:
        yield m.return_value


@pytest.fixture
def k8s_autoscaling_v2():
    with mock.patch("kubernetes.client.AutoscalingV2Api") as m:
        yield m.return_value


@pytest.fixture
def k8s_custom_objects():
    with mock.patch("kubernetes.client.CustomObjectsApi") as m:
        yield m.return_value


def test_reconcile_inference_stack_creates_resources(
    k8s_apps_v1, k8s_core_v1, k8s_autoscaling_v2, k8s_custom_objects, logger
):
    spec = {
        "image": "control-plane:v1",
        "replicas": 3,
        "service": {"enabled": True, "type": "ClusterIP", "port": 8080},
        "autoscaling": {
            "enabled": True,
            "minReplicas": 2,
            "maxReplicas": 5,
            "targetCPUUtilizationPercentage": 75,
        },
        "persistentVolumeClaim": {"name": "cp-data", "size": "50Gi", "mountPath": "/var/lib/stack"},
    }
    body = {"metadata": {"name": "test-stack", "namespace": "default"}}

    reconcile_inference_stack(spec, "test-stack", "default", body, logger)

    # Check Deployment creation
    k8s_apps_v1.create_namespaced_deployment.assert_called_once()
    args, kwargs = k8s_apps_v1.create_namespaced_deployment.call_args
    assert kwargs["body"]["spec"]["replicas"] == 3
    assert (
        kwargs["body"]["spec"]["template"]["spec"]["containers"][0]["image"] == "control-plane:v1"
    )
    assert (
        kwargs["body"]["spec"]["template"]["spec"]["containers"][0]["readinessProbe"]["httpGet"][
            "path"
        ]
        == "/healthz"
    )
    assert (
        kwargs["body"]["spec"]["template"]["spec"]["volumes"][0]["persistentVolumeClaim"][
            "claimName"
        ]
        == "cp-data"
    )

    # Check Service creation
    k8s_core_v1.create_namespaced_service.assert_called_once()
    k8s_core_v1.create_namespaced_persistent_volume_claim.assert_called_once()
    k8s_autoscaling_v2.create_namespaced_horizontal_pod_autoscaler.assert_called_once()

    # Check status update
    k8s_custom_objects.patch_namespaced_custom_object_status.assert_called_once()
    status_args = k8s_custom_objects.patch_namespaced_custom_object_status.call_args[0]
    assert status_args[5]["status"]["conditions"][0]["type"] == "Ready"


def test_reconcile_provider_missing_secret(k8s_custom_objects, logger):
    spec = {"type": "openai"}  # missing apiKeySecretRef

    reconcile_provider(spec, "test-provider", "default", logger)

    # Check status update to Degraded
    k8s_custom_objects.patch_namespaced_custom_object_status.assert_called_once()
    status_args = k8s_custom_objects.patch_namespaced_custom_object_status.call_args[0]
    assert status_args[5]["status"]["conditions"][0]["type"] == "Degraded"
    assert "apiKeySecretRef is required" in status_args[5]["status"]["conditions"][0]["message"]


def test_reconcile_model_runtime_gpu(k8s_apps_v1, k8s_custom_objects, logger):
    spec = {"image": "vllm:latest", "gpu": {"enabled": True, "count": 2}}
    body = {"metadata": {"name": "gpu-runtime", "namespace": "default"}}

    reconcile_model_runtime(spec, "gpu-runtime", "default", body, logger)

    # Check GPU limits
    args, kwargs = k8s_apps_v1.create_namespaced_deployment.call_args
    resources = kwargs["body"]["spec"]["template"]["spec"]["containers"][0]["resources"]
    assert resources["limits"]["nvidia.com/gpu"] == 2


def test_dry_run_mode(k8s_apps_v1, logger):
    with mock.patch.object(operator_main, "DRY_RUN", True):
        spec = {"image": "test"}
        body = {"metadata": {"name": "test", "namespace": "default"}}
        reconcile_model_runtime(spec, "test", "default", body, logger)

        # Should NOT call Kubernetes API
        k8s_apps_v1.create_namespaced_deployment.assert_not_called()
        logger.info.assert_any_call("[DRY-RUN] Would apply Deployment test")
