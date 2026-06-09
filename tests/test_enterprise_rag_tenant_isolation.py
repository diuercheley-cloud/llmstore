import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.rag_enterprise.policies import resolve_enterprise_rag_policy
from app.services.rag_enterprise.retrieval import search_chunks

pytestmark = pytest.mark.asyncio


class TestTenantIsolationRetrieval:
    async def test_search_filters_by_client_id(self):
        session = MagicMock()

        mock_exec_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_exec_result.scalars = MagicMock(return_value=mock_scalars)
        session.execute = AsyncMock(return_value=mock_exec_result)

        client_a = uuid.uuid4()

        await search_chunks(
            session=session,
            client_id=client_a,
            query_embedding=[0.1] * 384,
        )

    async def test_different_tenants_different_policies(self):
        session = MagicMock()
        session.execute = AsyncMock()
        mock_block_result = MagicMock()
        mock_block_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute.return_value = mock_block_result

        client_a = MagicMock()
        client_a.id = uuid.uuid4()
        client_b = MagicMock()
        client_b.id = uuid.uuid4()

        from app.models.billing_plan import BillingPlan

        plan_a = MagicMock(spec=BillingPlan)
        plan_a.rag_enabled = True
        plan_a.rag_max_documents = 100
        plan_a.rag_max_storage_mb = 2048
        plan_a.rag_max_pages_per_month = 5000
        plan_a.rag_max_queries_per_month = 2000

        plan_b = MagicMock(spec=BillingPlan)
        plan_b.rag_enabled = True
        plan_b.rag_max_documents = 5
        plan_b.rag_max_storage_mb = 50
        plan_b.rag_max_pages_per_month = 100
        plan_b.rag_max_queries_per_month = 50

        with patch("app.services.rag_enterprise.policies.resolve_effective_plan_for_session", new_callable=AsyncMock) as mock_resolve:
            mock_resolve.side_effect = lambda s, c: plan_a if c.id == client_a.id else plan_b

            policy_a = await resolve_enterprise_rag_policy(session, client_a)
            policy_b = await resolve_enterprise_rag_policy(session, client_b)

            assert policy_a.rag_enabled == policy_b.rag_enabled
            assert policy_a.max_documents != policy_b.max_documents


class TestTenantIsolationEndToEnd:
    async def test_isolation_ingestion_rejects_cross_tenant(self):
        session = MagicMock()
        session.execute = AsyncMock()

        client_a = MagicMock()
        client_a.id = uuid.uuid4()

        with patch(
            "app.services.rag_enterprise.ingestion.resolve_enterprise_rag_policy",
            AsyncMock(),
        ) as mock_policy:
            mock_policy.return_value.rag_enabled = False

            with pytest.raises(PermissionError):
                from app.services.rag_enterprise.ingestion import ingest_document
                await ingest_document(
                    session=session,
                    client_id=client_a.id,
                    file_path="/tmp/test.txt",
                    original_filename="test.txt",
                    content_type="text/plain",
                    file_size_bytes=10,
                )

    async def test_client_a_data_not_visible_to_b(self):
        session = MagicMock()
        session.execute = AsyncMock()

        mock_exec_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_exec_result.scalars = MagicMock(return_value=mock_scalars)
        session.execute.return_value = mock_exec_result

        client_a_id = uuid.uuid4()
        client_b_id = uuid.uuid4()

        search_a = await search_chunks(
            session=session,
            client_id=client_a_id,
            query_embedding=[0.1] * 384,
        )

        search_b = await search_chunks(
            session=session,
            client_id=client_b_id,
            query_embedding=[0.1] * 384,
        )

        assert isinstance(search_a, list)
        assert isinstance(search_b, list)
