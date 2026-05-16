def compatibility_status(source_version: str, target_version: str) -> str:
    return "compatible" if source_version.split(".")[0] == target_version.split(".")[0] else "breaking"

