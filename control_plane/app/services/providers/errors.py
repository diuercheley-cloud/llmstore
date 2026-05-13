class ProviderError(Exception):
    def __init__(self, provider_id: str, message: str, sanitized: str | None = None):
        self.provider_id = provider_id
        self.sanitized = sanitized or message
        super().__init__(message)


class ProviderNotConfiguredError(ProviderError):
    def __init__(self, provider_id: str):
        super().__init__(
            provider_id=provider_id,
            message=f"Provider {provider_id} is not configured",
            sanitized=f"provider {provider_id} not configured",
        )


class ProviderTimeoutError(ProviderError):
    def __init__(self, provider_id: str, timeout_seconds: int):
        super().__init__(
            provider_id=provider_id,
            message=f"Provider {provider_id} timed out after {timeout_seconds}s",
            sanitized=f"provider {provider_id} timed out",
        )


class ProviderAuthError(ProviderError):
    def __init__(self, provider_id: str):
        super().__init__(
            provider_id=provider_id,
            message=f"Provider {provider_id} authentication failed",
            sanitized=f"provider {provider_id} auth error",
        )


class ProviderApiError(ProviderError):
    def __init__(self, provider_id: str, status_code: int):
        super().__init__(
            provider_id=provider_id,
            message=f"Provider {provider_id} returned HTTP {status_code}",
            sanitized=f"provider {provider_id} HTTP {status_code}",
        )
