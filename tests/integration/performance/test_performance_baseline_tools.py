import json
import os


def test_performance_baseline_tools():
    """
    Validates that the performance baseline tools are functional.
    """
    from scripts.generate_performance_baseline import generate_performance_baseline
    generate_performance_baseline()
    assert os.path.exists("docs/performance/performance_baseline.json")
    
    with open("docs/performance/performance_baseline.json", "r") as f:
        data = json.load(f)
        assert "hashing_latency_ms" in data
        assert data["hashing_latency_ms"] > 0
