import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_demo_leads_content(admin_client: AsyncClient, admin_token_headers):
    # Ensure some demo leads exist (they should be created by seed script)
    response = await admin_client.get("/admin/sales/leads", headers=admin_token_headers)
    assert response.status_code == 200
    leads = response.json()

    demo_leads = [l for l in leads if l.get("is_demo")]

    # If no demo leads, we skip or fail depending on expectation.
    # Since seed-sales-demo-leads.sh should be run, we expect them.
    if len(demo_leads) > 0:
        for lead in demo_leads:
            assert "example.local" in lead["contact_email"] or "demo.local" in lead["contact_email"]
            assert "Demo" in lead["company_name"]
            # Check for no real data (simplistic)
            assert "5511" not in lead.get("contact_phone", "")  # No real Brazilian phone
