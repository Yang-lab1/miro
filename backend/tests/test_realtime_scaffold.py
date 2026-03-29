from sqlalchemy import select

from app.models.simulation import RealtimeSession

COUNTRY_SETUP = {
    "Japan": {
        "meetingType": "first_introduction",
        "goal": "establish_trust_before_pricing",
        "durationMinutes": 10,
        "voiceStyle": "formal_measured",
        "voiceProfileId": "vp_japan_female_01",
    },
    "Germany": {
        "meetingType": "commercial_alignment",
        "goal": "clarify_process_and_risk_ownership",
        "durationMinutes": 12,
        "voiceStyle": "direct_structured",
        "voiceProfileId": "vp_germany_male_01",
    },
}


def _create_simulation(client, country_key: str, *, full_setup: bool) -> dict:
    payload = {"countryKey": country_key}
    if full_setup:
        payload |= COUNTRY_SETUP[country_key]
        payload["constraints"] = "Keep the conversation calm and structured."

    response = client.post("/api/v1/simulations", json=payload)
    assert response.status_code == 200
    return response.json()


def _create_strategy_ready_simulation(client, country_key: str = "Japan") -> dict:
    created = _create_simulation(client, country_key, full_setup=True)
    generated = client.post(f"/api/v1/simulations/{created['simulationId']}/strategy")
    assert generated.status_code == 200
    return generated.json()


def _create_active_realtime_session(client, country_key: str = "Japan") -> tuple[dict, dict]:
    simulation = _create_strategy_ready_simulation(client, country_key)
    created = client.post(
        "/api/v1/realtime/sessions",
        json={"simulationId": simulation["simulationId"]},
    )
    assert created.status_code == 200
    started = client.post(f"/api/v1/realtime/sessions/{created.json()['sessionId']}/start")
    assert started.status_code == 200
    return simulation, started.json()


def _load_realtime_session(db_session, session_id: str) -> RealtimeSession:
    realtime_session = db_session.scalar(
        select(RealtimeSession).where(RealtimeSession.id == session_id)
    )
    assert realtime_session is not None
    return realtime_session


def test_grounding_context_includes_uploaded_file_metadata_and_strategy_summary(
    client,
    db_session,
):
    from app.modules.realtime.grounding import build_realtime_grounding_context

    created = _create_simulation(client, "Japan", full_setup=True)
    uploaded = client.post(
        f"/api/v1/simulations/{created['simulationId']}/files",
        json={
            "files": [
                {
                    "fileName": "brief.pdf",
                    "contentType": "application/pdf",
                    "sizeBytes": 4096,
                    "sourceType": "manual_upload",
                }
            ]
        },
    )
    assert uploaded.status_code == 200
    generated = client.post(f"/api/v1/simulations/{created['simulationId']}/strategy")
    assert generated.status_code == 200

    created_session = client.post(
        "/api/v1/realtime/sessions",
        json={"simulationId": created["simulationId"]},
    )
    assert created_session.status_code == 200

    realtime_session = _load_realtime_session(db_session, created_session.json()["sessionId"])
    grounding = build_realtime_grounding_context(db_session, realtime_session)

    assert grounding.simulation_id == created["simulationId"]
    assert grounding.country_key == "Japan"
    assert grounding.strategy_summary_en is not None
    assert "establish_trust_before_pricing" in grounding.strategy_summary_en
    assert len(grounding.uploaded_files) == 1
    assert grounding.uploaded_files[0].file_name == "brief.pdf"
    assert grounding.uploaded_files[0].source_type == "manual_upload"
    assert grounding.uploaded_files[0].parse_status == "ready"
    assert grounding.uploaded_files[0].extracted_summary_text is not None
    assert "brief" in grounding.uploaded_files[0].extracted_summary_text.lower()
    assert grounding.uploaded_files[0].extracted_excerpt_text is not None
    assert grounding.uploaded_context_summary_en is not None
    assert "brief" in grounding.uploaded_context_summary_en.lower()
    assert grounding.uploaded_context_excerpts_en
    assert "brief.pdf" in grounding.uploaded_context_excerpts_en[0]
    assert any("brief.pdf" in bullet for bullet in grounding.strategy_bullets_en)


def test_rule_based_turn_generator_uses_grounded_context_in_response(client, db_session):
    from app.modules.realtime.grounding import build_realtime_grounding_context
    from app.modules.realtime.providers.base import RealtimeTurnGenerationContext
    from app.modules.realtime.turn_engine import RuleBasedRealtimeTurnGenerator

    created = _create_simulation(client, "Japan", full_setup=True)
    uploaded = client.post(
        f"/api/v1/simulations/{created['simulationId']}/files",
        json={
            "files": [
                {
                    "fileName": "pricing-brief.pdf",
                    "contentType": "application/pdf",
                    "sizeBytes": 4096,
                    "sourceType": "manual_upload",
                }
            ]
        },
    )
    assert uploaded.status_code == 200
    generated = client.post(f"/api/v1/simulations/{created['simulationId']}/strategy")
    assert generated.status_code == 200
    created_session = client.post(
        "/api/v1/realtime/sessions",
        json={"simulationId": created["simulationId"]},
    )
    assert created_session.status_code == 200
    started = client.post(f"/api/v1/realtime/sessions/{created_session.json()['sessionId']}/start")
    assert started.status_code == 200
    realtime_session_payload = started.json()
    realtime_session = _load_realtime_session(db_session, realtime_session_payload["sessionId"])
    grounding = build_realtime_grounding_context(db_session, realtime_session)

    result = RuleBasedRealtimeTurnGenerator().generate_turn(
        RealtimeTurnGenerationContext(
            session_id=realtime_session.id,
            provider_mode=realtime_session.provider_mode,
            language="en",
            normalized_text=(
                "Before anything else, we should discuss price and budget expectations "
                "for this introduction."
            ),
            grounding=grounding,
            recent_transcript_lines=[
                "assistant: Let us align on one practical next step first.",
                (
                    "user: Before anything else, we should discuss price and budget "
                    "expectations for this introduction."
                ),
            ],
        )
    )

    assert "pricing expectations" in result.assistant_text
    assert "Before moving too fast on establish_trust_before_pricing" in result.assistant_text
    assert "uploaded brief" in result.assistant_text
    assert "pricing brief" in result.assistant_text.lower()
    assert result.focus_phrase == "pricing expectations"


def test_rule_based_alert_analyzer_preserves_existing_alert_priority_and_cap(client, db_session):
    from app.modules.realtime.alerts import RuleBasedRealtimeAlertAnalyzer
    from app.modules.realtime.grounding import build_realtime_grounding_context
    from app.modules.realtime.providers.base import RealtimeAlertExtractionContext

    _, realtime_session_payload = _create_active_realtime_session(client, "Japan")
    realtime_session = _load_realtime_session(db_session, realtime_session_payload["sessionId"])
    grounding = build_realtime_grounding_context(db_session, realtime_session)

    alerts = RuleBasedRealtimeAlertAnalyzer().extract_alerts(
        RealtimeAlertExtractionContext(
            session_id=realtime_session.id,
            normalized_text="price discount guarantee 100%",
            grounding=grounding,
        )
    )

    assert [alert.issue_key for alert in alerts] == [
        "underdeveloped_answer",
        "premature_pricing_push",
    ]
    assert len(alerts) == 2
    assert alerts[-1].severity == "high"
