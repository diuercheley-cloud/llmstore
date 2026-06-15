import socket
from unittest.mock import patch

import pytest
from app.services.agents.browser.browser_policy import check_browser_url_policy


@pytest.fixture(autouse=True)
def enable_external_browser(monkeypatch):
    settings = type(
        "Settings",
        (),
        {
            "agent_browser_tool_enabled": True,
            "agent_browser_external_network_enabled": True,
            "agent_browser_allowlist": "",
        },
    )()
    monkeypatch.setattr("app.services.agents.browser.browser_policy.get_settings", lambda: settings)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "http://10.0.0.1/",
        "http://192.168.1.1/",
        "http://[::1]/",
        "file:///etc/passwd",
    ],
)
def test_browser_policy_blocks_internal_and_unsafe_urls(url):
    with pytest.raises(ValueError):
        check_browser_url_policy(url)


def test_browser_policy_blocks_dns_resolving_to_private_ip():
    private_result = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.1.2.3", 0))]
    with patch("socket.getaddrinfo", return_value=private_result):
        with pytest.raises(ValueError, match="internal IP"):
            check_browser_url_policy("https://attacker.example/")


def test_browser_policy_allows_globally_routable_ip():
    public_result = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
    with patch("socket.getaddrinfo", return_value=public_result):
        check_browser_url_policy("https://example.com/")
