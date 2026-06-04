
import pytest


@pytest.mark.asyncio
async def test_rag_flow(e2e_client, admin_headers):
    # 0. Registrar um backend + modelo para o RAG query usar (precisa de LLM ativo)
    backend_payload = {
        "name": "rag-backend",
        "provider": "openai_compatible",
        "backend_url": "http://localhost:8081",
        "enabled": True,
        "priority": 1,
        "metadata_json": "{}"
    }
    resp = await e2e_client.post("/admin/backends", json=backend_payload, headers=admin_headers)
    assert resp.status_code == 201
    backend_id = resp.json()["id"]

    model_payload = {
        "model_id": "rag-model",
        "display_name": "RAG Model",
        "inference_backend_id": backend_id,
        "provider": "openai_compatible",
        "model_file": "rag-model.gguf",
        "is_active": True
    }
    resp = await e2e_client.post("/admin/models", json=model_payload, headers=admin_headers)
    assert resp.status_code == 201

    # 1. Criar clientes e chaves
    async def create_client(name):
        resp = await e2e_client.post("/admin/clients", json={"name": name}, headers=admin_headers)
        assert resp.status_code == 201
        c_id = resp.json()["id"]
        k_resp = await e2e_client.post("/admin/api-keys", json={"client_id": c_id, "name": name}, headers=admin_headers)
        assert k_resp.status_code == 201
        return c_id, k_resp.json()["api_key"]

    client_a_id, key_a = await create_client("Client A")
    client_b_id, key_b = await create_client("Client B")
    
    headers_a = {"Authorization": f"Bearer {key_a}"}
    headers_b = {"Authorization": f"Bearer {key_b}"}

    # 2. Criar coleção para Client A
    col_payload = {"name": "A-Collection", "description": "Client A Secret Docs"}
    resp = await e2e_client.post("/v1/rag/collections", json=col_payload, headers=headers_a)
    assert resp.status_code == 200
    col_a_id = resp.json()["id"]

    # 3. Subir documento fake para Client A
    files = {"file": ("secret.txt", b"O codigo de acesso eh 12345. Apenas para o Cliente A.")}
    resp = await e2e_client.post(f"/v1/rag/documents?collection_id={col_a_id}", headers=headers_a, files=files)
    assert resp.status_code == 200
    doc_a_id = resp.json()["id"]

    # 4. Consultar retrieval e validar isolamento
    query_payload = {"question": "qual o codigo de acesso?", "top_k": 3}
    
    # Client A deve achar
    resp_q_a = await e2e_client.post("/v1/rag/query", json=query_payload, headers=headers_a)
    assert resp_q_a.status_code == 200, f"RAG query failed: {resp_q_a.text}"
    body_a = resp_q_a.json()
    # Algumas implementações usam 'sources', outras 'results'
    results_a = body_a.get("sources", body_a.get("results", []))
    assert len(results_a) > 0, f"No results found for client A: {body_a}"
    assert "12345" in results_a[0].get("text", results_a[0].get("content", ""))

    # Client B NÃO deve achar nada do Client A
    resp_q_b = await e2e_client.post("/v1/rag/query", json=query_payload, headers=headers_b)
    assert resp_q_b.status_code == 200, f"RAG query failed: {resp_q_b.text}"
    body_b = resp_q_b.json()
    results_b = body_b.get("sources", body_b.get("results", []))
    assert len(results_b) == 0, f"Client B should not see Client A data: {results_b}"
