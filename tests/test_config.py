"""Settings parsing tests."""

import re

import pytest
from pydantic import ValidationError

from app.core.config import (
    DEFAULT_JWT_SECRET,
    DEFAULT_VERCEL_TEAM_SLUG,
    MIN_JWT_SECRET_LENGTH,
    PRODUCTION_WEB_ORIGIN,
    Settings,
    assert_production_jwt_secret,
)


def test_comma_separated_origins_become_a_list() -> None:
    settings = Settings(cors_origins="http://a.dev, http://b.dev ,")
    assert settings.allowed_origins == ["http://a.dev", "http://b.dev"]


def test_trailing_slash_in_an_origin_is_ignored() -> None:
    # Browsers send "https://app.dev", so keeping the slash would reject it.
    settings = Settings(cors_origins="https://app.dev/")
    assert settings.allowed_origins == ["https://app.dev"]


def test_default_origins_list_production_exactly() -> None:
    settings = Settings()
    assert PRODUCTION_WEB_ORIGIN in settings.allowed_origins
    assert (
        f"https://gold-queen-web-{DEFAULT_VERCEL_TEAM_SLUG}.vercel.app"
        in settings.allowed_origins
    )


def test_default_regex_matches_team_previews_but_not_other_apps() -> None:
    pattern = re.compile(Settings().allowed_origin_regex or "")
    slug = DEFAULT_VERCEL_TEAM_SLUG

    assert pattern.fullmatch(
        f"https://gold-queen-web-abc123456-{slug}.vercel.app"
    )
    assert pattern.fullmatch(f"https://gold-queen-web-git-main-{slug}.vercel.app")
    # Production is an exact origin, not a wildcard that any similar name satisfies.
    assert pattern.fullmatch(PRODUCTION_WEB_ORIGIN) is None
    # A project anyone can register under the gold-queen-web prefix.
    assert pattern.fullmatch("https://gold-queen-web-attacker.vercel.app") is None
    assert pattern.fullmatch("https://gold-queen-web-abc123-luiz.vercel.app") is None
    assert pattern.fullmatch("https://evil-app.vercel.app") is None
    assert pattern.fullmatch("https://gold-queen-web-abc.vercel.app.evil.com") is None


def test_preview_regex_follows_the_configured_team_slug() -> None:
    settings = Settings(vercel_team_slug="acme-team")
    pattern = re.compile(settings.allowed_origin_regex or "")

    assert pattern.fullmatch("https://gold-queen-web-git-main-acme-team.vercel.app")
    assert (
        pattern.fullmatch(
            f"https://gold-queen-web-git-main-{DEFAULT_VERCEL_TEAM_SLUG}.vercel.app"
        )
        is None
    )
    assert "https://gold-queen-web-acme-team.vercel.app" in settings.allowed_origins


def test_invalid_team_slug_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(vercel_team_slug=".*")


def test_production_rejects_the_default_jwt_secret() -> None:
    settings = Settings(environment="production", jwt_secret=DEFAULT_JWT_SECRET)
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        assert_production_jwt_secret(settings)


def test_production_rejects_a_short_jwt_secret() -> None:
    settings = Settings(environment="production", jwt_secret="short-but-not-the-default")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        assert_production_jwt_secret(settings)


def test_production_accepts_a_long_non_default_secret() -> None:
    secret = "p" * MIN_JWT_SECRET_LENGTH
    settings = Settings(environment="production", jwt_secret=secret)
    assert_production_jwt_secret(settings)
    assert settings.jwt_secret == secret


def test_development_keeps_the_default_jwt_secret() -> None:
    settings = Settings(environment="development", jwt_secret=DEFAULT_JWT_SECRET)
    assert_production_jwt_secret(settings)
    assert settings.jwt_secret == DEFAULT_JWT_SECRET


def test_production_startup_error_does_not_echo_the_secret() -> None:
    secret = "short-but-not-the-default"
    settings = Settings(environment="production", jwt_secret=secret)
    with pytest.raises(RuntimeError) as raised:
        assert_production_jwt_secret(settings)
    assert secret not in str(raised.value)


def test_regex_can_be_disabled() -> None:
    assert Settings(cors_origin_regex="").allowed_origin_regex is None


def test_empty_database_url_falls_back_to_sqlite() -> None:
    assert Settings(database_url="").database_url.startswith("sqlite")


def test_registration_defaults_open_outside_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ALLOW_REGISTRATION", raising=False)

    assert Settings(environment="development").registration_enabled is True
    assert Settings(environment="test").registration_enabled is True
    assert Settings(environment="development").allow_registration is None


def test_production_closes_registration_unless_set_explicitly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ALLOW_REGISTRATION", raising=False)

    closed = Settings(environment="production")
    assert closed.allow_registration is None
    assert closed.registration_enabled is False

    assert Settings(environment="production", allow_registration=True).registration_enabled
    assert Settings(environment="Production").registration_enabled is False
    assert (
        Settings(environment="development", allow_registration=False).registration_enabled
        is False
    )


def test_allow_registration_env_overrides_the_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALLOW_REGISTRATION", "true")
    assert Settings(environment="production").registration_enabled is True

    monkeypatch.setenv("ALLOW_REGISTRATION", "false")
    assert Settings(environment="development").registration_enabled is False


def test_integration_flags_reflect_credentials() -> None:
    disabled = Settings(pluggy_client_id="", pluggy_client_secret="", gemini_api_key="")
    assert disabled.pluggy_enabled is False
    assert disabled.gemini_enabled is False

    enabled = Settings(
        pluggy_client_id="id", pluggy_client_secret="secret", gemini_api_key="key"
    )
    assert enabled.pluggy_enabled is True
    assert enabled.gemini_enabled is True
