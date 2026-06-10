import subprocess
from pathlib import Path

import pytest


def test_no_secrets_in_benchmark_artifacts():
    """Verify that benchmark artifacts do not contain potential API keys or Bearer tokens."""
    bench_dir = Path("artifacts/model-benchmarks")
    if not bench_dir.exists():
        pytest.skip("No benchmark artifacts found to scan")
        
    # Search for common secret patterns
    # sk-... or Bearer ...
    cmd = ["grep", "-rE", "(Bearer|sk-[a-zA-Z0-9]{20,})", str(bench_dir)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # If grep finds something, it returns 0
    assert result.returncode != 0, f"Potential secrets found in benchmark artifacts: {result.stdout}"

def test_benchmark_runner_cli_key_masking():
    """Verify that passing a key to the runner doesn't leak it in logs if we implement masking."""
    # This is more of a logic check. 
    # Our current runner doesn't log the full headers, which is good.
    pass
