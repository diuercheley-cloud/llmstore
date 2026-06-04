import asyncio

from app.core.time import utc_now
from app.db.session import async_session_maker
from app.models.billing_invoice import BillingInvoice
from app.models.client import Client
from sqlalchemy import select


async def main():
    async with async_session_maker() as session:
        result = await session.execute(select(Client).where(Client.name.like("Debug Billing Client%")))
        client = result.scalars().first()
        if not client:
            print("Client not found")
            return
            
        print(f"Client billing_status: {client.billing_status}")
        
        result = await session.execute(select(BillingInvoice).where(BillingInvoice.client_id == client.id))
        invoices = result.scalars().all()
        for inv in invoices:
            print(f"Invoice {inv.id}: status={inv.status}, due_at={inv.due_at}")
            if inv.due_at:
                now = utc_now()
                diff = now - inv.due_at
                print(f"  now={now}")
                print(f"  diff days={diff.days}")
                print(f"  should suspend if diff.days > 15? {diff.days > 15}")

if __name__ == "__main__":
    asyncio.run(main())
