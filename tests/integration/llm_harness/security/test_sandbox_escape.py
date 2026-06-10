import os
import shutil
import tempfile

from scripts.llm_harness.policy import PolicyEngine
from scripts.llm_harness.sanitizer import Sanitizer


def test_symlink_escape_detection():
    """Verify that PolicyEngine detects and blocks attempts to resolve symlinks pointing outside the workspace."""
    engine = PolicyEngine()
    
    # Setup temporary directory structure representing the workspace and a secret external dir
    temp_dir = tempfile.mkdtemp()
    try:
        workspace_root = os.path.join(temp_dir, "workspace")
        os.makedirs(workspace_root)
        
        # Secret external file
        external_secret_file = os.path.join(temp_dir, "secret.txt")
        with open(external_secret_file, "w") as f:
            f.write("top-secret-credentials")
            
        # Create a symlink pointing to the external file inside the workspace
        symlink_path = os.path.join(workspace_root, "link_to_secret.txt")
        os.symlink(external_secret_file, symlink_path)
        
        # PolicyEngine checks raw paths using _is_within_workspace on resolved paths.
        # Let's verify that resolving the symlink points outside the workspace
        # and therefore evaluates to False on is_within_workspace.
        assert not engine._is_within_workspace("link_to_secret.txt", workspace_root=workspace_root)
        
    finally:
        shutil.rmtree(temp_dir)

def test_secrets_redacted_in_logs():
    """Verify that secret patterns are redacted in log and trace outputs."""
    raw_log = "API request failed with header Authorization: Bearer sk-1234567890abcdef"
    sanitized = Sanitizer.sanitize_text(raw_log)
    
    assert "sk-1234567890abcdef" not in sanitized
    assert "[REDACTED]" in sanitized
