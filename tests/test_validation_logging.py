import os
import subprocess
import pytest

HELPER_PATH = "scripts/lib/validation-logging.sh"

def test_helper_exists():
    assert os.path.exists(HELPER_PATH)

def test_mask_secrets():
    # Helper must mask secrets
    admin_token = "very-secret-token-123"
    api_key = "sk-ant-api03-abcdefghijklmnopqrstuvwxyz"
    bearer_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    
    cmd = f"""
    export ADMIN_TOKEN="{admin_token}"
    export API_KEY="{api_key}"
    source {HELPER_PATH}
    mask_secrets "Token is {admin_token}"
    mask_secrets "Key is {api_key}"
    mask_secrets "Header: {bearer_token}"
    mask_secrets "Generic key: sk-1234567890abcdef123456"
    """
    
    result = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, check=True)
    output = result.stdout
    
    assert admin_token not in output
    assert "[ADMIN_TOKEN_MASKED]" in output
    assert api_key not in output
    assert "[API_KEY_MASKED]" in output
    assert "sk-1234567890abcdef123456" not in output
    assert "sk-[MASKED]" in output
    assert bearer_token not in output
    assert "Bearer [MASKED]" in output

def test_log_functions():
    cmd = f"""
    source {HELPER_PATH}
    # Disable colors for easier testing if possible, or just strip them
    log_info "test info"
    log_ok "test ok"
    log_warn "test warn"
    log_error "test error"
    """
    
    result = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, check=True)
    output = result.stdout + result.stderr
    
    # Strip ANSI colors for validation
    import re
    clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output)
    
    assert "INFO: test info" in clean_output
    assert "OK: test ok" in clean_output
    assert "WARN: test warn" in clean_output
    assert "ERROR: test error" in clean_output

def test_timer():
    cmd = f"""
    source {HELPER_PATH}
    T=$(start_timer)
    sleep 0.1
    end_timer $T
    """
    
    result = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, check=True)
    duration_str = result.stdout.strip()
    # Should be something like 0.101s
    assert duration_str.endswith("s")
    duration = float(duration_str[:-1])
    assert 0.09 <= duration <= 0.5
