import os
import platform


def get_platform() -> str:
    """
    Returns the current platform name.
    Possible values: 'linux', 'macos', 'windows', 'wsl'
    """
    system = platform.system().lower()
    if system == "linux":
        # Check for WSL
        release = platform.release().lower()
        is_wsl_env = "wsl" in os.environ.get("IS_WSL", "").lower()
        if "microsoft" in release or is_wsl_env:
            return "wsl"
        try:
            with open("/proc/version") as f:
                if "microsoft" in f.read().lower():
                    return "wsl"
        except FileNotFoundError:
            pass
        return "linux"
    elif system == "darwin":
        return "macos"
    elif system == "windows":
        return "windows"
    return "unknown"


def is_windows() -> bool:
    return get_platform() == "windows"


def is_linux() -> bool:
    return get_platform() in ("linux", "wsl")


def is_macos() -> bool:
    return get_platform() == "macos"


def is_unix() -> bool:
    return is_linux() or is_macos()


def get_supported_signals() -> list[str]:
    """
    Returns a list of supported signals for the current platform.
    """
    import signal

    if is_windows():
        return ["SIGINT", "SIGTERM", "SIGABRT", "SIGILL", "SIGFPE", "SIGSEGV"]
    return [s for s in dir(signal) if s.startswith("SIG") and not s.startswith("SIG_")]
