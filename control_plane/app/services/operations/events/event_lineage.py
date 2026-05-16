def build_lineage(records: list[dict]) -> list[str]:
    return [record["event_hash"] for record in records]

