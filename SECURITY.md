# Security policy

## Supported versions

Security fixes go to the default branch. The package version in `pyproject.toml` is `1.0.0`. The only release tag is `v1.0.0`.

| Version | Supported |
| --- | --- |
| 1.0.x on `main` (the `v1.0.0` tag and later commits that keep version `1.0.0`) | Yes |
| Anything older than `v1.0.0` | No |

## Reporting a vulnerability

Please report a vulnerability in this repository in private. Do not open a public GitHub issue, and do not include live `JWT_SECRET`, Pluggy, or Gemini values in the report. Name the variable and the version or commit you tried.

Use GitHub private vulnerability reporting:

[https://github.com/luizssantiago92/gold-queen-api/security/advisories/new](https://github.com/luizssantiago92/gold-queen-api/security/advisories/new)

That opens a draft security advisory for the repository owner. Include the affected version, the endpoint or file, and a short reproduction if you have one. Please allow time for a fix before any public write-up.

If that page says private reporting is turned off, email [luizssantiago92@gmail.com](mailto:luizssantiago92@gmail.com) with the same details. Use the email only in that case.

This policy covers `gold-queen-api`. The web app is a separate repository.

## Security controls in this codebase

These are the controls the code and CI actually implement. A fuller trace is in [docs/requirements.md](docs/requirements.md) (RNF01 and RNF04) and in [docs/adr/](docs/adr/README.md).

- **Passwords.** bcrypt `$2b$`, 12 rounds. Registration rejects a password longer than 72 UTF-8 bytes. Verification does not truncate a longer password to force a match. Unknown emails still pay for a bcrypt check and return the same `401` message as a wrong password.
- **Tokens.** Bearer JWTs (PyJWT, HS256). Production refuses the default `JWT_SECRET` and any secret shorter than 32 characters, and the startup error does not echo the secret. There is no server-side session and no revocation list.
- **Login throttle.** 10 attempts per 60 seconds in process memory, before bcrypt, with `Retry-After` and code `login_rate_limited`. The window resets on a cold start and is not shared across instances. It trusts `X-Real-IP` or the first `X-Forwarded-For` hop by default, which is correct behind Render and spoofable if the process is exposed directly.
- **Authorization.** `/v1` routes other than register and login require a bearer token. Connection and treasury queries are limited to that user. A sync of someone else's Pluggy item returns `404`. The public demo cannot connect, sync, or delete (`403` / `demo_read_only`).
- **Signup.** Closed when `ENVIRONMENT=production` unless `ALLOW_REGISTRATION` is true. The Render blueprint sets it to `false`.
- **Errors.** Clients receive `{ "detail", "code" }`. Validation errors omit the submitted value. Unexpected failures return `500` / `internal_error` with no traceback. Pluggy bodies written to logs are redacted.
- **Browser headers.** `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, and `Strict-Transport-Security` (`max-age=31536000; includeSubDomains`). There is no `Content-Security-Policy`, so `/docs` can load Swagger UI.
- **CORS.** Exact origins plus a preview regex anchored to the Vercel team slug. An empty `CORS_ORIGIN_REGEX` disables previews.
- **Secrets.** `JWT_SECRET`, Pluggy, and Gemini stay in the host environment. `render.yaml` marks those values `sync: false`. The Gemini key is sent to Google in the `x-goog-api-key` header, not in the URL.
- **Data store.** PostgreSQL is reached with the table-owner connection, which bypasses row-level security. User isolation is the application filter. See [docs/data-model.md](docs/data-model.md).
- **Pipeline.** GitHub Actions runs ruff, mypy, pytest with a branch-coverage floor of 85, and `pip-audit`. CodeQL analyzes Python and GitHub Actions. Dependabot opens weekly updates for pip and actions. Retornatus gates run on pull requests.

The demo passwords in the README are published on purpose. There is no endpoint that exports or deletes a user account.
