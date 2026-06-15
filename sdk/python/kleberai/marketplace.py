from typing import Any, Dict, List


class MarketplaceAPI:
    def __init__(self, client):
        self.client = client

    def list_items(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/v1/marketplace/items")

    def publish_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/v1/marketplace/items", json=item)

    def get_item(self, item_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/v1/marketplace/items/{item_id}")

    def update_item(self, item_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("PUT", f"/v1/marketplace/items/{item_id}", json=item)

    def rate_item(self, item_id: str, rating: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", f"/v1/marketplace/items/{item_id}/rate", json=rating)

    def list_reviews(self, item_id: str) -> List[Dict[str, Any]]:
        return self.client._request("GET", f"/v1/marketplace/items/{item_id}/reviews")

    def download_item(self, item_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/v1/marketplace/items/{item_id}/download")

    def list_categories(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/v1/marketplace/categories")

    def list_my_items(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/v1/marketplace/my-items")

    def register_publisher(self, info: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/v1/marketplace/publishers/register", json=info)

    def get_my_publisher(self) -> Dict[str, Any]:
        return self.client._request("GET", "/v1/marketplace/publishers/me")

    # Admin endpoints
    def admin_list(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agent-marketplace")

    def admin_install(self, install_request: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request(
            "POST", "/admin/agent-marketplace/install", json=install_request
        )

    def admin_enable_install(self, install_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agent-marketplace/{install_id}/enable")

    def admin_disable_install(self, install_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agent-marketplace/{install_id}/disable")

    def admin_verify_bundle(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agent-marketplace/bundles/verify", json=bundle)

    def admin_publish_bundle(self, bundle_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agent-marketplace/bundles/{bundle_id}/publish")

    def admin_review_bundle(self, bundle_id: str, review: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request(
            "POST", f"/admin/agent-marketplace/bundles/{bundle_id}/review", json=review
        )

    def get_trust_report(self, version_id: str) -> Dict[str, Any]:
        return self.client._request(
            "GET", f"/admin/agent-marketplace/versions/{version_id}/trust-report"
        )
