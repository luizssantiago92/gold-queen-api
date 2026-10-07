# ADR 0001: FastAPI for the HTTP API

- Status: Accepted
- Recorded: 2026-10-07 (the service already runs this way)

## Context

The backend needs typed JSON routes, bearer authentication, and an OpenAPI document that Swagger UI and the web client can read. The historical brief named FastAPI. The code is Python 3.11+ with Pydantic v2.

## Decision

The process is a FastAPI application (`app/main.py`). Routers under `app/routers/` are thin adapters. Request and response bodies are Pydantic models. Route tags, summaries, and error responses are declared on the routes so they appear in `/openapi.json`. `info.version` is read from `pyproject.toml`.

Handlers that use the synchronous SQLAlchemy session are plain functions, so FastAPI runs them in a threadpool. Pluggy HTTP is scheduled back onto the event loop from that thread.

## Consequences

`/docs` and `/openapi.json` ship with the process. A `Content-Security-Policy` that blocked Swagger's scripts was not added (`app/core/security_headers.py`). Blocking Gemini and database work stay off the event loop. The ASGI app is started with uvicorn, which matches the Render start command.

## Alternatives

A bare Starlette app would need its own schema and validation. Django REST would pull in a larger stack than these routes use. Making every route `async` while calling synchronous SQLAlchemy and the Gemini client would block the loop; the current split keeps those calls in the threadpool.
