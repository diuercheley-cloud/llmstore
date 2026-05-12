import asyncio
from app.db.session import SessionLocal
from app.models.billing_invoice import BillingInvoice
from sqlalchemy import select

async def main():
    async with SessionLocal() as session:
        # Get the latest invoice
        result = await session.execute(select(BillingInvoice).order_by(BillingInvoice.created_at.desc()).limit(1))
        inv = result.scalars().first()
        print(f"Before: {inv.due_at}")

        # Try to modify it the same way the endpoint does
        from app.core.time import utc_now
        from datetime import timedelta
        
        inv.due_at = utc_now() - timedelta(days=16)
        inv.updated_at = utc_now()
        await session.commit()
        
        await session.refresh(inv)
        print(f"After: {inv.due_at}")

if __name__ == "__main__":
    asyncio.run(main())
