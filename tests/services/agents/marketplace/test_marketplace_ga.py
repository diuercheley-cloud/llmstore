import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_marketplace import MarketplaceItem, MarketplaceRating, MarketplacePublisher
from app.services.agents.marketplace.marketplace_search import MarketplaceSearchService
from app.services.agents.marketplace.marketplace_ratings import MarketplaceRatingService
from app.services.agents.marketplace.publisher_program import PublisherProgramService
from app.services.agents.marketplace.dependency_resolver import DependencyResolver

@pytest.fixture
def mock_db():
    return MagicMock(spec=AsyncSession)

@pytest.mark.asyncio
async def test_marketplace_search_filters(mock_db):
    service = MarketplaceSearchService(mock_db)
    items = [
        MarketplaceItem(name="Sales Agent", category="sales", tags=["crm", "email"], is_public=True),
        MarketplaceItem(name="Support Agent", category="support", tags=["chat"], is_public=True)
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = items
    mock_result.scalar_one.return_value = 2
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await service.search(category="sales")
    assert result["total"] == 2
    items_found = result["items"]
    sales_items = [i for i in items_found if i.category == "sales"]
    assert len(sales_items) == 1
    assert sales_items[0].name == "Sales Agent"

@pytest.mark.asyncio
async def test_marketplace_search_pagination(mock_db):
    service = MarketplaceSearchService(mock_db)
    items = [MarketplaceItem(name=f"Agent {i}", category="general", is_public=True) for i in range(5)]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = items
    mock_result.scalar_one.return_value = 25
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await service.search(limit=5, offset=0)
    assert result["total"] == 25
    assert len(result["items"]) == 5
    assert result["limit"] == 5
    assert result["offset"] == 0

@pytest.mark.asyncio
async def test_marketplace_search_empty(mock_db):
    service = MarketplaceSearchService(mock_db)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar_one.return_value = 0
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await service.search(query="nonexistent")
    assert result["total"] == 0
    assert result["items"] == []

@pytest.mark.asyncio
async def test_marketplace_rating_add(mock_db):
    service = MarketplaceRatingService(mock_db)
    item_id = uuid.uuid4()
    item = MarketplaceItem(id=item_id, avg_rating=0.0, total_ratings=0)

    stats_mock = MagicMock()
    stats_mock.one.return_value = (4.5, 10)

    item_mock = MagicMock()
    item_mock.scalar_one_or_none.return_value = item

    mock_db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=lambda: None),
        stats_mock,
        item_mock,
    ])

    result = await service.add_rating(item_id, "user_1", 5, "Great!")
    assert result.rating == 5
    assert result.review == "Great!"
    assert item.avg_rating == 4.5
    assert item.total_ratings == 10

@pytest.mark.asyncio
async def test_marketplace_rating_update(mock_db):
    service = MarketplaceRatingService(mock_db)
    item_id = uuid.uuid4()
    existing_rating = MarketplaceRating(item_id=item_id, user_id="user_1", rating=3)

    stats_mock = MagicMock()
    stats_mock.one.return_value = (4.0, 8)

    item_mock = MagicMock()
    item_mock.scalar_one_or_none.return_value = MarketplaceItem(id=item_id, avg_rating=0.0, total_ratings=0)

    mock_db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=lambda: existing_rating),
        stats_mock,
        item_mock,
    ])

    result = await service.add_rating(item_id, "user_1", 4, "Updated review")
    assert result.rating == 4
    assert result.review == "Updated review"

@pytest.mark.asyncio
async def test_marketplace_rating_invalid(mock_db):
    service = MarketplaceRatingService(mock_db)
    with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
        await service.add_rating(uuid.uuid4(), "user_1", 6)

@pytest.mark.asyncio
async def test_publisher_verification(mock_db):
    service = PublisherProgramService(mock_db)
    pub_id = uuid.uuid4()
    publisher = MarketplacePublisher(id=pub_id, is_verified=False)

    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: publisher))

    await service.verify_publisher(pub_id, trust_score=0.9)
    assert publisher.is_verified is True
    assert publisher.trust_score == 0.9

@pytest.mark.asyncio
async def test_dependency_conflict(mock_db):
    resolver = DependencyResolver(mock_db)

    new_deps = {"tools": [{"name": "search", "version": "2.0"}]}
    existing_deps = {"tools": [{"name": "search", "version": "1.0"}]}

    conflicts = await resolver.check_conflicts(new_deps, existing_deps)
    assert len(conflicts) == 1
    assert "Version conflict" in conflicts[0]

@pytest.mark.asyncio
async def test_dependency_no_conflict(mock_db):
    resolver = DependencyResolver(mock_db)

    new_deps = {"tools": [{"name": "search", "version": "2.0"}]}
    existing_deps = {}

    conflicts = await resolver.check_conflicts(new_deps, existing_deps)
    assert len(conflicts) == 0

@pytest.mark.asyncio
async def test_marketplace_search_by_tags(mock_db):
    service = MarketplaceSearchService(mock_db)
    items = [
        MarketplaceItem(name="Support Agent", category="support", tags=["chat", "ticket"], is_public=True),
        MarketplaceItem(name="Sales Agent", category="sales", tags=["crm", "email"], is_public=True),
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = items
    mock_result.scalar_one.return_value = 2
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await service.search(tags=["crm"])
    items_found = result["items"]
    assert len(items_found) == 1
    assert items_found[0].name == "Sales Agent"

@pytest.mark.asyncio
async def test_marketplace_get_categories(mock_db):
    service = MarketplaceSearchService(mock_db)

    mock_result = MagicMock()
    mock_result.all.return_value = [("sales",), ("support",), ("devops",)]
    mock_db.execute = AsyncMock(return_value=mock_result)

    categories = await service.get_categories()
    assert len(categories) == 3
    assert "devops" in categories

@pytest.mark.asyncio
async def test_publisher_registration(mock_db):
    service = PublisherProgramService(mock_db)
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

    publisher = await service.register_publisher(
        tenant_id="tenant-1",
        name="Acme Corp",
        description="Enterprise AI"
    )
    assert publisher.tenant_id == "tenant-1"
    assert publisher.name == "Acme Corp"
    assert publisher.description == "Enterprise AI"
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()
