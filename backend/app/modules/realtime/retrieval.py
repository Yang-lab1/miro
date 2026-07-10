"""Small, dependency-free retrieval layer for uploaded interview context."""

from __future__ import annotations

import re

from app.models.simulation import SimulationUploadedFile

CHUNK_SIZE = 620
CHUNK_OVERLAP = 90
MAX_RETRIEVED_CHUNKS = 4


def _tokens(text: str) -> set[str]:
    lowered = text.lower()
    words = set(re.findall(r"[a-z0-9][a-z0-9_-]{1,}", lowered))
    cjk = set(re.findall(r"[\u4e00-\u9fff]", lowered))
    return words | cjk


def _split_into_chunks(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    if not normalized:
        return []
    if len(normalized) <= CHUNK_SIZE:
        return [normalized]

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + CHUNK_SIZE)
        if end < len(normalized):
            boundary = max(
                normalized.rfind(". ", start, end),
                normalized.rfind("? ", start, end),
                normalized.rfind("! ", start, end),
                normalized.rfind("; ", start, end),
            )
            if boundary >= start + CHUNK_SIZE // 2:
                end = boundary + 1
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def retrieve_context_chunks(
    uploaded_files: list[SimulationUploadedFile],
    *,
    query_text: str | None,
    limit: int = MAX_RETRIEVED_CHUNKS,
) -> list[str]:
    query_tokens = _tokens(query_text or "")
    candidates: list[tuple[float, int, str, str]] = []
    candidate_order = 0

    for file_record in uploaded_files:
        source_text = file_record.extracted_text or ""
        if not source_text:
            source_text = " ".join(
                value
                for value in (
                    file_record.extracted_summary_text,
                    file_record.extracted_excerpt_text,
                )
                if value
            )
        for chunk in _split_into_chunks(source_text):
            chunk_tokens = _tokens(chunk)
            overlap = len(query_tokens & chunk_tokens)
            phrase_bonus = (
                2.0
                if query_text and query_text.lower().strip() in chunk.lower()
                else 0.0
            )
            score = float(overlap) + phrase_bonus
            candidates.append((score, candidate_order, file_record.file_name, chunk))
            candidate_order += 1

    if not candidates:
        return []

    candidates.sort(key=lambda item: (-item[0], item[1]))
    selected: list[str] = []
    seen: set[str] = set()
    for _, _, file_name, chunk in candidates:
        rendered = f"[{file_name}] {chunk}"
        if rendered in seen:
            continue
        selected.append(rendered)
        seen.add(rendered)
        if len(selected) >= limit:
            break
    return selected
