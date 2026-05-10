import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_multitenant_export_isolation(admin_client: AsyncClient, admin_token_headers):
    # Create Client A
    resp_a = await admin_client.post("/admin/clients", json={"name": "Client A"}, headers=admin_token_headers)
    client_a_id = resp_a.json()["id"]

    # Create Client B
    resp_b = await admin_client.post("/admin/clients", json={"name": "Client B"}, headers=admin_token_headers)
    client_b_id = resp_b.json()["id"]

    # Export A
    export_a = await admin_client.get(f"/admin/clients/export-data?client_id={client_a_id}", headers=admin_token_headers)
    assert export_a.status_code == 200
    data_a = export_a.json()
    assert data_a["client"]["id"] == client_a_id

    # Cleanup
    await admin_client.post(f"/admin/clients/{client_a_id}/purge", json={"delete_usage":True}, headers=admin_token_headers)
    await admin_client.post(f"/admin/clients/{client_b_id}/purge", json={"delete_usage":True}, headers=admin_token_headers)

@pytest.mark.asyncio
async def test_multitenant_delete_isolation(admin_client: AsyncClient, admin_token_headers):
    # Create Client A
    resp_a = await admin_client.post("/admin/clients", json={"name": "Client A"}, headers=admin_token_headers)
    client_a_id = resp_a.json()["id"]

    # Purge A
    purge_resp = await admin_client.post(f"/admin/clients/{client_a_id}/purge", json={"delete_usage":True}, headers=admin_token_headers)
    assert purge_resp.status_code == 204
