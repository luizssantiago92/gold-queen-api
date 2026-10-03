<!-- retornatus-meta
{
  "change_id": "C-0005",
  "schema_version": 1
}
-->

# Situation

## Demand

The API returns more than one error shape. Request validation echoes the submitted input, including passwords, and has no machine-readable code. HTTPException responses omit code. Dashboard transaction lookup raises a handmade 404. Unexpected errors can leak a traceback. OpenAPI tags, summaries, error responses, and examples are thin. The API version is copied in more than one place. The advisor queen-tips docstring is outdated. gold-queen-web depends on the existing detail strings, Portuguese 429 text, and headers such as Retry-After and WWW-Authenticate.

## Repo signals (inferred)

- stack manifests: `pyproject.toml`, `requirements.txt`
- tests: tests/, pytest (pyproject)
- ci: `ci.yml`, `codeql.yml`, `keep-alive.yml`, `retornatus.yml`
- architecture: docs/architecture.md; AGENTS.md
- code path present: `app/main.py`
- health endpoint symbols already present in app/main.py
- Retornatus already initialized

## Known facts

- Demand stated: The API returns more than one error shape. Request validation echoes the submitted input, including passwords, and has no machine-readable code. HTTPException responses omit code. Dashboard transaction lookup raises a handmade 404. Unexpected errors can leak a traceback. OpenAPI tags, summaries, error responses, and examples are thin. The API version is copied in more than one place. The advisor queen-tips docstring is outdated. gold-queen-web depends on the existing detail strings, Portuguese 429 text, and headers such as Retry-After and WWW-Authenticate.
- Repo: stack manifests: `pyproject.toml`, `requirements.txt`
- Repo: tests: tests/, pytest (pyproject)
- Repo: ci: `ci.yml`, `codeql.yml`, `keep-alive.yml`, `retornatus.yml`
- Repo: architecture: docs/architecture.md; AGENTS.md
- Repo: code path present: `app/main.py`
- Repo: health endpoint symbols already present in app/main.py
- Repo: Retornatus already initialized
- Situation narrative provided by agent/human
- Proposed WHAT: Serve one error body with string detail and string code, plus an optional errors list limited to loc, msg, and type. Handle RequestValidationError, HTTPException, and existing domain errors in one place, drop input and ctx, keep current headers and domain messages, replace the dashboard 404 with NotFoundError, and return a generic internal_error on unexpected failures while logging them. Document tags, summaries, descriptions, error responses, and examples in OpenAPI. Read the API version from one source. Correct the queen-tips docstring. Update the frontend integration guide.
- DONE criterion: pytest shows a 422 body has string detail and code validation_error, an errors list of only loc, msg, and type, and does not contain the submitted password or input or ctx
- DONE criterion: pytest shows domain errors, HTTP 404, HTTP 405, and an unexpected 500 share the detail and code shape, the 500 body is the generic internal error, and Retry-After and WWW-Authenticate are preserved
- DONE criterion: pytest shows OpenAPI tags have descriptions, routes have summaries, error responses use the error schema, register login overview and transaction schemas have examples, and the API version equals the pyproject version
- DONE criterion: pytest shows the queen-tips docstring describes the summary-based cache and the shared daily quota

## Constraints

- Prefer pytest for automated verification (inferred from repo)
- Prefer pytest for automated verification (inferred from repo)
- Do not echo submitted field values, input, or ctx in error bodies or logs.
- Auth failures stay fail-closed and keep their current detail strings.
- Do not add noqa or type ignore comments.
- Do not change the Portuguese 429 quota message.
- Do not add dependencies.
- No secrets in logs and no submitted passwords in error bodies. Auth failures stay fail-closed. Do not add noqa or type ignore comments. Do not change existing domain detail strings or the Portuguese 429 message. Do not add dependencies.

## Assumptions

- (none)

## Ambiguities

- (none)

## Missing decisions

- (none)

## Contract readiness

- Sufficient: **yes**
- Rationale: Demand, WHAT, and DONE are sufficiently clear; repo/kickoff signals incorporated; no material requirements ambiguity detected

## Agent narrative

gold-queen-web errorMessage reads detail only when it is a string and maps registration_disabled and demo_read_only to its own copy. Themed 429 details and Retry-After must stay. Validation today returns detail as a list of objects that include input and ctx.
