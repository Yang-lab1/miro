# Phase 25 Findings

## The hosted stack is healthy and contract-consistent
- `validate:online` passed against the real Vercel frontend and ECS backend.
- Hosted `runtime-config.js` points to the correct ECS API base and Supabase project.
- Backend `/api/v1/health` is healthy and unauthenticated `/api/v1/auth/session` still returns `401`.

## A real browser rehearsal is now repeatable from the repo
- The repo now has a dedicated command for hosted browser rehearsal:
  - `npm run rehearse:hosted`
- That command exercises:
  - home load
  - authenticated pricing mutation
  - hardware sync mutation
  - live -> grounded review flow
  - logout
- This is better than relying on ad hoc manual clicking for final demo readiness.

## The current hosted auth UI has a real demo caveat
- Hosted `runtime-config.js` currently exposes an empty `MIRO_TURNSTILE_SITE_KEY`.
- As a result, the email/password submit button is disabled in the hosted auth modal.
- The workspace itself is healthy once a valid Supabase session exists, but the hosted email form is not currently demo-ready.

## The main demo chain is viable with one valid account
- Pricing persisted online.
- Hardware sync persisted online.
- Learning precheck could be completed through the existing backend API.
- Live -> Review successfully reflected grounded uploaded text in the hosted environment.
- Logout returned the app to a public route.

## Dual-account isolation still depends on valid external credentials
- The second supplied account did not authenticate with Supabase password login.
- Because of that, dual-account isolation could not be fully re-run in the browser this phase.
- This is an external credential/input issue, not a repository regression.
