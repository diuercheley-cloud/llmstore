from app.api.commercial_crypto_admin import router
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()
app.include_router(router, prefix="/admin/crypto")

client = TestClient(app)

def test_get_trust_chain_mock():
    # In a real setup, we would override deps.get_db
    response = client.get("/admin/crypto/trust-chain")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert len(data["nodes"]) == 3
    assert len(data["links"]) == 2
    assert data["nodes"][0]["id"] == "root-ca"
