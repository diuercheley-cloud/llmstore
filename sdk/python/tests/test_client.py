import unittest
from unittest.mock import patch, MagicMock
from kleberai import Client, KleberAIError


class TestClient(unittest.TestCase):
    def setUp(self):
        self.client = Client(api_key="test-key", base_url="http://mock-api")

    @patch("httpx.Client.request")
    def test_chat_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "Hello world"}}]}
        mock_request.return_value = mock_response

        res = self.client.chat("Hi")
        self.assertEqual(res["choices"][0]["message"]["content"], "Hello world")
        mock_request.assert_called_once()

    @patch("httpx.Client.request")
    def test_models_list(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": "gpt-4", "name": "GPT-4"}]}
        mock_request.return_value = mock_response

        models = self.client.models()
        self.assertEqual(len(models), 1)
        self.assertEqual(models[0]["id"], "gpt-4")

    @patch("httpx.Client.request")
    def test_error_handling(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        # Manually trigger raise_for_status error simulation or just check how _request handles it
        import httpx

        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=mock_response
        )
        mock_request.return_value = mock_response

        with self.assertRaises(KleberAIError) as cm:
            self.client.models()
        self.assertIn("401", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
