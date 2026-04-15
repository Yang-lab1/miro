import pytest
from sqlalchemy import select

from app.core.errors import AppError
from app.models.simulation import Simulation, SimulationUploadedFile
from app.models.user import User
from app.modules.simulation import service as simulation_service
from app.services.current_actor import resolve_current_actor

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


def test_get_simulation_setup_defaults_returns_launch_fields(client):
    response = client.get("/api/v1/simulations/setup-defaults/Japan")

    assert response.status_code == 200
    assert response.json() == {
        "countryKey": "Japan",
        "meetingType": "first_introduction",
        "goal": "establish_trust_before_pricing",
        "durationMinutes": 10,
        "voiceStyle": "formal_measured",
        "voiceProfileId": "vp_japan_female_01",
    }


def test_get_simulation_setup_defaults_rejects_unknown_country(client):
    response = client.get("/api/v1/simulations/setup-defaults/Atlantis")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "country_not_found"


def _create_simulation(client, country_key: str, *, full_setup: bool) -> dict:
    payload = {"countryKey": country_key}
    if full_setup:
        payload |= COUNTRY_SETUP[country_key]
        payload["constraints"] = "Keep the language conservative."

    response = client.post("/api/v1/simulations", json=payload)
    assert response.status_code == 200
    return response.json()


def test_create_simulation_with_country_only_returns_draft(client):
    payload = _create_simulation(client, "Japan", full_setup=False)

    assert payload["status"] == "draft"
    assert payload["setupRevision"] == 1
    assert payload["meetingType"] is None
    assert payload["voiceProfileId"] is None
    assert payload["uploadedFiles"] == []
    assert payload["strategy"] is None


def test_patch_simulation_to_ready_and_noop_preserves_revision(client):
    created = _create_simulation(client, "Japan", full_setup=False)

    patched = client.patch(
        f"/api/v1/simulations/{created['simulationId']}",
        json={
            **COUNTRY_SETUP["Japan"],
            "constraints": "The client is traditional and risk-sensitive.",
        },
    )
    assert patched.status_code == 200
    payload = patched.json()
    assert payload["status"] == "ready_for_strategy"
    assert payload["setupRevision"] == 2
    assert payload["voiceProfileId"] == "vp_japan_female_01"

    fetched = client.get(f"/api/v1/simulations/{created['simulationId']}")
    assert fetched.status_code == 200
    assert fetched.json()["simulationId"] == created["simulationId"]
    assert fetched.json()["status"] == "ready_for_strategy"

    noop = client.patch(f"/api/v1/simulations/{created['simulationId']}", json={})
    assert noop.status_code == 200
    assert noop.json()["setupRevision"] == 2


def test_add_files_bumps_revision_and_persists_grounding_stub_fields(client, db_session):
    created = _create_simulation(client, "Japan", full_setup=True)

    response = client.post(
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

    assert response.status_code == 200
    payload = response.json()
    assert payload["setupRevision"] == 2
    assert payload["status"] == "ready_for_strategy"
    assert len(payload["uploadedFiles"]) == 1
    file_payload = payload["uploadedFiles"][0]
    assert file_payload["sourceType"] == "manual_upload"
    assert file_payload["storageKey"] is None
    assert file_payload["parseStatus"] == "ready"
    assert file_payload["status"] == "registered"

    record = db_session.scalar(
        select(SimulationUploadedFile).where(
            SimulationUploadedFile.id == file_payload["fileId"]
        )
    )
    assert record is not None
    assert record.extracted_summary_text is not None
    assert "brief" in record.extracted_summary_text.lower()
    assert record.extracted_excerpt_text is not None
    assert "brief.pdf" in record.extracted_excerpt_text


def test_add_text_file_extracts_real_text_content(client, db_session):
    created = _create_simulation(client, "Japan", full_setup=True)
    text_content = (
        "Renewal timing should stay conservative. "
        "Do not push pricing before confirming the internal owner and timeline."
    )

    response = client.post(
        f"/api/v1/simulations/{created['simulationId']}/files",
        json={
            "files": [
                {
                    "fileName": "renewal-notes.txt",
                    "contentType": "text/plain",
                    "sizeBytes": len(text_content.encode('utf-8')),
                    "sourceType": "manual_upload",
                    "textContent": text_content,
                }
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()["uploadedFiles"][0]
    assert payload["parseStatus"] == "ready"

    record = db_session.scalar(
        select(SimulationUploadedFile).where(
            SimulationUploadedFile.id == payload["fileId"]
        )
    )
    assert record is not None
    assert record.extracted_summary_text is not None
    assert "renewal timing should stay conservative" in record.extracted_summary_text.lower()
    assert record.extracted_excerpt_text is not None
    assert "internal owner and timeline" in record.extracted_excerpt_text.lower()


def test_add_pdf_file_extracts_simple_text(client, db_session):
    created = _create_simulation(client, "Japan", full_setup=True)
    pdf_base64 = (
        "JVBERi0xLjQKMSAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZyAvUGFnZXMgMiAwIFIgPj4KZW5kb2Jq"
        "CjIgMCBvYmoKPDwgL1R5cGUgL1BhZ2VzIC9Db3VudCAxIC9LaWRzIFszIDAgUl0gPj4KZW5kb2Jq"
        "CjMgMCBvYmoKPDwgL1R5cGUgL1BhZ2UgL1BhcmVudCAyIDAgUiAvTWVkaWFCb3ggWzAgMCA2MTIg"
        "NzkyXSAvUmVzb3VyY2VzIDw8IC9Gb250IDw8IC9GMSA0IDAgUiA+PiA+PiAvQ29udGVudHMgNSAw"
        "IFIgPj4KZW5kb2JqCjQgMCBvYmoKPDwgL1R5cGUgL0ZvbnQgL1N1YnR5cGUgL1R5cGUxIC9CYXNl"
        "Rm9udCAvSGVsdmV0aWNhID4+CmVuZG9iago1IDAgb2JqCjw8IC9MZW5ndGggNzEgPj4Kc3RyZWFt"
        "CkJUCi9GMSAxOCBUZgo3MiA3MjAgVGQKKFJlbmV3YWwgdGltaW5nIHN0YXlzIGNvbnNlcnZhdGl2"
        "ZS4pIFRqCkVUCmVuZHN0cmVhbQplbmRvYmoKeHJlZgowIDYKMDAwMDAwMDAwMCA2NTUzNSBmIAow"
        "MDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNTggMDAwMDAgbiAKMDAwMDAwMDExNSAwMDAwMCBu"
        "IAowMDAwMDAwMjQxIDAwMDAwIG4gCjAwMDAwMDAzMTEgMDAwMDAgbiAKdHJhaWxlcgo8PCAvU2l6"
        "ZSA2IC9Sb290IDEgMCBSID4+CnN0YXJ0eHJlZgo0MzIKJSVFT0Y="
    )

    response = client.post(
        f"/api/v1/simulations/{created['simulationId']}/files",
        json={
            "files": [
                {
                    "fileName": "renewal-brief.pdf",
                    "contentType": "application/pdf",
                    "sizeBytes": 1024,
                    "sourceType": "manual_upload",
                    "fileDataBase64": pdf_base64,
                }
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()["uploadedFiles"][0]
    assert payload["parseStatus"] == "ready"

    record = db_session.scalar(
        select(SimulationUploadedFile).where(
            SimulationUploadedFile.id == payload["fileId"]
        )
    )
    assert record is not None
    assert record.extracted_summary_text is not None
    assert "renewal timing stays conservative" in record.extracted_summary_text.lower()
    assert record.extracted_excerpt_text is not None
    assert "renewal timing stays conservative" in record.extracted_excerpt_text.lower()


def test_add_pdf_file_falls_back_safely_when_text_extraction_fails(client, db_session):
    created = _create_simulation(client, "Japan", full_setup=True)

    response = client.post(
        f"/api/v1/simulations/{created['simulationId']}/files",
        json={
            "files": [
                {
                    "fileName": "broken-brief.pdf",
                    "contentType": "application/pdf",
                    "sizeBytes": 64,
                    "sourceType": "manual_upload",
                    "fileDataBase64": "bm90LWEtcmVhbC1wZGY=",
                }
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()["uploadedFiles"][0]
    assert payload["parseStatus"] == "fallback"

    record = db_session.scalar(
        select(SimulationUploadedFile).where(
            SimulationUploadedFile.id == payload["fileId"]
        )
    )
    assert record is not None
    assert record.extracted_summary_text is not None
    assert "broken brief" in record.extracted_summary_text.lower()


def test_generate_strategy_and_invalidate_on_setup_change(client):
    created = _create_simulation(client, "Japan", full_setup=True)

    generated = client.post(f"/api/v1/simulations/{created['simulationId']}/strategy")
    assert generated.status_code == 200
    generated_payload = generated.json()
    assert generated_payload["status"] == "strategy_ready"
    assert generated_payload["strategy"]["generatedFrom"]["setupRevision"] == 1

    updated = client.patch(
        f"/api/v1/simulations/{created['simulationId']}",
        json={"constraints": "Use even softer trust-building language."},
    )
    assert updated.status_code == 200
    updated_payload = updated.json()
    assert updated_payload["setupRevision"] == 2
    assert updated_payload["status"] == "ready_for_strategy"
    assert updated_payload["strategy"] is None


def test_voice_profile_country_mismatch_returns_error(client):
    created = _create_simulation(client, "Japan", full_setup=False)

    response = client.patch(
        f"/api/v1/simulations/{created['simulationId']}",
        json={"voiceProfileId": "vp_germany_male_01"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "voice_profile_country_mismatch"


def test_simulation_is_actor_scoped(client, db_session):
    other_user = User(email="other@miro.local", status="active")
    db_session.add(other_user)
    db_session.flush()
    simulation = Simulation(user_id=other_user.id, country_key="Japan", simulation_status="draft")
    db_session.add(simulation)
    db_session.commit()

    response = client.get(f"/api/v1/simulations/{simulation.id}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "simulation_not_found"


def test_validate_realtime_launch_prerequisites_requires_learning_ready(client, db_session):
    created = _create_simulation(client, "Germany", full_setup=True)
    generated = client.post(f"/api/v1/simulations/{created['simulationId']}/strategy")
    assert generated.status_code == 200

    actor = resolve_current_actor(db_session)
    with pytest.raises(AppError) as exc_info:
        simulation_service.validate_realtime_launch_prerequisites(
            db_session,
            actor,
            created["simulationId"],
        )
    assert exc_info.value.code == "learning_precheck_failed"


def test_validate_realtime_launch_prerequisites_allows_explicit_learning_skip(client, db_session):
    created = _create_simulation(client, "Germany", full_setup=True)
    generated = client.post(f"/api/v1/simulations/{created['simulationId']}/strategy")
    assert generated.status_code == 200

    actor = resolve_current_actor(db_session)
    prerequisites = simulation_service.validate_realtime_launch_prerequisites(
        db_session,
        actor,
        created["simulationId"],
        skip_learning_precheck=True,
    )

    assert prerequisites.simulation_id == created["simulationId"]
    assert prerequisites.precheck.ready is False
    assert prerequisites.precheck.skipLearningAllowed is True


def test_validate_realtime_launch_prerequisites_requires_strategy(client, db_session):
    created = _create_simulation(client, "Japan", full_setup=True)

    actor = resolve_current_actor(db_session)
    with pytest.raises(AppError) as exc_info:
        simulation_service.validate_realtime_launch_prerequisites(
            db_session,
            actor,
            created["simulationId"],
        )
    assert exc_info.value.code == "simulation_strategy_missing"


def test_validate_realtime_launch_prerequisites_requires_current_revision(client, db_session):
    created = _create_simulation(client, "Japan", full_setup=True)
    generated = client.post(f"/api/v1/simulations/{created['simulationId']}/strategy")
    assert generated.status_code == 200

    simulation = db_session.scalar(
        select(Simulation).where(Simulation.id == created["simulationId"])
    )
    assert simulation is not None
    simulation.setup_revision += 1
    db_session.commit()

    actor = resolve_current_actor(db_session)
    with pytest.raises(AppError) as exc_info:
        simulation_service.validate_realtime_launch_prerequisites(
            db_session,
            actor,
            created["simulationId"],
        )
    assert exc_info.value.code == "simulation_strategy_outdated"


def test_validate_realtime_launch_prerequisites_rejects_draft(client, db_session):
    created = _create_simulation(client, "Japan", full_setup=False)

    actor = resolve_current_actor(db_session)
    with pytest.raises(AppError) as exc_info:
        simulation_service.validate_realtime_launch_prerequisites(
            db_session,
            actor,
            created["simulationId"],
        )
    assert exc_info.value.code == "simulation_not_ready_for_launch"
