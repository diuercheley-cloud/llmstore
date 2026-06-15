from app.api.operations_admin import _sanitize_payload
from httpx import AsyncClient

SIGNAL_PAYLOAD = {
    "client_id": "test-client",
    "signal_type": "latency_spike",
    "source_domain": "runtime",
    "severity": "warning",
    "confidence": 0.75,
    "payload_json": {"latency_ms": 5000},
}


# ── POST /admin/operations/failure-signals ───────────────────────────────────


class TestCreateFailureSignal:
    def test_sanitize_payload_redacts_sensitive_keys(self):
        sanitized = _sanitize_payload({"api_key": "sk-123", "cpu": 95, "note": "x" * 600})
        assert sanitized == {
            "api_key": "<redacted>",
            "cpu": 95,
            "note": "x" * 500,
        }

    async def test_creates_signal(self, admin_client: AsyncClient, admin_token_headers: dict):
        r = await admin_client.post(
            "/admin/operations/failure-signals",
            json=SIGNAL_PAYLOAD,
            headers=admin_token_headers,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "signal" in data
        assert "receipt" in data
        assert data["signal"]["client_id"] == "test-client"
        assert data["signal"]["signal_type"] == "latency_spike"
        assert data["receipt"]["receipt_type"] == "failure_signal_recorded"
        assert data["receipt"]["advisory_only"] is True

    async def test_advisory_only_in_receipt(
        self, admin_client: AsyncClient, admin_token_headers: dict
    ):
        r = await admin_client.post(
            "/admin/operations/failure-signals",
            json=SIGNAL_PAYLOAD,
            headers=admin_token_headers,
        )
        assert r.status_code == 200
        assert r.json()["receipt"]["advisory_only"] is True

    async def test_rejects_missing_client_id(
        self, admin_client: AsyncClient, admin_token_headers: dict
    ):
        r = await admin_client.post(
            "/admin/operations/failure-signals",
            json={"signal_type": "cpu"},
            headers=admin_token_headers,
        )
        assert r.status_code == 422

    async def test_sanitizes_sensitive_payload(
        self, admin_client: AsyncClient, admin_token_headers: dict
    ):
        r = await admin_client.post(
            "/admin/operations/failure-signals",
            json={**SIGNAL_PAYLOAD, "payload_json": {"api_key": "sk-123", "cpu": 95}},
            headers=admin_token_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert "payload_json" not in data["signal"]


# ── GET /admin/operations/failure-signals ────────────────────────────────────


class TestListFailureSignals:
    async def test_lists_signals_by_client(
        self, admin_client: AsyncClient, admin_token_headers: dict
    ):
        await admin_client.post(
            "/admin/operations/failure-signals",
            json=SIGNAL_PAYLOAD,
            headers=admin_token_headers,
        )
        r = await admin_client.get(
            "/admin/operations/failure-signals",
            params={"client_id": "test-client"},
            headers=admin_token_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["client_id"] == "test-client"

    async def test_tenant_isolation(self, admin_client: AsyncClient, admin_token_headers: dict):
        await admin_client.post(
            "/admin/operations/failure-signals",
            json={**SIGNAL_PAYLOAD, "client_id": "client-a"},
            headers=admin_token_headers,
        )
        r = await admin_client.get(
            "/admin/operations/failure-signals",
            params={"client_id": "client-b"},
            headers=admin_token_headers,
        )
        assert r.status_code == 200
        assert r.json() == []

    async def test_requires_client_id(self, admin_client: AsyncClient, admin_token_headers: dict):
        r = await admin_client.get(
            "/admin/operations/failure-signals",
            headers=admin_token_headers,
        )
        assert r.status_code == 422

    async def test_respects_limit(self, admin_client: AsyncClient, admin_token_headers: dict):
        for i in range(3):
            await admin_client.post(
                "/admin/operations/failure-signals",
                json={**SIGNAL_PAYLOAD, "signal_type": f"type-{i}"},
                headers=admin_token_headers,
            )
        r = await admin_client.get(
            "/admin/operations/failure-signals",
            params={"client_id": "test-client", "limit": 2},
            headers=admin_token_headers,
        )
        assert len(r.json()) <= 2


# ── POST /admin/operations/failure-forecasts/run ────────────────────────────


class TestRunForecast:
    async def test_runs_forecast(self, admin_client: AsyncClient, admin_token_headers: dict):
        await admin_client.post(
            "/admin/operations/failure-signals",
            json=SIGNAL_PAYLOAD,
            headers=admin_token_headers,
        )
        r = await admin_client.post(
            "/admin/operations/failure-forecasts/run",
            params={"client_id": "test-client"},
            headers=admin_token_headers,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "forecast" in data
        assert "receipt" in data
        assert data["forecast"]["advisory_only"] is True
        assert data["forecast"]["risk_score"] >= 0
        assert data["receipt"]["receipt_type"] == "failure_forecast_created"

    async def test_forecast_contains_required_fields(
        self, admin_client: AsyncClient, admin_token_headers: dict
    ):
        await admin_client.post(
            "/admin/operations/failure-signals",
            json=SIGNAL_PAYLOAD,
            headers=admin_token_headers,
        )
        r = await admin_client.post(
            "/admin/operations/failure-forecasts/run",
            params={"client_id": "test-client"},
            headers=admin_token_headers,
        )
        f = r.json()["forecast"]
        assert "forecast_type" in f
        assert "risk_score" in f
        assert "confidence" in f
        assert "deterministic_version" in f
        assert "input_hash" in f
        assert "explanation" in f
        assert "advisory_only" in f

    async def test_deterministic(self, admin_client: AsyncClient, admin_token_headers: dict):
        await admin_client.post(
            "/admin/operations/failure-signals",
            json=SIGNAL_PAYLOAD,
            headers=admin_token_headers,
        )
        r1 = await admin_client.post(
            "/admin/operations/failure-forecasts/run",
            params={"client_id": "test-client"},
            headers=admin_token_headers,
        )
        r2 = await admin_client.post(
            "/admin/operations/failure-forecasts/run",
            params={"client_id": "test-client"},
            headers=admin_token_headers,
        )
        assert r1.json()["forecast"]["risk_score"] == r2.json()["forecast"]["risk_score"]
        assert r1.json()["forecast"]["input_hash"] == r2.json()["forecast"]["input_hash"]

    async def test_zero_risk_without_signals(
        self, admin_client: AsyncClient, admin_token_headers: dict
    ):
        r = await admin_client.post(
            "/admin/operations/failure-forecasts/run",
            params={"client_id": "no-signals"},
            headers=admin_token_headers,
        )
        assert r.status_code == 200
        assert r.json()["forecast"]["risk_score"] == 0.0

    async def test_window_minutes_param(self, admin_client: AsyncClient, admin_token_headers: dict):
        await admin_client.post(
            "/admin/operations/failure-signals",
            json=SIGNAL_PAYLOAD,
            headers=admin_token_headers,
        )
        r = await admin_client.post(
            "/admin/operations/failure-forecasts/run",
            params={"client_id": "test-client", "window_minutes": 30},
            headers=admin_token_headers,
        )
        assert r.status_code == 200


# ── GET /admin/operations/failure-forecasts ──────────────────────────────────


class TestListForecasts:
    async def test_lists_forecasts(self, admin_client: AsyncClient, admin_token_headers: dict):
        await admin_client.post(
            "/admin/operations/failure-signals",
            json=SIGNAL_PAYLOAD,
            headers=admin_token_headers,
        )
        await admin_client.post(
            "/admin/operations/failure-forecasts/run",
            params={"client_id": "test-client"},
            headers=admin_token_headers,
        )
        r = await admin_client.get(
            "/admin/operations/failure-forecasts",
            params={"client_id": "test-client"},
            headers=admin_token_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_tenant_isolation(self, admin_client: AsyncClient, admin_token_headers: dict):
        r = await admin_client.get(
            "/admin/operations/failure-forecasts",
            params={"client_id": "isolated"},
            headers=admin_token_headers,
        )
        assert r.status_code == 200
        assert r.json() == []


# ── POST /admin/operations/failure-risk-assessments ─────────────────────────


class TestCreateRiskAssessment:
    async def test_creates_assessment(self, admin_client: AsyncClient, admin_token_headers: dict):
        await admin_client.post(
            "/admin/operations/failure-signals",
            json=SIGNAL_PAYLOAD,
            headers=admin_token_headers,
        )
        fr = await admin_client.post(
            "/admin/operations/failure-forecasts/run",
            params={"client_id": "test-client"},
            headers=admin_token_headers,
        )
        forecast_id = fr.json()["forecast"]["input_hash"]
        forecast_list = await admin_client.get(
            "/admin/operations/failure-forecasts",
            params={"client_id": "test-client"},
            headers=admin_token_headers,
        )
        fid = forecast_list.json()[0]["id"]

        r = await admin_client.post(
            "/admin/operations/failure-risk-assessments",
            json={"client_id": "test-client", "forecast_id": fid},
            headers=admin_token_headers,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "assessment" in data
        assert "receipt" in data
        assert data["assessment"]["advisory_only"] is True
        assert data["assessment"]["dry_run"] is True
        assert data["receipt"]["receipt_type"] == "failure_risk_assessment_created"

    async def test_404_for_missing_forecast(
        self, admin_client: AsyncClient, admin_token_headers: dict
    ):
        r = await admin_client.post(
            "/admin/operations/failure-risk-assessments",
            json={"client_id": "x", "forecast_id": "nonexistent"},
            headers=admin_token_headers,
        )
        assert r.status_code == 404

    async def test_dry_run_false(self, admin_client: AsyncClient, admin_token_headers: dict):
        await admin_client.post(
            "/admin/operations/failure-signals",
            json=SIGNAL_PAYLOAD,
            headers=admin_token_headers,
        )
        await admin_client.post(
            "/admin/operations/failure-forecasts/run",
            params={"client_id": "test-client"},
            headers=admin_token_headers,
        )
        flist = await admin_client.get(
            "/admin/operations/failure-forecasts",
            params={"client_id": "test-client"},
            headers=admin_token_headers,
        )
        r = await admin_client.post(
            "/admin/operations/failure-risk-assessments",
            json={
                "client_id": "test-client",
                "forecast_id": flist.json()[0]["id"],
                "dry_run": False,
            },
            headers=admin_token_headers,
        )
        assert r.status_code == 200
        assert r.json()["assessment"]["dry_run"] is False
        assert r.json()["assessment"]["advisory_only"] is True

    async def test_rejects_cross_tenant_forecast_reference(
        self, admin_client: AsyncClient, admin_token_headers: dict
    ):
        await admin_client.post(
            "/admin/operations/failure-signals",
            json={**SIGNAL_PAYLOAD, "client_id": "client-a"},
            headers=admin_token_headers,
        )
        await admin_client.post(
            "/admin/operations/failure-forecasts/run",
            params={"client_id": "client-a"},
            headers=admin_token_headers,
        )
        flist = await admin_client.get(
            "/admin/operations/failure-forecasts",
            params={"client_id": "client-a"},
            headers=admin_token_headers,
        )
        forecast_id = flist.json()[0]["id"]

        r = await admin_client.post(
            "/admin/operations/failure-risk-assessments",
            json={"client_id": "client-b", "forecast_id": forecast_id},
            headers=admin_token_headers,
        )
        assert r.status_code == 404


# ── GET /admin/operations/failure-risk-assessments ───────────────────────────


class TestListRiskAssessments:
    async def test_lists_assessments(self, admin_client: AsyncClient, admin_token_headers: dict):
        await admin_client.post(
            "/admin/operations/failure-signals",
            json=SIGNAL_PAYLOAD,
            headers=admin_token_headers,
        )
        fr = await admin_client.post(
            "/admin/operations/failure-forecasts/run",
            params={"client_id": "test-client"},
            headers=admin_token_headers,
        )
        flist = await admin_client.get(
            "/admin/operations/failure-forecasts",
            params={"client_id": "test-client"},
            headers=admin_token_headers,
        )
        await admin_client.post(
            "/admin/operations/failure-risk-assessments",
            json={"client_id": "test-client", "forecast_id": flist.json()[0]["id"]},
            headers=admin_token_headers,
        )
        r = await admin_client.get(
            "/admin/operations/failure-risk-assessments",
            params={"client_id": "test-client"},
            headers=admin_token_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["advisory_only"] is True

    async def test_tenant_isolation(self, admin_client: AsyncClient, admin_token_headers: dict):
        r = await admin_client.get(
            "/admin/operations/failure-risk-assessments",
            params={"client_id": "other-client"},
            headers=admin_token_headers,
        )
        assert r.status_code == 200
        assert r.json() == []


# ── Auth ─────────────────────────────────────────────────────────────────────


class TestAuth:
    async def test_rejects_no_token(self, admin_client: AsyncClient):
        r = await admin_client.post(
            "/admin/operations/failure-signals",
            json=SIGNAL_PAYLOAD,
        )
        assert r.status_code == 401
