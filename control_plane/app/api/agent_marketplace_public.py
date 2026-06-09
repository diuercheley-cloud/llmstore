import logging
import uuid
from typing import List, Optional

from app.api.deps import get_current_user, get_db
from app.models.agent_marketplace import MarketplaceItem, MarketplacePublisher
from app.services.agents.agent_state import get_agent_definition
from app.services.agents.marketplace.marketplace_analytics import MarketplaceAnalyticsService
from app.services.agents.marketplace.marketplace_ratings import MarketplaceRatingService
from app.services.agents.marketplace.marketplace_search import MarketplaceSearchService
from app.services.agents.marketplace.publisher_program import PublisherProgramService
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/marketplace", tags=["marketplace"])

class MarketplaceItemResponse(BaseModel):
    id: uuid.UUID
    publisher_id: uuid.UUID
    publisher_name: str = ""
    agent_definition_id: uuid.UUID
    name: str
    category: str
    tags: list = []
    capabilities: list = []
    risk_level: str = "medium"
    price_brl: float = 0.0
    avg_rating: float = 0.0
    total_ratings: int = 0
    total_downloads: int = 0
    created_at: str = ""
    updated_at: str = ""

class PaginatedResponse(BaseModel):
    items: list
    total: int
    limit: int
    offset: int

class PublishItemRequest(BaseModel):
    agent_definition_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=64)
    tags: List[str] = []
    capabilities: List[str] = []
    risk_level: str = "medium"
    price_brl: float = 0.0

class UpdateItemRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    capabilities: Optional[List[str]] = None
    risk_level: Optional[str] = None
    price_brl: Optional[float] = None
    is_public: Optional[bool] = None

class RatingRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    review: Optional[str] = None

class RatingResponse(BaseModel):
    id: uuid.UUID
    item_id: uuid.UUID
    user_id: str
    rating: int
    review: Optional[str] = None
    created_at: str = ""

class RegisterPublisherRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    website: Optional[str] = None

def _item_to_response(item: MarketplaceItem, publisher_name: str = "") -> dict:
    return {
        "id": str(item.id),
        "publisher_id": str(item.publisher_id),
        "publisher_name": publisher_name,
        "agent_definition_id": str(item.agent_definition_id),
        "name": item.name,
        "category": item.category,
        "tags": item.tags or [],
        "capabilities": item.capabilities or [],
        "risk_level": item.risk_level,
        "price_brl": item.price_brl,
        "avg_rating": item.avg_rating,
        "total_ratings": item.total_ratings,
        "total_downloads": item.total_downloads,
        "created_at": item.created_at.isoformat() if item.created_at else "",
        "updated_at": item.updated_at.isoformat() if item.updated_at else "",
    }

@router.get("/items", response_model=PaginatedResponse)
async def list_items(
    query: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    capabilities: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    min_rating: float = Query(0.0, ge=0.0, le=5.0),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    search_svc = MarketplaceSearchService(db)
    tag_list = tags.split(",") if tags else None
    cap_list = capabilities.split(",") if capabilities else None
    result = await search_svc.search(
        query=query, category=category, tags=tag_list,
        capabilities=cap_list, risk_level=risk_level,
        min_rating=min_rating, sort_by=sort_by, sort_order=sort_order,
        limit=limit, offset=offset,
    )
    items_response = []
    for item in result["items"]:
        publisher_name = ""
        pub_stmt = await db.execute(
            select(MarketplacePublisher).where(MarketplacePublisher.id == item.publisher_id)
        )
        pub = pub_stmt.scalar_one_or_none()
        if pub:
            publisher_name = pub.name
        items_response.append(_item_to_response(item, publisher_name))

    return {"items": items_response, "total": result["total"], "limit": result["limit"], "offset": result["offset"]}

@router.get("/items/{item_id}")
async def get_item(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    search_svc = MarketplaceSearchService(db)
    item = await search_svc.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    pub_stmt = await db.execute(
        select(MarketplacePublisher).where(MarketplacePublisher.id == item.publisher_id)
    )
    pub = pub_stmt.scalar_one_or_none()
    return _item_to_response(item, pub.name if pub else "")

@router.post("/items", status_code=201)
async def publish_item(
    req: PublishItemRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    tenant_id = getattr(user, "tenant_id", "default") or "default"
    pub_svc = PublisherProgramService(db)
    publisher = await pub_svc.get_publisher(tenant_id)
    if not publisher:
        raise HTTPException(status_code=400, detail="Tenant not registered as publisher. Register first via POST /v1/marketplace/publishers/register")

    agent_def = await get_agent_definition(db, req.agent_definition_id)
    if not agent_def:
        raise HTTPException(status_code=404, detail="Agent definition not found")
    if str(agent_def.tenant_id) != tenant_id:
        raise HTTPException(status_code=403, detail="Agent definition does not belong to your tenant")

    item = MarketplaceItem(
        publisher_id=publisher.id,
        agent_definition_id=req.agent_definition_id,
        name=req.name,
        category=req.category,
        tags=req.tags,
        capabilities=req.capabilities,
        risk_level=req.risk_level,
        price_brl=req.price_brl,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _item_to_response(item, publisher.name)

@router.put("/items/{item_id}")
async def update_item(
    item_id: uuid.UUID,
    req: UpdateItemRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    tenant_id = getattr(user, "tenant_id", "default") or "default"
    pub_svc = PublisherProgramService(db)
    publisher = await pub_svc.get_publisher(tenant_id)
    if not publisher:
        raise HTTPException(status_code=403, detail="Tenant not registered as publisher")

    stmt = select(MarketplaceItem).where(MarketplaceItem.id == item_id)
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.publisher_id != publisher.id:
        raise HTTPException(status_code=403, detail="Not your item")

    if req.name is not None:
        item.name = req.name
    if req.category is not None:
        item.category = req.category
    if req.tags is not None:
        item.tags = req.tags
    if req.capabilities is not None:
        item.capabilities = req.capabilities
    if req.risk_level is not None:
        item.risk_level = req.risk_level
    if req.price_brl is not None:
        item.price_brl = req.price_brl
    if req.is_public is not None:
        item.is_public = req.is_public

    await db.commit()
    await db.refresh(item)
    return _item_to_response(item, publisher.name)

@router.post("/items/{item_id}/rate", response_model=RatingResponse)
async def rate_item(
    item_id: uuid.UUID,
    req: RatingRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = getattr(user, "id", str(user)) if user else "anonymous"
    rating_svc = MarketplaceRatingService(db)
    rating = await rating_svc.add_rating(item_id, user_id, req.rating, req.review)
    return {
        "id": rating.id,
        "item_id": rating.item_id,
        "user_id": rating.user_id,
        "rating": rating.rating,
        "review": rating.review,
        "created_at": rating.created_at.isoformat() if rating.created_at else "",
    }

@router.get("/items/{item_id}/reviews")
async def get_item_reviews(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    from app.models.agent_marketplace import MarketplaceRating
    from sqlalchemy import select
    stmt = select(MarketplaceRating).where(
        MarketplaceRating.item_id == item_id
    ).order_by(MarketplaceRating.created_at.desc())
    res = await db.execute(stmt)
    ratings = res.scalars().all()
    return [
        {
            "id": str(r.id),
            "user_id": r.user_id,
            "rating": r.rating,
            "review": r.review,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in ratings
    ]

@router.post("/publishers/register")
async def register_publisher(
    req: RegisterPublisherRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    tenant_id = getattr(user, "tenant_id", "default") or "default"
    pub_svc = PublisherProgramService(db)
    existing = await pub_svc.get_publisher(tenant_id)
    if existing:
        raise HTTPException(status_code=409, detail="Tenant already registered as publisher")

    publisher = await pub_svc.register_publisher(
        tenant_id=tenant_id, name=req.name, description=req.description
    )
    if req.website:
        publisher.website = req.website
        await db.flush()
    return {
        "id": str(publisher.id),
        "tenant_id": publisher.tenant_id,
        "name": publisher.name,
        "description": publisher.description,
        "website": publisher.website,
        "is_verified": publisher.is_verified,
    }

@router.get("/publishers/me")
async def get_my_publisher_profile(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    tenant_id = getattr(user, "tenant_id", "default") or "default"
    pub_svc = PublisherProgramService(db)
    publisher = await pub_svc.get_publisher(tenant_id)
    if not publisher:
        raise HTTPException(status_code=404, detail="Not registered as publisher")
    return {
        "id": str(publisher.id),
        "tenant_id": publisher.tenant_id,
        "name": publisher.name,
        "description": publisher.description,
        "website": publisher.website,
        "is_verified": publisher.is_verified,
        "trust_score": publisher.trust_score,
    }

@router.get("/categories")
async def list_categories(
    db: AsyncSession = Depends(get_db),
):
    search_svc = MarketplaceSearchService(db)
    return {"categories": await search_svc.get_categories()}

@router.get("/my-items")
async def get_my_items(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    tenant_id = getattr(user, "tenant_id", "default") or "default"
    pub_svc = PublisherProgramService(db)
    publisher = await pub_svc.get_publisher(tenant_id)
    if not publisher:
        return {"items": []}
    search_svc = MarketplaceSearchService(db)
    result = await search_svc.search(publisher_id=publisher.id)
    return {"items": [_item_to_response(item) for item in result["items"]]}

@router.post("/items/{item_id}/download")
async def download_item(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    tenant_id = getattr(user, "tenant_id", "default") or "default"
    search_svc = MarketplaceSearchService(db)
    item = await search_svc.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    analytics_svc = MarketplaceAnalyticsService(db)
    await analytics_svc.record_download(item_id, tenant_id, "latest")
    await db.commit()
    return {"status": "downloaded", "item_id": str(item_id)}
