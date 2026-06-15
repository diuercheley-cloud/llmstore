import os

from control_plane.app.services.flag_loader import FlagLoader


def test_flag_hierarchy():
    loader = FlagLoader(profile="local")
    # Should get from environment specific
    assert loader.get("CREATE_TABLES_ON_STARTUP") is True

    loader_prod = FlagLoader(profile="production")
    assert loader_prod.get("CREATE_TABLES_ON_STARTUP") is False

    # Should get from product
    assert loader.get("ABUSE_DETECTION_ENABLED") is True


def test_flag_env_override():
    os.environ["FF_AGENT_MARKETPLACE_ENABLED"] = "false"
    loader = FlagLoader()
    assert loader.get("AGENT_MARKETPLACE_ENABLED") is False
    del os.environ["FF_AGENT_MARKETPLACE_ENABLED"]
