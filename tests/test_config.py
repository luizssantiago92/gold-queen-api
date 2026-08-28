"""Settings parsing tests."""

from app.core.config import Settings


def test_comma_separated_origins_become_a_list() -> None:
    settings = Settings(cors_origins="http://a.dev, http://b.dev ,")
    assert settings.allowed_origins == ["http://a.dev", "http://b.dev"]


def test_empty_database_url_falls_back_to_sqlite() -> None:
    assert Settings(database_url="").database_url.startswith("sqlite")


def test_integration_flags_reflect_credentials() -> None:
    disabled = Settings(pluggy_client_id="", pluggy_client_secret="", gemini_api_key="")
    assert disabled.pluggy_enabled is False
    assert disabled.gemini_enabled is False

    enabled = Settings(
        pluggy_client_id="id", pluggy_client_secret="secret", gemini_api_key="key"
    )
    assert enabled.pluggy_enabled is True
    assert enabled.gemini_enabled is True
