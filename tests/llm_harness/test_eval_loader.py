import json

import pytest
import yaml

from scripts.llm_harness.evals.loader import EvalLoader, EvalSchemaError


def test_eval_loader_json(tmp_path):
    suite_file = tmp_path / "suite.json"
    data = {
        "name": "Test Suite",
        "cases": [
            {"id": "case1", "task": "task1"}
        ]
    }
    suite_file.write_text(json.dumps(data))
    
    suite = EvalLoader.load(str(suite_file))
    assert suite.name == "Test Suite"
    assert len(suite.cases) == 1
    assert suite.cases[0].id == "case1"

def test_eval_loader_yaml(tmp_path):
    suite_file = tmp_path / "suite.yaml"
    data = {
        "name": "YAML Suite",
        "cases": [
            {"id": "y1", "task": "ytask"}
        ]
    }
    suite_file.write_text(yaml.dump(data))
    
    suite = EvalLoader.load(str(suite_file))
    assert suite.name == "YAML Suite"
    assert suite.cases[0].id == "y1"

def test_eval_loader_invalid_schema(tmp_path):
    suite_file = tmp_path / "invalid.json"
    data = {
        "name": "Invalid",
        "cases": [
            {"id": "c1"} # Missing task
        ]
    }
    suite_file.write_text(json.dumps(data))
    
    with pytest.raises(EvalSchemaError):
        EvalLoader.load(str(suite_file))

def test_eval_loader_backward_compat(tmp_path):
    suite_file = tmp_path / "old.json"
    data = {
        "name": "Old Suite",
        "test_cases": [
            {"name": "old_name", "input": "old_task"}
        ]
    }
    suite_file.write_text(json.dumps(data))
    
    suite = EvalLoader.load(str(suite_file))
    assert suite.name == "Old Suite"
    assert len(suite.cases) == 1
    assert suite.cases[0].id == "old_name"
    assert suite.cases[0].task == "old_task"
