from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models.review import Review, ReviewLine
from app.models.simulation import (
    RealtimeSession,
    RealtimeSessionAlert,
    RealtimeSessionTurn,
    Simulation,
    VoiceProfileCatalog,
)
from app.models.user import User

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


def _create_realtime_session(client, simulation_id: str, *, transport: str | None = None) -> dict:
    payload = {"simulationId": simulation_id}
    if transport is not None:
        payload["transport"] = transport

    response = client.post("/api/v1/realtime/sessions", json=payload)
    assert response.status_code == 200
    return response.json()


def _create_active_realtime_session(client, country_key: str = "Japan") -> tuple[dict, dict]:
    simulation = _create_strategy_ready_simulation(client, country_key)
    created = _create_realtime_session(client, simulation["simulationId"])
    started = client.post(f"/api/v1/realtime/sessions/{created['sessionId']}/start")
    assert started.status_code == 200
    return simulation, started.json()


def _respond_turn(
    client,
    session_id: str,
    *,
    source_text: str,
    input_mode: str = "text",
    language: str | None = None,
):
    payload = {"inputMode": input_mode, "sourceText": source_text}
    if language is not None:
        payload["language"] = language
    return client.post(f"/api/v1/realtime/sessions/{session_id}/turns/respond", json=payload)


def _bridge_review(client, session_id: str):
    return client.post(f"/api/v1/reviews/from-realtime/{session_id}")


def _end_realtime_session(client, session_id: str):
    return client.post(f"/api/v1/realtime/sessions/{session_id}/end")


def _expire_realtime_session(db_session, session_id: str) -> None:
    record = db_session.scalar(select(RealtimeSession).where(RealtimeSession.id == session_id))
    assert record is not None
    record.launch_expires_at = datetime.now(tz=UTC) - timedelta(minutes=1)
    db_session.commit()


def _get_review_record(db_session, review_id: str) -> Review:
    db_session.expire_all()
    review = db_session.scalar(select(Review).where(Review.id == review_id))
    assert review is not None
    return review


def _get_voice_profile(db_session, voice_profile_id: str) -> VoiceProfileCatalog:
    voice_profile = db_session.scalar(
        select(VoiceProfileCatalog).where(VoiceProfileCatalog.voice_profile_id == voice_profile_id)
    )
    assert voice_profile is not None
    return voice_profile


def _create_other_actor_finished_session(
    db_session,
    *,
    country_key: str = "Japan",
) -> tuple[User, RealtimeSession]:
    other_user = User(email=f"other-review-{country_key.lower()}@miro.local", status="active")
    db_session.add(other_user)
    db_session.flush()

    voice_profile = _get_voice_profile(db_session, COUNTRY_SETUP[country_key]["voiceProfileId"])
    simulation = Simulation(
        user_id=other_user.id,
        country_key=country_key,
        meeting_type_key=COUNTRY_SETUP[country_key]["meetingType"],
        goal_key=COUNTRY_SETUP[country_key]["goal"],
        duration_minutes=COUNTRY_SETUP[country_key]["durationMinutes"],
        voice_style_key=COUNTRY_SETUP[country_key]["voiceStyle"],
        voice_profile_catalog_id=voice_profile.id,
        simulation_status="strategy_ready",
        setup_revision=1,
        strategy_payload_json={"templateKey": "seed"},
        strategy_for_setup_revision=1,
    )
    db_session.add(simulation)
    db_session.flush()

    now = datetime.now(tz=UTC)
    realtime_session = RealtimeSession(
        simulation_id=simulation.id,
        user_id=other_user.id,
        country_key=country_key,
        meeting_type_key=simulation.meeting_type_key or "",
        goal_key=simulation.goal_key or "",
        duration_minutes=simulation.duration_minutes or 0,
        voice_style_key=simulation.voice_style_key or "",
        voice_profile_catalog_id=voice_profile.id,
        setup_revision=1,
        strategy_for_setup_revision=1,
        transport="webrtc",
        session_status="ended",
        status_reason="manually_ended",
        provider_mode="stub",
        provider_status="closed",
        provider_payload_json={"kind": "stub"},
        launch_payload_json={
            "mode": "stub",
            "transport": "webrtc",
            "sessionToken": "other-review-token",
            "connectUrl": None,
            "fallbackTransport": "websocket",
            "expiresAt": (now + timedelta(minutes=15)).isoformat(),
        },
        launch_expires_at=now + timedelta(minutes=15),
        ended_at=now,
        started_at=now - timedelta(minutes=1),
        next_turn_index=1,
        turn_count=0,
        alert_count=0,
    )
    db_session.add(realtime_session)
    db_session.commit()
    return other_user, realtime_session


def _create_manual_review_for_other_actor(db_session) -> Review:
    other_user, realtime_session = _create_other_actor_finished_session(db_session)
    voice_profile = _get_voice_profile(db_session, COUNTRY_SETUP["Japan"]["voiceProfileId"])

    review = Review(
        user_id=other_user.id,
        realtime_session_id=realtime_session.id,
        review_source="realtime_session",
        country_key="Japan",
        meeting_type_key="first_introduction",
        goal_key="establish_trust_before_pricing",
        duration_minutes=10,
        voice_style_key="formal_measured",
        voice_profile_catalog_id=voice_profile.id,
        setup_revision=1,
        strategy_for_setup_revision=1,
        review_status="ready",
        overall_assessment="mixed",
        title_text="Good momentum with room to sharpen.",
        summary_json={
            "headline": "Good momentum with room to sharpen.",
            "coachSummary": (
                "The session showed useful momentum, but answers still needed more structure."
            ),
            "nextStep": (
                "Next time, answer with one concrete point and one follow-up question "
                "before you pause."
            ),
        },
        metrics_json={
            "turnCount": 2,
            "alertCount": 1,
            "highSeverityCount": 0,
            "mediumSeverityCount": 1,
            "topIssueKeys": ["underdeveloped_answer"],
        },
        repeated_issues_json=["underdeveloped_answer"],
        ended_at=realtime_session.ended_at,
    )
    db_session.add(review)
    db_session.flush()
    db_session.add(
        ReviewLine(
            review_id=review.id,
            line_index=1,
            speaker="user",
            turn_index=1,
            text="Need more context.",
            source_text="Need more context.",
            alert_issue_keys_json=["underdeveloped_answer"],
        )
    )
    db_session.commit()
    return review


def test_create_review_from_ended_session_returns_detail_snapshot(client):
    _, realtime_session = _create_active_realtime_session(client, "Japan")
    responded = _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text="We can align on one practical milestone and confirm the next owner together.",
    )
    assert responded.status_code == 200
    ended = _end_realtime_session(client, realtime_session["sessionId"])
    assert ended.status_code == 200

    response = _bridge_review(client, realtime_session["sessionId"])

    assert response.status_code == 200
    payload = response.json()
    assert payload["sourceType"] == "realtime_session"
    assert payload["sourceSessionId"] == realtime_session["sessionId"]
    assert payload["status"] == "ready"
    assert payload["countryKey"] == "Japan"
    assert payload["meetingType"] == "first_introduction"
    assert payload["goal"] == "establish_trust_before_pricing"
    assert payload["voiceProfileId"] == "vp_japan_female_01"
    assert len(payload["lines"]) == 2


def test_create_review_from_failed_session_after_runtime_sync(client, db_session):
    simulation = _create_strategy_ready_simulation(client, "Japan")
    created = _create_realtime_session(client, simulation["simulationId"])
    _expire_realtime_session(db_session, created["sessionId"])

    response = _bridge_review(client, created["sessionId"])

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["sourceSessionId"] == created["sessionId"]
    session_record = db_session.scalar(
        select(RealtimeSession).where(RealtimeSession.id == created["sessionId"])
    )
    assert session_record is not None
    assert session_record.session_status == "failed"


def test_create_review_rejects_pending_session(client):
    simulation = _create_strategy_ready_simulation(client, "Japan")
    created = _create_realtime_session(client, simulation["simulationId"])

    response = _bridge_review(client, created["sessionId"])

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "realtime_session_not_finished"


def test_create_review_rejects_active_session(client):
    _, realtime_session = _create_active_realtime_session(client, "Japan")

    response = _bridge_review(client, realtime_session["sessionId"])

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "realtime_session_not_finished"


def test_create_review_is_idempotent_for_same_session(client):
    _, realtime_session = _create_active_realtime_session(client, "Japan")
    first_turn = _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text="We can align on one practical milestone and confirm the next owner together.",
    )
    assert first_turn.status_code == 200
    ended = client.post(f"/api/v1/realtime/sessions/{realtime_session['sessionId']}/end")
    assert ended.status_code == 200

    first = _bridge_review(client, realtime_session["sessionId"])
    second = _bridge_review(client, realtime_session["sessionId"])

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["reviewId"] == first.json()["reviewId"]


def test_reviews_list_returns_current_actor_reviews_in_desc_order(client, db_session):
    _, session_one = _create_active_realtime_session(client, "Japan")
    response_one = _respond_turn(
        client,
        session_one["sessionId"],
        source_text="Need more context.",
    )
    assert response_one.status_code == 200
    assert _end_realtime_session(client, session_one["sessionId"]).status_code == 200
    review_one = _bridge_review(client, session_one["sessionId"]).json()

    _, session_two = _create_active_realtime_session(client, "Japan")
    response_two = _respond_turn(
        client,
        session_two["sessionId"],
        source_text=(
            "We can document the owner, the timeline, and the next milestone before "
            "we move on."
        ),
    )
    assert response_two.status_code == 200
    assert _end_realtime_session(client, session_two["sessionId"]).status_code == 200
    review_two = _bridge_review(client, session_two["sessionId"]).json()

    record_one = _get_review_record(db_session, review_one["reviewId"])
    record_two = _get_review_record(db_session, review_two["reviewId"])
    record_one.created_at = datetime.now(tz=UTC) - timedelta(hours=1)
    record_two.created_at = datetime.now(tz=UTC)
    db_session.commit()

    response = client.get("/api/v1/reviews")

    assert response.status_code == 200
    payload = response.json()
    assert [item["reviewId"] for item in payload][:2] == [
        review_two["reviewId"],
        review_one["reviewId"],
    ]


def test_review_detail_is_snapshot_not_live_aggregate(client, db_session):
    _, realtime_session = _create_active_realtime_session(client, "Japan")
    responded = _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text="Need more context.",
    )
    assert responded.status_code == 200
    assert _end_realtime_session(client, realtime_session["sessionId"]).status_code == 200
    review = _bridge_review(client, realtime_session["sessionId"]).json()

    session_record = db_session.scalar(
        select(RealtimeSession).where(RealtimeSession.id == realtime_session["sessionId"])
    )
    assert session_record is not None
    extra_turn = RealtimeSessionTurn(
        session_id=session_record.id,
        turn_index=99,
        speaker="user",
        input_mode="text",
        source_text="Late mutation should not appear in the review snapshot.",
        normalized_text="Late mutation should not appear in the review snapshot.",
        language="en",
    )
    db_session.add(extra_turn)
    db_session.flush()
    db_session.add(
        RealtimeSessionAlert(
            session_id=session_record.id,
            turn_id=extra_turn.id,
            severity="high",
            issue_key="overclaiming",
            title_text="Claim sounds too absolute",
            detail_text="The wording may sound overconfident or hard to defend.",
        )
    )
    session_record.turn_count += 1
    session_record.alert_count += 1
    session_record.last_alert_severity = "high"
    db_session.commit()

    detail = client.get(f"/api/v1/reviews/{review['reviewId']}")

    assert detail.status_code == 200
    payload = detail.json()
    assert payload["metrics"]["turnCount"] == 2
    assert payload["metrics"]["alertCount"] == 1
    assert len(payload["lines"]) == 2


def test_review_lines_keep_user_and_assistant_and_map_alerts(client):
    _, realtime_session = _create_active_realtime_session(client, "Japan")
    responded = _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text="price 100%",
    )
    assert responded.status_code == 200
    assert _end_realtime_session(client, realtime_session["sessionId"]).status_code == 200

    detail = _bridge_review(client, realtime_session["sessionId"])

    assert detail.status_code == 200
    payload = detail.json()
    assert payload["overallAssessment"] == "needs_work"
    assert payload["lines"][0]["lineIndex"] == 1
    assert payload["lines"][0]["speaker"] == "user"
    assert payload["lines"][0]["turnIndex"] == 1
    assert payload["lines"][0]["alertIssueKeys"] == [
        "underdeveloped_answer",
        "premature_pricing_push",
    ]
    assert payload["lines"][1]["lineIndex"] == 2
    assert payload["lines"][1]["speaker"] == "assistant"
    assert payload["lines"][1]["alertIssueKeys"] == []


def test_review_top_issue_keys_sort_by_frequency_then_first_seen(client):
    _, realtime_session = _create_active_realtime_session(client, "Japan")
    first = _respond_turn(client, realtime_session["sessionId"], source_text="price 100%")
    second = _respond_turn(client, realtime_session["sessionId"], source_text="always")
    assert first.status_code == 200
    assert second.status_code == 200
    assert _end_realtime_session(client, realtime_session["sessionId"]).status_code == 200

    detail = _bridge_review(client, realtime_session["sessionId"])

    assert detail.status_code == 200
    assert detail.json()["metrics"]["topIssueKeys"] == [
        "underdeveloped_answer",
        "premature_pricing_push",
        "overclaiming",
    ]


def test_review_overall_assessment_mixed(client):
    _, realtime_session = _create_active_realtime_session(client, "Japan")
    responded = _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text="Need more context.",
    )
    assert responded.status_code == 200
    assert _end_realtime_session(client, realtime_session["sessionId"]).status_code == 200

    detail = _bridge_review(client, realtime_session["sessionId"])

    assert detail.status_code == 200
    assert detail.json()["overallAssessment"] == "mixed"


def test_review_overall_assessment_promising(client):
    _, realtime_session = _create_active_realtime_session(client, "Japan")
    first = _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text="We can align on one practical milestone and confirm the next owner together.",
    )
    second = _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text=(
            "We should map the next decision, the timeline, and the internal "
            "approval path clearly."
        ),
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert _end_realtime_session(client, realtime_session["sessionId"]).status_code == 200

    detail = _bridge_review(client, realtime_session["sessionId"])

    assert detail.status_code == 200
    payload = detail.json()
    assert payload["overallAssessment"] == "promising"
    assert payload["summary"]["headline"] == "Strong rehearsal baseline."


def test_review_list_and_detail_are_actor_scoped(client, db_session):
    _, own_session = _create_active_realtime_session(client, "Japan")
    responded = _respond_turn(
        client,
        own_session["sessionId"],
        source_text="Need more context.",
    )
    assert responded.status_code == 200
    assert _end_realtime_session(client, own_session["sessionId"]).status_code == 200
    own_review = _bridge_review(client, own_session["sessionId"]).json()

    other_review = _create_manual_review_for_other_actor(db_session)

    listed = client.get("/api/v1/reviews")
    assert listed.status_code == 200
    listed_ids = [item["reviewId"] for item in listed.json()]
    assert own_review["reviewId"] in listed_ids
    assert other_review.id not in listed_ids

    detail = client.get(f"/api/v1/reviews/{other_review.id}")
    assert detail.status_code == 404
    assert detail.json()["error"]["code"] == "review_not_found"


def test_review_bridge_is_actor_scoped(client, db_session):
    _, other_session = _create_other_actor_finished_session(db_session)

    response = _bridge_review(client, other_session.id)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "realtime_session_not_found"
