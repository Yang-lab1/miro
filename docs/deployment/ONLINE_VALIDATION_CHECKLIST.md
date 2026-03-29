# Miro Online Validation Checklist

This checklist is the post-deploy dry-run path for the current repository shape:

- Vercel static frontend
- Alibaba Cloud ECS-hosted FastAPI backend
- Supabase Auth + Postgres

## 1. Required deployed values

Frontend runtime config on Vercel:

- `MIRO_API_BASE`
- `MIRO_REVIEW_API_BASE`
- `MIRO_SUPABASE_URL`
- `MIRO_SUPABASE_PUBLISHABLE_KEY`
- `MIRO_SUPABASE_AUTH_REDIRECT_TO`

Backend env on ECS:

- `APP_ENV=production`
- `APP_DEBUG=false`
- `ENABLE_DOCS=false`
- `DATABASE_URL`
- `SUPABASE_URL`
- `SUPABASE_JWT_AUDIENCE=authenticated`
- `FRONTEND_SITE_URL`
- `CORS_ORIGINS`
- `ALLOW_DEMO_ACTOR_FALLBACK=false`

Supabase dashboard:

- `Site URL` should match the deployed frontend origin
- `Redirect URLs` should include the deployed frontend origin
- If signup email confirmation is enabled, email templates should use `{{ .RedirectTo }}` rather than assuming only `{{ .SiteURL }}`

## 2. Standard online validation command

Run this from the repo root after deployment:

```bash
npm run validate:online -- \
  --frontend-url https://<frontend-domain> \
  --backend-url https://<backend-domain> \
  --expected-supabase-url https://<project-ref>.supabase.co
```

What it checks automatically:

- frontend root is reachable
- deployed `runtime-config.js` is reachable
- frontend API base is not accidentally tied to localhost
- frontend runtime config points at the expected backend origin
- backend health path responds at `/api/v1/health`
- unauthenticated `GET /api/v1/auth/session` still returns `401`
- CORS preflight from the frontend origin to `/api/v1/auth/session` succeeds
- frontend signup redirect target matches the frontend origin when configured

For a local no-account dry run of the same validation path:

```bash
npm run validate:online -- --local-dry-run
```

This mode temporarily:

- generates a deploy-shaped `runtime-config.js`
- starts a local static frontend on `127.0.0.1:4273`
- starts a local backend on `127.0.0.1:8070`
- runs the same runtime-config, health, auth-boundary, and CORS checks
- restores the default `runtime-config.js` afterwards

For a real hosted browser rehearsal with demo credentials:

```bash
npm run rehearse:hosted
```

Required env for that command:

- `MIRO_DEMO_EMAIL_1`
- `MIRO_DEMO_PASSWORD_1`
- `MIRO_DEMO_EMAIL_2` and `MIRO_DEMO_PASSWORD_2` when dual-account isolation should also be checked

## 3. Manual verification checklist

### Public access

- Open the deployed frontend root and confirm the home route loads.
- Open a protected route directly and confirm the user is redirected or gated instead of seeing protected workspace data.

### Auth

- Register or log in through the deployed frontend.
- Confirm Supabase email redirect or login callback returns to the frontend, not localhost.
- Log out and confirm protected snapshots are cleared.

Current hosted snapshot note:

- `runtime-config.js` currently exposes an empty `MIRO_TURNSTILE_SITE_KEY`.
- The hosted auth modal now falls back to demo-safe email/password auth instead of disabling submit.
- Dual-account hosted isolation has now been validated with two real accounts. If a future fresh second account must be created during rehearsal, signup confirmation may still require email verification before that new account can log in.

### Account-scoped data

- Pricing: switch a plan, top up credits, refresh, and confirm summary persists.
- Hardware: connect, sync, refresh, and confirm demo device state, logs, and sync records persist.
- Live -> Review: start a session, respond at least once, end session, bridge to review, and confirm review detail loads.

### Isolation

- Repeat the flow with a second account.
- Confirm Pricing, Hardware, and Review data do not leak between accounts.

## 4. Fast failure mapping

- Frontend root fails:
  - static site publish path or rewrite rule is wrong
- `runtime-config.js` missing or stale:
  - `npm run runtime:config` was not run during build
  - deploy picked up an old artifact
- API base points to localhost:
  - `MIRO_API_BASE` was not set for production
- Backend health fails:
  - ECS service process did not start correctly
  - uvicorn process, environment file, or migration step is wrong
  - security group / nginx / sslip routing is wrong
- CORS preflight fails:
  - `FRONTEND_SITE_URL` / `CORS_ORIGINS` does not match the deployed frontend origin
- Auth redirect fails:
  - Supabase `Site URL` or `Redirect URLs` do not match the deployed frontend origin
  - `MIRO_SUPABASE_AUTH_REDIRECT_TO` is wrong
- Unauthenticated auth boundary does not return `401`:
  - backend auth middleware/config has regressed

## 5. Scope note

This checklist validates the current demo-capable product:

- demo billing
- demo hardware
- rule-based live session behavior

It does not validate real payment providers, real hardware connectivity, or media-streaming infrastructure.

## 6. Platform configuration pairing

- Vercel frontend origin
  - becomes `MIRO_SUPABASE_AUTH_REDIRECT_TO`
  - becomes backend `FRONTEND_SITE_URL`
  - must be included in backend `CORS_ORIGINS`
  - must be registered in Supabase `Site URL` and `Redirect URLs`
- ECS backend origin
  - becomes `MIRO_API_BASE`
  - becomes `MIRO_REVIEW_API_BASE`
  - should answer `GET /api/v1/health`
- Supabase project URL
  - becomes `MIRO_SUPABASE_URL`
  - becomes backend `SUPABASE_URL`
  - should match `--expected-supabase-url` in `validate:online`
