"""Locale parsing helpers."""

from app.core.locale import parse_accept_language, parse_locale


def test_parse_locale_defaults_to_english() -> None:
    assert parse_locale(None) == "en"
    assert parse_locale("en") == "en"
    assert parse_locale("en-US") == "en"


def test_parse_locale_detects_portuguese() -> None:
    assert parse_locale("pt") == "pt"
    assert parse_locale("pt-BR") == "pt"


def test_parse_accept_language() -> None:
    assert parse_accept_language("en-US,en;q=0.9") == "en"
    assert parse_accept_language("pt-BR,pt;q=0.9,en;q=0.8") == "pt"
    assert parse_accept_language(None) == "en"
