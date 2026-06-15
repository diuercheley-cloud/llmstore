import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

HTML_FILE = ROOT / "control_plane" / "app" / "static" / "www" / "capabilities.html"
PUBLIC_PY = ROOT / "control_plane" / "app" / "api" / "public.py"


def test_no_real_api_keys():
    for filepath in [HTML_FILE, PUBLIC_PY]:
        content = filepath.read_text()
        patterns = [
            (r"sk-[a-zA-Z0-9]{20,}", "sk- key"),
            (r"ADMIN_TOKEN=[a-zA-Z0-9._-]{12,}", "ADMIN_TOKEN"),
            (r"Bearer [a-zA-Z0-9._-]{20,}", "Bearer token"),
        ]
        for pattern, label in patterns:
            matches = re.findall(pattern, content)
            for m in matches:
                safe = any(
                    marker in m
                    for marker in [
                        "masked",
                        "example",
                        "test",
                        "changeme",
                        "sk-demo-xxxx",
                        "sk-example",
                        "admin-token-123",
                        "test-admin-token",
                        "sk-demo",
                        "xxxx",
                    ]
                )
                if not safe:
                    assert False, f"Potential real {label}: {m[:50]}"


def test_no_sensitive_paths_in_html():
    content = HTML_FILE.read_text()
    for bad in ["/home/", "/root/", "/var/", "/etc/", "/models/", "/data/"]:
        assert bad not in content, f"Sensitive path leaked: {bad}"


def test_no_database_urls():
    for filepath in [HTML_FILE, PUBLIC_PY]:
        content = filepath.read_text()
        assert "postgresql://" not in content, "Database URL leaked"
        assert "redis://" not in content, "Redis URL leaked"


def test_no_private_keys():
    for filepath in [HTML_FILE, PUBLIC_PY]:
        content = filepath.read_text()
        assert "PRIVATE KEY" not in content, "Private key marker found"


def test_psp_pix_not_promised_as_real():
    content = HTML_FILE.read_text()
    lines_with_psp = [l for l in content.split("\n") if "PSP" in l.upper() or "PIX" in l.upper()]
    for line in lines_with_psp:
        line_lower = line.lower()
        assert any(
            word in line_lower
            for word in ["nao", "não", "not", "sem", "desabilitado", "mock", "offline", "future"]
        ), f"PSP/PIX may be falsely promised: {line.strip()}"


def test_tools_not_promised():
    content = HTML_FILE.read_text()
    assert (
        "Parcial" in content
        or "Nao suportado" in content
        or "partial" in content.lower()
        or "unsupported" in content.lower()
    )


def test_no_absolute_security_guarantee():
    content = HTML_FILE.read_text()
    phrases = [
        "seguranca absoluta",
        "nao prometemos",
    ]
    found = any(p in content.lower() for p in phrases)
    assert found, "No disclaimer about no absolute security guarantee"


def test_https_not_promised():
    content = HTML_FILE.read_text()
    assert "opcional" in content.lower() or "optional" in content.lower()


def test_fictional_data_disclaimer():
    content = HTML_FILE.read_text()
    assert "ficticios" in content.lower() or "fictícios" in content.lower()


def test_no_raw_env_vars():
    for filepath in [HTML_FILE, PUBLIC_PY]:
        content = filepath.read_text()
        dangerous = [
            "POSTGRES_PASSWORD",
            "DATABASE_URL",
            "REDIS_URL",
            "JWT_SECRET",
            "SECRET_KEY",
        ]
        for env_var in dangerous:
            assert env_var not in content, f"Env var name leaked: {env_var}"
