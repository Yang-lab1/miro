# Phase 23 Task Plan

## Goal
- Move uploaded files from metadata-only placeholders into real internal grounding inputs.
- Improve basic live realism without changing the current public API contract or hosted deployment shape.
- Make review output reflect grounded uploaded context in a stable, testable way.

## Stages
| Stage | Status | Notes |
|---|---|---|
| 1. Repo-first + docs-first audit | complete | Re-read product, deployment, architecture, API, flow, and planning docs; confirmed hosted deployment is already done and the next gap is uploaded context grounding. |
| 2. TDD coverage for grounding realism | complete | Added failing tests for uploaded extraction persistence, grounding payload enrichment, grounded turn output, and grounded review summary. |
| 3. Backend grounding enhancement | complete | Added lightweight extracted summary/excerpt persistence, grounding payload expansion, transcript-aware turn generation, and grounded review summary notes. |
| 4. Regression + doc sync | complete | Backend full pytest, `smoke:http`, architecture/API/backend docs, and planning files are all updated to the new state. |

## Decisions
- Keep the hosted stack unchanged:
  - frontend on Vercel
  - backend on Alibaba Cloud ECS
  - auth + database on Supabase
- Keep realtime API shape unchanged.
- Use a lightweight deterministic extraction model for uploaded files in this phase instead of full parsing/OCR/RAG infrastructure.
- Let grounded context affect:
  - internal realtime grounding payload
  - assistant turn generation
  - review summary text

## Constraints
- Do not break `npm run smoke:http`, hosted validation assumptions, or current actor-scoped security boundaries.
- Do not introduce vector DB, embeddings, OCR, or media pipeline dependencies.
- Do not expand Hardware or Billing beyond their demo-only scope.
