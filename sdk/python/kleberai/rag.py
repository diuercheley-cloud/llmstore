import httpx
from typing import Any, Dict, List, Optional


class RAGAPI:
    def __init__(self, client):
        self.client = client

    def query(self, question: str, **kwargs) -> Dict[str, Any]:
        payload = {"question": question, **kwargs}
        return self.client._request("POST", "/v1/rag/query", json=payload)

    def search(self, query: str, collection_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Alias for query to match intuitive naming."""
        payload = {"question": query, "collection_id": collection_id, **kwargs}
        return self.client._request("POST", "/v1/rag/query", json=payload)

    def upload_file(self, file_path: str, collection_id: Optional[str] = None) -> Dict[str, Any]:
        """Upload a file using multipart/form-data."""
        url = f"{self.client.base_url}/v1/rag/files"
        data = {}
        if collection_id:
            data["collection_id"] = collection_id

        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.split("/")[-1], f)}
                with httpx.Client(timeout=self.client.timeout) as client:
                    response = client.post(url, headers=self.client.headers, data=data, files=files)
                    response.raise_for_status()
                    return response.json()
        except Exception as e:
            from .client import KleberAIError

            raise KleberAIError(f"Upload failed: {str(e)}")

    def upload_document(
        self, file_path: str, collection_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Alias for upload_file to match documentation."""
        return self.upload_file(file_path, collection_id)

    def list_files(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/v1/rag/files")

    def get_file(self, file_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/v1/rag/files/{file_id}")

    def delete_file(self, file_id: str) -> Dict[str, Any]:
        return self.client._request("DELETE", f"/v1/rag/files/{file_id}")

    def reprocess_file(self, file_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/v1/rag/files/{file_id}/reprocess")

    def get_usage(self) -> Dict[str, Any]:
        return self.client._request("GET", "/v1/rag/usage")

    def create_collection(self, collection_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/v1/rag/collections", json=collection_def)

    def list_collections(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/v1/rag/collections")

    def list_vaults(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/rag/vaults")

    def create_vault(self, vault_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/rag/vaults", json=vault_def)

    def get_overview(self) -> Dict[str, Any]:
        return self.client._request("GET", "/admin/rag/overview")

    def list_admin_documents(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/rag/documents")

    def create_admin_document(self, doc_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/rag/documents", json=doc_def)

    def get_retrieval_audit(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/rag/retrieval-audit")

    def list_legal_holds(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/rag/legal-holds")

    def create_legal_hold(self, hold_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/rag/legal-holds", json=hold_def)

    def reindex(self) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/rag/reindex")
