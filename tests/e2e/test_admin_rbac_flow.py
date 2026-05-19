import pytest
import httpx
import os

@pytest.mark.asyncio
async def test_admin_rbac_flow(e2e_client, admin_headers):
    # 1. Criar admin user
    user_payload = {
        "username": "e2e-admin",
        "display_name": "E2E Admin",
        "email": "e2e@example.com",
        "password": "strong-password-123",
        "role_names": []
    }
    resp = await e2e_client.post("/admin/rbac/users", json=user_payload, headers=admin_headers)
    assert resp.status_code == 201
    user_data = resp.json()
    user_id = user_data["user"]["id"]

    # 2. Atribuir role (precisamos de uma role que exista ou criar uma)
    # No seed, deve existir 'super-admin', 'read-only', etc.
    # Vamos criar uma role customizada para testar permissões granulares
    role_payload = {
        "name": "model-manager",
        "description": "Can manage models but not users",
        "permission_codes": ["models:read", "models:write"]
    }
    resp = await e2e_client.post("/admin/rbac/roles", json=role_payload, headers=admin_headers)
    assert resp.status_code == 201
    
    # Atribuir a role ao user
    update_payload = {"role_names": ["model-manager"]}
    resp = await e2e_client.patch(f"/admin/rbac/users/{user_id}", json=update_payload, headers=admin_headers)
    assert resp.status_code == 200

    # Login com o novo usuário para obter um token
    # No backend real não existe /admin/rbac/login, usamos o token diretamente
    user_token = user_data["admin_token"]
    user_headers = {"X-Admin-Token": user_token}

    # 3. Acessar endpoint permitido (models list)
    resp = await e2e_client.get("/admin/models", headers=user_headers)
    assert resp.status_code == 200

    # 4. Bloquear endpoint sem permissão (rbac users list)
    resp = await e2e_client.get("/admin/rbac/users", headers=user_headers)
    assert resp.status_code == 403

    # 5. Verificar audit event
    audit_resp = await e2e_client.get("/admin/rbac/audit", headers=admin_headers)
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    # Deve haver eventos de criação de user, role, etc.
    assert len(events) > 0
    # Verificar se o acesso negado foi logado
    denied_events = [e for e in events if e["event_type"] == "admin.permission.denied"]
    assert len(denied_events) > 0
