import httpx

from app.modules.realtime.providers.base import (
    RealtimeGroundingContext,
    RealtimeTurnGenerationContext,
)
from app.modules.realtime.turn_engine import OpenAICompatibleRealtimeTurnGenerator


def _context() -> RealtimeTurnGenerationContext:
    return RealtimeTurnGenerationContext(
        session_id="session-1",
        provider_mode="stub",
        language="en",
        normalized_text="We can discuss the renewal deadline.",
        recent_transcript_lines=["assistant: What matters most to your team?"],
        grounding=RealtimeGroundingContext(
            simulation_id="simulation-1",
            country_key="Germany",
            meeting_type_key="commercial_alignment",
            goal_key="clarify_process_and_risk_ownership",
            duration_minutes=12,
            voice_style_key="direct_structured",
            setup_revision=1,
            strategy_for_setup_revision=1,
            strategy_summary_en="Keep ownership and timing explicit.",
            strategy_bullets_en=[],
            uploaded_files=[],
            uploaded_context_summary_en=None,
            uploaded_context_excerpts_en=[],
            retrieved_context_chunks=["[brief.txt] The renewal deadline is 30 September."],
        ),
    )


def test_openai_compatible_generator_sends_retrieved_context_and_parses_json(monkeypatch):
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = request.read()
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"assistantText":"What owner will confirm the renewal date?",'
                                '"focusPhrase":"renewal ownership"}'
                            )
                        }
                    }
                ]
            },
        )

    def post(*args, **kwargs):
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            return client.post(*args, **kwargs)

    monkeypatch.setattr(httpx, "post", post)
    generator = OpenAICompatibleRealtimeTurnGenerator(
        api_key="test-key",
        base_url="https://llm.example/v1",
        model="test-model",
        timeout_seconds=5,
    )

    result = generator.generate_turn(_context())

    assert result.assistant_text == "What owner will confirm the renewal date?"
    assert result.focus_phrase == "renewal ownership"
    assert "renewal deadline" in captured["json"].decode("utf-8").lower()
