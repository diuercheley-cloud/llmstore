import subprocess
import os
import pytest
from pathlib import Path

def test_script_exists():
    assert os.path.isfile("scripts/check-secrets.sh")
    assert os.access("scripts/check-secrets.sh", os.X_OK)

def test_hook_exists():
    assert os.path.isfile(".githooks/pre-commit")
    assert os.access(".githooks/pre-commit", os.X_OK)

def test_detects_secret(tmp_path):
    cwd = os.getcwd()
    script_path = os.path.abspath("scripts/check-secrets.sh")
    try:
        os.chdir(tmp_path)
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True)
        
        f = tmp_path / "dirty.txt"
        secret_val = "sk-abcdefghijklmnopqrstuvwxyz123456"
        f.write_text(f"Key is {secret_val}")
        subprocess.run(["git", "add", "dirty.txt"], check=True)
        
        result = subprocess.run([script_path, "--all"], capture_output=True, text=True)
        assert result.returncode != 0
        assert "Potential secret in dirty.txt" in result.stdout
        # Check masking: sk-a****3456 or similar
        assert "sk-a****3456" in result.stdout or "sk-a" in result.stdout
        assert secret_val not in result.stdout # Should be masked
        
    finally:
        os.chdir(cwd)

def test_allows_safe_patterns(tmp_path):
    cwd = os.getcwd()
    script_path = os.path.abspath("scripts/check-secrets.sh")
    try:
        os.chdir(tmp_path)
        subprocess.run(["git", "init"], check=True, capture_output=True)
        
        f = tmp_path / "safe.txt"
        f.write_text("ADMIN_TOKEN=admin-token-123\nMY_KEY=sk-local-example\nURL=http://user:changeme@localhost:8080")
        subprocess.run(["git", "add", "safe.txt"], check=True)
        
        result = subprocess.run([script_path, "--all"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "No secrets found" in result.stdout
        
    finally:
        os.chdir(cwd)

def test_detects_pem_file(tmp_path):
    cwd = os.getcwd()
    script_path = os.path.abspath("scripts/check-secrets.sh")
    try:
        os.chdir(tmp_path)
        subprocess.run(["git", "init"], check=True, capture_output=True)
        
        f = tmp_path / "cert.pem"
        f.write_text("fake pem content")
        subprocess.run(["git", "add", "cert.pem"], check=True)
        
        result = subprocess.run([script_path, "--all"], capture_output=True, text=True)
        assert result.returncode != 0
        assert "Potential secret file found by extension: cert.pem" in result.stdout
        
    finally:
        os.chdir(cwd)

def test_staged_mode(tmp_path):
    cwd = os.getcwd()
    script_path = os.path.abspath("scripts/check-secrets.sh")
    try:
        os.chdir(tmp_path)
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True)
        
        # Create a secret but don't stage it
        f1 = tmp_path / "unstaged.txt"
        f1.write_text("ADMIN_TOKEN=very-secret-token-12345")
        
        # Create another secret and stage it
        f2 = tmp_path / "staged.txt"
        f2.write_text("JWT_SECRET=another-secret-token-67890")
        subprocess.run(["git", "add", "staged.txt"], check=True)
        
        # Run with --staged
        result = subprocess.run([script_path, "--staged"], capture_output=True, text=True)
        assert result.returncode != 0
        assert "staged.txt" in result.stdout
        assert "unstaged.txt" not in result.stdout
        
    finally:
        os.chdir(cwd)
