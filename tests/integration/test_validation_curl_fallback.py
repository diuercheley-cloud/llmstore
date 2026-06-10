import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_validate_localhost_mode_uses_curl_base_url():
    content = (ROOT / "scripts" / "validate-localhost-mode.sh").read_text(encoding="utf-8")
    assert 'curl_base_url "${BASE_URL}/health"' in content
    assert 'curl_base_url "$BASE_URL/v1/models"' in content


def test_common_curl_base_url_reports_container_fallback_mode():
    command = """
source scripts/dev/common.sh
curl() { return 7; }
dc() {
  if [[ "$1" == "exec" ]]; then
    return 0
  fi
  return 1
}
HOST_PORT=18080
curl_base_url "http://localhost:18080/health" -fsS >/dev/null
printf '%s' "${CURL_BASE_URL_LAST_MODE}"
"""
    result = subprocess.run(
        ["bash", "-lc", command],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout == "container"
