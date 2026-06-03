
from unittest.mock import patch

from scripts.llm_harness.platforms import get_platform, is_linux, is_macos, is_windows


def test_platform_detection():
    # Test current platform (monitored)
    p = get_platform()
    assert p in ("linux", "macos", "windows", "wsl")
    
    if p == "windows":
        assert is_windows() is True
        assert is_linux() is False
    elif p == "macos":
        assert is_macos() is True
        assert is_windows() is False
    elif p == "linux" or p == "wsl":
        assert is_linux() is True
        assert is_windows() is False

def test_platform_simulation():
    with patch("platform.system", return_value="Windows"):
        assert is_windows() is True
        assert is_linux() is False
        
    with patch("platform.system", return_value="Darwin"):
        assert is_macos() is True
        assert is_windows() is False
        
    with patch("platform.system", return_value="Linux"), \
         patch("platform.release", return_value="standard-kernel"):
        assert is_linux() is True
        # Ensure it's not detected as WSL if no microsoft in release
        with patch("os.environ.get", return_value=""):
            # We also need to mock /proc/version which might exist on the host
            with patch("builtins.open", side_effect=FileNotFoundError):
                assert get_platform() == "linux"

def test_supported_signals():
    from scripts.llm_harness.platforms import get_supported_signals
    signals = get_supported_signals()
    assert len(signals) > 0
    if is_windows():
        assert "SIGTERM" in signals
        assert "SIGKILL" not in signals # os.kill(pid, signal.SIGKILL) is not valid on Windows usually
    else:
        assert "SIGKILL" in signals
        assert "SIGUSR1" in signals or "SIGQUIT" in signals
