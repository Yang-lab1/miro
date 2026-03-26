# Miro Flow, State, and API Map

This document turns the current prototype UI into an implementation map for parallel frontend and backend work.

## 1. How to Use the UI to Reverse-Engineer Product Scope

Do not start from abstract architecture first. Start from each page and ask:

1. Why does the user come to this page?
2. What can the user do here?
3. What page states must exist?
4. What data is shown on the page?
5. What happens after each action?

That gives you:

- page purpose
- user actions
- UI states
- frontend state shape
- backend API contract

## 2. Product Modules

The current product should be treated as five parallel modules:

1. Auth
2. Simulation
3. Hardware Sync
4. Review
5. Billing / Pricing

`Home` and `Settings` are not backend-heavy modules. They mostly aggregate data from the five modules above.

## 3. Page Map

| Page | User Goal | Main Actions | Core UI States | Required Data | Backend Owner |
|---|---|---|---|---|---|
| Home | Understand product and jump into work | Log in, start simulation, open review | signed out, signed in, summary-loaded | user summary, CQ score, repeated issues, testimonials, counts | Auth, User Twin, Review |
| Live Simulation / Setup | Configure one rehearsal | choose country, meeting type, goal, duration, upload files, generate strategy, start session | idle, dirty, generating strategy, ready to start, upload pending | country package, user twin memory, uploaded files, current setup | Simulation |
| Live Simulation / Session | Run one rehearsal and get language feedback | type response, evaluate, toggle drawer, end session | session-started, evaluating, transcript-active, alerts-active, ended | transcript, alerts, partner response, live metrics, countdown | Simulation |
| Hardware Devices | Explore a demo hardware surface and simulated sync history | connect, disconnect, view status, trigger demo sync, open related review | disconnected, connected, syncing, success, failed | device status, firmware, battery, transfer health, sync records, demo event history | Hardware Demo State |
| Review Center | Inspect results over time | filter by source, open a review, inspect lines | loading, list empty, list loaded, filtered empty, review selected | review list, summary, repeated issues, line details, source type | Review |
| Pricing | Pick plan and top up credits | select plan, top up | current plan, selected plan, top-up in progress, top-up success, top-up failed | plan catalog, balance, current subscription, credit packages | Billing |
| Settings | Manage profile and language | change language, view account summary, log out | read-only summary, updating language, logged out | profile, org, plan, language preference | Auth, Billing |

## 4. End-to-End Flows

### 4.1 Auth Flow

Current prototype entry points:

- nav register / login
- protected route access
- log out

Flow:

1. User clicks `Register` or `Log In`.
2. Frontend opens the Supabase-managed auth flow.
3. Supabase returns an access token to the frontend.
4. Frontend calls `GET /api/v1/auth/session` with `Authorization: Bearer <access_token>`.
5. Backend verifies the Supabase JWT, resolves the local business user, and returns session + user profile + org context.
6. Frontend stores auth state and retries any pending protected route.

Must-have UI states:

- modal closed
- modal open
- submitting
- auth success
- auth failed
- session expired

Suggested API surface:

- `GET /api/v1/auth/session`
- `POST /api/v1/auth/register` (compatibility placeholder; auth is managed by Supabase)
- `POST /api/v1/auth/login` (compatibility placeholder; auth is managed by Supabase)
- `POST /api/v1/auth/logout` (compatibility placeholder; auth is managed by Supabase)

Response shape to freeze early:

```json
{
  "user": {
    "id": "usr_123",
    "name": "Alex Morgan",
    "email": "alex@northriver.com",
    "role": "Director, Global Partnerships",
    "company": "North River Commerce",
    "language": "en"
  },
  "organization": {
    "id": "org_123",
    "name": "North River Commerce"
  },
  "auth": {
    "source": "supabase",
    "subject": "usr_123",
    "expiresAt": "2026-04-12T09:00:00Z",
    "role": "authenticated"
  }
}
```

### 4.2 Simulation Flow

This is the main business flow.

#### Setup stage

User actions:

- select country
- edit meeting type
- edit goal
- edit duration
- edit voice style
- add free-text constraints
- upload files
- generate strategy
- start session

UI states:

- setup idle
- setup dirty
- file upload pending
- strategy generating
- strategy ready
- start blocked

Suggested APIs:

- `GET /api/simulation/packages/countries`
- `POST /api/simulations`
- `POST /api/simulations/{simulationId}/files`
- `POST /api/simulations/{simulationId}/strategy`

#### Session stage

User actions:

- type practice response
- evaluate language
- inspect transcript
- inspect alerts
- collapse / expand drawer
- end session

UI states:

- session created
- first partner turn seeded
- evaluating
- transcript updated
- alerts updated
- session ended

Suggested APIs:

- `POST /api/simulations/{simulationId}/turns/evaluate`
- `GET /api/simulations/{simulationId}`
- `POST /api/simulations/{simulationId}/complete`

Minimal evaluate response:

```json
{
  "metrics": {
    "wording": "watch",
    "pauses": "balanced",
    "repetition": "low",
    "taboo": "clear",
    "intensity": "measured",
    "metaphor": "concrete"
  },
  "issues": ["price_pressure"],
  "alerts": [
    {
      "severity": "high",
      "issueKey": "price_pressure",
      "title": "Price pressure too early",
      "detail": "You pushed for commitment or price closure before trust was established."
    }
  ],
  "partnerTurn": {
    "speaker": "Partner",
    "local": "少し社内で相談したいと思います。",
    "en": "I would like to consult internally first.",
    "zh": "我想先在内部再讨论一下。",
    "tags": ["Partner response", "Context"]
  }
}
```

### 4.3 Hardware Flow

This is a demo hardware workflow. It supports the product story, but it is not a real device integration program.

User actions:

- open hardware page
- see current device state
- connect device
- sync records
- inspect transfer health
- open related review

Must-have state machine:

- disconnected
- connected
- sync_idle
- syncing
- sync_success
- sync_failed

Required data model:

```json
{
  "device": {
    "id": "dev_123",
    "name": "Miro Pin 01",
    "connected": true,
    "connectionState": "connected",
    "transferState": "healthy",
    "battery": 84,
    "firmware": "1.4.2",
    "versionPath": "1.3.8 -> 1.4.2",
    "lastSyncAt": "2026-03-15T10:00:00Z",
    "capturedSessions": 14,
    "vibrationEvents": 9
  }
}
```

Suggested APIs:

- `GET /api/v1/hardware/devices`
- `POST /api/v1/hardware/devices/{deviceId}/connect`
- `POST /api/v1/hardware/devices/{deviceId}/disconnect`
- `POST /api/v1/hardware/devices/{deviceId}/sync`
- `GET /api/v1/hardware/devices/{deviceId}/logs`
- `GET /api/v1/hardware/devices/{deviceId}/sync-records`

Important implementation note:

- Connect, disconnect, and sync are demo state transitions, not proof of physical connectivity.
- Frontend animation may imply upload or download progress, but backend persistence should stay limited to demo-safe state and event history.
- If a signed-in user has no demo device yet, `GET /api/v1/hardware/devices` may auto-create one default demo device for continuity. This is demo convenience, not a real hardware registration flow.

### 4.4 Review Flow

This is where simulation output and hardware data converge.

User actions:

- open list
- filter by `all / simulation / device`
- open one review
- inspect line-level advice

UI states:

- loading
- no reviews
- filtered empty
- selected review loaded

Suggested APIs:

- `GET /api/reviews?source=all`
- `GET /api/reviews/{reviewId}`

Response shape to freeze:

```json
{
  "id": "review_123",
  "source": "simulation",
  "country": "Japan",
  "score": 72,
  "modules": [74, 68, 76, 70],
  "repeatedIssues": ["soft_refusal_missed", "price_pressure"],
  "summary": {
    "en": "You introduced price pressure before the buyer signalled readiness.",
    "zh": "你在买方尚未释放准备信号时就推进价格。"
  },
  "lines": [
    {
      "speaker": "User",
      "sourceText": "We can lock the final price today if you move quickly.",
      "translation": {
        "en": "We can lock the final price today if you move quickly.",
        "zh": "如果你们尽快决定，我们今天就能锁定最终价格。"
      },
      "tags": ["Price", "Directness"],
      "issueKey": "price_pressure",
      "advice": {
        "en": "Replace price closure with a lighter trust step.",
        "zh": "把价格收口改为更轻的信任动作。"
      }
    }
  ]
}
```

### 4.5 Pricing Flow

User actions:

- browse plans
- select a plan
- top up credits

UI states:

- plans loaded
- plan selected
- top-up pending
- top-up success
- top-up failed

Suggested APIs:

- `GET /api/v1/billing/plans`
- `GET /api/v1/billing/summary`
- `POST /api/v1/billing/select-plan`
- `POST /api/v1/billing/top-up`

Freeze early:

- plan IDs
- display names
- price units
- balance units
- what top-up actually means in backend accounting

Important implementation note:

- Billing in this capstone is a demo state surface, not a real payment platform.
- `select-plan` and `top-up` mutate actor-scoped demo state only.
- On first `GET /api/v1/billing/summary`, the backend may auto-create one default billing account for continuity. This is demo convenience, not a real subscription signup flow.

## 5. Frontend State to Freeze Early

These state objects should be stabilized before real backend integration.

### Auth state

```ts
type AuthState = {
  loggedIn: boolean;
  authOpen: boolean;
  authMode: "login" | "register";
  pendingRoute: string | null;
  user: UserSummary | null;
};
```

### Simulation state

```ts
type SimulationState = {
  simulationId: string | null;
  phase: "setup" | "session";
  country: string;
  meetingType: string;
  goal: string;
  duration: number;
  voiceStyle: string;
  constraint: string;
  files: UploadedContextFile[];
  strategies: StrategyCard[];
  transcript: TranscriptTurn[];
  alerts: SimulationAlert[];
  metrics: LanguageMetrics;
  issueCounts: Record<string, number>;
  practiceText: string;
  countdown: number;
};
```

### Hardware state

```ts
type HardwareState = {
  deviceId: string | null;
  connectionState: "disconnected" | "connected";
  syncState: "idle" | "syncing" | "success" | "failed";
  transferHealth: "healthy" | "warning";
  battery: number | null;
  firmware: string | null;
  logs: DeviceLog[];
  syncRecords: DeviceSyncRecord[];
};
```

### Review state

```ts
type ReviewState = {
  filter: "all" | "simulation" | "device";
  selectedReviewId: string | null;
  reviews: ReviewListItem[];
};
```

### Billing state

```ts
type BillingState = {
  currentPlanId: string;
  selectedPlanId: string | null;
  balance: number;
  topUpStatus: "idle" | "pending" | "success" | "failed";
};
```

## 6. What Must Be Decided Before Backend Starts

Do not wait for final UI polish. Freeze these instead:

1. Route list
2. Main entities
3. State machine for simulation
4. State machine for hardware demo connection and sync
5. Review record shape
6. Billing event shape
7. Auth session shape

If these seven are stable, frontend and backend can move in parallel.

## 7. Recommended Parallel Build Order

### Track A: Frontend

1. Keep refining page layout and states
2. Replace mock state with typed state contracts
3. Add loading, error, empty, and success states
4. Swap mock service layer to real API calls later

### Track B: Backend

1. Auth session endpoints
2. Simulation setup + evaluate endpoints
3. Review read endpoints
4. Hardware demo state endpoints
5. Billing endpoints

### Track C: Integration

1. Connect auth
2. Connect simulation setup and evaluate
3. Connect review list and detail
4. Connect hardware dashboard
5. Connect billing

## 8. Immediate Next Step

The next useful deliverable is not more visual polish. It is a thin API contract doc with concrete request/response schemas for:

1. login
2. create simulation
3. evaluate turn
4. list reviews
5. get review detail
6. list devices
7. sync device
8. select plan
9. top up credits

Once that is written, frontend and backend work can run in parallel without waiting for UI to be "finished."
