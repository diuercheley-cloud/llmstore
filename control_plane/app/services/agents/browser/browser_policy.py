# Owner: agent-platform
import ipaddress
import socket
from urllib.parse import urlparse

from app.core.config import get_settings


def check_browser_url_policy(url: str, *, check_feature_flags: bool = True) -> None:
    settings = get_settings()

    # Check if tool is enabled
    if check_feature_flags and not getattr(settings, "agent_browser_tool_enabled", False):
        raise ValueError("Browser tool is disabled by feature flag.")

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https", "mock", "test"}:
        raise ValueError(f"URL scheme '{parsed.scheme}' is not allowed.")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: no hostname found.")

    hostname_lower = hostname.lower()
    is_mock = (
        parsed.scheme in ("mock", "test")
        or hostname_lower.endswith(".test")
        or hostname_lower == "mock"
    )
    if is_mock:
        return

    # Hostnames and every resolved address must be globally routable.
    blocked_hosts = {"localhost", "metadata.google.internal"}
    if hostname_lower in blocked_hosts or hostname_lower.endswith(".localhost"):
        raise ValueError(f"Access to internal host '{hostname}' is blocked.")

    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(hostname, None)}
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve URL hostname '{hostname}'.") from exc

    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError(f"Access to internal IP '{ip}' is blocked.")

    # Check external network flag
    is_external_enabled = getattr(settings, "agent_browser_external_network_enabled", False)
    if check_feature_flags and not is_mock and not is_external_enabled:
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
