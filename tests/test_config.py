"""Settings parsing tests."""

import re

from app.core.config import Settings


def test_comma_separated_origins_become_a_list() -> None:
    settings = Settings(cors_origins="http://a.dev, http://b.dev ,")
    assert settings.allowed_origins == ["http://a.dev", "http://b.dev"]


def test_trailing_slash_in_an_origin_is_ignored() -> None:
    # Browsers send "https://app.dev", so keeping the slash would reject it.
    settings = Settings(cors_origins="https://app.dev/")
    assert settings.allowed_origins == ["https://app.dev"]


def test_default_regex_matches_vercel_previews_but_not_other_apps() -> None:
    pattern = re.compile(Settings().allowed_origin_regex or "")

    assert pattern.fullmatch("https://gold-queen-web.vercel.app")
    assert pattern.fullmatch("https://gold-queen-web-abc123-luiz.vercel.app")
    # A blanket *.vercel.app would hand the API to any app hosted on Vercel.
    assert pattern.fullmatch("https://evil-app.vercel.app") is None
    assert pattern.fullmatch("https://gold-queen-web-abc.vercel.app.evil.com") is None


def test_regex_can_be_disabled() -> None:
    assert Settings(cors_origin_regex="").allowed_origin_regex is None


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
