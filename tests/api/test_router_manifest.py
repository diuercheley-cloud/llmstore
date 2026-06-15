from app.bootstrap.router_manifest import ROUTER_MANIFEST


def test_no_duplicate_routers():
    seen = set()
    for entry in ROUTER_MANIFEST:
        key = (entry["module"], entry["router_name"])
        assert key not in seen, f"Duplicate router found: {key}"
        seen.add(key)


def test_manifest_is_not_empty():
    assert len(ROUTER_MANIFEST) > 0, "Router manifest should not be empty"
