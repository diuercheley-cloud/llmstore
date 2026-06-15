import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.billing.billing_plan import BillingPlan
from app.models.core.client_feature_block import ClientFeatureBlock
from app.services.rag_enterprise.policies import (
    ALLOWED_FILE_TYPES_DEFAULT,
    EnterpriseRagPolicy,
    check_file_type_allowed,
    check_quota_documents,
    check_quota_pages,
    check_quota_storage,
    is_cloud_embedding_allowed,
    resolve_enterprise_rag_policy,
)


class TestEnterpriseRagPolicy:
    def test_default_policy(self):
        policy = EnterpriseRagPolicy()
        assert policy.rag_enabled is True
        assert policy.max_documents is None
        assert policy.max_storage_mb is None
        assert policy.cloud_embeddings_allowed is False
        assert ".txt" in policy.allowed_file_types

    def test_custom_policy(self):
        policy = EnterpriseRagPolicy(
            rag_enabled=True,
            max_documents=50,
            max_storage_mb=500,
            max_pages_per_month=1000,
            cloud_embeddings_allowed=False,
        )
        assert policy.max_documents == 50
        assert policy.max_storage_mb == 500
        assert policy.max_pages_per_month == 1000

    def test_policy_disabled(self):
        policy = EnterpriseRagPolicy(rag_enabled=False)
        assert policy.rag_enabled is False

    def test_allowed_file_types_default(self):
        policy = EnterpriseRagPolicy()
        assert all(
            ext in policy.allowed_file_types
            for ext in [".txt", ".md", ".pdf", ".docx", ".xlsx", ".csv"]
        )


class TestResolvePolicy:
    async def test_resolve_from_plan(self, mock_session):
        client = MagicMock()
        client.id = uuid.uuid4()

        effective_plan = MagicMock(spec=BillingPlan)
        effective_plan.rag_enabled = True
        effective_plan.rag_max_documents = 100
        effective_plan.rag_max_storage_mb = 2048
        effective_plan.rag_max_pages_per_month = 5000

        mock_session.execute = AsyncMock()
        mock_exec_result = MagicMock()
        mock_exec_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_exec_result

        with patch(
            "app.services.rag_enterprise.policies.resolve_effective_plan_for_session",
            new_callable=AsyncMock,
            return_value=effective_plan,
        ):
            policy = await resolve_enterprise_rag_policy(mock_session, client)
            assert policy.rag_enabled is True
            assert policy.max_documents == 100

    async def test_resolve_blocked(self, mock_session):
        client = MagicMock()
        client.id = uuid.uuid4()

        effective_plan = MagicMock(spec=BillingPlan)
        effective_plan.rag_enabled = True

        block = MagicMock(spec=ClientFeatureBlock)
        block.blocked = True
        block.reason = "Blocked by admin"

        mock_session.execute = AsyncMock()
        mock_exec_result = MagicMock()
        mock_exec_result.scalar_one_or_none = MagicMock(return_value=block)
        mock_session.execute.return_value = mock_exec_result

        with patch(
            "app.services.rag_enterprise.policies.resolve_effective_plan_for_session",
            new_callable=AsyncMock,
            return_value=effective_plan,
        ):
            policy = await resolve_enterprise_rag_policy(mock_session, client)
            assert policy.rag_enabled is False


class TestQuotaCheck:
    async def test_unlimited_quota(self, mock_session):
        client_id = uuid.uuid4()
        policy = EnterpriseRagPolicy(
            max_documents=None, max_storage_mb=None, max_pages_per_month=None
        )
        ok, msg = await check_quota_documents(mock_session, client_id, policy)
        assert ok is True
        ok, msg = await check_quota_storage(mock_session, client_id, policy)
        assert ok is True
        ok, msg = await check_quota_pages(mock_session, client_id, policy)
        assert ok is True

    async def test_document_limit_exceeded(self, mock_session):
        client_id = uuid.uuid4()
        policy = EnterpriseRagPolicy(max_documents=5)
        mock_session.execute = AsyncMock()
        result = MagicMock()
        result.scalar = MagicMock(return_value=5)
        mock_session.execute.return_value = result

        ok, msg = await check_quota_documents(mock_session, client_id, policy)
        assert ok is False
        assert "Maximum document limit" in msg

    async def test_document_limit_not_exceeded(self, mock_session):
        client_id = uuid.uuid4()
        policy = EnterpriseRagPolicy(max_documents=10)
        mock_session.execute = AsyncMock()
        result = MagicMock()
        result.scalar = MagicMock(return_value=3)
        mock_session.execute.return_value = result

        ok, msg = await check_quota_documents(mock_session, client_id, policy)
        assert ok is True

    async def test_storage_limit_exceeded(self, mock_session):
        client_id = uuid.uuid4()
        policy = EnterpriseRagPolicy(max_storage_mb=1)
        mock_session.execute = AsyncMock()
        result = MagicMock()
        result.scalar = MagicMock(return_value=2 * 1024 * 1024)
        mock_session.execute.return_value = result

        ok, msg = await check_quota_storage(mock_session, client_id, policy)
        assert ok is False
        assert "Storage limit" in msg

    async def test_storage_with_additional_bytes(self, mock_session):
        client_id = uuid.uuid4()
        policy = EnterpriseRagPolicy(max_storage_mb=10)
        mock_session.execute = AsyncMock()
        result = MagicMock()
        result.scalar = MagicMock(return_value=9 * 1024 * 1024)
        mock_session.execute.return_value = result

        ok, msg = await check_quota_storage(
            mock_session, client_id, policy, additional_bytes=2 * 1024 * 1024
        )
        assert ok is False


class TestFileTypeCheck:
    @pytest.mark.asyncio
    async def test_allowed_type(self):
        policy = EnterpriseRagPolicy()
        ok, msg = await check_file_type_allowed("test.txt", policy)
        assert ok is True

    @pytest.mark.asyncio
    async def test_disallowed_type(self):
        policy = EnterpriseRagPolicy(allowed_file_types=[".txt", ".md"])
        ok, msg = await check_file_type_allowed("test.pdf", policy)
        assert ok is False
        assert "pdf" in msg.lower()

    @pytest.mark.asyncio
    async def test_default_allowed_types(self):
        policy = EnterpriseRagPolicy()
        for ext in ALLOWED_FILE_TYPES_DEFAULT:
            ok, msg = await check_file_type_allowed(f"file{ext}", policy)
            assert ok is True, f"File type {ext} should be allowed"


class TestCloudEmbeddings:
    def test_default_not_allowed(self):
        policy = EnterpriseRagPolicy()
        assert policy.cloud_embeddings_allowed is False

    def test_explicitly_allowed(self):
        policy = EnterpriseRagPolicy(cloud_embeddings_allowed=True)
        assert policy.cloud_embeddings_allowed is True

    @pytest.mark.asyncio
    async def test_is_cloud_embedding_allowed(self):
        client = MagicMock()
        client.id = uuid.uuid4()

        policy = EnterpriseRagPolicy(cloud_embeddings_allowed=False)
        allowed = await is_cloud_embedding_allowed(client, policy)
        assert allowed is False

        policy = EnterpriseRagPolicy(cloud_embeddings_allowed=True)
        allowed = await is_cloud_embedding_allowed(client, policy)
        assert allowed is True


@pytest.fixture
def mock_session():
    session = MagicMock()
    return session
