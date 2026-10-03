"""OpenAPI describes the live routes, errors, and the single API version."""

import tomllib
from pathlib import Path

from fastapi.testclient import TestClient

from app import __version__
from app.main import app
from app.routers.advisor import queen_tips

_HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _schema(client: TestClient) -> dict[str, object]:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict)
    return body


def test_api_version_comes_from_pyproject(client: TestClient) -> None:
    document = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    project = document["project"]
    assert isinstance(project, dict)
    assert __version__ == project["version"]
    assert app.version == __version__
    info = _schema(client)["info"]
    assert isinstance(info, dict)
    assert info["version"] == __version__
    assert info["title"] == "Gold Queen API"
    assert "Open Finance" in str(info["description"])
    contact = info["contact"]
    assert isinstance(contact, dict)
    assert contact["name"] == "Gold Queen API"
    assert str(contact["url"]).startswith("https://github.com/luizssantiago92/")


def test_tags_and_routes_are_described(client: TestClient) -> None:
    schema = _schema(client)
    tags = schema["tags"]
    assert isinstance(tags, list)
    described = {
        tag["name"]: tag["description"] for tag in tags if isinstance(tag, dict)
    }
    assert described["auth"]
    assert described["connections"]
    assert described["dashboard"]
    assert described["advisor"]
    assert described["chat"]
    assert described["health"]

    paths = schema["paths"]
    assert isinstance(paths, dict)
    for path, operations in paths.items():
        assert isinstance(operations, dict)
        for method, operation in operations.items():
            if method not in _HTTP_METHODS:
                continue
            assert isinstance(operation, dict)
            assert operation["summary"], path
            assert operation["description"], path


def test_error_responses_use_the_public_schema(client: TestClient) -> None:
    schema = _schema(client)
    components = schema["components"]
    assert isinstance(components, dict)
    models = components["schemas"]
    assert isinstance(models, dict)
    assert "HTTPValidationError" not in models
    assert "input" not in models["FieldError"]["properties"]
    assert "ctx" not in models["FieldError"]["properties"]

    paths = schema["paths"]
    assert isinstance(paths, dict)
    register = paths["/v1/auth/register"]["post"]
    assert "422" in register["responses"]
    assert "403" in register["responses"]
    assert "409" in register["responses"]
    login = paths["/v1/auth/login"]["post"]
    assert "401" in login["responses"]
    assert "429" in login["responses"]
    missing = paths["/v1/dashboard/transactions/{transaction_id}"]["get"]
    assert "404" in missing["responses"]

    encoded = str(schema)
    assert "ErrorResponse" in encoded
    assert "HTTPValidationError" not in encoded


def test_main_schemas_include_examples(client: TestClient) -> None:
    schema = _schema(client)
    components = schema["components"]
    assert isinstance(components, dict)
    models = components["schemas"]
    assert isinstance(models, dict)
    for name in (
        "RegisterRequest",
        "LoginRequest",
        "OverviewResponse",
        "TransactionResponse",
        "TransactionPage",
        "TransactionDetailResponse",
    ):
        model = models[name]
        assert isinstance(model, dict)
        examples = model.get("examples")
        assert isinstance(examples, list) and examples


def test_queen_tips_docstring_describes_the_cache_and_quota() -> None:
    doc = queen_tips.__doc__ or ""
    assert "treasury summary" in doc
    assert "quota" in doc
    assert "Demo visitors" in doc
