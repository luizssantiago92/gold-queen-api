"""Locale helpers for bilingual AI responses and error messages."""

from typing import Literal

Locale = Literal["en", "pt"]
DEFAULT_LOCALE: Locale = "en"


def parse_locale(value: str | None) -> Locale:
    if value and value.lower().startswith("pt"):
        return "pt"
    return "en"


def parse_accept_language(header: str | None) -> Locale:
    if not header:
        return DEFAULT_LOCALE
    for part in header.split(","):
        token = part.split(";")[0].strip().lower()
        if token.startswith("pt"):
            return "pt"
        if token.startswith("en"):
            return "en"
    return DEFAULT_LOCALE
