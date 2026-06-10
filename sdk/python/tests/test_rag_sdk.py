from unittest.mock import MagicMock, patch
import pytest
from kleberai import Client

@pytest.fixture
def client():
    return Client(api_key="test-key")

def test_rag_query(client):
    with patch("httpx.Client.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"answer": "Paris"}
        mock_request.return_value = mock_response
        
        res = client.rag.query("What is the capital of France?")
        assert res["answer"] == "Paris"
        mock_request.assert_called_once()
        args, _ = mock_request.call_args
        assert args[1] == "http://localhost:18080/v1/rag/query"

def test_rag_search(client):
    with patch("httpx.Client.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"answer": "Paris"}
        mock_request.return_value = mock_response
        
        res = client.rag.search("What is the capital of France?", collection_id="my-docs")
        assert res["answer"] == "Paris"
        mock_request.assert_called_once()
        _, kwargs = mock_request.call_args
        assert kwargs["json"]["collection_id"] == "my-docs"

def test_rag_upload_document(client):
    with patch("httpx.Client.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "file-1"}
        mock_post.return_value = mock_response
        
        # We need a real file or mock open
        with patch("builtins.open", MagicMock()):
            res = client.rag.upload_document("test.pdf", collection_id="my-docs")
            assert res["id"] == "file-1"
            mock_post.assert_called_once()
            _, kwargs = mock_post.call_args
            assert kwargs["data"]["collection_id"] == "my-docs"
            assert "file" in kwargs["files"]

def test_rag_list_files(client):
    with patch("httpx.Client.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": "file-1"}]
        mock_request.return_value = mock_response
        
        files = client.rag.list_files()
        assert len(files) == 1
        assert files[0]["id"] == "file-1"
        args, _ = mock_request.call_args
        assert args[1] == "http://localhost:18080/v1/rag/files"

def test_rag_create_collection(client):
    with patch("httpx.Client.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "coll-1"}
        mock_request.return_value = mock_response
        
        coll = client.rag.create_collection({"name": "test"})
        assert coll["id"] == "coll-1"
        args, _ = mock_request.call_args
        assert args[1] == "http://localhost:18080/v1/rag/collections"
