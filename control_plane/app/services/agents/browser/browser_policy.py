# Owner: agent-platform
import socket
from urllib.parse import urlparse

from app.core.config import get_settings


def check_browser_url_policy(url: str) -> None:
    settings = get_settings()
    
    # Check if tool is enabled
    if not getattr(settings, "agent_browser_tool_enabled", False):
        raise ValueError("Browser tool is disabled by feature flag.")
        
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: no hostname found.")
        
    hostname_lower = hostname.lower()
    
    # Block localhost / internal metadata
    blocked_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254"}
    if hostname_lower in blocked_hosts:
        raise ValueError(f"Access to internal host '{hostname}' is blocked.")
        
    try:
        ip = socket.gethostbyname(hostname)
        if ip in blocked_hosts or ip.startswith("127.") or ip.startswith("169.254."):
            raise ValueError(f"Access to internal IP '{ip}' is blocked.")
    except Exception:
        pass

    # Check external network flag
    is_external_enabled = getattr(settings, "agent_browser_external_network_enabled", False)
    is_mock = parsed.scheme in ("mock", "test") or hostname_lower.endswith(".test") or hostname_lower == "mock"
    
    if not is_mock and not is_external_enabled:
        raise ValueError("External network access is disabled for the browser tool.")
        
    # Check domain allowlist
    allowlist_raw = getattr(settings, "agent_browser_allowlist", "")
    if allowlist_raw:
        if isinstance(allowlist_raw, str):
            allowlist = [d.strip().lower() for d in allowlist_raw.split(",") if d.strip()]
        else:
            allowlist = [str(d).strip().lower() for d in allowlist_raw]
            
        matched = False
        for allowed in allowlist:
            if hostname_lower == allowed or hostname_lower.endswith("." + allowed):
                matched = True
                break
        if not matched and not is_mock:
            raise ValueError(f"Domain '{hostname}' is not in the browser allowlist.")
