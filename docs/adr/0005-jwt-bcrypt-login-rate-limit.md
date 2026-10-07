# ADR 0005: JWT, bcrypt, and an in-process login limit

- Status: Accepted
- Recorded: 2026-10-07 (the service already runs this way)

## Context

The HTTP process stores no session. Passwords cannot be stored in clear text, and existing production hashes are bcrypt `$2b$` strings written at 12 rounds. Login is exposed on the public internet. The host has no Redis.

## Decision

Access tokens are PyJWT, algorithm `HS256` (`JWT_ALGORITHM`). The payload is `sub` (the user id), `exp`, and `iat`. Lifetime is `JWT_EXPIRE_MINUTES`, default 1440. `ENVIRONMENT=production` aborts startup when `JWT_SECRET` is the placeholder `change-me-use-a-long-random-string` or shorter than 32 characters. The raised error does not include the secret value.

Passwords are hashed with `bcrypt.hashpw` and `gensalt(rounds=12)`. A password longer than 72 UTF-8 bytes is rejected before hashing. Verification of an over-long password or a non-bcrypt hash is a mismatch, not a truncated comparison. Login of an unknown email still checks a fixed dummy hash so the response time is not a user-enumeration signal. The HTTP message is the same for a missing user and a wrong password.

`POST /v1/auth/login` consumes one attempt per caller before bcrypt. The default window is 10 attempts per 60 seconds, in process memory. The caller key is `X-Real-IP`, else the first `X-Forwarded-For` hop, when `LOGIN_TRUST_PROXY_HEADERS` is true (the default). Exhaustion returns `429` / `login_rate_limited` with `Retry-After`, which clients can tell apart from the Queen's daily AI quota.

## Consequences

Anyone holding a token can act as that user until it expires. The API does not keep a revocation list. The login window blunts a burst against one warm process. A cold start resets it, and another instance does not see it. Trusting proxy headers is correct behind Render and is spoofable if the process is reachable directly.

## Alternatives

Server-side sessions would need a store this process does not have. A shared limiter was not added; `app/core/login_rate_limit.py` says a shared store is intentionally absent. Argon2 would not verify the bcrypt hashes already stored. Raising the bcrypt cost above 12 rounds would change the cost of every login without a migration of old hashes; the code keeps 12, which matches those hashes.
