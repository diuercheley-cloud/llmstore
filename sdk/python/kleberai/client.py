import httpx
from typing import List, Optional, Union, Any, Dict

from .agents import AgentsAPI, AgentEvalsAPI

class KleberAIError(Exception):
    """Base exception for Kleber AI SDK"""
    pass

class Client:
    def __init__(
        self, 
        api_key: str, 
        base_url: str = "http://localhost:18080",
        timeout: float = 60.0
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.agents = AgentsAPI(self)
        self.agent_evals = AgentEvalsAPI(self)

    def _request(self, method: str, path: str, json: Any = None) -> Any:
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(method, url, headers=self.headers, json=json)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            raise KleberAIError(f"HTTP error: {e.response.status_code} - {e.response.text}") from e
        except Exception as e:
            raise KleberAIError(f"Request failed: {str(e)}") from e

    def chat(
        self, 
        messages: Union[str, List[Dict[str, str]]], 
        model: str = "default",
        **kwargs
    ) -> Dict[str, Any]:
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        
        payload = {
            "model": model,
            "messages": messages,
            **kwargs
        }
        return self._request("POST", "/v1/chat/completions", json=payload)

    def models(self) -> List[Dict[str, Any]]:
        response = self._request("GET", "/v1/models")
        return response.get("data", [])

    def embeddings(self, input: Union[str, List[str]], model: str = "default") -> Dict[str, Any]:
        if isinstance(input, str):
            input = [input]
        payload = {
            "input": input,
            "model": model
        }
        return self._request("POST", "/v1/embeddings", json=payload)

    def rag_query(
        self, 
        question: str, 
        file_ids: Optional[List[str]] = None, 
        model: str = "default",
        **kwargs
    ) -> Dict[str, Any]:
        payload = {
            "question": question,
            "file_ids": file_ids,
            "model": model,
            **kwargs
        }
        return self._request("POST", "/client/rag/query", json=payload)
