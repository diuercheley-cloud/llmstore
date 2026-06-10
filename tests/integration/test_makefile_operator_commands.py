import subprocess
from pathlib import Path


def run_make(target, env=None, extra_args=None):
    cmd = ["make", target]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(cmd, capture_output=True, text=True, env=env)

def test_makefile_exists():
    assert Path("Makefile").exists()

def test_make_help():
    result = run_make("help")
    assert result.returncode == 0
    assert "LLM Inference Stack - Operator Commands" in result.stdout
    assert "first-run" in result.stdout
    assert "up" in result.stdout
    assert "down" in result.stdout
    assert "status" in result.stdout
    assert "health" in result.stdout
    assert "validate" in result.stdout
    assert "demo" in result.stdout
    assert "security" in result.stdout
    assert "readiness" in result.stdout
    assert "release" in result.stdout
    assert "backup" in result.stdout
    assert "restore" in result.stdout
    assert "upgrade" in result.stdout
    assert "rollback" in result.stdout
    assert "benchmark" in result.stdout
    assert "smoke" in result.stdout
    assert "clean-safe" in result.stdout

def test_mandatory_targets_exist():
    # Parse Makefile to find all targets
    with open("Makefile", "r") as f:
        content = f.read()
    
    mandatory_targets = [
        "help", "first-run", "up", "down", "restart", "status", "health",
        "validate", "demo", "security", "readiness", "release", "backup",
        "restore", "upgrade", "rollback", "benchmark", "smoke", "clean-safe"
    ]
    
    for target in mandatory_targets:
        assert f"{target}:" in content

def test_restore_requires_backup_dir():
    # Should fail without BACKUP_DIR
    result = run_make("restore")
    assert result.returncode != 0
    assert "Usage: make restore BACKUP_DIR=/path/to/backup" in result.stdout

def test_operator_docs_exist():
    assert Path("docs/OPERATOR_COMMANDS.md").exists()
    with open("docs/OPERATOR_COMMANDS.md", "r") as f:
        content = f.read()
    assert "# Guia de Comandos do Operador" in content
    assert "make first-run" in content
    assert "make restore" in content

def test_targets_call_scripts():
    with open("Makefile", "r") as f:
        lines = f.readlines()
    
    mappings = {
        "first-run:": "./scripts/deploy/first-run-local.sh --with-demo",
        "up:": "./scripts/deploy/up.sh",
        "down:": "./scripts/deploy/down.sh",
        "health:": "./scripts/dev/test-health.sh",
        "validate-full:": "./scripts/validators/validate-local-production-full.sh",
        "demo:": "./scripts/dev/demo-full-local.sh --no-build",
        "security:": "./scripts/validators/security-report-local.sh",
        "readiness:": "./scripts/dev/production-readiness-local.sh",
        "backup:": "./scripts/backup/backup-local.sh",
        "restore:": "./scripts/backup/restore-local.sh $(BACKUP_DIR)",
        "upgrade:": "./scripts/deploy/upgrade-local.sh",
        "rollback:": "./scripts/dev/rollback-local.sh",
        "benchmark:": "./scripts/dev/benchmark-model-local.sh --quick",
        "smoke:": "./scripts/validators/post-upgrade-smoke-local.sh",
        "clean-safe:": "./scripts/backup/retention-local.sh --dry-run --section all"
    }
    
    for target, script in mappings.items():
        found = False
        in_target = False
        for line in lines:
            if line.startswith(target):
                in_target = True
                continue
            if in_target:
                if line.startswith(("\t", " ")): # Command line
                    if script in line:
                        found = True
                        break
                elif line.strip() == "" or ":" in line: # Next target or empty line
                    break
        assert found, f"Target {target} does not seem to call expected script {script}"
