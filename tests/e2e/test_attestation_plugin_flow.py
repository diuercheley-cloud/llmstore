import pytest
import uuid

@pytest.mark.asyncio
async def test_attestation_plugin_flow(e2e_client, admin_headers):
    # 0. Inicializar PKI (necessário para gerar reports)
    # /admin/security/pki/init
    # Note: dependendo da versão pode ser /admin/pki/init. 
    # Em pki_attestation_admin.py o prefixo é /admin/security.
    await e2e_client.post("/admin/security/pki/init", headers=admin_headers)

    # 1. Gerar attestation report
    # /admin/security/attestation/report
    resp = await e2e_client.get("/admin/security/attestation/report", headers=admin_headers)
    assert resp.status_code == 200
    report = resp.json()
    assert "signature" in report

    # 2. Validar assinatura
    resp = await e2e_client.post("/admin/security/attestation/verify", json=report, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["verified"] is True

    # 3. Carregar plugin fake válido (via ABI Contract)
    client_resp = await e2e_client.post("/admin/clients", json={"name": "Plugin Client"}, headers=admin_headers)
    client_id = client_resp.json()["id"]
    
    contract_payload = {
        "client_id": client_id,
        "plugin_name": "e2e-plugin",
        "plugin_version": "1.0.0",
        "abi_version": "v1",
        "schema_version": "1.0",
        "contract_scope": "attestation",
        "contract_status": "active"
    }
    resp = await e2e_client.post("/admin/operations/plugin-runtime/contracts", json=contract_payload, headers=admin_headers)
    assert resp.status_code == 200
    contract_data = resp.json()["contract"]
    assert contract_data["plugin_name"] == "e2e-plugin"

    # 4. Validar hash imutável
    assert "immutable_hash" in contract_data
