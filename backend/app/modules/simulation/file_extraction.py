from __future__ import annotations

import base64
import io
import re
from dataclasses import dataclass

from pypdf import PdfReader

MAX_TEXT_CHARS = 12000
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
SUMMARY_CHAR_LIMIT = 220
EXCERPT_CHAR_LIMIT = 260


@dataclass(slots=True)
class FileExtractionResult:
    parse_status: str
    extracted_text: str | None
    extracted_summary_text: str | None
    extracted_excerpt_text: str | None


def build_failed_extraction(
    file_name: str,
    *,
    content_type: str,
    size_bytes: int,
    source_type: str | None,
    parse_status: str = "failed",
) -> FileExtractionResult:
    del file_name, content_type, size_bytes, source_type
    return FileExtractionResult(
        parse_status=parse_status,
        extracted_text=None,
        extracted_summary_text=None,
        extracted_excerpt_text=None,
    )


def _normalize_text_content(raw_text: str) -> str:
    return re.sub(r"\s+", " ", raw_text).strip()


def _shorten(text: str, *, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _build_text_summary(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    summary_parts = [segment.strip() for segment in sentences if segment.strip()]
    if not summary_parts:
        return _shorten(text, limit=SUMMARY_CHAR_LIMIT)
    return _shorten(" ".join(summary_parts[:2]), limit=SUMMARY_CHAR_LIMIT)


def _build_text_excerpt(text: str) -> str:
    if len(text) <= EXCERPT_CHAR_LIMIT:
        return text
    midpoint = max(len(text) // 2, EXCERPT_CHAR_LIMIT)
    start_excerpt = text[: EXCERPT_CHAR_LIMIT // 2].strip()
    middle_excerpt = text[
        midpoint - (EXCERPT_CHAR_LIMIT // 4) : midpoint + (EXCERPT_CHAR_LIMIT // 4)
    ]
    excerpt = f"{start_excerpt} ... {middle_excerpt.strip()}"
    return _shorten(excerpt, limit=EXCERPT_CHAR_LIMIT)


def _extract_text_plain(
    *,
    text_content: str | None,
    file_data_base64: str | None,
) -> str | None:
    if text_content is not None:
        return _normalize_text_content(text_content[:MAX_TEXT_CHARS])
    if file_data_base64 is None:
        return None
    decoded = base64.b64decode(file_data_base64, validate=True)
    return _normalize_text_content(decoded.decode("utf-8", errors="replace")[:MAX_TEXT_CHARS])


def _is_text_upload(file_name: str, content_type: str) -> bool:
    normalized_type = content_type.strip().lower()
    extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if extension == "pdf":
        return False
    return (
        normalized_type.startswith("text/")
        or normalized_type == "application/json"
        or extension == "txt"
    )


def _is_pdf_upload(file_name: str, content_type: str) -> bool:
    normalized_type = content_type.strip().lower()
    extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    return normalized_type == "application/pdf" or extension == "pdf"


def _extract_pdf_text(file_data_base64: str) -> str:
    decoded = base64.b64decode(file_data_base64, validate=True)
    if len(decoded) > MAX_UPLOAD_BYTES:
        raise ValueError("Uploaded file exceeds the maximum supported size.")
    reader = PdfReader(io.BytesIO(decoded))
    extracted_parts: list[str] = []
    for page in reader.pages[:3]:
        page_text = page.extract_text() or ""
        if page_text.strip():
            extracted_parts.append(page_text.strip())
    return _normalize_text_content(" ".join(extracted_parts)[:MAX_TEXT_CHARS])


def extract_uploaded_file_content(
    file_name: str,
    *,
    content_type: str,
    size_bytes: int,
    source_type: str | None,
    text_content: str | None,
    file_data_base64: str | None,
) -> FileExtractionResult:
    try:
        if size_bytes > MAX_UPLOAD_BYTES:
            return build_failed_extraction(
                file_name,
                content_type=content_type,
                size_bytes=size_bytes,
                source_type=source_type,
            )
        extracted_text: str | None = None
        if _is_text_upload(file_name, content_type):
            extracted_text = _extract_text_plain(
                text_content=text_content,
                file_data_base64=file_data_base64,
            )
        elif _is_pdf_upload(file_name, content_type) and file_data_base64 is not None:
            extracted_text = _extract_pdf_text(file_data_base64)

        if extracted_text:
            return FileExtractionResult(
                parse_status="ready",
                extracted_text=extracted_text,
                extracted_summary_text=_build_text_summary(extracted_text),
                extracted_excerpt_text=_build_text_excerpt(extracted_text),
            )
    except Exception:
        return build_failed_extraction(
            file_name,
            content_type=content_type,
            size_bytes=size_bytes,
            source_type=source_type,
        )

    return build_failed_extraction(
        file_name,
        content_type=content_type,
        size_bytes=size_bytes,
        source_type=source_type,
    )
