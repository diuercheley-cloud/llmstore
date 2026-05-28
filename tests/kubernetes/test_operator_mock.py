import kopf
import pytest
import unittest.mock as mock
from importlib.util import spec_from_file_location, module_from_spec

def load_operator_main():
    spec = spec_from_file_location("operator_main", "operator/main.py")
    m = module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

operator_main = load_operator_main()

def test_operator_handlers_exist():
    # Check if handlers are defined for our CRDs
    assert operator_main.reconcile_inference_stack is not None
    assert operator_main.reconcile_model_runtime is not None
    assert operator_main.reconcile_provider is not None
    assert operator_main.reconcile_tenant is not None

def test_operator_reconcile_inference_stack_mock():
    class MockLogger:
        def info(self, msg): pass
        def error(self, msg): pass
    
    spec = {'image': 'test-image', 'replicas': 2}
    body = {'metadata': {'name': 'test-stack', 'namespace': 'default'}}
    
    # Mocking Kubernetes API calls inside the function
    with mock.patch('kubernetes.client.AppsV1Api'), \
         mock.patch('kubernetes.client.CoreV1Api'), \
         mock.patch('kubernetes.client.CustomObjectsApi'):
        
        # This shouldn't raise exception now
        operator_main.reconcile_inference_stack(spec=spec, name='test-stack', namespace='default', body=body, logger=MockLogger())
