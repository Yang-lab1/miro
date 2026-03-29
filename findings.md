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

## Dual-account hosted isolation is now truly verified
- The newly supplied second account `593976339@qq.com` authenticated through the hosted public auth UI.
- Account 1 and account 2 resolved to different actor ids.
- After account 1 changed Pricing, Hardware, and Review state, account 2's billing, hardware, and review snapshots remained unchanged.
- The previous dual-account blocker has therefore been cleared.

## The repo and docs now match the real hosted state
- README and deployment docs no longer claim the hosted email form is disabled.
- Planning files now reflect the true final state:
  - public hosted auth works
  - true hosted rehearsal works
  - dual-account isolation has been verified
