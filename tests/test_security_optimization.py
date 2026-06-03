import pytest
import time
from scripts.llm_harness._security import SecurityManager

def test_sanitization_performance():
    large_content = "some text " * 10000 + "<script>bad</script>"
    start = time.time()
    SecurityManager.sanitize_output(large_content)
    duration = time.time() - start
    assert duration < 0.1 # Should be fast
