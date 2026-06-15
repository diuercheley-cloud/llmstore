import pytest
from app.services.runtime_profiles import RuntimeProfilesService


@pytest.fixture
def temp_env_dir(tmp_path):
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    env_path = tmp_path / ".env.test"
    env_path.write_text("PROJECT_NAME=test\n")
    return profiles_dir, env_path


def test_list_profiles(temp_env_dir):
    p_dir, e_path = temp_env_dir
    (p_dir / "profile1.yaml").write_text(
        "profile_id: prof1\nname: Profile 1\nsettings:\n  MAX_QUEUE_SIZE: 10\n"
    )

    service = RuntimeProfilesService(profiles_dir=str(p_dir), env_path=str(e_path))
    profiles = service.get_all_profiles()
    assert len(profiles) == 1
    assert profiles[0]["profile_id"] == "prof1"


def test_validate_profile_success(temp_env_dir):
    p_dir, e_path = temp_env_dir
    (p_dir / "profile1.yaml").write_text("profile_id: prof1\nsettings:\n  MAX_QUEUE_SIZE: 10\n")

    service = RuntimeProfilesService(profiles_dir=str(p_dir), env_path=str(e_path))
    is_valid, errors = service.validate_profile("prof1")
    assert is_valid
    assert not errors


def test_validate_profile_invalid_key(temp_env_dir):
    p_dir, e_path = temp_env_dir
    (p_dir / "profile1.yaml").write_text("profile_id: prof1\nsettings:\n  INVALID_KEY: 10\n")

    service = RuntimeProfilesService(profiles_dir=str(p_dir), env_path=str(e_path))
    is_valid, errors = service.validate_profile("prof1")
    assert not is_valid
    assert any("Invalid setting key 'INVALID_KEY'" in e for e in errors)


def test_apply_profile_dry_run(temp_env_dir):
    p_dir, e_path = temp_env_dir
    (p_dir / "profile1.yaml").write_text("profile_id: prof1\nsettings:\n  MAX_QUEUE_SIZE: 10\n")

    service = RuntimeProfilesService(profiles_dir=str(p_dir), env_path=str(e_path))
    before, after, msg = service.apply_profile("prof1", dry_run=True)

    assert "MAX_QUEUE_SIZE" in after
    assert after["MAX_QUEUE_SIZE"] == 10
    assert "dry-run" in msg.lower()
