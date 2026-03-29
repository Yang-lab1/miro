# Phase 23 Findings

## The realtime scaffold already had the right seam lines
- `respond_realtime_turn` was already split into:
  - session orchestration
  - grounding prep
  - turn generation
  - alert extraction
- The main gap was not architecture. It was that uploaded files still stopped at metadata.

## A lightweight persisted extraction layer is enough for this phase
- Full OCR/RAG infrastructure is still unnecessary here.
- Two persisted fields on `simulation_uploaded_files` are enough to create real internal grounding value:
  - `extracted_summary_text`
  - `extracted_excerpt_text`
- This keeps the enhancement stable, actor-scoped, and deployment-safe.

## Grounding now affects both live and review in observable ways
- Uploaded files now produce deterministic internal summaries/excerpts.
- Realtime grounding payload now includes:
  - per-file extracted text
  - uploaded context summary
  - uploaded context excerpts
- Turn generation now visibly references uploaded context.
- Review `coachSummary` and assistant review lines now show that grounded input influenced the final snapshot.

## The main remaining gap is still true document intelligence
- Uploaded context is no longer metadata-only.
- But it is still not full parsing, chunking, embedding, or retrieval.
- The next step after this phase is richer provider-backed grounding quality, not another deployment or API-contract pass.
