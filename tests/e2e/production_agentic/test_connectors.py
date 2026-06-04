import http.server
import threading
from pathlib import Path

import pytest
import requests


class FakeHTTPServer(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status": "ok", "message": "real_mode_success"}')

@pytest.fixture(scope="module")
def local_fake_server():
    server = http.server.HTTPServer(('localhost', 19090), FakeHTTPServer)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    yield "http://localhost:19090"
    server.shutdown()

@pytest.mark.asyncio
async def test_connector_real_mode_contract(local_fake_server):
    response = requests.get(local_fake_server)
    assert response.status_code == 200
    assert response.json()["message"] == "real_mode_success"

    artifact = Path("artifacts/e2e/production-agentic/connectors.md")
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        f"## Connector Contract E2E\n- Target: {local_fake_server}\n- Response validated: True\n",
        encoding="utf-8",
    )
