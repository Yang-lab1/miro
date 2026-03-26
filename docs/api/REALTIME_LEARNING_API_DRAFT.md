# Miro Realtime + Learning API Draft

This draft freezes the new product direction:

1. `Learning` becomes a first-class module between `Home` and `Live Simulation`
2. `Live Simulation` becomes a realtime voice conversation product, not just a text evaluator
3. Starting a simulation requires a learning precheck for the selected country

## 1. Frozen Product Decisions

### 1.1 Module order

- Home
- Learning
- Live Simulation
- Review
- Hardware
- Pricing
- Settings

### 1.2 Learning gate rule

When the user clicks `Start simulation`, the app checks whether the selected country's learning content has been reviewed recently enough.

If not ready, show a modal with:

- `Start simulation anyway`
- `Go to learning`

### 1.3 Realtime route

The target interaction is voice-first and near seamless, similar to a natural spoken conversation.

That means the backend must support:

- streaming audio input
- turn detection
- streaming transcript updates
- realtime alert emission
- partner text response
- partner voice response
- end-of-session review generation

## 2. Recommended Transport Split

Use two planes:

### Control plane: REST

Used for:

- auth
- learning content
- learning progress
- simulation precheck
- session creation
- session completion
- review retrieval

### Realtime plane: WebRTC preferred

Used for:

- microphone audio upstream
- assistant voice downstream
- low-latency session events

Why:

- If the goal is seamless spoken interaction, WebRTC is the correct target.
- WebSocket can work for text and even audio chunks, but it is a weaker fit for production-grade voice conversation.

Recommended fallback:

- WebRTC for audio sessions
- WebSocket for local development, text-only fallback, and diagnostics

## 3. New Learning Module

## 3.1 User-facing purpose

Before rehearsal, the user should be able to study country-specific:

- business etiquette
- politeness expectations
- taboo language
- directness preferences
- opening style
- pacing expectations
- example good phrases
- example risky phrases
- meeting checklist

## 3.2 Core entities

### CountryLearningContent

```json
{
  "countryCode": "JP",
  "countryName": {
    "en": "Japan",
    "zh": "日本"
  },
  "version": "2026.03",
  "sections": [
    {
      "id": "etiquette",
      "title": {
        "en": "Business etiquette",
        "zh": "商务礼仪"
      },
      "items": [
        {
          "type": "bullet",
          "content": {
            "en": "Treat hesitation as a signal, not resistance.",
            "zh": "把犹豫视为信号，而不是阻力。"
          }
        }
      ]
    }
  ],
  "checklist": [
    {
      "id": "avoid-price-push",
      "label": {
        "en": "Avoid pushing price before trust is established.",
        "zh": "在建立信任前避免推进价格。"
      }
    }
  ]
}
```

### UserLearningProgress

```json
{
  "userId": "usr_123",
  "countryCode": "JP",
  "contentVersion": "2026.03",
  "status": "completed",
  "completedAt": "2026-03-15T10:00:00Z",
  "expiresAt": "2026-04-14T10:00:00Z"
}
```

## 3.3 Learning APIs

### `GET /api/learning/countries`

Purpose:

- get list of countries with learning coverage

Response:

```json
[
  {
    "countryCode": "JP",
    "countryName": {
      "en": "Japan",
      "zh": "日本"
    },
    "hasContent": true
  }
]
```

### `GET /api/learning/countries/{countryCode}`

Purpose:

- fetch country learning content

### `GET /api/learning/progress/{countryCode}`

Purpose:

- fetch current user's progress for one country

Response:

```json
{
  "countryCode": "JP",
  "status": "completed",
  "contentVersion": "2026.03",
  "completedAt": "2026-03-15T10:00:00Z",
  "expiresAt": "2026-04-14T10:00:00Z",
  "isUpToDate": true
}
```

### `POST /api/learning/progress/{countryCode}/complete`

Purpose:

- mark country learning as completed

Request:

```json
{
  "contentVersion": "2026.03"
}
```

### `POST /api/simulations/precheck`

Purpose:

- check if user is ready to start simulation for the selected country

Request:

```json
{
  "countryCode": "JP"
}
```

Response:

```json
{
  "ready": false,
  "countryCode": "JP",
  "reason": "learning_required",
  "learning": {
    "status": "missing",
    "contentVersion": "2026.03"
  },
  "recommendedAction": "go_to_learning"
}
```

Possible `reason` values:

- `ready`
- `learning_required`
- `learning_outdated`
- `country_not_supported`

## 4. Live Simulation Configuration

The setup phase should now include:

- `countryCode`
- `meetingType`
- `goal`
- `durationMinutes`
- `voiceStyle`
- `voiceProfile`
- `constraint`
- `files`

### VoiceProfile

Do not model this as just `male/female`. Use a concrete profile object.

```json
{
  "voiceProfile": {
    "gender": "female",
    "locale": "ja-JP",
    "voiceId": "ja_female_01"
  }
}
```

## 5. Realtime Session Model

## 5.1 Core entities

### RealtimeSession

```json
{
  "sessionId": "sim_123",
  "userId": "usr_123",
  "countryCode": "JP",
  "meetingType": "first_introduction",
  "goal": "establish_trust_before_pricing",
  "durationMinutes": 10,
  "voiceStyle": "formal_measured",
  "voiceProfile": {
    "gender": "female",
    "locale": "ja-JP",
    "voiceId": "ja_female_01"
  },
  "status": "active",
  "transport": "webrtc"
}
```

### TranscriptTurn

```json
{
  "turnId": "turn_123",
  "speaker": "user",
  "inputMode": "speech",
  "sourceText": "We can lock the final price today if you move quickly.",
  "normalizedText": "We can lock the final price today if you move quickly.",
  "language": "en",
  "startedAt": "2026-03-15T10:00:00Z",
  "endedAt": "2026-03-15T10:00:04Z"
}
```

### SessionAlert

```json
{
  "alertId": "alt_123",
  "severity": "high",
  "issueKey": "price_pressure",
  "title": {
    "en": "Price pressure too early",
    "zh": "过早施加价格压力"
  },
  "detail": {
    "en": "You pushed for commitment before trust was established.",
    "zh": "你在信任尚未建立前推进了承诺。"
  },
  "turnId": "turn_123",
  "createdAt": "2026-03-15T10:00:05Z"
}
```

### AssistantTurn

```json
{
  "turnId": "turn_124",
  "speaker": "partner",
  "text": {
    "local": "少し社内で相談したいと思います。",
    "en": "I would like to consult internally first.",
    "zh": "我想先在内部再讨论一下。"
  },
  "audio": {
    "voiceId": "ja_female_01",
    "mimeType": "audio/ogg",
    "url": "https://example.com/audio/turn_124.ogg"
  }
}
```

## 5.2 Realtime session lifecycle

### Step 1: create session

`POST /api/realtime/sessions`

Request:

```json
{
  "countryCode": "JP",
  "meetingType": "first_introduction",
  "goal": "establish_trust_before_pricing",
  "durationMinutes": 10,
  "voiceStyle": "formal_measured",
  "voiceProfile": {
    "gender": "female",
    "locale": "ja-JP",
    "voiceId": "ja_female_01"
  },
  "constraint": "The client is traditional and risk-sensitive.",
  "files": [
    {
      "fileId": "file_123"
    }
  ]
}
```

Response:

```json
{
  "sessionId": "sim_123",
  "transport": "webrtc",
  "connection": {
    "clientSecret": "rt_secret_123",
    "expiresAt": "2026-03-15T10:20:00Z"
  },
  "seedPartnerTurn": {
    "speaker": "partner",
    "text": {
      "local": "本日はお時間をいただきありがとうございます。",
      "en": "Thank you for making time today.",
      "zh": "感谢今天拨冗会面。"
    }
  }
}
```

### Step 2: connect realtime transport

Preferred:

- client uses returned realtime credential to establish WebRTC session

### Step 3: exchange session events

Client-to-server events:

- `session.started`
- `user.audio.buffer.append`
- `user.audio.turn.commit`
- `user.text.turn.submit`
- `assistant.interrupt`
- `session.end`

Server-to-client events:

- `session.ready`
- `transcript.partial`
- `transcript.final`
- `alert.created`
- `metrics.updated`
- `assistant.response.text`
- `assistant.response.audio`
- `assistant.response.done`
- `session.error`

## 5.3 Event examples

### `transcript.partial`

```json
{
  "type": "transcript.partial",
  "sessionId": "sim_123",
  "turnId": "turn_123",
  "speaker": "user",
  "text": "We can lock the final..."
}
```

### `transcript.final`

```json
{
  "type": "transcript.final",
  "sessionId": "sim_123",
  "turnId": "turn_123",
  "speaker": "user",
  "text": "We can lock the final price today if you move quickly."
}
```

### `alert.created`

```json
{
  "type": "alert.created",
  "sessionId": "sim_123",
  "turnId": "turn_123",
  "alert": {
    "severity": "high",
    "issueKey": "price_pressure",
    "title": "Price pressure too early"
  }
}
```

### `assistant.response.text`

```json
{
  "type": "assistant.response.text",
  "sessionId": "sim_123",
  "turnId": "turn_124",
  "speaker": "partner",
  "text": {
    "local": "少し社内で相談したいと思います。",
    "en": "I would like to consult internally first.",
    "zh": "我想先在内部再讨论一下。"
  }
}
```

### `assistant.response.audio`

```json
{
  "type": "assistant.response.audio",
  "sessionId": "sim_123",
  "turnId": "turn_124",
  "voiceId": "ja_female_01",
  "audioChunk": "base64_or_transport_specific_payload"
}
```

## 6. Session Completion

### `POST /api/realtime/sessions/{sessionId}/complete`

Purpose:

- finalize session
- generate review
- update user twin memory

Response:

```json
{
  "sessionId": "sim_123",
  "reviewId": "review_987",
  "summary": {
    "score": 72,
    "repeatedIssues": ["soft_refusal_missed", "price_pressure"]
  }
}
```

## 7. Review APIs

These remain close to the previous draft.

### `GET /api/reviews`

Supports:

- `source=all|simulation|device`

### `GET /api/reviews/{reviewId}`

Should return:

- summary
- module scores
- repeated issues
- line-by-line advice
- transcript turns
- source metadata

## 8. Implementation Phasing

## Phase 1: viable realtime conversation

Target:

- realtime session creation
- streaming speech input
- final transcript
- alert emission
- partner text response
- partner audio response
- end session review

This is already enough to feel like a real spoken rehearsal product.

## Phase 2: seamless conversation quality

Add:

- faster turn detection
- partial transcript stabilization
- interruption / barge-in
- assistant speech cancellation
- better latency control

If the product goal is truly "ChatGPT voice style seamlessness", Phase 2 is required.

## 9. Immediate Contract Decisions Still Needed

Before backend implementation starts, these must be frozen:

1. country code format: `JP` or `Japan`
2. canonical enums for meeting type and goal
3. voice profile catalog shape
4. learning expiry rule: first-time only, 30-day expiry, or content-version-based
5. whether `Start simulation anyway` is allowed for all orgs
6. whether realtime transport is WebRTC-only or WebRTC + WebSocket fallback
7. whether partner audio is streamed chunked or returned as whole-turn audio

## 10. Recommended Next Step

Turn this draft into a strict backend contract document for:

1. learning APIs
2. simulation precheck
3. realtime session creation
4. realtime event schema
5. session completion
6. review retrieval
