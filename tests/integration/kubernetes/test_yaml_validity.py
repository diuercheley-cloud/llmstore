import os

import pytest
import yaml


def _get_manifest_dir():
    manifest_dir = "deploy/kubernetes"
    if not os.path.exists(manifest_dir):
        pytest.skip(
            f"Manifest directory {manifest_dir} not found, skipping.", allow_module_level=True
        )
    return manifest_dir


def test_kubernetes_manifests_valid_yaml():
    manifest_dir = _get_manifest_dir()
    for filename in os.listdir(manifest_dir):
        if filename.endswith(".yaml"):
            with open(os.path.join(manifest_dir, filename)) as f:
                try:
                    docs = yaml.safe_load_all(f)
                    for doc in docs:
                        assert doc is not None
                except yaml.YAMLError as exc:
                    pytest.fail(f"YAML error in {filename}: {exc}")


def test_crds_valid_yaml():
    manifest_dir = _get_manifest_dir()
    crd_path = os.path.join(manifest_dir, "crds.yaml")
    if not os.path.exists(crd_path):
        pytest.skip(f"CRD file {crd_path} not found, skipping.", allow_module_level=True)

    with open(crd_path) as f:
        try:
            docs = yaml.safe_load_all(f)
            for doc in docs:
                assert doc["kind"] == "CustomResourceDefinition"
        except yaml.YAMLError as exc:
            pytest.fail(f"YAML error in crds.yaml: {exc}")
