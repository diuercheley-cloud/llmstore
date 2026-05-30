# Owner: agent-platform
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
    
    mock_db.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: items)))
    
    # 1. Search by category
    results = await service.search(category="sales")
    assert len(results) == 1
    assert results[0].name == "Sales Agent"

    # 2. Search by tag
    results = await service.search(tags=["crm"])
    assert len(results) == 1
    assert "crm" in results[0].tags

@pytest.mark.asyncio
async def test_marketplace_rating_aggregates(mock_db):
    service = MarketplaceRatingService(mock_db)
    item_id = uuid.uuid4()
    item = MarketplaceItem(id=item_id, avg_rating=0.0, total_ratings=0)
    
    # Mocking rating existence check and aggregate update
    mock_db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=lambda: None), # no existing rating
        MagicMock(one=lambda: (4.5, 10)), # aggregate stats
        MagicMock(scalar_one_or_none=lambda: item) # item for update
    ])
    
    await service.add_rating(item_id, "user_1", 5, "Great!")
    assert item.avg_rating == 4.5
    assert item.total_ratings == 10

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
