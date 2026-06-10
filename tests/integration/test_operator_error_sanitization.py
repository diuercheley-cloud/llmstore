import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
LIB_PATH = ROOT_DIR / "scripts" / "lib" / "operator-errors.sh"

def test_mask_sensitive():
    # secrets need to be long enough for redaction.sh regex
    api_key_secret = "sk-" + "1234567890abcdef" + "1234567890abcdef"
    admin_token_secret = "my-token-" + "long-enough-123"
    test_cases = [
        (f"api-key={api_key_secret}", "[REDACTED]"),
        (f"X-Admin-Token: {admin_token_secret}", "[REDACTED]"),
    ]
    
    for input_str, expected_part in test_cases:
        cmd = f"source {LIB_PATH} && mask_sensitive '{input_str}'"
        res = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
        # We check if the sensitive value is GONE
        assert "[REDACTED]" in res.stdout or "********" in res.stdout
        assert "1234567890abcdef" not in res.stdout

def test_no_secrets_in_operator_error():
    # Simulate an error with a secret in details
    secret = "sk-" + "deadbeef1234567890" + "abcdef1234567890"
    # We must ensure mask_sensitive is evaluated BEFORE passing to operator_error in bash
    cmd = f"source {LIB_PATH} && msg=$(mask_sensitive 'key={secret}') && operator_error 'CODE' 'msg' 'rem' \"$msg\""
    res = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
    assert secret not in res.stdout
    assert "[REDACTED]" in res.stdout or "********" in res.stdout
