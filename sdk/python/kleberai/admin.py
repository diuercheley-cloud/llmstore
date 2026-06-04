from typing import Any, Dict, List


class AdminAPI:
    def __init__(self, client):
        self.client = client

    def list_clients(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/clients")

    def create_client(self, client_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/clients", json=client_def)

    def update_client(self, client_id: str, client_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("PATCH", f"/admin/clients/{client_id}", json=client_def)

    def delete_client(self, client_id: str) -> Dict[str, Any]:
        return self.client._request("DELETE", f"/admin/clients/{client_id}")

    def block_client(self, client_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/clients/{client_id}/block")

    def unblock_client(self, client_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/clients/{client_id}/unblock")

    def suspend_client(self, client_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/security/clients/{client_id}/suspend")

    def unsuspend_client(self, client_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/security/clients/{client_id}/unsuspend")

    def list_api_keys(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/api-keys")

    def create_api_key(self, key_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/api-keys", json=key_def)

    def rotate_api_key(self, api_key_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/api-keys/{api_key_id}/rotate")

    def delete_api_key(self, api_key_id: str) -> Dict[str, Any]:
        return self.client._request("DELETE", f"/admin/api-keys/{api_key_id}")

    def list_models(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/models")

    def create_model(self, model_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/models", json=model_def)

    def update_model(self, model_id: str, model_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("PATCH", f"/admin/models/{model_id}", json=model_def)

    def delete_model(self, model_id: str) -> Dict[str, Any]:
        return self.client._request("DELETE", f"/admin/models/{model_id}")

    def enable_model(self, model_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/models/{model_id}/enable")

    def disable_model(self, model_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/models/{model_id}/disable")

    def list_backends(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/backends")

    def create_backend(self, backend_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/backends", json=backend_def)

    def update_backend(self, backend_id: str, backend_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("PATCH", f"/admin/backends/{backend_id}", json=backend_def)

    def get_backend_health(self, backend_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/admin/backends/{backend_id}/health")

    def start_backend(self, backend_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/backends/{backend_id}/start")

    def stop_backend(self, backend_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/backends/{backend_id}/stop")

    def restart_backend(self, backend_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/backends/{backend_id}/restart")

    def test_backend_connection(self, backend_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/backends/test-connection", json=backend_def)

    def get_usage_summary(self) -> Dict[str, Any]:
        return self.client._request("GET", "/admin/usage/summary")

    def get_revenue_summary(self) -> Dict[str, Any]:
        return self.client._request("GET", "/admin/revenue/summary")

    # Billing
    def list_billing_plans(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/billing/plans")

    def create_billing_plan(self, plan_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/billing/plans", json=plan_def)

    def list_invoices(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/billing/invoices")

    def generate_invoices(self) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/billing/invoices/generate")

    def list_payments(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/billing/payments")

    def record_payment(self, payment_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/billing/payments", json=payment_def)

    # Security
    def list_security_events(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/security/events")

    def get_security_report(self) -> Dict[str, Any]:
        return self.client._request("GET", "/admin/security/latest")

    # RBAC
    def list_rbac_users(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/rbac/users")

    def create_rbac_user(self, user_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/rbac/users", json=user_def)

    def update_rbac_user(self, user_id: str, user_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("PATCH", f"/admin/rbac/users/{user_id}", json=user_def)

    def delete_rbac_user(self, user_id: str) -> Dict[str, Any]:
        return self.client._request("DELETE", f"/admin/rbac/users/{user_id}")

    def list_rbac_roles(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/rbac/roles")

    def create_rbac_role(self, role_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/rbac/roles", json=role_def)

    def list_rbac_permissions(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/rbac/permissions")

    def get_rbac_audit(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/rbac/audit")

    # Test / Admin users
    def whoami(self) -> Dict[str, Any]:
        return self.client._request("GET", "/admin/tests/auth/whoami")

    def get_user(self, user_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/admin/tests/users/{user_id}")

    def block_user(self, user_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/tests/users/{user_id}/block")

    def unblock_user(self, user_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/tests/users/{user_id}/unblock")

    def set_user_plan(self, user_id: str, plan_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/tests/users/{user_id}/plan", json=plan_def)
