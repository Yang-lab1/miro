def test_txt_upload_to_review_to_hardware_sync_backend_flow(client):
    text_content = (
        "Renewal timing should stay conservative. "
        "Confirm the internal owner before discussing pricing."
    )

    created = client.post(
        "/api/v1/simulations",
        json={
            "countryKey": "Japan",
            "meetingType": "first_introduction",
            "goal": "establish_trust_before_pricing",
            "durationMinutes": 10,
            "voiceStyle": "formal_measured",
            "voiceProfileId": "vp_japan_female_01",
            "constraints": "Keep the conversation calm and evidence-led.",
        },
    )
    assert created.status_code == 200
    simulation_id = created.json()["simulationId"]

    uploaded = client.post(
        f"/api/v1/simulations/{simulation_id}/files",
        json={
            "files": [
                {
                    "fileName": "renewal-notes.txt",
                    "contentType": "text/plain",
                    "sizeBytes": len(text_content.encode("utf-8")),
                    "sourceType": "manual_upload",
                    "textContent": text_content,
                }
            ]
        },
    )
    assert uploaded.status_code == 200
    uploaded_file = uploaded.json()["uploadedFiles"][0]
    assert uploaded_file["parseStatus"] == "ready"
    assert "renewal timing" in uploaded_file["extractedSummaryText"].lower()

    strategy_response = client.post(f"/api/v1/simulations/{simulation_id}/strategy")
    assert strategy_response.status_code == 200
    strategy = strategy_response.json()["strategy"]
    assert strategy["interviewOutline"]
    assert "renewal timing" in strategy["interviewOutline"][0]["prompt"].lower()

    realtime_created = client.post(
        "/api/v1/realtime/sessions",
        json={"simulationId": simulation_id, "seedOpeningTurn": True},
    )
    assert realtime_created.status_code == 200
    session_id = realtime_created.json()["sessionId"]

    started = client.post(f"/api/v1/realtime/sessions/{session_id}/start")
    assert started.status_code == 200
    assert started.json()["openingTurn"]["speaker"] == "assistant"
    assert "renewal timing" in started.json()["openingTurn"]["sourceText"].lower()

    exchange = client.post(
        f"/api/v1/realtime/sessions/{session_id}/turns/respond",
        json={
            "inputMode": "speech_stub",
            "sourceText": "We need to discuss price now.",
            "language": "en",
        },
    )
    assert exchange.status_code == 200
    assert exchange.json()["userTurn"]["turnIndex"] == 2
    assert exchange.json()["assistantTurn"]["turnIndex"] == 3

    ended = client.post(f"/api/v1/realtime/sessions/{session_id}/end")
    assert ended.status_code == 200

    review = client.post(f"/api/v1/reviews/from-realtime/{session_id}")
    assert review.status_code == 200
    review_payload = review.json()
    assert review_payload["reviewId"]
    assert review_payload["sourceSessionId"] == session_id
    assert review_payload["lines"][0]["speaker"] == "assistant"

    user_twin = client.get("/api/v1/user-twin", params={"countryKey": "Japan"})
    assert user_twin.status_code == 200
    assert user_twin.json()["items"]
    memory = user_twin.json()["items"][0]
    assert memory["issueCount"] == 1
    refreshed = client.post(
        f"/api/v1/user-twin/refresh-from-review/{review_payload['reviewId']}"
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["items"][0]["issueCount"] == 1

    reviews = client.get("/api/v1/reviews")
    assert reviews.status_code == 200
    assert review_payload["reviewId"] in {item["reviewId"] for item in reviews.json()}

    hardware_sync = client.post(f"/api/v1/hardware/reviews/{review_payload['reviewId']}/sync")
    assert hardware_sync.status_code == 200
    sync_payload = hardware_sync.json()
    assert sync_payload["syncRecord"]["reviewId"] == review_payload["reviewId"]
    assert sync_payload["device"]["connected"] is True
