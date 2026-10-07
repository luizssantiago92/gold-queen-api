# Architecture decision records

Short records of decisions that are already in the code. Each note has context, the decision, consequences, and the alternatives that were set aside. They describe the running system. They do not propose new work.

| ADR | Decision |
| --- | --- |
| [0001](0001-fastapi.md) | FastAPI for the HTTP API |
| [0002](0002-postgresql-supabase-alembic.md) | PostgreSQL on Supabase, schema owned by Alembic |
| [0003](0003-render-hosting.md) | Render for the API, and the cold start that comes with it |
| [0004](0004-vercel-frontend.md) | Vercel hosts the frontend, not this API |
| [0005](0005-jwt-bcrypt-login-rate-limit.md) | JWT, bcrypt, and an in-process login limit |
| [0006](0006-gemini-guardrails-quota.md) | Gemini categorization with guardrails, a rule fallback, and a daily quota |
| [0007](0007-read-only-demo.md) | The public demo account is read-only |
| [0008](0008-retornatus-governance.md) | Retornatus governs changes in this repository |

Related reading: [requirements](../requirements.md), [data model](../data-model.md), [architecture](../architecture.md), [deployment](../deployment.md).
