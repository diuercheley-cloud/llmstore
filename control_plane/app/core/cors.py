import re


def resolve_cors_origins(
    configured_origins: str,
    public_base_url: str,
    localhost_mode: bool,
    local_appliance_mode: bool,
) -> list[str]:
    raw_origins = [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
    origins: list[str] = []

    for origin in raw_origins:
        if origin == "*":
            if local_appliance_mode:
                continue
            return ["*"]
        if origin.startswith(("http://", "https://")):
            origins.append(origin.rstrip("/"))

    if localhost_mode or local_appliance_mode:
        if public_base_url.startswith(("http://", "https://")):
            origin = public_base_url.rstrip("/")
            if origin not in origins:
                origins.append(origin)

        localhost_variants = [
            "http://localhost",
            "http://127.0.0.1",
            "http://0.0.0.0",
        ]
        match = re.search(r":(\d+)", public_base_url) if public_base_url else None
        public_port = match.group(1) if match else None

        for base in localhost_variants:
            if base not in origins:
                origins.append(base)
            if public_port:
                origin_with_port = f"{base}:{public_port}"
                if origin_with_port not in origins:
                    origins.append(origin_with_port)
            if not local_appliance_mode:
                for port in ("18080", "3000", "3001"):
                    origin_with_port = f"{base}:{port}"
                    if origin_with_port not in origins:
                        origins.append(origin_with_port)

    return sorted(set(origins))


def get_cors_warnings(configured_origins: str, local_appliance_mode: bool) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    raw_origins = [origin.strip() for origin in configured_origins.split(",") if origin.strip()]

    if local_appliance_mode:
        if not raw_origins:
            warnings.append(
                {
                    "id": "CORS_EMPTY_APPLIANCE",
                    "severity": "medium",
                    "message": "CORS_ALLOW_ORIGINS is empty in appliance mode. Using secure local defaults.",
                }
            )
        if "*" in raw_origins:
            warnings.append(
                {
                    "id": "CORS_WILDCARD_APPLIANCE",
                    "severity": "high",
                    "message": "Wildcard '*' CORS is not allowed in LOCAL_APPLIANCE_MODE and was ignored.",
                }
            )

    for origin in raw_origins:
        if origin != "*" and not origin.startswith(("http://", "https://")):
            warnings.append(
                {
                    "id": "CORS_INVALID_ORIGIN",
                    "severity": "low",
                    "message": f"Invalid CORS origin ignored: {origin}. Must start with http:// or https://",
                }
            )

    return warnings
