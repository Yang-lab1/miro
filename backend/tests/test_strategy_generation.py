import httpx

from app.modules.simulation.strategy_generation import (
    OpenAICompatibleStrategyGenerator,
    StrategyGenerationContext,
)


def _context() -> StrategyGenerationContext:
    return StrategyGenerationContext(
        country_key="Japan",
        meeting_type_key="first_introduction",
        goal_key="establish_trust_before_pricing",
        voice_style_key="formal_measured",
        learning_bullets=["Build trust before introducing commercial pressure."],
        uploaded_sources=[
            {
                "file_id": "file-1",
                "file_name": "renewal-brief.txt",
                "text": "Renewal timing should stay conservative. Confirm the internal owner.",
            }
        ],
        user_twin_memories=["premature_pricing_push: appeared 2 times"],
    )


def test_openai_compatible_strategy_generator_uses_grounding_and_returns_three_stages(
    monkeypatch,
):
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read().decode("utf-8")
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"questions":['
                                '{"stage":"opening","prompt":"What is your opening goal?",'
                                '"expectedSignal":"A clear goal tied to the brief."},'
                                '{"stage":"probe","prompt":"Who owns the renewal decision?",'
                                '"expectedSignal":"The owner and timing are explicit."},'
                                '{"stage":"close","prompt":"What is the safest next step?",'
                                '"expectedSignal":"One dated, low-pressure action."}'
                                ']}'
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
    generator = OpenAICompatibleStrategyGenerator(
        api_key="test-key",
        base_url="https://llm.example/v1",
        model="test-model",
        timeout_seconds=5,
    )

    result = generator.generate(_context())

    assert [item.stage for item in result] == ["opening", "probe", "close"]
    assert result[0].groundingFileId == "file-1"
    assert "renewal timing" in captured["body"].lower()
    assert "premature_pricing_push" in captured["body"]


def test_simulation_strategy_uses_configured_provider_for_uploaded_context(
    client,
    monkeypatch,
):
    from app.core.config import get_settings

    captured: dict = {}

    def post(*args, **kwargs):
        captured["body"] = kwargs["json"]
        return httpx.Response(
            200,
            request=httpx.Request("POST", args[0]),
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"questions":['
                                '{"stage":"opening","prompt":"What is the trust goal?",'
                                '"expectedSignal":"A source-grounded goal."},'
                                '{"stage":"probe","prompt":"Who owns the next decision?",'
                                '"expectedSignal":"A named owner."},'
                                '{"stage":"close","prompt":"What happens next?",'
                                '"expectedSignal":"A concrete next step."}'
                                ']}'
                            )
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(httpx, "post", post)
    monkeypatch.setenv("LLM_PROVIDER_MODE", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    get_settings.cache_clear()

    created = client.post(
        "/api/v1/simulations",
        json={
            "countryKey": "Japan",
            "meetingType": "first_introduction",
            "goal": "establish_trust_before_pricing",
            "durationMinutes": 10,
            "voiceStyle": "formal_measured",
            "voiceProfileId": "vp_japan_female_01",
        },
    )
    simulation_id = created.json()["simulationId"]
    client.post(
        f"/api/v1/simulations/{simulation_id}/files",
        json={
            "files": [
                {
                    "fileName": "customer-brief.txt",
                    "contentType": "text/plain",
                    "sizeBytes": 68,
                    "sourceType": "manual_upload",
                    "textContent": "Confirm the internal owner before discussing renewal pricing.",
                }
            ]
        },
    )

    response = client.post(f"/api/v1/simulations/{simulation_id}/strategy")

    assert response.status_code == 200
    outline = response.json()["strategy"]["interviewOutline"]
    assert outline[0]["questionId"] == "llm-opening"
    assert outline[2]["stage"] == "close"
    assert "internal owner" in str(captured["body"]).lower()
