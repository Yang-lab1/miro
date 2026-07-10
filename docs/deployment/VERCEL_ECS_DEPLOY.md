# Vercel + ECS Deployment Guide

This is the primary hosted deployment path for the current repository:

- frontend on Vercel
- backend on Alibaba Cloud ECS
- auth + database on Supabase

## 1. Frontend on Vercel

Project root:

- repository root

Important project files:

- [vercel.json](/C:/Users/Yang/Desktop/miro/vercel.json)
- [runtime-config.js](/C:/Users/Yang/Desktop/miro/runtime-config.js)
- [scripts/generate-runtime-config.js](/C:/Users/Yang/Desktop/miro/scripts/generate-runtime-config.js)

Vercel runtime env:

- `MIRO_API_BASE=https://47-238-228-236.sslip.io/api/v1`
- `MIRO_REVIEW_API_BASE=https://47-238-228-236.sslip.io/api/v1`
- `MIRO_SUPABASE_URL=https://wzqpboqlhzxqbfautlxe.supabase.co`
- `MIRO_SUPABASE_PUBLISHABLE_KEY=<supabase-publishable-key>`
- `MIRO_SUPABASE_AUTH_REDIRECT_TO=https://miro-vert.vercel.app`
- `MIRO_TURNSTILE_SITE_KEY=<optional-turnstile-site-key>`
- `MIRO_ALLOW_LOCAL_FALLBACK=false`

Notes:

- `vercel.json` runs `npm run runtime:config` during build.
- `runtime-config.js` is served with `Cache-Control: no-store` so production env changes are not hidden behind stale cache.
- SPA routes are rewritten back to `index.html`.
- When `MIRO_TURNSTILE_SITE_KEY` is omitted, the hosted auth modal now falls back to demo-safe email auth instead of disabling the public form.
- `MIRO_ALLOW_LOCAL_FALLBACK` must remain `false` in production. The hosted Live flow will stop in setup when auth or the backend session cannot be created; only localhost previews may use the local demo fallback.

## 2. Backend on Alibaba Cloud ECS

Current live backend host:

- public IP: `47.238.228.236`
- HTTPS API origin: `https://47-238-228-236.sslip.io/api/v1`

Recommended server shape:

- Ubuntu 22.04
- Python 3.11
- repo cloned to the VM
- backend virtualenv under `backend/.venv`

Key backend env:

- `APP_ENV=production`
- `APP_DEBUG=false`
- `ENABLE_DOCS=false`
- `FRONTEND_SITE_URL=https://miro-vert.vercel.app`
- `CORS_ORIGINS=["https://miro-vert.vercel.app"]`
- `DATABASE_URL=<supabase-postgres-connection-string>`
- `SUPABASE_URL=https://wzqpboqlhzxqbfautlxe.supabase.co`
- `SUPABASE_JWT_AUDIENCE=authenticated`
- `SUPABASE_JWT_ISSUER=https://wzqpboqlhzxqbfautlxe.supabase.co/auth/v1`
- `SUPABASE_JWKS_URL=https://wzqpboqlhzxqbfautlxe.supabase.co/auth/v1/.well-known/jwks.json`
- `ALLOW_DEMO_ACTOR_FALLBACK=false`
- `HARDWARE_PROVIDER_MODE=webhook`
- `HARDWARE_PROVIDER_URL=<https-hardware-bridge-sync-endpoint>`
- `HARDWARE_PROVIDER_API_KEY=<hardware-bridge-token>`
- `HARDWARE_PROVIDER_TIMEOUT_SECONDS=10`

Runtime shape:

- run `alembic upgrade head`
- start `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- expose the API behind the sslip-backed HTTPS origin used by the frontend

The hardware bridge receives JSON with `X-Miro-Protocol: miro.hardware.sync.v1`.
For a review sync, the nested `payload` contains the versioned
`miro.review.packet.v1` packet and its hash. Miro writes the local sync record
only after the bridge returns a 2xx response.

Health check:

- `/api/v1/health`

Production readiness check:

- `/api/v1/ready`
- returns `200` only when the database is reachable and production text-model/Doubao configuration exists
- returns `503` with per-provider checks when the backend is not ready for a real interview
- hardware readiness requires `HARDWARE_PROVIDER_MODE=webhook` and an HTTPS bridge URL; `demo` and unknown modes never count as production hardware

Container option:

- `backend/Dockerfile` runs `alembic upgrade head` before starting Uvicorn
- build with `docker build -t miro-backend ./backend`
- run with `docker run --env-file backend/.env -p 8000:8000 miro-backend`
- keep `backend/.env` outside the image and provide production secrets at runtime

## 3. Supabase pairing

Supabase dashboard must match the deployed Vercel frontend origin:

- `Site URL=https://miro-vert.vercel.app`
- `Redirect URLs` include:
  - `https://miro-vert.vercel.app/**`
  - `http://localhost:3000/**`
  - `http://localhost:5173/**`

If signup confirmation is enabled, the email template should use `{{ .RedirectTo }}`.

## 4. Hosted validation

After both services are deployed, run:

```bash
npm run validate:online -- \
  --frontend-url https://miro-vert.vercel.app \
  --backend-url https://47-238-228-236.sslip.io \
  --expected-supabase-url https://wzqpboqlhzxqbfautlxe.supabase.co
```

Then complete the manual flow in [ONLINE_VALIDATION_CHECKLIST.md](/C:/Users/Yang/Desktop/miro/docs/deployment/ONLINE_VALIDATION_CHECKLIST.md).
