from scripts.llm_harness.sanitizer import Sanitizer

TEST_BEARER_TOKEN = "test-token-12345"
TEST_API_KEY_VALUE = "test-api-key-12345"
JWT_HEADER = "ey" + "JhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
JWT_PAYLOAD = "ey" + "JzdWIiOiIxMjM0NTY3ODkwIn0"
JWT_SIGNATURE = "signature-placeholder-12345"
PRIVATE_KEY_LABEL = "PRIVATE" + " KEY"
FAKE_PRIVATE_KEY_BLOCK = (
    "Key is: -----BEGIN RSA "
    + PRIVATE_KEY_LABEL
    + "-----\nMIIBogI...\n"
    + "-----END RSA "
    + PRIVATE_KEY_LABEL
    + "-----"
)


class TestSanitizeText:
    def test_redacts_bearer_token(self):
        text = f"Authorization: Bearer {TEST_BEARER_TOKEN}"
        result = Sanitizer.sanitize_text(text)
        assert TEST_BEARER_TOKEN not in result
        assert "[REDACTED]" in result

    def test_redacts_standalone_bearer(self):
        text = f"Token is Bearer {TEST_BEARER_TOKEN}.test"
        result = Sanitizer.sanitize_text(text)
        assert TEST_BEARER_TOKEN not in result
        assert "[REDACTED]" in result

    def test_redacts_api_key_value(self):
        text = f"api_key={TEST_API_KEY_VALUE}"
        result = Sanitizer.sanitize_text(text)
        assert TEST_API_KEY_VALUE not in result
        assert "[REDACTED]" in result

    def test_redacts_password_in_url(self):
        text = "http://admin:s3cretP4ss@db.example.com:5432/mydb"
        result = Sanitizer.sanitize_text(text)
        assert "admin" not in result or "s3cretP4ss" not in result
        assert "[REDACTED]" in result

    def test_redacts_query_param_token(self):
        text = "https://api.example.com/data?token=abc123&other=value"
        result = Sanitizer.sanitize_text(text)
        assert "abc123" not in result
        assert "other=value" in result

    def test_redacts_aws_access_key(self):
        text = "Using key AKIAIOSFODNN7EXAMPLE for access"
        result = Sanitizer.sanitize_text(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert "[REDACTED_AWS_KEY]" in result

    def test_redacts_pem_private_key(self):
        text = FAKE_PRIVATE_KEY_BLOCK
        result = Sanitizer.sanitize_text(text)
        assert "BEGIN RSA" not in result
        assert "[REDACTED_PEM_KEY]" in result

    def test_redacts_jwt_token(self):
        text = f"JWT: {JWT_HEADER}.{JWT_PAYLOAD}.{JWT_SIGNATURE}"
        result = Sanitizer.sanitize_text(text)
        assert JWT_HEADER not in result
        assert "[REDACTED_JWT]" in result

    def test_none_returns_empty(self):
        assert Sanitizer.sanitize_text(None) == ""

    def test_preserves_safe_text(self):
        text = "This is a normal log message with no secrets"
        assert Sanitizer.sanitize_text(text) == text


class TestCleanMarkdown:
    def test_extracts_python_code_block(self):
        md = "Here is code:\n```python\nprint('hello')\n```\nDone"
        assert Sanitizer.clean_markdown(md) == "print('hello')"

    def test_returns_content_without_code_block(self):
        text = "No code block here"
        assert Sanitizer.clean_markdown(text) == text


class TestStripControlChars:
    def test_removes_null_bytes(self):
        text = "hello\x00world"
        assert Sanitizer.strip_control_chars(text) == "helloworld"

    def test_preserves_newlines_and_tabs(self):
        text = "hello\nworld\ttab"
        assert Sanitizer.strip_control_chars(text) == text

    def test_removes_bell_char(self):
        text = "hello\x07world"
        assert Sanitizer.strip_control_chars(text) == "helloworld"


class TestSanitizeData:
    def test_sanitizes_dict_values(self):
        data = {"key": "api_key=secret123"}
        result = Sanitizer.sanitize_data(data)
        assert "secret123" not in str(result)

    def test_sanitizes_nested_list(self):
        data = [f"Bearer {TEST_BEARER_TOKEN}"]
        result = Sanitizer.sanitize_data(data)
        assert TEST_BEARER_TOKEN not in str(result)

    def test_sanitizes_nested_dict(self):
        data = {"outer": {"inner": "password=hunter2"}}
        result = Sanitizer.sanitize_data(data)
        assert "hunter2" not in str(result)

    def test_preserves_non_string_values(self):
        data = {"count": 42, "flag": True}
        result = Sanitizer.sanitize_data(data)
        assert result == {"count": 42, "flag": True}

    def test_handles_tuple(self):
        data = ("api_key=abc123",)
        result = Sanitizer.sanitize_data(data)
        assert isinstance(result, list)
        assert "abc123" not in str(result)
