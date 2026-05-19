import os
import yaml
import pytest

def test_kubernetes_manifests_valid_yaml():
    manifest_dir = "deploy/kubernetes"
    for filename in os.listdir(manifest_dir):
        if filename.endswith(".yaml"):
            with open(os.path.join(manifest_dir, filename), 'r') as f:
                try:
                    docs = yaml.safe_load_all(f)
                    for doc in docs:
                        assert doc is not None
                except yaml.YAMLError as exc:
                    pytest.fail(f"YAML error in {filename}: {exc}")

def test_crds_valid_yaml():
    with open("deploy/kubernetes/crds.yaml", 'r') as f:
        try:
            docs = yaml.safe_load_all(f)
            for doc in docs:
                assert doc['kind'] == "CustomResourceDefinition"
        except yaml.YAMLError as exc:
            pytest.fail(f"YAML error in crds.yaml: {exc}")
