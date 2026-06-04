import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import httpx

# Adiciona o diretório do SDK ao path para teste
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from kleberai import Client, KleberAIError


class TestClient(unittest.TestCase):
    def setUp(self):
        self.client = Client(api_key="test-key")

    @patch("httpx.Client.request")
    def test_chat_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello!"}}]
        }
        mock_request.return_value = mock_response

        response = self.client.chat("Hi")
        self.assertEqual(response["choices"][0]["message"]["content"], "Hello!")
        
        # Verifica se o payload foi enviado corretamente
        args, kwargs = mock_request.call_args
        self.assertEqual(kwargs["json"]["messages"][0]["content"], "Hi")

    @patch("httpx.Client.request")
    def test_models_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": "model-1"}]
        }
        mock_request.return_value = mock_response

        models = self.client.models()
        self.assertEqual(len(models), 1)
        self.assertEqual(models[0]["id"], "model-1")

    @patch("httpx.Client.request")
    def test_error_handling(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )
        mock_request.return_value = mock_response

        with self.assertRaises(KleberAIError):
            self.client.models()

if __name__ == "__main__":
    unittest.main()
