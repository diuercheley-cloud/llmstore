import importlib.util
import os
import sys
from unittest.mock import mock_open, patch

# Setup sys.path to find scripts folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Load platform-freeze-check.py dynamically due to the dash in the filename
script_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../scripts/validators/platform-freeze-check.py")
)
spec = importlib.util.spec_from_file_location("platform_freeze_check", script_path)
platform_freeze_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(platform_freeze_check)


def test_check_top_level_dirs():
    rules = {
        "forbid_new_top_level_dirs": True,
        "allowed_top_level_dirs": ["control_plane", "config"],
        "approved_exceptions": [],
    }
    # No violation
    with (
        patch("os.listdir", return_value=["control_plane", "config", ".venv"]),
        patch("os.path.isdir", return_value=True),
    ):
        assert platform_freeze_check.check_top_level_dirs(rules) is True

    # Violation detected
    with (
        patch("os.listdir", return_value=["control_plane", "config", "new_forbidden_dir"]),
        patch("os.path.isdir", return_value=True),
    ):
        assert platform_freeze_check.check_top_level_dirs(rules) is False

    # Exception approved
    rules_with_exception = {
        "forbid_new_top_level_dirs": True,
        "allowed_top_level_dirs": ["control_plane", "config"],
        "approved_exceptions": ["new_forbidden_dir"],
    }
    with (
        patch("os.listdir", return_value=["control_plane", "config", "new_forbidden_dir"]),
        patch("os.path.isdir", return_value=True),
    ):
        assert platform_freeze_check.check_top_level_dirs(rules_with_exception) is True


def test_check_bounded_contexts():
    rules = {
        "forbid_new_bounded_contexts": True,
        "allowed_bounded_contexts": ["agents", "billing"],
        "approved_exceptions": [],
    }

    with (
        patch("os.path.exists", return_value=True),
        patch("os.listdir", return_value=["agents", "billing", "__pycache__"]),
        patch("os.path.isdir", return_value=True),
    ):
        assert platform_freeze_check.check_bounded_contexts(rules) is True

    # New context
    with (
        patch("os.path.exists", return_value=True),
        patch("os.listdir", return_value=["agents", "billing", "new_context"]),
        patch("os.path.isdir", return_value=True),
    ):
        assert platform_freeze_check.check_bounded_contexts(rules) is False

    # Context exception approved
    rules_with_exception = {
        "forbid_new_bounded_contexts": True,
        "allowed_bounded_contexts": ["agents", "billing"],
        "approved_exceptions": ["new_context"],
    }
    with (
        patch("os.path.exists", return_value=True),
        patch("os.listdir", return_value=["agents", "billing", "new_context"]),
        patch("os.path.isdir", return_value=True),
    ):
        assert platform_freeze_check.check_bounded_contexts(rules_with_exception) is True


def test_check_api_routers():
    rules = {"allowed_api_routers": ["client.py", "admin.py"], "approved_exceptions": []}

    # Case 1: Pre-existing allowed router
    with (
        patch("os.path.exists", return_value=True),
        patch("os.listdir", return_value=["client.py", "admin.py"]),
        patch("builtins.open", mock_open(read_data="""# Existing router""")),
    ):
        assert platform_freeze_check.check_api_routers(rules) is True

    # Case 2: New admin router without owner -> Fails
    with (
        patch("os.path.exists", return_value=True),
        patch("os.listdir", return_value=["client.py", "admin.py", "new_admin.py"]),
        patch(
            "builtins.open",
            mock_open(read_data="""# Surface: admin\nrouter = APIRouter(prefix="/admin")"""),
        ),
    ):
        assert platform_freeze_check.check_api_routers(rules) is False

    # Case 3: New admin router with owner and surface tag -> Passes (if approved exception)
    rules_approved = {
        "allowed_api_routers": ["client.py", "admin.py"],
        "approved_exceptions": ["new_admin.py"],
    }
    with (
        patch("os.path.exists", return_value=True),
        patch("os.listdir", return_value=["client.py", "admin.py", "new_admin.py"]),
        patch(
            "builtins.open",
            mock_open(
                read_data="""# Owner: Architecture\n# Surface: admin\nrouter = APIRouter(prefix="/admin")"""
            ),
        ),
    ):
        assert platform_freeze_check.check_api_routers(rules_approved) is True

    # Case 4: New router missing surface classification prefix or tag -> Fails (even if approved exception)
    with (
        patch("os.path.exists", return_value=True),
        patch("os.listdir", return_value=["client.py", "admin.py", "new_unclassified.py"]),
        patch(
            "builtins.open",
            mock_open(read_data="""# Owner: Dev\nrouter = APIRouter(prefix="/foo")"""),
        ),
    ):
        assert platform_freeze_check.check_api_routers(rules_approved) is False


def test_check_new_services():
    rules = {"allowed_services": ["auth.py"], "approved_exceptions": ["new_service.py"]}

    # Case 1: New service with docstring -> Passes
    with (
        patch("os.path.exists", return_value=True),
        patch(
            "os.walk",
            return_value=[("control_plane/app/services", [], ["auth.py", "new_service.py"])],
        ),
        patch("builtins.open", mock_open(read_data='"""Module docstring"""')),
    ):
        assert platform_freeze_check.check_new_services(rules) is True

    # Case 2: New service without docstring/owner -> Fails
    with (
        patch("os.path.exists", return_value=True),
        patch(
            "os.walk",
            return_value=[("control_plane/app/services", [], ["auth.py", "new_service.py"])],
        ),
        patch("builtins.open", mock_open(read_data="# no docs")),
    ):
        assert platform_freeze_check.check_new_services(rules) is False


def test_check_feature_flags():
    rules = {
        "allowed_feature_flags": ["old_flag_enabled"],
        "approved_exceptions": ["new_flag_enabled"],
    }

    # Case 1: New feature flag with Owner/Status comments -> Passes
    flag_content_ok = """
    # Owner: Architecture
    # Status: temporary
    new_flag_enabled: bool = False
    old_flag_enabled: bool = True
    """
    with (
        patch("os.path.exists", return_value=True),
        patch("builtins.open", mock_open(read_data=flag_content_ok)),
    ):
        assert platform_freeze_check.check_feature_flags(rules) is True

    # Case 2: New feature flag without Owner/Status comments -> Fails
    flag_content_bad = """
    new_flag_enabled: bool = False
    old_flag_enabled: bool = True
    """
    with (
        patch("os.path.exists", return_value=True),
        patch("builtins.open", mock_open(read_data=flag_content_bad)),
    ):
        assert platform_freeze_check.check_feature_flags(rules) is False


def test_check_models_and_migrations():
    rules = {"allowed_models": ["OldModel"], "approved_exceptions": ["NewModel"]}

    # Mock migration contents (contains NewModel name)
    migration_mock = "op.create_table('newmodel', ...)"

    # Mock model file contents
    model_content_ok = """
    # Owner: DataTeam
    class NewModel(Base):
        __tablename__ = "new_models"
    """

    with (
        patch("os.path.exists", return_value=True),
        patch("os.listdir", return_value=["0001_migration.py"]),
        patch("os.walk", return_value=[("control_plane/app/models", [], ["model.py"])]),
    ):
        # Passes with migration & owner
        with patch("builtins.open", mock_open(read_data=model_content_ok)) as mock_file:
            # First open is migrations, second is model file
            mock_file.side_effect = [
                mock_open(read_data=migration_mock)(),
                mock_open(read_data=model_content_ok)(),
            ]
            assert platform_freeze_check.check_models_and_migrations(rules) is True

        # Fails when missing migration
        with patch("builtins.open", mock_open(read_data=model_content_ok)) as mock_file:
            mock_file.side_effect = [
                mock_open(read_data="")(),
                mock_open(read_data=model_content_ok)(),
            ]
            assert platform_freeze_check.check_models_and_migrations(rules) is False


def test_check_new_endpoints():
    rules = {"require_supported_surface_classification": True}

    diff_with_endpoint = """
diff --git a/control_plane/app/api/new_router.py b/control_plane/app/api/new_router.py
+++ b/control_plane/app/api/new_router.py
@@ -10,3 +10,12 @@
+@router.get("/test-endpoint")
+async def test_endpoint():
    pass
"""

    # Mock subprocess runs
    class MockCompletedProcess:
        def __init__(self, stdout, returncode=0):
            self.stdout = stdout
            self.returncode = returncode

    # Case 1: Classified router -> Passes
    classified_router_content = """# Surface: client\nrouter = APIRouter(prefix="/client")"""
    with (
        patch("os.path.exists", return_value=True),
        patch("builtins.open", mock_open(read_data=classified_router_content)),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.side_effect = [
            MockCompletedProcess(""),  # rev-parse
            MockCompletedProcess(diff_with_endpoint),  # git diff
        ]
        assert platform_freeze_check.check_new_endpoints(rules) is True

    # Case 2: Unclassified router -> Fails
    unclassified_router_content = """router = APIRouter(prefix="/other")"""
    with (
        patch("os.path.exists", return_value=True),
        patch("builtins.open", mock_open(read_data=unclassified_router_content)),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.side_effect = [
            MockCompletedProcess(""),  # rev-parse
            MockCompletedProcess(diff_with_endpoint),  # git diff
        ]
        assert platform_freeze_check.check_new_endpoints(rules) is False
