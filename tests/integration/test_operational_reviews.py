from __future__ import annotations

from datetime import timedelta

import pytest
from app.models.commercial.commercial_compliance import CommercialOperationalReview
from app.services.compliance.operational_controls import (
    complete_review,
    create_control,
    detect_overdue_reviews,
)
from sqlalchemy import select


@pytest.mark.asyncio
async def test_quarterly_review_auto_generation_and_overdue_detection(session):
    control = await create_control(
        session,
        control_code="OPS-REV-001",
        name="Quarterly dependency review",
        category="operational",
        review_frequency="quarterly",
    )
    await session.commit()

    reviews = (await session.execute(select(CommercialOperationalReview).where(CommercialOperationalReview.control_id == control.id))).scalars().all()
    assert len(reviews) == 1
    assert reviews[0].status == "pending"

    overdue = await detect_overdue_reviews(session, control_id=control.id, as_of=reviews[0].created_at + timedelta(days=120))
    await session.commit()
    assert len(overdue) == 1
    assert overdue[0].status == "overdue"


@pytest.mark.asyncio
async def test_review_completion_generates_next_pending_review(session):
    control = await create_control(
        session,
        control_code="OPS-REV-002",
        name="Access review cadence",
        category="security",
        review_frequency="quarterly",
    )
    review = (await session.execute(select(CommercialOperationalReview).where(CommercialOperationalReview.control_id == control.id))).scalar_one()

    completed = await complete_review(
        session,
        review_id=review.id,
        reviewed_by="reviewer@example.com",
        findings="No critical gaps.",
        recommendations="Refresh one export.",
        create_policy_attestation=True,
    )
    await session.commit()

    assert completed.status == "completed"
    assert completed.completed_at is not None

    reviews = (
        await session.execute(
            select(CommercialOperationalReview)
            .where(CommercialOperationalReview.control_id == control.id)
            .order_by(CommercialOperationalReview.created_at.asc())
        )
    ).scalars().all()
    assert len(reviews) == 2
    assert reviews[0].status == "completed"
    assert reviews[1].status == "pending"
