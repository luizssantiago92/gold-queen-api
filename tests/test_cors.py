"""CORS tests.

These cover the failure that broke the deployed frontend: the preflight and the
actual response are handled by different code paths, and only the second one was
missing ``Access-Control-Allow-Origin``. A browser aborts the call either way, so
both paths are asserted here.
"""

from fastapi.testclient import TestClient

ALLOWED = "http://localhost:5173"
PRODUCTION = "https://gold-queen-web.vercel.app"
PREVIEW = "https://gold-queen-web-abc123456-luizssantiago92.vercel.app"
BRANCH_PREVIEW = "https://gold-queen-web-git-main-luizssantiago92.vercel.app"
LOOKALIKE = "https://gold-queen-web-attacker.vercel.app"
FOREIGN = "https://evil-app.vercel.app"


def _preflight(client: TestClient, origin: str):
    return client.options(
        "/v1/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )


def test_listed_origin_is_allowed_on_both_paths(client: TestClient) -> None:
    assert _preflight(client, ALLOWED).headers["access-control-allow-origin"] == ALLOWED

    response = client.get("/health", headers={"Origin": ALLOWED})
    assert response.headers["access-control-allow-origin"] == ALLOWED


def test_production_and_team_previews_are_allowed(client: TestClient) -> None:
    for origin in (PRODUCTION, PREVIEW, BRANCH_PREVIEW):
        assert (
            _preflight(client, origin).headers["access-control-allow-origin"] == origin
        )

        response = client.get("/health", headers={"Origin": origin})
        assert response.headers["access-control-allow-origin"] == origin


def test_unknown_origin_is_refused(client: TestClient) -> None:
    for origin in (FOREIGN, LOOKALIKE):
        assert _preflight(client, origin).status_code == 400

        response = client.get("/health", headers={"Origin": origin})
        assert "access-control-allow-origin" not in response.headers
