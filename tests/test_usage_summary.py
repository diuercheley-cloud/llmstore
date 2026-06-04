from types import SimpleNamespace
from uuid import uuid4

import app.api.admin as admin_api
import pytest
from app.api.deps import get_inference_proxy
from app.db.session import get_db_session, get_redis
from app.main import app
from app.services import export_reporting as reporting
from app.services import security_monitor as security_monitor


class FakeProxy:
    def __init__(self) -> None:
        self.queue_manager = SimpleNamespace(
            get_snapshot=lambda: {
                "queues": {
                    "inference_admin": {"waiting": 0, "active": 1, "max_active": 10, "max_waiting": 20},
                    "inference_premium": {"waiting": 2, "active": 3, "max_active": 5, "max_waiting": 15},
                    "inference_basic": {"waiting": 1, "active": 2, "max_active": 2, "max_waiting": 10},
                    "inference_free": {"waiting": 4, "active": 1, "max_active": 1, "max_waiting": 5},
                },
                "total_pending": 8,
            }
        )


class FakeRedis:
    async def ping(self) -> bool:
        return True


class FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class FakeExecuteResult:
    def __init__(self, rows=None, scalar_value=None):
        self._rows = rows or []
        self._scalar_value = scalar_value

    def scalars(self):
        return FakeScalarResult(self._rows)

    def scalar_one_or_none(self):
        return self._scalar_value


class FakeSession:
    def __init__(self) -> None:
        client_id = str(uuid4())
        pricing_rule = SimpleNamespace(
            is_active=True,
            monthly_price=0,
            overage_price_per_1k_tokens=0,
            currency="USD",
        )
        billing_plan = SimpleNamespace(
            code="basic",
            name="Basic",
            rate_limit_per_minute=10,
            daily_token_quota=1000,
            weekly_token_quota=5000,
            monthly_token_quota=10000,
            max_output_tokens=512,
            allow_streaming=True,
            rag_max_documents=5,
            rag_max_storage_mb=50,
            rag_max_pages_per_month=100,
            rag_max_queries_per_month=50,
            # TTS
            tts_enabled=True,
            tts_chars_per_request=1000,
            tts_chars_per_day=5000,
            tts_chars_per_month=50000,
            tts_audio_retention_days=7,
            tts_max_files=100,
            # Embeddings
            embeddings_enabled=True,
            embeddings_requests_per_month=1000,
            embeddings_tokens_per_month=100000,
            embeddings_max_inputs_per_request=16,
            pricing_rules=[pricing_rule],
        )
        self.client = SimpleNamespace(
            id=client_id,
            created_at=0,
            billing_plan=billing_plan,
        )

    async def execute(self, *args, **kwargs):
        query_text = str(args[0]) if args else ""
        if "FROM clients" in query_text:
            return FakeExecuteResult(rows=[self.client])
        if "FROM quota_counters" in query_text:
            return FakeExecuteResult(scalar_value=None)
        return FakeExecuteResult()

    async def commit(self) -> None:
        return None


@pytest.fixture
def usage_payloads(monkeypatch):
    summary_payload = {
        "generated_at": "2026-05-07T12:00:00+00:00",
        "requests_today": 2,
        "requests_month": 3,
        "prompt_tokens_today": 22,
        "completion_tokens_today": 18,
        "tokens_today": 40,
        "prompt_tokens_month": 40,
        "completion_tokens_month": 30,
        "tokens_month": 70,
        "avg_latency_ms_month": 123.45,
        "cache_hits_month": 1,
        "cache_misses_month": 2,
        "cache_hit_rate_month": 0.3333,
        "invoices_pending": 1,
        "invoices_paid": 1,
        "invoices_overdue": 1,
        "clients_active": 1,
        "clients_suspended": 1,
        "clients_blocked": 0,
        "clients_total": 2,
        "invoices_total": 3,
        "queues_by_plan": {
            "queues": {
                "inference_basic": {"waiting": 1, "active": 2, "max_active": 2, "max_waiting": 10},
            }
        },
    }
    by_client_payload = [
        {
            "client_id": "client-a",
            "client_name": "active-client",
            "name": "active-client",
            "billing_status": "active",
            "billing_plan_code": "basic",
            "requests_today": 1,
            "requests_month": 2,
            "requests_total": 2,
            "prompt_tokens_today": 12,
            "completion_tokens_today": 18,
            "tokens_today": 30,
            "prompt_tokens_month": 24,
            "completion_tokens_month": 36,
            "tokens_month": 60,
            "tokens_estimated_total": 60,
            "avg_latency_ms_month": 111.11,
            "avg_latency_ms": 111.11,
            "cache_hits_month": 1,
            "cache_misses_month": 1,
            "cache_hit_rate_month": 0.5,
            "errors_month": 1,
            "errors_total": 1,
            "estimated_cost_usd": 0.0,
            "last_request_at": "2026-05-07T12:00:00+00:00",
        }
    ]
    by_model_payload = [
        {
            "model": "model-a",
            "requests_today": 1,
            "requests_month": 2,
            "prompt_tokens_today": 10,
            "completion_tokens_today": 15,
            "tokens_today": 25,
            "prompt_tokens_month": 20,
            "completion_tokens_month": 30,
            "tokens_month": 50,
            "avg_latency_ms_month": 222.22,
            "backend_errors_month": 1,
            "model_errors_month": 1,
            "cache_hits_month": 1,
            "cache_misses_month": 1,
            "cache_hit_rate_month": 0.5,
        }
    ]

    async def fake_build_usage_summary(session, queue_snapshot=None):
        return summary_payload

    async def fake_build_usage_by_client(session):
        return by_client_payload

    async def fake_build_usage_by_model(session):
        return by_model_payload

    async def fake_observe_billing_status_metrics(session):
        return None

    monkeypatch.setattr(reporting, "build_usage_summary", fake_build_usage_summary)
    monkeypatch.setattr(reporting, "build_usage_by_client", fake_build_usage_by_client)
    monkeypatch.setattr(reporting, "build_usage_by_model", fake_build_usage_by_model)
    monkeypatch.setattr(security_monitor, "observe_billing_status_metrics", fake_observe_billing_status_metrics)
    monkeypatch.setattr(admin_api, "build_usage_summary", fake_build_usage_summary)
    monkeypatch.setattr(admin_api, "build_usage_by_client", fake_build_usage_by_client)
    monkeypatch.setattr(admin_api, "build_usage_by_model", fake_build_usage_by_model)
    monkeypatch.setattr(admin_api, "observe_billing_status_metrics", fake_observe_billing_status_metrics)
    return summary_payload, by_client_payload, by_model_payload


@pytest.fixture
def usage_client(monkeypatch, usage_payloads):
    fake_session = FakeSession()
    fake_proxy = FakeProxy()
    fake_redis = FakeRedis()

    async def override_get_db_session():
        yield fake_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redis] = lambda: fake_redis
    app.dependency_overrides[get_inference_proxy] = lambda: fake_proxy
    yield fake_session
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_usage_endpoints_return_summary_data(usage_client, usage_payloads):
    summary_payload, by_client_payload, by_model_payload = usage_payloads
    fake_session = usage_client
    fake_proxy = FakeProxy()

    summary = await admin_api.get_usage_summary(session=fake_session, proxy=fake_proxy)
    by_client = await admin_api.get_usage_by_client(session=fake_session)
    by_model = await admin_api.get_usage_by_model(session=fake_session)

    assert summary["summary"]["requests_today"] == summary_payload["requests_today"]
    assert summary["summary"]["tokens_month"] == summary_payload["tokens_month"]
    assert summary["summary"]["clients_suspended"] == summary_payload["clients_suspended"]
    assert summary["summary"]["invoices_overdue"] == summary_payload["invoices_overdue"]
    assert summary["queues"]["queues"]["inference_basic"]["waiting"] == 1

    assert by_client == by_client_payload
    assert by_model == by_model_payload
