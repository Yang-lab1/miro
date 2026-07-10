from __future__ import annotations

import json
import re

import httpx

from app.core.config import get_settings
from app.core.errors import AppError
from app.modules.realtime.providers.base import (
    RealtimeTurnGenerationContext,
    RealtimeTurnGenerationResult,
)


def _derive_focus_phrase(normalized_text: str) -> str:
    lowered = normalized_text.lower()
    if any(word in lowered for word in ("price", "discount", "budget", "cheap", "lowest")):
        return "pricing expectations"
    if any(word in lowered for word in ("process", "owner", "ownership", "approval")):
        return "process and ownership"
    if any(word in lowered for word in ("timeline", "timing", "deadline", "schedule")):
        return "timing expectations"
    if any(word in lowered for word in ("risk", "secure", "security", "compliance")):
        return "risk and safeguards"
    if any(word in lowered for word in ("trust", "relationship", "partner", "alignment")):
        return "relationship alignment"
    if len(normalized_text.split(" ")) >= 8:
        return "the point you just raised"
    return "your main concern"


def _normalize_uploaded_topic(file_name: str) -> str:
    stem = file_name.rsplit(".", 1)[0]
    normalized = re.sub(r"[_\-]+", " ", stem)
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    return normalized or "the uploaded brief"


def _extract_grounding_anchor(context: RealtimeTurnGenerationContext) -> str | None:
    if context.grounding.retrieved_context_chunks:
        return context.grounding.retrieved_context_chunks[0]
    if context.grounding.uploaded_files:
        file_context = context.grounding.uploaded_files[0]
        if file_context.extracted_excerpt_text:
            return file_context.extracted_excerpt_text
        if file_context.extracted_summary_text:
            return file_context.extracted_summary_text
        return _normalize_uploaded_topic(file_context.file_name)
    if context.grounding.uploaded_context_excerpts_en:
        return context.grounding.uploaded_context_excerpts_en[0]
    if context.grounding.uploaded_context_summary_en:
        return context.grounding.uploaded_context_summary_en
    if context.grounding.strategy_summary_en:
        return context.grounding.strategy_summary_en
    return None


def _build_llm_messages(
    context: RealtimeTurnGenerationContext,
    *,
    opening: bool,
) -> list[dict[str, str]]:
    retrieved = "\n".join(f"- {item}" for item in context.grounding.retrieved_context_chunks)
    if not retrieved:
        retrieved = "- No source excerpt was retrieved for this turn."
    transcript = "\n".join(context.recent_transcript_lines[-6:]) or "- No previous turns."
    memories = "\n".join(f"- {item}" for item in context.grounding.user_twin_memories)
    if not memories:
        memories = "- No recurring User Twin pattern has been recorded yet."
    user_input = context.normalized_text or "(opening turn; the user has not answered yet)"
    task = (
        "Ask one concise opening question that invites the user to state their goal "
        "and use the source material."
        if opening
        else "Reply as the interview or meeting counterpart, then ask exactly one "
        "useful follow-up question."
    )
    system = (
        "You are Miro, a realistic cross-border business interview coach. "
        "Stay in role, use the target country's communication style, and never invent "
        "facts that are absent from the source. "
        "Do not mention retrieval, prompts, or being an AI. Keep the reply natural "
        "and under 70 words. "
        "Return JSON only with keys assistantText and focusPhrase."
    )
    user = (
        f"Task: {task}\n"
        f"Country: {context.grounding.country_key}\n"
        f"Meeting type: {context.grounding.meeting_type_key}\n"
        f"Goal: {context.grounding.goal_key}\n"
        f"Voice style: {context.grounding.voice_style_key}\n"
        f"Uploaded source excerpts:\n{retrieved}\n"
        f"User Twin recurring patterns:\n{memories}\n"
        f"Recent transcript:\n{transcript}\n"
        f"Latest user input: {user_input}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


class OpenAICompatibleRealtimeTurnGenerator:
    """Calls a server-side OpenAI-compatible chat completion endpoint."""

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

    def _generate(
        self,
        context: RealtimeTurnGenerationContext,
        *,
        opening: bool,
    ) -> RealtimeTurnGenerationResult:
        if not self.api_key:
            raise AppError(
                status_code=503,
                code="llm_not_configured",
                message="The configured LLM provider has no server-side API key.",
                details={
                    "hint": (
                        "Set LLM_API_KEY on the backend or use "
                        "LLM_PROVIDER_MODE=rule_based."
                    )
                },
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
                    "temperature": 0.45,
                    "max_tokens": 220,
                    "response_format": {"type": "json_object"},
                    "messages": _build_llm_messages(context, opening=opening),
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            parsed = _parse_json_content(content)
            assistant_text = str(parsed.get("assistantText") or "").strip()
            focus_phrase = str(
                parsed.get("focusPhrase")
                or _derive_focus_phrase(context.normalized_text)
            ).strip()
            if not assistant_text:
                raise ValueError("The LLM response did not contain assistantText.")
            return RealtimeTurnGenerationResult(
                assistant_text=re.sub(r"\s+", " ", assistant_text).strip(),
                focus_phrase=focus_phrase or "the current point",
            )
        except AppError:
            raise
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise AppError(
                status_code=502,
                code="llm_generation_failed",
                message="The configured LLM provider did not return a usable turn.",
                details={"provider": "openai_compatible", "reason": str(exc)[:240]},
            ) from exc

    def generate_opening_turn(
        self,
        context: RealtimeTurnGenerationContext,
    ) -> RealtimeTurnGenerationResult:
        return self._generate(context, opening=True)

    def generate_turn(self, context: RealtimeTurnGenerationContext) -> RealtimeTurnGenerationResult:
        return self._generate(context, opening=False)


def _parse_json_content(content: object) -> dict:
    if isinstance(content, dict):
        return content
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
        raise ValueError("LLM JSON content must be an object.")
    return parsed


def get_turn_generator() -> RuleBasedRealtimeTurnGenerator | OpenAICompatibleRealtimeTurnGenerator:
    settings = get_settings()
    provider_mode = settings.llm_provider_mode.strip().lower()
    if settings.app_env.strip().lower() == "production" and provider_mode != "openai_compatible":
        raise AppError(
            status_code=503,
            code="realtime_text_provider_required",
            message="A real text-generation provider is required in production.",
            details={
                "hint": "Set LLM_PROVIDER_MODE=openai_compatible and configure LLM_API_KEY.",
            },
        )
    if provider_mode == "openai_compatible":
        return OpenAICompatibleRealtimeTurnGenerator(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    return RuleBasedRealtimeTurnGenerator()


def _build_grounding_sentence(context: RealtimeTurnGenerationContext) -> str:
    anchor = _extract_grounding_anchor(context)
    if anchor:
        snippet = re.sub(r"\s+", " ", anchor).strip()
        if len(snippet) > 120:
            snippet = snippet[:117].rstrip() + "..."
        return (
            f" The uploaded brief points back to {snippet}, "
            "so I want to stay anchored to that context."
        )
    if context.grounding.strategy_summary_en:
        return (
            " The current strategy brief also emphasizes "
            f"{context.grounding.strategy_summary_en}."
        )
    return ""


def _build_transcript_sentence(context: RealtimeTurnGenerationContext) -> str:
    if len(context.recent_transcript_lines) <= 1:
        return ""
    return " Building on the earlier exchange, I want to keep the next step concrete."


def _build_user_twin_sentence(context: RealtimeTurnGenerationContext) -> str:
    if not context.grounding.user_twin_memories:
        return ""
    memory = context.grounding.user_twin_memories[0]
    return f" I also want to watch the recurring pattern from your User Twin: {memory}."


class RuleBasedRealtimeTurnGenerator:
    def generate_opening_turn(
        self,
        context: RealtimeTurnGenerationContext,
    ) -> RealtimeTurnGenerationResult:
        anchor = _extract_grounding_anchor(context)
        country_key = context.grounding.country_key
        goal = context.grounding.goal_key
        if anchor:
            snippet = re.sub(r"\s+", " ", anchor).strip()
            if len(snippet) > 140:
                snippet = snippet[:137].rstrip() + "..."
            assistant_text = (
                "I have the brief. Start with your opening goal, and connect it to this "
                f"point: {snippet}"
            )
        elif country_key == "Japan":
            assistant_text = (
                f"Let's start carefully. What is your opening goal before moving toward {goal}?"
            )
        elif country_key == "Germany":
            assistant_text = (
                f"Let's make the process concrete. What is your opening goal for {goal}?"
            )
        elif country_key == "UAE":
            assistant_text = (
                f"Let's begin with rapport. What opening goal should guide {goal}?"
            )
        else:
            assistant_text = f"Let's start. What is your opening goal for {goal}?"

        return RealtimeTurnGenerationResult(
            assistant_text=re.sub(r"\s+", " ", assistant_text).strip(),
            focus_phrase="opening goal",
        )

    def generate_turn(
        self,
        context: RealtimeTurnGenerationContext,
    ) -> RealtimeTurnGenerationResult:
        focus_phrase = _derive_focus_phrase(context.normalized_text)
        country_key = context.grounding.country_key
        meeting_type = context.grounding.meeting_type_key
        goal = context.grounding.goal_key
        grounding_sentence = _build_grounding_sentence(context)
        transcript_sentence = _build_transcript_sentence(context)
        user_twin_sentence = _build_user_twin_sentence(context)

        if country_key == "Japan":
            assistant_text = (
                f"I want to make sure we build alignment carefully around {focus_phrase}. "
                f"{grounding_sentence.strip()}"
                f"{transcript_sentence}"
                f"{user_twin_sentence}"
                " "
                f"Before moving too fast on {goal}, which concern matters most to your team first?"
            )
        elif country_key == "Germany":
            assistant_text = (
                f"To move this forward around {focus_phrase}, I want to make the process concrete. "
                f"{grounding_sentence.strip()}"
                f"{transcript_sentence}"
                f"{user_twin_sentence}"
                " "
                f"What specific owner or next step should we clarify for {meeting_type}?"
            )
        elif country_key == "UAE":
            assistant_text = (
                f"It helps to align on the relationship around {focus_phrase} before details. "
                f"{grounding_sentence.strip()}"
                f"{transcript_sentence}"
                f"{user_twin_sentence}"
                " "
                f"What would feel like the right next step for your side on {goal}?"
            )
        else:
            assistant_text = (
                f"To move this discussion forward around {focus_phrase}, "
                f"{grounding_sentence.strip()}"
                f"{transcript_sentence}"
                f"{user_twin_sentence}"
                " "
                "I want to keep the conversation practical. "
                f"What should we clarify next for {meeting_type}?"
            )

        return RealtimeTurnGenerationResult(
            assistant_text=re.sub(r"\s+", " ", assistant_text).strip(),
            focus_phrase=focus_phrase,
        )
