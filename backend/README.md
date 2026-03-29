# Miro Backend Scaffold

This folder now contains the backend foundation plus the phase-10 Supabase auth integration and the earlier learning / simulation / realtime minimum loops:

- FastAPI application bootstrap
- centralized config, logging, and error handling
- route skeletons for planned backend modules
- SQLAlchemy database layer
- Alembic migration wiring
- shared contract handoff points under `/shared`

It intentionally does not implement full business logic for turn runtime, ASR/TTS, real hardware sync, real payment processing, or full identity lifecycle management. Phase 10 now validates Supabase bearer tokens and exposes a backend auth session snapshot, but register / login / logout remain Supabase-managed frontend flows. Hardware should currently be understood as a demo state surface, not as a real connected-device stack, and Billing should be understood as a demo billing state layer rather than a real payment platform.

## Chosen Stack

- API framework: FastAPI
- configuration: Pydantic Settings
- ORM / DB access: SQLAlchemy 2.x
- migrations: Alembic
- target database: PostgreSQL

## Directory Layout

- `app/api`
  - route registration and transport-facing endpoints
- `app/core`
  - config, logging, middleware, error handling
- `app/db`
  - database metadata and session factory
- `app/models`
  - foundational persistence models only
- `app/modules`
  - reserved for future business services
- `migrations`
  - Alembic environment and migration versions
- `tests`
  - backend-only tests

## Local Startup

1. Start local Postgres: `docker compose -f docker-compose.dev.yml up -d`
2. Create a virtual environment from the `backend` directory.
3. Install the package in editable mode: `pip install -e .[dev]`
4. Copy `.env.example` to `.env` and adjust `DATABASE_URL` if needed.
5. Apply migrations: `alembic upgrade head`
6. Start the server: `uvicorn app.main:app --reload`
7. Verify the service: `GET /api/v1/health`

If Docker is unavailable on a developer machine, point `DATABASE_URL` at an existing local PostgreSQL instance. The committed default remains PostgreSQL.

## Production Runtime Config

The backend is now ready to run as a standalone FastAPI web service behind a static frontend.

Recommended production env:

- `APP_ENV=production`
- `APP_DEBUG=false`
- `ENABLE_DOCS=false`
- `DATABASE_URL=<supabase postgres connection string>`
- `SUPABASE_URL=https://<project-ref>.supabase.co`
- `SUPABASE_JWT_ISSUER=https://<project-ref>.supabase.co/auth/v1` (optional override)
- `SUPABASE_JWT_AUDIENCE=authenticated`
- `SUPABASE_JWKS_URL=https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json` (optional override)
- `FRONTEND_SITE_URL=https://<your-frontend-domain>`
- `CORS_ORIGINS=["https://<your-frontend-domain>"]`
- `ALLOW_DEMO_ACTOR_FALLBACK=false`

Config notes:

- `FRONTEND_SITE_URL` is normalized into an origin and folded into the resolved CORS allow-list.
- `SUPABASE_JWT_ISSUER` and `SUPABASE_JWKS_URL` can still be overridden explicitly, but they are now derived automatically from `SUPABASE_URL` when omitted.
- Health checks should target `GET /api/v1/health`.

The current hosted deployment path is:

- frontend on Vercel
- backend on Alibaba Cloud ECS
- auth + database on Supabase

Repo deployment entrypoints:

- frontend config: [vercel.json](/C:/Users/Yang/Desktop/miro/vercel.json)
- ECS deployment guide: [VERCEL_ECS_DEPLOY.md](/C:/Users/Yang/Desktop/miro/docs/deployment/VERCEL_ECS_DEPLOY.md)
- legacy PaaS backend entrypoint: [Procfile](/C:/Users/Yang/Desktop/miro/backend/Procfile)
- legacy Render reference: [render.yaml](/C:/Users/Yang/Desktop/miro/render.yaml)

For post-deploy validation, run the root command:

- `npm run validate:online -- --frontend-url https://<frontend-domain> --backend-url https://<backend-domain> --expected-supabase-url https://<project-ref>.supabase.co`
- For a local dry run of the same checks without an external deployment:
  - `npm run validate:online -- --local-dry-run`
- For a real hosted browser rehearsal against the deployed stack:
  - `npm run rehearse:hosted`

Current hosted auth note:

- if `MIRO_TURNSTILE_SITE_KEY` is empty, the frontend now uses a demo-safe email auth fallback instead of disabling the public auth form
- dual-account hosted isolation still requires a second confirmed Supabase account

Use [docs/deployment/ONLINE_VALIDATION_CHECKLIST.md](/C:/Users/Yang/Desktop/miro/docs/deployment/ONLINE_VALIDATION_CHECKLIST.md) for the manual auth, isolation, Pricing, Hardware, and Live -> Review checks that follow the automated probe.

For the hosted platform pairing itself, use [docs/deployment/VERCEL_ECS_DEPLOY.md](/C:/Users/Yang/Desktop/miro/docs/deployment/VERCEL_ECS_DEPLOY.md).

## Route Strategy

The scaffold exposes `/api/v1` as the common prefix and mounts module route groups for:

- `auth`
- `learning`
- `simulations`
- `voice-profiles`
- `realtime`
- `reviews`
- `hardware`
- `billing`

Phase 2 and Phase 3 currently implement:

- `GET /api/v1/auth/session`
- `GET /api/v1/learning/countries`
- `GET /api/v1/learning/countries/{countryKey}`
- `GET /api/v1/learning/progress/{countryKey}`
- `POST /api/v1/learning/progress/{countryKey}/complete`
- `POST /api/v1/simulations/precheck`
- `POST /api/v1/simulations`
- `GET /api/v1/simulations/{simulationId}`
- `PATCH /api/v1/simulations/{simulationId}`
- `POST /api/v1/simulations/{simulationId}/files`
- `POST /api/v1/simulations/{simulationId}/strategy`
- `GET /api/v1/voice-profiles?countryKey=Japan`
- `POST /api/v1/realtime/sessions`
- `GET /api/v1/realtime/sessions/{sessionId}`
- `POST /api/v1/realtime/sessions/{sessionId}/start`
- `POST /api/v1/realtime/sessions/{sessionId}/end`
- `GET /api/v1/hardware/devices`
- `POST /api/v1/hardware/devices/{deviceId}/connect`
- `POST /api/v1/hardware/devices/{deviceId}/disconnect`
- `POST /api/v1/hardware/devices/{deviceId}/sync`
- `GET /api/v1/hardware/devices/{deviceId}/logs`
- `GET /api/v1/hardware/devices/{deviceId}/sync-records`
- `GET /api/v1/billing/plans`
- `GET /api/v1/billing/summary`
- `POST /api/v1/billing/select-plan`
- `POST /api/v1/billing/top-up`

The setup flow stores revisions, uploaded file metadata, lightweight extracted summaries/excerpts, and stable strategy payloads. Realtime create/start/end now exist with a stub launch provider, but there is still no real media transport or external provider integration.

Auth is now wired as a thin Supabase integration:

- FastAPI accepts `Authorization: Bearer <access_token>`
- backend verifies Supabase JWTs through JWKS
- current actor resolves from JWT `sub`, with dev-only demo fallback behind explicit config
- `POST /api/v1/auth/register|login|logout` remain compatibility placeholders and return `501 auth_managed_by_supabase`

Hardware is now wired as a demo simulation state layer:

- `GET /api/v1/hardware/devices` returns actor-scoped demo devices and auto-creates one default demo device on first access when needed
- `connect`, `disconnect`, and `sync` persist demo-only state transitions
- `logs` and `sync-records` expose UI-safe demo history only
- the backend does not implement BLE, USB, provisioning, firmware, or real wearable ingestion

Billing is now wired as a demo state layer:

- `GET /api/v1/billing/plans` returns the actor-visible demo plan catalog
- `GET /api/v1/billing/summary` returns an actor-scoped billing snapshot and auto-creates one default demo billing account on first access when needed
- `select-plan` updates the current demo subscription snapshot only
- `top-up` increases demo credits and records a demo payment event only
- the backend does not implement Stripe, PayPal, invoices, taxes, refunds, webhooks, or recurring charges

Live grounding is now wired as a lightweight internal scaffold:

- uploaded files persist extracted summaries/excerpts for internal grounding only
- the extraction path now supports:
  - direct `text/plain` content
  - simple text extraction from text-based PDFs
  - deterministic fallback summaries when extraction is unavailable
- realtime turn generation can read strategy summary, uploaded context, and recent transcript lines
- review summaries can reflect grounded uploaded context without changing the public review contract
- the backend still does not implement OCR, chunking, embeddings, vector retrieval, or real multimodal/live media handling

## Shared Source Of Truth

Cross-stack enums and JSON-schema contracts live under:

- `../shared/enums`
- `../shared/contracts`
- `../shared/schemas`

Those files are language-neutral on purpose so the current static frontend and the future FastAPI backend can evolve from the same contract directory.
