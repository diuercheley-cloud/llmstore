import os
import json
import logging
from typing import List, Dict, Any, Optional, Union, BinaryIO
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

class LLMStackClient:
    """
    Client for the LLM Inference Stack.
    Supports Inference (OpenAI-compatible), Portal (Account Management), and RAG.
    """

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

    # --- Inference API (OpenAI Compatible) ---

    def chat_completions(
        self, 
        messages: List[Dict[str, str]], 
        model: str = "default",
        temperature: float = 0.7,
        max_tokens: int = 512,
        stream: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], Any]:
        """
        Create a chat completion.
        """
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            **kwargs
        }
        
        if stream:
            return self._stream_request("POST", url, json=payload)
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

    def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models.
        """
        url = f"{self.base_url}/v1/models"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            # Handle both OpenAI format and internal format
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            return data

    # --- Portal API (Management) ---

    def get_account_info(self) -> Dict[str, Any]:
        """
        Get current account and plan information.
        """
        url = f"{self.base_url}/portal/me"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    def get_usage(self) -> Dict[str, Any]:
        """
        Get detailed usage statistics.
        """
        url = f"{self.base_url}/portal/usage"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    def list_api_keys(self) -> List[Dict[str, Any]]:
        """
        List your API keys.
        """
        url = f"{self.base_url}/portal/api-keys"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    def create_api_key(self, name: str) -> Dict[str, Any]:
        """
        Create a new API key.
        """
        url = f"{self.base_url}/portal/api-keys"
        payload = {"name": name}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

    # --- RAG API ---

    def rag_upload(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Upload a document for RAG.
        Supported: .pdf, .txt, .md
        """
        url = f"{self.base_url}/client/rag/documents"
        file_path = Path(file_path)
        
        headers = self.headers.copy()
        del headers["Content-Type"] # httpx handles multipart content type
        
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f)}
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=headers, files=files)
                response.raise_for_status()
                return response.json()

    def rag_query(
        self, 
        question: str, 
        model: str = "default",
        top_k: int = 3,
        max_tokens: int = 512
    ) -> Dict[str, Any]:
        """
        Query your documents using RAG.
        """
        url = f"{self.base_url}/client/rag/query"
        payload = {
            "question": question,
            "model": model,
            "top_k": top_k,
            "max_tokens": max_tokens
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

    def get_rag_usage(self) -> Dict[str, Any]:
        """
        Get RAG specific usage and limits.
        """
        url = f"{self.base_url}/client/rag/usage"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    # --- Internal Helpers ---

    def _stream_request(self, method: str, url: str, **kwargs):
        """
        Handle streaming responses.
        """
        with httpx.Client(timeout=self.timeout) as client:
            with client.stream(method, url, headers=self.headers, **kwargs) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        content = line[6:]
                        if content == "[DONE]":
                            break
                        try:
                            yield json.loads(content)
                        except json.JSONDecodeError:
                            continue

if __name__ == "__main__":
    # Example usage:
    # client = LLMStackClient(api_key="sk_your_key_here")
    # print(client.list_models())
    print("LLM Stack Client SDK loaded. Use as a library.")
