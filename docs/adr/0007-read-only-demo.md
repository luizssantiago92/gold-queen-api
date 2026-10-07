# ADR 0007: The public demo account is read-only

- Status: Accepted
- Recorded: 2026-10-07 (the service already runs this way)

## Context

The README publishes `queen@goldqueen.dev` and `squire@goldqueen.dev` with their passwords so a visitor can try the API. Those two rows are one shared user each. A visitor who can connect, sync, or delete would replace or remove the sandbox bank that the next visitor expects to see. Production signup is closed.

## Decision

`app/services/demo_access.py` rejects `POST /v1/connections/connect`, `POST /v1/connections/sync`, and `DELETE /v1/connections/{id}` for those emails with `403` / `demo_read_only`. Reads, Queen's Tips, and chat stay open.

The daily AI quota for a demo user is counted per client address, using the same proxy-header rules as the login limiter, truncated to 128 characters. A normal user still has a single daily counter.

On demo login, `maybe_refresh_demo` slides transaction dates forward when the newest row is older than yesterday, so the dashboard does not freeze on the month the sandbox was first synced. Dashboard reads do not write. `python -m app.seed` creates the users only. Linking a bank is a separate script, and that script cannot connect while the guard is on.

## Consequences

The published passwords are a demo, not a secret. One visitor's chat does not exhaust another visitor's quota on the same account. Date refresh rewrites `transaction_date` for that user. A deploy that needs a new sandbox link has to do it outside the guarded routes.

## Alternatives

A fresh user per visitor would require open registration, which production turns off. Disabling chat and tips on the demo would hide the feature the public site is there to show. Leaving connect enabled would let any visitor who read the README delete the shared bank.
