# Phase 25A Task Plan

## Goal
- Close the hosted public auth gap without changing auth semantics.
- Re-run the hosted rehearsal through the real public auth UI.
- Replace Phase 25 overstatement with a precise final state and remove the old dual-account blocker once it is truly verified.

## Stages
| Stage | Status | Notes |
|---|---|---|
| 1. Docs-first + hosted-first re-audit | complete | Re-checked product, deployment, architecture, API, flow, and planning docs plus the current hosted runtime-config and backend health. |
| 2. Public auth closure | complete | Removed the frontend-only hard block that treated an empty `MIRO_TURNSTILE_SITE_KEY` as “disable email auth entirely”. Hosted auth modal now keeps email auth available in the current demo environment. |
| 3. True hosted rehearsal path | complete | `rehearse:hosted` now uses the real auth modal and form instead of injecting Supabase sessions. Account 1 completed the full hosted chain through true UI login and logout. |
| 4. Dual-account isolation | complete | A second real account now logs in through the hosted auth UI and remains isolated while account 1 mutates Pricing, Hardware, and Live -> Review data. |
| 5. Repo/doc sync | complete | README, backend README, deployment docs, and planning files now reflect the true hosted auth state and the completed dual-account verification. |

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
- Only mark dual-account isolation complete after both accounts log in through the hosted browser flow and the second snapshot remains unchanged after account 1 actions.

## Constraints
- Do not break `validate:online`, `smoke:http`, or the current hosted deployment.
- Do not add product scope or change Pricing / Hardware / Live / Review semantics.
- Keep documentation aligned with what was actually validated in the hosted stack.
