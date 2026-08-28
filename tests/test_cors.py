"""CORS tests.

These cover the failure that broke the deployed frontend: the preflight and the
actual response are handled by different code paths, and only the second one was
missing ``Access-Control-Allow-Origin``. A browser aborts the call either way, so
both paths are asserted here.
"""

from fastapi.testclient import TestClient

ALLOWED = "http://localhost:5173"
PREVIEW = "https://gold-queen-web-abc123-luiz.vercel.app"
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


def test_vercel_preview_is_allowed_by_regex(client: TestClient) -> None:
    assert _preflight(client, PREVIEW).headers["access-control-allow-origin"] == PREVIEW

    response = client.get("/health", headers={"Origin": PREVIEW})
    assert response.headers["access-control-allow-origin"] == PREVIEW


def test_unknown_origin_is_refused(client: TestClient) -> None:
    assert _preflight(client, FOREIGN).status_code == 400

    response = client.get("/health", headers={"Origin": FOREIGN})
    assert "access-control-allow-origin" not in response.headers
