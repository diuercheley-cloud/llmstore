import subprocess
from pathlib import Path

def test_restore_dry_run():
    """
    Validates that --dry-run works and does not attempt to restore.
    """
    root_dir = Path(__file__).resolve().parents[1]
    restore_script = root_dir / "scripts" / "restore-local.sh"
    backup_script = root_dir / "scripts" / "backup-local.sh"
    
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a "fake" backup first (or a real one if possible)
        subprocess.run([str(backup_script), tmp_dir], capture_output=True, cwd=str(root_dir))
        
        # Now run restore with --dry-run
        result = subprocess.run(
            [str(restore_script), "--dry-run", tmp_dir],
            capture_output=True,
            text=True,
            cwd=str(root_dir)
        )
        
        assert "modo dry-run: validacao concluida com sucesso" in result.stdout
        assert result.returncode == 0

def test_restore_requires_confirmation():
    """
    Ensures that restore script doesn't proceed without --yes or interactive input.
    """
    root_dir = Path(__file__).resolve().parents[1]
    restore_script = root_dir / "scripts" / "restore-local.sh"
    backup_script = root_dir / "scripts" / "backup-local.sh"

    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        subprocess.run([str(backup_script), tmp_dir], capture_output=True, cwd=str(root_dir))
        
        # Run restore without --yes and with closed stdin
        result = subprocess.run(
            [str(restore_script), tmp_dir],
            capture_output=True,
            text=True,
            cwd=str(root_dir),
            input="", # empty input to simulate non-interactive or immediate failure
        )
        
        # It should either fail or wait for input. 
        # Since we gave empty input, it might fail or exit if it sees EOF.
        # Based on my change: if ! [[ "${response}" =~ ^[Yy]$ ]]; then exit 0; fi
        # Empty input will not match [Yy], so it should say "abortado pelo usuario".
        assert "abortado pelo usuario" in result.stdout or result.returncode != 0
