import re

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


def _build_grounding_sentence(context: RealtimeTurnGenerationContext) -> str:
    if context.grounding.uploaded_files:
        topic = _normalize_uploaded_topic(context.grounding.uploaded_files[0].file_name)
        return (
            f" The uploaded brief points back to {topic}, "
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


class RuleBasedRealtimeTurnGenerator:
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

        if country_key == "Japan":
            assistant_text = (
                f"I want to make sure we build alignment carefully around {focus_phrase}. "
                f"{grounding_sentence.strip()}"
                f"{transcript_sentence}"
                " "
                f"Before moving too fast on {goal}, which concern matters most to your team first?"
            )
        elif country_key == "Germany":
            assistant_text = (
                f"To move this forward around {focus_phrase}, I want to make the process concrete. "
                f"{grounding_sentence.strip()}"
                f"{transcript_sentence}"
                " "
                f"What specific owner or next step should we clarify for {meeting_type}?"
            )
        elif country_key == "UAE":
            assistant_text = (
                f"It helps to align on the relationship around {focus_phrase} before details. "
                f"{grounding_sentence.strip()}"
                f"{transcript_sentence}"
                " "
                f"What would feel like the right next step for your side on {goal}?"
            )
        else:
            assistant_text = (
                f"To move this discussion forward around {focus_phrase}, "
                f"{grounding_sentence.strip()}"
                f"{transcript_sentence}"
                " "
                "I want to keep the conversation practical. "
                f"What should we clarify next for {meeting_type}?"
            )

        return RealtimeTurnGenerationResult(
            assistant_text=re.sub(r"\s+", " ", assistant_text).strip(),
            focus_phrase=focus_phrase,
        )
