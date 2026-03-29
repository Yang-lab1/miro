# Phase 25A Findings

## The hosted auth failure was a frontend gating bug, not a backend outage
- Hosted `runtime-config.js` still exposes an empty `MIRO_TURNSTILE_SITE_KEY`.
- Backend health and auth boundary were already healthy.
- The real blocker was the frontend treating “no site key” as “disable email auth entirely”.

## Public email auth is now truly available in the hosted demo
- The auth modal now keeps email/password submit enabled when Turnstile is not configured.
- The UI copy makes that downgrade explicit:
  - security check not configured
  - email auth remains enabled in the demo environment
- This fixes the gap without changing backend auth semantics.

## Hosted rehearsal now uses the real auth UI
- `rehearse:hosted` no longer calls Supabase sign-in directly through `page.evaluate`.
- It now opens the real modal, fills the real form, submits it, and waits for the real logged-in workspace state.
- Account 1 completed:
  - true UI login
  - Pricing mutation
  - Hardware sync mutation
  - Live -> grounded Review flow
  - true UI logout

## Public register also works through the real UI, but second-account verification still needs one external input
- The supplied second credential still fails real hosted login with `Invalid login credentials`.
- A real hosted register attempt for that account now reaches the email-confirmation path instead of being blocked by the frontend.
- A generated fallback account also reached the hosted register path, but Supabase then hit email send rate limiting.
- Because of that, dual-account hosted isolation is still not honestly complete.

## The repo and docs now match the real hosted state
- README and deployment docs no longer claim the hosted email form is disabled.
- The remaining limitation is now stated correctly:
  - the second account is not yet confirmed/login-capable for the hosted isolation check.
