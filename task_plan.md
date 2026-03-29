# Phase 25 Task Plan

## Goal
- Run one full hosted demo rehearsal against the real Vercel + ECS + Supabase stack.
- Reconcile repository docs and scripts with the actual hosted state.
- Leave the repo in a clear, demo-ready, syncable state without adding new product scope.

## Stages
| Stage | Status | Notes |
|---|---|---|
| 1. Docs-first + repo-first + hosted-first audit | complete | Re-read product, deployment, architecture, API, flow, and planning docs; verified git branch/remote/status and the current hosted frontend/backend/runtime state. |
| 2. Hosted validation baseline | complete | Re-ran `validate:online`, checked hosted `runtime-config.js`, backend health, and unauthenticated auth boundary. |
| 3. Real browser rehearsal | complete with one external limitation | Added and ran `rehearse:hosted`; confirmed home, authenticated workspace flows, pricing, hardware, learning-prechecked live, grounded review, and logout. Dual-account isolation could not be fully completed because the second supplied credential was invalid. |
| 4. Repo/doc sync | complete | Added hosted rehearsal script/command, updated deployment docs/READMEs to reflect the actual hosted auth modal state, and synced planning files to Phase 25. |

## Decisions
- Keep the current hosted stack unchanged:
  - frontend on Vercel
  - backend on Alibaba Cloud ECS
  - auth + database on Supabase
- Do not add new business features in the final rehearsal phase.
- Add a real browser-level hosted rehearsal command:
  - `npm run rehearse:hosted`
- Record the current hosted auth caveat explicitly:
  - `MIRO_TURNSTILE_SITE_KEY` is empty in the hosted runtime config
  - email/password submit is therefore disabled in the hosted auth modal right now
- Treat dual-account isolation as “best effort this phase”: verify it when valid second credentials exist, but do not block the full rehearsal on an invalid external credential.

## Constraints
- Do not break `npm run validate:online`, `npm run smoke:http`, or the current hosted deployment.
- Do not change Auth, Hardware, Billing, Live, or Review product semantics.
- Do not hide hosted limitations; document them clearly when observed during rehearsal.
