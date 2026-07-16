from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx

from app.api.schemas.simulation import SimulationStrategyOutlineQuestion
from app.core.errors import AppError

MAX_SOURCE_CHARS = 5000
MAX_PROMPT_CHARS = 320
MAX_SIGNAL_CHARS = 240
REQUIRED_STAGES = ("opening", "probe", "close")


@dataclass(frozen=True, slots=True)
class StrategySource:
    file_id: str
    file_name: str
    text: str


@dataclass(frozen=True, slots=True)
class StrategyGenerationContext:
    country_key: str
    meeting_type_key: str
    goal_key: str
    voice_style_key: str
    learning_bullets: list[str]
    uploaded_sources: list[dict[str, str]]
    user_twin_memories: list[str]


def _compact(value: object, *, limit: int) -> str:
    normalized = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def _build_messages(context: StrategyGenerationContext) -> list[dict[str, str]]:
    sources = "\n".join(
        f"[{source.get('file_name', 'uploaded source')}]\n"
        f"{_compact(source.get('text'), limit=MAX_SOURCE_CHARS)}"
        for source in context.uploaded_sources
        if str(source.get("text") or "").strip()
    ) or "- No uploaded source text was available."
    learning = "\n".join(
        f"- {_compact(item, limit=240)}"
        for item in context.learning_bullets[:8]
        if str(item).strip()
    ) or "- No learning note was available."
    memories = "\n".join(
        f"- {_compact(item, limit=240)}"
        for item in context.user_twin_memories[:5]
        if str(item).strip()
    ) or "- No recurring User Twin pattern has been recorded yet."
    system = (
        "You are Miro, a cross-border business interview coach. Build a short interview "
        "outline from the supplied source and context. Use only facts present in the input. "
        "Return JSON only with a questions array containing exactly three objects, one each "
        "for stages opening, probe, and close. Each object must have stage, prompt, and "
        "expectedSignal. Keep each prompt concise and ask only one question."
    )
    user = (
        f"Country: {context.country_key}\n"
        f"Meeting type: {context.meeting_type_key}\n"
        f"Goal: {context.goal_key}\n"
        f"Voice style: {context.voice_style_key}\n"
        f"Learning notes:\n{learning}\n"
        f"Uploaded source text:\n{sources}\n"
        f"User Twin memory:\n{memories}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _parse_json_content(content: object) -> dict:
    if isinstance(content, dict):
        parsed = content
    else:
        text = str(content or "").strip()
        if text.startswith("```"):
            text = re.sub(
                r"^```(?:json)?\s*|\s*```$",
                "",
                text,
                flags=re.IGNORECASE | re.DOTALL,
            ).strip()
        parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Strategy response must be a JSON object.")
    return parsed


def _normalize_questions(
    payload: dict,
    *,
    grounding_file_id: str | None,
) -> list[SimulationStrategyOutlineQuestion]:
    questions = payload.get("questions")
    if not isinstance(questions, list) or len(questions) != len(REQUIRED_STAGES):
        raise ValueError("Strategy response must contain exactly three questions.")

    by_stage: dict[str, dict] = {}
    for question in questions:
        if not isinstance(question, dict):
            raise ValueError("Strategy question must be an object.")
        stage = str(question.get("stage") or "").strip().lower()
        if stage not in REQUIRED_STAGES or stage in by_stage:
            raise ValueError("Strategy response must contain one question per stage.")
        prompt = _compact(question.get("prompt"), limit=MAX_PROMPT_CHARS)
        expected_signal = _compact(question.get("expectedSignal"), limit=MAX_SIGNAL_CHARS)
        if not prompt or not expected_signal:
            raise ValueError("Strategy questions require prompt and expectedSignal.")
        by_stage[stage] = {
            "prompt": prompt,
            "expectedSignal": expected_signal,
        }

    return [
        SimulationStrategyOutlineQuestion(
            questionId=f"llm-{stage}",
            stage=stage,  # type: ignore[arg-type]
            prompt=by_stage[stage]["prompt"],
            expectedSignal=by_stage[stage]["expectedSignal"],
            groundingFileId=grounding_file_id,
        )
        for stage in REQUIRED_STAGES
    ]


class OpenAICompatibleStrategyGenerator:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float,
    ) -> None:
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate(
        self,
        context: StrategyGenerationContext,
    ) -> list[SimulationStrategyOutlineQuestion]:
        if not self.api_key:
            raise AppError(
                status_code=503,
                code="llm_not_configured",
                message="The configured LLM provider has no server-side API key.",
                details={"hint": "Set LLM_API_KEY on the backend."},
            )

        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "temperature": 0.25,
                    "max_tokens": 500,
                    "response_format": {"type": "json_object"},
                    "messages": _build_messages(context),
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            primary_file_id = next(
                (
                    str(source.get("file_id"))
                    for source in context.uploaded_sources
                    if source.get("file_id")
                ),
                None,
            )
            return _normalize_questions(
                _parse_json_content(content),
                grounding_file_id=primary_file_id,
            )
        except AppError:
            raise
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise AppError(
                status_code=502,
                code="llm_strategy_generation_failed",
                message="The configured LLM provider did not return a usable interview outline.",
                details={"provider": "openai_compatible", "reason": str(exc)[:240]},
            ) from exc
