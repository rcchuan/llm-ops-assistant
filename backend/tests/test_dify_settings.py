import pytest

from app.core.config import Settings


def test_dify_settings_normalize_url_and_hide_key() -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        dify_base_url="https://api.dify.ai/v1/",
        dify_app_api_key="test-secret-dify-key",
        dify_timeout_seconds=60,
    )

    assert settings.dify_base_url == "https://api.dify.ai/v1"
    assert settings.dify_app_api_key.get_secret_value() == "test-secret-dify-key"
    assert "test-secret-dify-key" not in repr(settings)
    assert settings.dify_timeout_seconds == 60


@pytest.mark.parametrize("timeout", [0, -1, 61])
def test_dify_timeout_must_remain_60_seconds(timeout: int) -> None:
    with pytest.raises(ValueError):
        Settings(_env_file=None, app_env="test", dify_timeout_seconds=timeout)
