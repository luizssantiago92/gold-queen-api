"""Application settings loaded from environment variables."""

import re
from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Placeholder shipped for local development. Production startup rejects it.
DEFAULT_JWT_SECRET = "change-me-use-a-long-random-string"
# HS256 needs a 256-bit key. 32 characters is the floor we enforce in production.
MIN_JWT_SECRET_LENGTH = 32

# Team that owns gold-queen-web on Vercel (see docs/deployment.md). Preview
# hostnames end with this slug; a project name prefix alone is not enough,
# because anyone can register gold-queen-web-<anything>.vercel.app.
DEFAULT_VERCEL_TEAM_SLUG = "luizssantiago92"
PRODUCTION_WEB_ORIGIN = "https://gold-queen-web.vercel.app"

_TEAM_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def normalize_vercel_team_slug(team_slug: str) -> str:
    """Return a Vercel team slug, or raise if it could widen the CORS regex."""
    slug = team_slug.strip().lower()
    if _TEAM_SLUG_PATTERN.fullmatch(slug) is None or len(slug) > 63:
        raise ValueError(
            "VERCEL_TEAM_SLUG must be a Vercel team slug: lowercase letters, "
            "digits, and single hyphens, at most 63 characters."
        )
    return slug


def default_cors_origins(team_slug: str) -> str:
    slug = normalize_vercel_team_slug(team_slug)
    # Exact origins only. The team alias is the stable `<project>-<scope>` URL
    # Vercel issues for this account; it is not a wildcard.
    return (
        "http://localhost:5173,"
        "http://localhost:3000,"
        f"{PRODUCTION_WEB_ORIGIN},"
        f"https://gold-queen-web-{slug}.vercel.app"
    )


def vercel_preview_origin_regex(team_slug: str) -> str:
    """Match this project's preview hosts and no other Vercel account.

    Vercel generates ``<project>-<hash>-<scope>``, ``<project>-git-<branch>-<scope>``,
    and ``<project>-<author>-<scope>``. The scope slug is the part an outsider
    cannot choose. A pattern of ``gold-queen-web-*`` without it accepts any
    lookalike project.
    """
    slug = normalize_vercel_team_slug(team_slug)
    return rf"^https://gold-queen-web-[a-z0-9-]+-{re.escape(slug)}\.vercel\.app$"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Gold Queen API"
    environment: str = "development"
    # Owning Vercel team. Used to build the preview regex when CORS_ORIGIN_REGEX
    # is unset, and to keep the default exact-origin list on that team.
    vercel_team_slug: str = DEFAULT_VERCEL_TEAM_SLUG
    # Kept as a raw string: pydantic-settings would try to JSON-decode a list field
    # before any validator runs, which rejects the comma-separated form.
    cors_origins: str = default_cors_origins(DEFAULT_VERCEL_TEAM_SLUG)
    # None means "derive from VERCEL_TEAM_SLUG". An empty string disables previews.
    cors_origin_regex: str | None = None

    database_url: str = "sqlite:///./gold_queen.db"

    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # In-process login throttle. See app.core.login_rate_limit for the
    # serverless limitation: counters are not shared across isolates.
    login_rate_limit_max: int = 10
    login_rate_limit_window_seconds: int = 60
    # Vercel and Render set X-Real-IP / X-Forwarded-For. Direct exposure of the
    # process would let clients spoof those headers and skip the throttle.
    login_trust_proxy_headers: bool = True

    pluggy_client_id: str = ""
    pluggy_client_secret: str = ""
    pluggy_base_url: str = "https://api.pluggy.ai"

    gemini_api_key: str = ""
    # The PRD specified gemini-1.5-flash, which Google has since retired; 2.5-flash
    # is also closed to new API keys. 3.6-flash is the current flash tier.
    gemini_model: str = "gemini-3.6-flash"

    max_bank_connections: int = 3
    # Gemini's free tier caps the whole project at 20 generations per day, shared
    # with Queen's Tips and transaction categorization. A higher figure here would
    # only promise questions the upstream quota cannot serve.
    chat_daily_limit: int = 5

    @field_validator("database_url", mode="before")
    @classmethod
    def fallback_to_sqlite(cls, value: object) -> object:
        if not value:
            return "sqlite:///./gold_queen.db"
        return value

    @field_validator("login_rate_limit_max", "login_rate_limit_window_seconds")
    @classmethod
    def require_positive_limit(cls, value: int) -> int:
        if value < 1:
            raise ValueError("must be at least 1")
        return value

    @model_validator(mode="after")
    def apply_cors_scope(self) -> "Settings":
        slug = normalize_vercel_team_slug(self.vercel_team_slug)
        self.vercel_team_slug = slug
        builtin_origins = default_cors_origins(DEFAULT_VERCEL_TEAM_SLUG)
        if self.cors_origins == builtin_origins:
            self.cors_origins = default_cors_origins(slug)
        if self.cors_origin_regex is None:
            self.cors_origin_regex = vercel_preview_origin_regex(slug)
        return self

    @property
    def allowed_origins(self) -> list[str]:
        # Browsers send the Origin without a trailing slash, so a stray one in the
        # env var would silently reject the very domain it was meant to allow.
        return [
            origin.strip().rstrip("/")
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def allowed_origin_regex(self) -> str | None:
        return self.cors_origin_regex or None

    @property
    def pluggy_enabled(self) -> bool:
        return bool(self.pluggy_client_id and self.pluggy_client_secret)

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.gemini_api_key)


def assert_production_jwt_secret(settings: Settings) -> None:
    """Refuse to boot in production with the placeholder or a short HMAC key.

    Development keeps the placeholder so local ``uvicorn`` still starts.
    Raised as ``RuntimeError`` (not a validation error) so the secret value
    is not copied into the traceback.
    """
    if settings.environment.strip().lower() != "production":
        return
    secret = settings.jwt_secret.strip()
    if secret == DEFAULT_JWT_SECRET or len(secret) < MIN_JWT_SECRET_LENGTH:
        raise RuntimeError(
            "Refusing to start: JWT_SECRET must be changed from the default and "
            f"be at least {MIN_JWT_SECRET_LENGTH} characters when ENVIRONMENT=production."
        )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # `app.main` calls this while building the ASGI app, so a bad production
    # secret aborts process start instead of serving traffic.
    assert_production_jwt_secret(settings)
    return settings
