import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select, text

from app.models.hardware import Device, DeviceSyncEvent
from app.models.review import Review
from app.models.user import User


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_user(db_session, *, user_id: str, email: str) -> User:
    user = User(id=user_id, email=email, status="active")
    db_session.add(user)
    db_session.commit()
    return user


def _seed_device(
    db_session,
    *,
    user_id: str,
    device_name: str = "Miro Pin 01",
    connection_state: str = "disconnected",
    transfer_state: str = "idle",
    firmware_version: str = "1.4.2",
    battery_percent: int = 84,
    updated_at: datetime | None = None,
) -> Device:
    device = Device(
        user_id=user_id,
        device_name=device_name,
        connection_state=connection_state,
        transfer_state=transfer_state,
        firmware_version=firmware_version,
        battery_percent=battery_percent,
    )
    if updated_at is not None:
        device.created_at = updated_at
        device.updated_at = updated_at
    db_session.add(device)
    db_session.commit()
    return device


def _seed_review(db_session, *, user_id: str, device_id: str | None = None) -> Review:
    review = Review(
        user_id=user_id,
        device_id=device_id,
        review_source="device",
        country_key="Japan",
        title_text="Demo hardware review",
        review_status="ready",
    )
    db_session.add(review)
    db_session.commit()
    return review


def _build_authenticated_client(make_client, supabase_jwks_server, *, user_id: str, email: str):
    client = make_client(
        ALLOW_DEMO_ACTOR_FALLBACK="false",
        SUPABASE_URL=supabase_jwks_server["base_url"],
    )
    token = supabase_jwks_server["issue_token"](sub=user_id, email=email)
    return client, token


def _insert_device_log(
    db_session,
    *,
    log_id: str,
    device_id: str,
    title_text: str,
    detail_text: str,
    event_type: str,
    severity: str,
    created_at: datetime,
    review_id: str | None = None,
) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO device_logs (
                id,
                device_id,
                review_id,
                event_type,
                severity,
                title_text,
                detail_text,
                payload_json,
                created_at,
                updated_at
            ) VALUES (
                :id,
                :device_id,
                :review_id,
                :event_type,
                :severity,
                :title_text,
                :detail_text,
                :payload_json,
                :created_at,
                :updated_at
            )
            """
        ),
        {
            "id": log_id,
            "device_id": device_id,
            "review_id": review_id,
            "event_type": event_type,
            "severity": severity,
            "title_text": title_text,
            "detail_text": detail_text,
            "payload_json": json.dumps({"source": "test"}),
            "created_at": created_at,
            "updated_at": created_at,
        },
    )
    db_session.commit()


def test_list_devices_auto_creates_default_demo_device_and_persists(
    make_client,
    supabase_jwks_server,
    db_session,
):
    user_id = str(uuid4())
    client, token = _build_authenticated_client(
        make_client,
        supabase_jwks_server,
        user_id=user_id,
        email="hardware-demo@miro.local",
    )

    first = client.get("/api/v1/hardware/devices", headers=_auth_headers(token))
    second = client.get("/api/v1/hardware/devices", headers=_auth_headers(token))

    assert first.status_code == 200
    payload = first.json()
    assert len(payload) == 1
    assert payload[0]["deviceName"] == "Miro Pin 01"
    assert payload[0]["connected"] is False
    assert payload[0]["connectionState"] == "disconnected"
    assert payload[0]["transferState"] == "idle"
    assert payload[0]["firmwareVersion"] == "1.4.2"
    assert payload[0]["batteryPercent"] == 84
    assert payload[0]["capturedSessions"] == 0
    assert payload[0]["vibrationEvents"] == 0

    assert second.status_code == 200
    assert len(second.json()) == 1
    assert second.json()[0]["deviceId"] == payload[0]["deviceId"]

    device_count = db_session.scalar(
        select(func.count()).select_from(Device).where(Device.user_id == user_id)
    )
    assert device_count == 1


def test_list_devices_returns_only_current_actor_devices_in_stable_order(
    make_client,
    supabase_jwks_server,
    db_session,
):
    user_id = str(uuid4())
    other_user_id = str(uuid4())
    _seed_user(db_session, user_id=user_id, email="owner@miro.local")
    _seed_user(db_session, user_id=other_user_id, email="other@miro.local")

    older = _seed_device(
        db_session,
        user_id=user_id,
        device_name="Miro Pin 01",
        updated_at=datetime(2026, 3, 20, 8, 0, tzinfo=UTC),
    )
    newer = _seed_device(
        db_session,
        user_id=user_id,
        device_name="Miro Pin 02",
        updated_at=datetime(2026, 3, 21, 8, 0, tzinfo=UTC),
    )
    _seed_device(
        db_session,
        user_id=other_user_id,
        device_name="Other Actor Device",
        updated_at=datetime(2026, 3, 22, 8, 0, tzinfo=UTC),
    )

    client, token = _build_authenticated_client(
        make_client,
        supabase_jwks_server,
        user_id=user_id,
        email="owner@miro.local",
    )

    response = client.get("/api/v1/hardware/devices", headers=_auth_headers(token))

    assert response.status_code == 200
    payload = response.json()
    assert [item["deviceId"] for item in payload] == [newer.id, older.id]
    assert {item["deviceName"] for item in payload} == {"Miro Pin 01", "Miro Pin 02"}


def test_hardware_requires_auth_when_demo_fallback_disabled(make_client, supabase_jwks_server):
    client = make_client(
        ALLOW_DEMO_ACTOR_FALLBACK="false",
        SUPABASE_URL=supabase_jwks_server["base_url"],
    )

    response = client.get("/api/v1/hardware/devices")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth_token_required"


def test_connect_device_marks_demo_device_connected_and_writes_log(
    make_client,
    supabase_jwks_server,
    db_session,
):
    user_id = str(uuid4())
    _seed_user(db_session, user_id=user_id, email="connect-owner@miro.local")
    device = _seed_device(db_session, user_id=user_id, connection_state="disconnected")
    client, token = _build_authenticated_client(
        make_client,
        supabase_jwks_server,
        user_id=user_id,
        email="connect-owner@miro.local",
    )

    response = client.post(
        f"/api/v1/hardware/devices/{device.id}/connect",
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["deviceId"] == device.id
    assert payload["connected"] is True
    assert payload["connectionState"] == "connected"

    db_session.expire_all()
    refreshed = db_session.scalar(select(Device).where(Device.id == device.id))
    assert refreshed is not None
    assert refreshed.connection_state == "connected"

    logs = client.get(
        f"/api/v1/hardware/devices/{device.id}/logs",
        headers=_auth_headers(token),
    )
    assert logs.status_code == 200
    assert logs.json()[0]["eventType"] == "connection"


def test_disconnect_device_marks_demo_device_disconnected_and_resets_transfer_state(
    make_client,
    supabase_jwks_server,
    db_session,
):
    user_id = str(uuid4())
    _seed_user(db_session, user_id=user_id, email="disconnect-owner@miro.local")
    device = _seed_device(
        db_session,
        user_id=user_id,
        connection_state="connected",
        transfer_state="healthy",
    )
    client, token = _build_authenticated_client(
        make_client,
        supabase_jwks_server,
        user_id=user_id,
        email="disconnect-owner@miro.local",
    )

    response = client.post(
        f"/api/v1/hardware/devices/{device.id}/disconnect",
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["connected"] is False
    assert payload["connectionState"] == "disconnected"
    assert payload["transferState"] == "idle"

    db_session.expire_all()
    refreshed = db_session.scalar(select(Device).where(Device.id == device.id))
    assert refreshed is not None
    assert refreshed.connection_state == "disconnected"
    assert refreshed.transfer_state == "idle"


def test_connect_and_disconnect_return_not_found_for_unknown_device(
    make_client,
    supabase_jwks_server,
):
    user_id = str(uuid4())
    client, token = _build_authenticated_client(
        make_client,
        supabase_jwks_server,
        user_id=user_id,
        email="missing-device@miro.local",
    )

    for action in ("connect", "disconnect"):
        response = client.post(
            f"/api/v1/hardware/devices/{uuid4()}/{action}",
            headers=_auth_headers(token),
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "hardware_device_not_found"


def test_sync_updates_demo_device_and_creates_logs_and_sync_record(
    make_client,
    supabase_jwks_server,
    db_session,
):
    user_id = str(uuid4())
    _seed_user(db_session, user_id=user_id, email="sync-owner@miro.local")
    device = _seed_device(
        db_session,
        user_id=user_id,
        connection_state="disconnected",
        firmware_version="1.3.8",
        battery_percent=40,
    )
    review = _seed_review(db_session, user_id=user_id, device_id=device.id)
    client, token = _build_authenticated_client(
        make_client,
        supabase_jwks_server,
        user_id=user_id,
        email="sync-owner@miro.local",
    )

    response = client.post(
        f"/api/v1/hardware/devices/{device.id}/sync",
        headers=_auth_headers(token),
        json={
            "syncKind": "upload",
            "healthStatus": "healthy",
            "summaryText": "Demo sync after rehearsal",
            "detailText": "18 language events uploaded.",
            "firmwareVersion": "1.4.2",
            "batteryPercent": 84,
            "reviewId": review.id,
            "vibrationEventCount": 2,
            "payload": {"mode": "upload", "source": "hardware-demo"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["device"]["deviceId"] == device.id
    assert payload["device"]["connected"] is True
    assert payload["device"]["connectionState"] == "connected"
    assert payload["device"]["transferState"] == "healthy"
    assert payload["device"]["firmwareVersion"] == "1.4.2"
    assert payload["device"]["batteryPercent"] == 84
    assert payload["device"]["capturedSessions"] == 1
    assert payload["device"]["vibrationEvents"] == 2
    assert payload["syncRecord"]["syncKind"] == "upload"
    assert payload["syncRecord"]["status"] == "healthy"
    assert payload["log"]["eventType"] == "sync"

    db_session.expire_all()
    refreshed = db_session.scalar(select(Device).where(Device.id == device.id))
    assert refreshed is not None
    assert refreshed.connection_state == "connected"
    assert refreshed.transfer_state == "healthy"
    assert refreshed.firmware_version == "1.4.2"
    assert refreshed.battery_percent == 84
    assert refreshed.last_sync_at is not None

    logs = client.get(
        f"/api/v1/hardware/devices/{device.id}/logs",
        headers=_auth_headers(token),
    )
    assert logs.status_code == 200
    assert len(logs.json()) == 3
    assert {entry["eventType"] for entry in logs.json()} == {"sync", "vibration"}

    sync_records = client.get(
        f"/api/v1/hardware/devices/{device.id}/sync-records",
        headers=_auth_headers(token),
    )
    assert sync_records.status_code == 200
    assert len(sync_records.json()) == 1
    assert sync_records.json()[0]["syncRecordId"] == payload["syncRecord"]["syncRecordId"]


def test_logs_endpoint_returns_entries_in_stable_desc_order(
    make_client,
    supabase_jwks_server,
    db_session,
):
    user_id = str(uuid4())
    _seed_user(db_session, user_id=user_id, email="logs-owner@miro.local")
    device = _seed_device(db_session, user_id=user_id)
    review = _seed_review(db_session, user_id=user_id, device_id=device.id)

    older_time = datetime(2026, 3, 20, 8, 0, tzinfo=UTC)
    newer_time = older_time + timedelta(hours=1)
    older_id = str(uuid4())
    newer_id = str(uuid4())
    _insert_device_log(
        db_session,
        log_id=older_id,
        device_id=device.id,
        review_id=review.id,
        event_type="sync",
        severity="info",
        title_text="Older sync event",
        detail_text="Older detail",
        created_at=older_time,
    )
    _insert_device_log(
        db_session,
        log_id=newer_id,
        device_id=device.id,
        event_type="connection",
        severity="info",
        title_text="Newer connection event",
        detail_text="Newer detail",
        created_at=newer_time,
    )

    client, token = _build_authenticated_client(
        make_client,
        supabase_jwks_server,
        user_id=user_id,
        email="logs-owner@miro.local",
    )

    response = client.get(
        f"/api/v1/hardware/devices/{device.id}/logs",
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["logId"] for item in payload] == [newer_id, older_id]
    assert payload[1]["reviewId"] == review.id


def test_sync_records_endpoint_returns_entries_in_stable_desc_order(
    make_client,
    supabase_jwks_server,
    db_session,
):
    user_id = str(uuid4())
    _seed_user(db_session, user_id=user_id, email="records-owner@miro.local")
    device = _seed_device(db_session, user_id=user_id)

    older = DeviceSyncEvent(
        device_id=device.id,
        health_status="warning",
        summary_text="Older sync",
        payload_json={"syncKind": "download", "detailText": "Older detail"},
    )
    newer = DeviceSyncEvent(
        device_id=device.id,
        health_status="healthy",
        summary_text="Newer sync",
        payload_json={"syncKind": "upload", "detailText": "Newer detail"},
    )
    older.created_at = datetime(2026, 3, 20, 8, 0, tzinfo=UTC)
    older.updated_at = older.created_at
    newer.created_at = datetime(2026, 3, 20, 9, 0, tzinfo=UTC)
    newer.updated_at = newer.created_at
    db_session.add_all([older, newer])
    db_session.commit()

    client, token = _build_authenticated_client(
        make_client,
        supabase_jwks_server,
        user_id=user_id,
        email="records-owner@miro.local",
    )

    response = client.get(
        f"/api/v1/hardware/devices/{device.id}/sync-records",
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["syncRecordId"] for item in payload] == [newer.id, older.id]
    assert payload[0]["syncKind"] == "upload"
    assert payload[1]["status"] == "warning"


def test_cross_actor_device_access_returns_not_found(
    make_client,
    supabase_jwks_server,
    db_session,
):
    owner_id = str(uuid4())
    viewer_id = str(uuid4())
    _seed_user(db_session, user_id=owner_id, email="owner-hidden@miro.local")
    _seed_user(db_session, user_id=viewer_id, email="viewer-hidden@miro.local")
    device = _seed_device(db_session, user_id=owner_id)
    client, token = _build_authenticated_client(
        make_client,
        supabase_jwks_server,
        user_id=viewer_id,
        email="viewer-hidden@miro.local",
    )

    for method, url in (
        ("get", f"/api/v1/hardware/devices/{device.id}/logs"),
        ("get", f"/api/v1/hardware/devices/{device.id}/sync-records"),
        ("post", f"/api/v1/hardware/devices/{device.id}/connect"),
        ("post", f"/api/v1/hardware/devices/{device.id}/disconnect"),
        ("post", f"/api/v1/hardware/devices/{device.id}/sync"),
    ):
        kwargs = {"headers": _auth_headers(token)}
        if url.endswith("/sync"):
            kwargs["json"] = {"syncKind": "upload", "healthStatus": "healthy"}
        response = getattr(client, method)(url, **kwargs)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "hardware_device_not_found"


def test_sync_with_other_actors_review_returns_not_found(
    make_client,
    supabase_jwks_server,
    db_session,
):
    user_id = str(uuid4())
    other_user_id = str(uuid4())
    _seed_user(db_session, user_id=user_id, email="review-owner@miro.local")
    _seed_user(db_session, user_id=other_user_id, email="review-other@miro.local")
    device = _seed_device(db_session, user_id=user_id)
    other_review = _seed_review(db_session, user_id=other_user_id)
    client, token = _build_authenticated_client(
        make_client,
        supabase_jwks_server,
        user_id=user_id,
        email="review-owner@miro.local",
    )

    response = client.post(
        f"/api/v1/hardware/devices/{device.id}/sync",
        headers=_auth_headers(token),
        json={
            "syncKind": "sync_complete",
            "healthStatus": "healthy",
            "reviewId": other_review.id,
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "hardware_review_not_found"


def test_refreshing_after_sync_returns_persisted_demo_device_state(
    make_client,
    supabase_jwks_server,
    db_session,
):
    user_id = str(uuid4())
    _seed_user(db_session, user_id=user_id, email="refresh-owner@miro.local")
    device = _seed_device(db_session, user_id=user_id, battery_percent=51, firmware_version="1.3.8")
    client, token = _build_authenticated_client(
        make_client,
        supabase_jwks_server,
        user_id=user_id,
        email="refresh-owner@miro.local",
    )

    sync_response = client.post(
        f"/api/v1/hardware/devices/{device.id}/sync",
        headers=_auth_headers(token),
        json={
            "syncKind": "download",
            "healthStatus": "warning",
            "firmwareVersion": "1.4.2",
            "batteryPercent": 73,
            "summaryText": "Demo download complete",
        },
    )
    assert sync_response.status_code == 200

    first = client.get("/api/v1/hardware/devices", headers=_auth_headers(token))
    second = client.get("/api/v1/hardware/devices", headers=_auth_headers(token))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert first.json()[0]["deviceId"] == device.id
    assert first.json()[0]["transferState"] == "warning"
    assert first.json()[0]["firmwareVersion"] == "1.4.2"
    assert first.json()[0]["batteryPercent"] == 73
