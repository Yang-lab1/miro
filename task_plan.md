# Phase 25A Task Plan

## Goal
- Close the hosted public auth gap without changing auth semantics.
- Re-run the hosted rehearsal through the real public auth UI.
- Replace Phase 25 overstatement with a precise final state, including the remaining second-account blocker.

## Stages
| Stage | Status | Notes |
|---|---|---|
| 1. Docs-first + hosted-first re-audit | complete | Re-checked product, deployment, architecture, API, flow, and planning docs plus the current hosted runtime-config and backend health. |
| 2. Public auth closure | complete | Removed the frontend-only hard block that treated an empty `MIRO_TURNSTILE_SITE_KEY` as “disable email auth entirely”. Hosted auth modal now keeps email auth available in the current demo environment. |
| 3. True hosted rehearsal path | complete with one external limitation | `rehearse:hosted` now uses the real auth modal and form instead of injecting Supabase sessions. Account 1 completed the full hosted chain through true UI login and logout. |
| 4. Dual-account isolation | blocked by one external prerequisite | The supplied second account still does not authenticate; a new registration attempt through the real hosted UI reaches email-confirmation flow, so a confirmed second account is still required to finish the dual-account hosted isolation check. |
| 5. Repo/doc sync | complete | README, backend README, deployment docs, and planning files now reflect the true hosted auth state and the exact remaining blocker. |

## Decisions
- Keep the hosted stack unchanged:
  - frontend on Vercel
  - backend on Alibaba Cloud ECS
  - auth + database on Supabase
- Keep backend auth semantics unchanged; fix only the frontend-only Turnstile gating bug.
- Treat an empty `MIRO_TURNSTILE_SITE_KEY` as:
  - no Turnstile widget
  - demo-safe email auth still enabled
  - explicit UI copy that the security check is not configured in this demo environment
- Require all hosted rehearsal auth actions to use the real public modal and form.
- Do not mark dual-account isolation as complete unless a second confirmed account actually logs in and remains isolated in the hosted browser flow.

## Constraints
- Do not break `validate:online`, `smoke:http`, or the current hosted deployment.
- Do not add product scope or change Pricing / Hardware / Live / Review semantics.
- Do not hide the remaining external blocker; report it explicitly if the second account cannot be confirmed and logged in.
