import pytest


@pytest.mark.asyncio
async def test_billing_tokenization_flow(e2e_client, admin_headers):
    # 1. Criar cliente e API key
    client_resp = await e2e_client.post(
        "/admin/clients", json={"name": "Billing Client"}, headers=admin_headers
    )
    assert client_resp.status_code == 201
    client_id = client_resp.json()["id"]

    key_resp = await e2e_client.post(
        "/admin/api-keys",
        json={"client_id": client_id, "name": "Billing Key"},
        headers=admin_headers,
    )
    assert key_resp.status_code == 201
    api_key = key_resp.json()["api_key"]
    client_headers = {"Authorization": f"Bearer {api_key}"}

    # 2. Registrar backend e modelo
    backend_payload = {
        "name": "billing-backend",
        "provider": "openai_compatible",
        "backend_url": "http://localhost:8081",
        "enabled": True,
        "priority": 1,
    }
    resp = await e2e_client.post("/admin/backends", json=backend_payload, headers=admin_headers)
    backend_id = resp.json()["id"]

    model_payload = {
        "model_id": "billing-model",
        "display_name": "Billing Model",
        "inference_backend_id": backend_id,
        "provider": "openai_compatible",
        "model_file": "billing-model.gguf",
        "is_active": True,
    }
    await e2e_client.post("/admin/models", json=model_payload, headers=admin_headers)

    # 3. Fazer request de chat
    chat_payload = {
        "model": "billing-model",
        "messages": [{"role": "user", "content": "Count my tokens please"}],
    }
    # Fazemos duas requests para garantir volume
    await e2e_client.post("/v1/chat/completions", json=chat_payload, headers=client_headers)
    await e2e_client.post("/v1/chat/completions", json=chat_payload, headers=client_headers)

    # 4. Validar que o usage record foi criado com token count
    usage_resp = await e2e_client.get(
        f"/admin/clients/export-data?client_id={client_id}", headers=admin_headers
    )
    assert usage_resp.status_code == 200
    usage = usage_resp.json()["usage"]
    assert len(usage) >= 1
    # O data_plane_mock retorna 20 tokens por request.
    # Dependendo de como é agregado (por dia/mês), somamos.
    total_tokens = sum(u["prompt_tokens"] + u["completion_tokens"] for u in usage)
    assert total_tokens >= 30

    # 5. Gerar invoice simulada
    # POST /admin/billing/invoices/generate
    gen_payload = {"client_id": client_id, "force": True}
    gen_resp = await e2e_client.post(
        "/admin/billing/invoices/generate", json=gen_payload, headers=admin_headers
    )
    assert gen_resp.status_code == 201

    invoices = gen_resp.json()["created"]
    if not invoices:
        invoices = gen_resp.json()["updated"]

    assert len(invoices) > 0
    invoice = invoices[0]

    # 6. Validar valores sem dinheiro real
    assert "total_amount" in invoice

    # Verificar se aparece no portal do cliente
    portal_resp = await e2e_client.get("/portal/invoices", headers=client_headers)
    assert portal_resp.status_code == 200
    portal_invoices = portal_resp.json()["invoices"]
    assert any(inv["id"] == invoice["id"] for inv in portal_invoices)
