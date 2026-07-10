# Miro API and Schema Specification

## 1. API Scope

The static prototype in this workspace uses local state, but the production path should expose the following API surface.

## 2. Core API Endpoints

### System

- `GET /api/v1/health`
- `GET /api/v1/ready`

Health response example:

```json
{
  "status": "ok"
}
```

Deployment validation note:

- Post-deploy probes should hit `GET /api/v1/health` for liveness, `GET /api/v1/ready` for production readiness, and `GET /api/v1/auth/session` without a token to confirm the auth boundary still returns `401`.

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

- `GET /api/v1/user-twin?countryKey={countryKey}`
- `POST /api/v1/user-twin/refresh-from-review/{reviewId}`

Review creation refreshes the memory automatically. The explicit refresh endpoint
is idempotent for the same review, so the frontend can safely retry it.

Response example:

```json
{
  "items": [
    {
      "issue_key": "soft_refusal_missed",
      "issueCount": 3,
      "riskLevel": "high",
      "last_context": "Tokyo distributor introduction"
    }
  ]
}
```

### Learning / Preparation

- `GET /api/v1/learning/countries`
- `GET /api/v1/learning/countries/{countryKey}`
- `GET /api/v1/learning/progress/{countryKey}`
- `POST /api/v1/learning/progress/{countryKey}/complete`
- `GET /api/v1/learning/modules`
- `POST /api/v1/learning/modules/{moduleId}/state`

Current implementation note:

- Country-level learning content and country-level progress remain the source of simulation precheck.
- Preparation modules are now a separate additive board surface:
  - published module catalog rows
  - actor-scoped saved / started / completed timestamps
- This phase does not introduce a learning CMS. History records and continue-from-review now live in dedicated History / Simulation endpoints.

Modules list response example:

```json
{
  "recommendedModule": {
    "moduleId": "00000000-0000-4000-8000-000000000051",
    "countryKey": "Japan",
    "title": "Read hesitation before pricing",
    "summary": "Spot trust signals before you introduce price or commitment pressure.",
    "theme": "trust",
    "scene": "first_introduction",
    "status": "new",
    "stateLabel": "New",
    "saved": false,
    "recommended": true,
    "sortOrder": 10
  },
  "snapshotCounts": {
    "open": 1,
    "new": 4,
    "saved": 1
  },
  "items": [
    {
      "moduleId": "00000000-0000-4000-8000-000000000051",
      "countryKey": "Japan",
      "title": "Read hesitation before pricing",
      "summary": "Spot trust signals before you introduce price or commitment pressure.",
      "theme": "trust",
      "scene": "first_introduction",
      "status": "new",
      "stateLabel": "New",
      "saved": false,
      "recommended": true,
      "sortOrder": 10
    }
  ]
}
```

Modules list filters:

- `countryKey`
- `theme`
- `scene`
- `status`
- `tab`
- `query`

Module state mutation request:

```json
{
  "action": "save"
}
```

Module state mutation response example:

```json
{
  "item": {
    "moduleId": "00000000-0000-4000-8000-000000000051",
    "countryKey": "Japan",
    "title": "Read hesitation before pricing",
    "summary": "Spot trust signals before you introduce price or commitment pressure.",
    "theme": "trust",
    "scene": "first_introduction",
    "status": "saved",
    "stateLabel": "Saved",
    "saved": true,
    "recommended": false,
    "sortOrder": 10
  },
  "recommendedModule": {
    "moduleId": "00000000-0000-4000-8000-000000000052",
    "countryKey": "Japan",
    "title": "Keep face-safe pacing",
    "summary": "Slow the exchange and leave room for indirect hesitation to surface.",
    "theme": "pacing",
    "scene": "first_introduction",
    "status": "new",
    "stateLabel": "New",
    "saved": false,
    "recommended": true,
    "sortOrder": 20
  },
  "snapshotCounts": {
    "open": 0,
    "new": 5,
    "saved": 1
  }
}
```

### Simulation

- `POST /api/v1/simulations/precheck`
- `POST /api/v1/simulations`
- `GET /api/v1/simulations/{simulationId}`
- `PATCH /api/v1/simulations/{simulationId}`
- `POST /api/v1/simulations/{simulationId}/files`
- `POST /api/v1/simulations/{simulationId}/strategy`
- `POST /api/v1/simulations/from-review/{reviewId}`

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

- Uploaded files now persist extracted summaries and short excerpts for internal grounding prep.
- The current extraction path supports:
  - direct `text/plain` content
  - simple text extraction from text-based PDFs
  - safe fallback to deterministic summaries when extraction is unavailable
- They are still not parsed through a full document pipeline, chunked, embedded, or retrieved through a vector database.

Simulation files request example:

```json
{
  "files": [
    {
      "fileName": "renewal-notes.txt",
      "contentType": "text/plain",
      "sizeBytes": 104,
      "sourceType": "manual_upload",
      "textContent": "Renewal timing should stay conservative. Confirm the internal owner before discussing pricing."
    },
    {
      "fileName": "renewal-brief.pdf",
      "contentType": "application/pdf",
      "sizeBytes": 58214,
      "sourceType": "manual_upload",
      "fileDataBase64": "<base64-pdf-bytes>"
    }
  ]
}
```

Production runtime note:

- The frontend should call these endpoints through a runtime-configured API base instead of hardcoded localhost origins.
- `POST /api/v1/simulations/from-review/{reviewId}` creates the next simulation from an actor-scoped review snapshot and copies uploaded grounding context when the source review points back to a simulation.

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
- Turn generation now consumes:
  - strategy summary
  - uploaded context summary / excerpts derived from real text when available
  - recent transcript lines
- This scaffold is intended for future provider integration and RAG grounding work without changing the current API contract.

### Review Center

- `GET /reviews`
- `GET /reviews/{id}`

Query params:

- `source=simulation|device`
- `country=Japan`
- `user_id=...`

Current detail response note:

- `GET /api/v1/reviews/{reviewId}` now preserves the existing detail payload and adds an additive `analysis` object for the Review workspace.
- The current `analysis` block is deterministic and rule-derived from the persisted review snapshot:
  - `summary`
  - `metrics`
  - `lines`
  - repeated issue ordering
- It does not claim model-grade scoring or hidden inference beyond the stored review evidence.

Review detail response example:

```json
{
  "reviewId": "review_123",
  "sourceType": "realtime_session",
  "sourceSessionId": "rt_123",
  "status": "ready",
  "countryKey": "Japan",
  "meetingType": "first_introduction",
  "goal": "establish_trust_before_pricing",
  "durationMinutes": 10,
  "voiceStyle": "formal_measured",
  "voiceProfileId": "vp_japan_female_01",
  "setupRevision": 1,
  "strategyForSetupRevision": 1,
  "overallAssessment": "mixed",
  "summary": {
    "headline": "Good momentum with room to sharpen.",
    "coachSummary": "The session showed useful momentum, but pricing pressure arrived too early.",
    "nextStep": "Next time, hold pricing until the counterpart signals enough trust to discuss commercial terms."
  },
  "metrics": {
    "turnCount": 4,
    "alertCount": 2,
    "highSeverityCount": 1,
    "mediumSeverityCount": 1,
    "topIssueKeys": ["premature_pricing_push", "underdeveloped_answer"]
  },
  "analysis": {
    "overallScore": 64,
    "dimensions": [
      {
        "dimensionKey": "goalFit",
        "label": "Goal fit",
        "score": 60,
        "status": "weak",
        "reason": "Make one explicit link between the answer and the stated meeting goal."
      }
    ],
    "trend": [
      {
        "turnIndex": 1,
        "minuteLabel": "00:00",
        "score": 54,
        "issueKeys": ["premature_pricing_push"]
      }
    ],
    "focusItems": [
      {
        "title": "Delay pricing until trust is visible",
        "detail": "Hold commercial pressure until the counterpart signals enough trust to discuss pricing.",
        "dimensionKey": "pacing",
        "relatedIssueKeys": ["premature_pricing_push"]
      }
    ],
    "evidenceMoments": [
      {
        "minuteLabel": "00:00",
        "text": "We should move to pricing today.",
        "relatedIssueKeys": ["premature_pricing_push"]
      }
    ],
    "derivedInsights": {
      "strongest": "grounding",
      "weakest": "pacing",
      "spread": 22
    }
  },
  "lines": [
    {
      "lineIndex": 1,
      "speaker": "user",
      "turnIndex": 1,
      "text": "We should move to pricing today.",
      "alertIssueKeys": ["premature_pricing_push"],
      "createdAt": "2026-04-11T08:01:00Z"
    }
  ],
  "createdAt": "2026-04-11T08:00:00Z",
  "endedAt": "2026-04-11T08:10:00Z"
}
```

### History

- `GET /api/v1/history/records`

History filters:

- `countryKey`
- `type=review|hardware_sync`
- `status`
- `query`

History response example:

```json
{
  "items": [
    {
      "recordId": "review_123",
      "recordType": "review",
      "title": "Good momentum with room to sharpen.",
      "summary": "Good momentum with room to sharpen.",
      "detail": "Uploaded brief stayed relevant and the pacing improved.",
      "countryKey": "Japan",
      "status": "ready",
      "createdAt": "2026-04-11T08:00:00Z",
      "reviewId": "review_123",
      "sourceSessionId": "rt_123",
      "overallAssessment": "mixed",
      "score": 68,
      "canContinue": true,
      "canOpenReview": true,
      "canReplay": true
    },
    {
      "recordId": "sync_123",
      "recordType": "hardware_sync",
      "title": "Demo upload completed",
      "summary": "Demo upload completed",
      "detail": "18 language events uploaded.",
      "countryKey": "Japan",
      "status": "warning",
      "createdAt": "2026-04-11T08:05:00Z",
      "reviewId": "review_123",
      "sourceSessionId": "rt_123",
      "overallAssessment": "mixed",
      "score": 68,
      "canContinue": true,
      "canOpenReview": true,
      "canReplay": false
    }
  ]
}
```

### Hardware Devices

- `GET /api/v1/hardware/devices`
- `POST /api/v1/hardware/devices/{id}/connect`
- `POST /api/v1/hardware/devices/{id}/disconnect`
- `POST /api/v1/hardware/devices/{id}/sync`
- `POST /api/v1/hardware/reviews/{reviewId}/sync`
- `GET /api/v1/hardware/reviews/{reviewId}/packet`
- `GET /api/v1/hardware/devices/{id}/logs`
- `GET /api/v1/hardware/devices/{id}/sync-records`

Hardware is a demo state surface in this capstone. These endpoints should simulate device state and sync history for UI display; they do not imply BLE, USB, firmware, or physical wearable ingestion.

`GET /api/v1/hardware/reviews/{reviewId}/packet` returns a versioned `miro.review.packet.v1` payload and SHA-256 `packetHash`. Review-linked sync stores the same packet in the sync event so a future physical adapter can verify the exact report bytes before transfer.

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
