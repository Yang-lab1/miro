# Miro API and Schema Specification

## 1. API Scope

The static prototype in this workspace uses local state, but the production path should expose the following API surface.

## 2. Core API Endpoints

### System

- `GET /api/v1/health`

Health response example:

```json
{
  "status": "ok"
}
```

Deployment validation note:

- Post-deploy probes should hit `GET /api/v1/health` for backend readiness and `GET /api/v1/auth/session` without a token to confirm the auth boundary still returns `401`.

### Auth

- `GET /api/v1/auth/session`
- `POST /api/v1/auth/register` returns `501 auth_managed_by_supabase`
- `POST /api/v1/auth/login` returns `501 auth_managed_by_supabase`
- `POST /api/v1/auth/logout` returns `501 auth_managed_by_supabase`

Request example:

```json
Authorization: Bearer <supabase_access_token>
```

Response example:

```json
{
  "user": {
    "id": "usr_123",
    "email": "alex@northriver.com",
    "fullName": "Alex Morgan",
    "companyName": "North River Commerce",
    "roleTitle": "Director, Global Partnerships",
    "preferredLanguage": "en",
    "status": "active"
  },
  "membership": {
    "organizationId": "org_123",
    "roleKey": "member",
    "membershipStatus": "active"
  },
  "organization": {
    "id": "org_123",
    "name": "North River Commerce",
    "countryKey": "Japan"
  },
  "auth": {
    "source": "supabase",
    "subject": "usr_123",
    "expiresAt": "2026-04-12T09:00:00Z",
    "role": "authenticated"
  }
}
```

### User Settings

- `GET /me/settings`
- `PATCH /me/settings`

Request example:

```json
{
  "language": "zh",
  "notification_mode": "live_only"
}
```

### User Twin Memory

- `GET /user-twin`
- `POST /user-twin/refresh-from-review/{reviewId}`

Response example:

```json
{
  "items": [
    {
      "issue_key": "soft_refusal_missed",
      "count": 3,
      "risk": "HIGH",
      "last_context": "Tokyo distributor introduction"
    }
  ]
}
```

### Simulation

- `POST /simulations`
- `POST /simulations/{id}/strategy-preview`
- `POST /simulations/{id}/evaluate-turn`
- `POST /simulations/{id}/complete`

Create simulation request:

```json
{
  "country": "Japan",
  "meeting_type": "First Introduction",
  "goal": "Establish trust before pricing",
  "duration_minutes": 10,
  "voice_style": "Formal / measured",
  "constraint": "The client is traditional and risk-sensitive. Keep language conservative."
}
```

Evaluate turn request:

```json
{
  "draft_text": "We need your final price today and this is our best offer."
}
```

Evaluate turn response:

```json
{
  "issues": ["price_pressure", "soft_refusal_missed"],
  "metrics": {
    "wording": "Risky",
    "pauses": "Balanced",
    "repetition": "Low",
    "taboo": "Clear",
    "intensity": "High",
    "metaphor": "Concrete"
  },
  "partner_response": {
    "local": "慎重に考えさせていただければと思います。",
    "english": "We would appreciate time to consider this carefully."
  }
}
```

Current implementation note:

- Uploaded files are still metadata-only at this stage. They are available for strategy generation and internal grounding prep, but they are not yet parsed, chunked, embedded, or retrieved through a vector database.

Production runtime note:

- The frontend should call these endpoints through a runtime-configured API base instead of hardcoded localhost origins.

### Realtime Live Sessions

- `POST /api/v1/realtime/sessions`
- `GET /api/v1/realtime/sessions/{sessionId}`
- `GET /api/v1/realtime/sessions/{sessionId}/summary`
- `POST /api/v1/realtime/sessions/{sessionId}/start`
- `POST /api/v1/realtime/sessions/{sessionId}/end`
- `POST /api/v1/realtime/sessions/{sessionId}/sync`
- `POST /api/v1/realtime/sessions/{sessionId}/turns/respond`
- `GET /api/v1/realtime/sessions/{sessionId}/turns`
- `GET /api/v1/realtime/sessions/{sessionId}/alerts`

Current implementation note:

- The public API is stable, but the backend now keeps separate internal boundaries for:
  - session orchestration
  - uploaded context grounding prep
  - turn generation
  - alert extraction
- The default turn generation and alert extraction paths remain demo-safe and rule-based.
- This scaffold is intended for future provider integration and RAG grounding work without changing the current API contract.

### Review Center

- `GET /reviews`
- `GET /reviews/{id}`

Query params:

- `source=simulation|device`
- `country=Japan`
- `user_id=...`

### Hardware Devices

- `GET /api/v1/hardware/devices`
- `POST /api/v1/hardware/devices/{id}/connect`
- `POST /api/v1/hardware/devices/{id}/disconnect`
- `POST /api/v1/hardware/devices/{id}/sync`
- `GET /api/v1/hardware/devices/{id}/logs`
- `GET /api/v1/hardware/devices/{id}/sync-records`

Hardware is a demo state surface in this capstone. These endpoints should simulate device state and sync history for UI display; they do not imply BLE, USB, firmware, or physical wearable ingestion.

On first `GET /api/v1/hardware/devices`, the backend may auto-create one default demo device for the signed-in user if none exists yet. This is demo convenience only, not a provisioning flow.

List devices response example:

```json
[
  {
    "deviceId": "dev_123",
    "deviceName": "Miro Pin 01",
    "connected": false,
    "connectionState": "disconnected",
    "transferState": "idle",
    "firmwareVersion": "1.4.2",
    "versionPath": null,
    "batteryPercent": 84,
    "lastSyncAt": null,
    "capturedSessions": 0,
    "vibrationEvents": 0
  }
]
```

Device sync request:

```json
{
  "syncKind": "upload",
  "firmwareVersion": "1.4.2",
  "healthStatus": "healthy",
  "summaryText": "Demo sync after rehearsal",
  "detailText": "18 language events uploaded.",
  "vibrationEventCount": 2,
  "payload": {
    "mode": "upload",
    "source": "hardware-demo"
  }
}
```

Logs response example:

```json
[
  {
    "logId": "log_123",
    "eventType": "sync",
    "severity": "info",
    "title": "Demo sync after rehearsal",
    "detail": "18 language events uploaded.",
    "reviewId": "review_123",
    "createdAt": "2026-03-24T12:00:00Z"
  }
]
```

### Billing

Billing remains a demo state layer in this capstone. It supports plan selection and credit top-up UI states, but it does not connect to a real payment provider.

- `GET /api/v1/billing/plans`
- `GET /api/v1/billing/summary`
- `POST /api/v1/billing/select-plan`
- `POST /api/v1/billing/top-up`

Billing summary response example:

```json
{
  "account": {
    "currentPlanKey": "plus",
    "creditBalance": 1500,
    "renewalAt": "2026-04-25T09:00:00Z",
    "currencyCode": "USD"
  },
  "currentPlan": {
    "planId": "plan_123",
    "planKey": "plus",
    "displayName": "Plus",
    "billingCycle": "monthly",
    "currencyCode": "USD",
    "amountValue": 20.0,
    "isCurrent": true
  },
  "allowedTopUpAmounts": [500, 1500, 3000]
}
```

Select plan request:

```json
{
  "planKey": "pro"
}
```

Top-up request:

```json
{
  "amount": 1500
}
```

Top-up response example:

```json
{
  "summary": {
    "account": {
      "currentPlanKey": "plus",
      "creditBalance": 3000,
      "renewalAt": "2026-04-25T09:00:00Z",
      "currencyCode": "USD"
    },
    "currentPlan": {
      "planId": "plan_123",
      "planKey": "plus",
      "displayName": "Plus",
      "billingCycle": "monthly",
      "currencyCode": "USD",
      "amountValue": 20.0,
      "isCurrent": true
    },
    "allowedTopUpAmounts": [500, 1500, 3000]
  },
  "payment": {
    "paymentId": "pay_123",
    "eventType": "top_up",
    "amountValue": 1500,
    "currencyCode": "CREDIT",
    "paymentStatus": "demo_completed",
    "createdAt": "2026-03-26T09:00:00Z"
  }
}
```

## 3. Primary Schema

### users

- `id`
- `email`
- `name`
- `company`
- `role`
- `created_at`

### user_settings

- `user_id`
- `language`
- `notification_mode`
- `theme`

### user_twin_memory

- `id`
- `user_id`
- `issue_key`
- `count`
- `risk_level`
- `last_country`
- `last_context`
- `last_seen_at`

### simulations

- `id`
- `user_id`
- `country`
- `meeting_type`
- `goal`
- `duration_minutes`
- `voice_style`
- `constraint_text`
- `status`
- `created_at`

### simulation_turns

- `id`
- `simulation_id`
- `speaker`
- `source_text`
- `translated_text`
- `issue_key`
- `created_at`

### reviews

- `id`
- `user_id`
- `source`
- `country`
- `title`
- `score_total`
- `score_trust`
- `score_pragmatic`
- `score_etiquette`
- `score_pressure`
- `summary`
- `created_at`

### review_lines

- `id`
- `review_id`
- `speaker`
- `source_text`
- `translated_text`
- `issue_key`
- `advice_text`

### devices

- `id`
- `user_id`
- `device_name`
- `firmware_version`
- `connection_state`
- `transfer_state`
- `battery_percent`
- `last_sync_at`

### device_sync_events

- `id`
- `device_id`
- `review_id`
- `health_status`
- `summary_text`
- `payload_json`
- `created_at`

### device_logs

- `id`
- `device_id`
- `review_id`
- `event_type`
- `severity`
- `title_text`
- `detail_text`
- `payload_json`
- `created_at`

### payments

- `id`
- `user_id`
- `plan_id`
- `event_type`
- `amount_value`
- `currency_code`
- `payment_status`
- `external_reference`
- `created_at`

### billing_accounts

- `id`
- `user_id`
- `current_plan_id`
- `credit_balance`
- `renewal_at`
- `currency_code`
- `created_at`

## 4. Issue Key Canonical Set

- `soft_refusal_missed`
- `price_pressure`
- `repetition_loop`
- `taboo_wording`
- `pause_control`
- `metaphor_risk`
- `intensity_spike`

## 5. Notes

- Billing exists as a backend module, but it is currently a demo billing state layer rather than a real payment system.
- Review Center merges device and simulation records by design.
- Production APIs should preserve the narrow capstone scope: language signals only.
