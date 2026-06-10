import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_lead(admin_client: AsyncClient, admin_token_headers):
    payload = {
        "company_name": "Test Company",
        "contact_name": "Test Contact",
        "contact_email": "test@example.local",
        "segment": "Test Segment",
        "source": "Test Source",
        "estimated_value": 1000.0,
        "is_demo": True
    }
    response = await admin_client.post("/admin/sales/leads", json=payload, headers=admin_token_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["company_name"] == "Test Company"
    assert "id" in data
    return data["id"]

@pytest.mark.asyncio
async def test_list_leads(admin_client: AsyncClient, admin_token_headers):
    response = await admin_client.get("/admin/sales/leads", headers=admin_token_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_get_lead(admin_client: AsyncClient, admin_token_headers):
    # Create first
    payload = {
        "company_name": "Get Test",
        "contact_name": "Contact",
        "contact_email": "get@example.local",
        "segment": "Test",
        "source": "Test",
        "is_demo": True
    }
    create_res = await admin_client.post("/admin/sales/leads", json=payload, headers=admin_token_headers)
    lead_id = create_res.json()["id"]

    response = await admin_client.get(f"/admin/sales/leads/{lead_id}", headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["company_name"] == "Get Test"

@pytest.mark.asyncio
async def test_update_lead(admin_client: AsyncClient, admin_token_headers):
    # Create first
    payload = {
        "company_name": "Update Test",
        "contact_name": "Contact",
        "contact_email": "update@example.local",
        "segment": "Test",
        "source": "Test",
        "is_demo": True
    }
    create_res = await admin_client.post("/admin/sales/leads", json=payload, headers=admin_token_headers)
    lead_id = create_res.json()["id"]

    update_payload = {"company_name": "Updated Name", "status": "contacted"}
    response = await admin_client.patch(f"/admin/sales/leads/{lead_id}", json=update_payload, headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["company_name"] == "Updated Name"
    assert response.json()["status"] == "contacted"

@pytest.mark.asyncio
async def test_advance_stage(admin_client: AsyncClient, admin_token_headers):
    # Create first
    payload = {
        "company_name": "Stage Test",
        "contact_name": "Contact",
        "contact_email": "stage@example.local",
        "segment": "Test",
        "source": "Test",
        "status": "new",
        "is_demo": True
    }
    create_res = await admin_client.post("/admin/sales/leads", json=payload, headers=admin_token_headers)
    lead_id = create_res.json()["id"]

    advance_payload = {"new_status": "demo_scheduled", "note": "Scheduled via test"}
    response = await admin_client.post(f"/admin/sales/leads/{lead_id}/advance-stage", json=advance_payload, headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "demo_scheduled"
    assert len(response.json()["timeline_notes"]) >= 1

@pytest.mark.asyncio
async def test_add_note(admin_client: AsyncClient, admin_token_headers):
    # Create first
    payload = {
        "company_name": "Note Test",
        "contact_name": "Contact",
        "contact_email": "note@example.local",
        "segment": "Test",
        "source": "Test",
        "is_demo": True
    }
    create_res = await admin_client.post("/admin/sales/leads", json=payload, headers=admin_token_headers)
    lead_id = create_res.json()["id"]

    note_payload = {"content": "Test note content"}
    response = await admin_client.post(f"/admin/sales/leads/{lead_id}/notes", json=note_payload, headers=admin_token_headers)
    assert response.status_code == 200
    assert any(n["content"] == "Test note content" for n in response.json()["timeline_notes"])

@pytest.mark.asyncio
async def test_delete_lead(admin_client: AsyncClient, admin_token_headers):
    # Create first
    payload = {
        "company_name": "Delete Test",
        "contact_name": "Contact",
        "contact_email": "delete@example.local",
        "segment": "Test",
        "source": "Test",
        "is_demo": True
    }
    create_res = await admin_client.post("/admin/sales/leads", json=payload, headers=admin_token_headers)
    lead_id = create_res.json()["id"]

    response = await admin_client.delete(f"/admin/sales/leads/{lead_id}", headers=admin_token_headers)
    assert response.status_code == 204

    get_res = await admin_client.get(f"/admin/sales/leads/{lead_id}", headers=admin_token_headers)
    assert get_res.status_code == 404
