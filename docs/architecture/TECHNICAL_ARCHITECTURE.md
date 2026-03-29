# Miro Technical Architecture Document

## 1. Architecture Summary

Target production architecture for the current repository:

- Frontend: static HTML/CSS/JS site with runtime-injected config
- API and AI orchestration: FastAPI
- Database and auth: Supabase Postgres + Supabase Auth
- Vector retrieval: future-phase only, not wired yet
- Realtime transport: current demo uses HTTP APIs; future media transport remains a later phase

Current implementation in this workspace:

- Interactive static prototype in HTML/CSS/JS
- FastAPI backend with Supabase-backed auth and Postgres
- Static-site runtime config generated into `runtime-config.js`

## 2. System Modules

### 2.1 Web Frontend

Responsibilities:

- Top navigation and route shell
- Liquid Glass auth modal
- Home long-page presentation
- Live Simulation setup and cabin UI
- Hardware Devices dashboard
- Review Center
- Settings with language and payment module

### 2.2 Auth Service

Responsibilities:

- Supabase JWT verification
- Local actor hydration
- Org membership and role checks

### 2.3 User Twin Service

Responsibilities:

- Store repeated pragmatic issues
- Rank memory items by count and recency
- Inject memory into strategy prompts
- Update memory after every simulation or reviewed meeting

### 2.4 Simulation Service

Responsibilities:

- Accept meeting setup config
- Retrieve country package and user memory
- Run language-signal evaluation
- Stream transcript and alerts to the session UI
- Prepare lightweight uploaded context summaries and excerpts plus strategy output for live grounding

### 2.5 Review Service

Responsibilities:

- Generate review summaries and score modules
- Merge Simulation and Device records
- Support filters and detail views

### 2.6 Hardware Demo State Service

Responsibilities:

- Store demo device status for the current user
- Simulate connect, disconnect, and sync transitions
- Expose firmware, transfer health, and recent demo events for UI display
- Allow Review Center to reference demo device-originated records when needed

### 2.7 Billing Service

Responsibilities:

- Manage subscriptions and top-up credits
- Expose balance to Settings
- Store payment events and invoices

## 3. Key Data Flows

### 3.1 Pre-meeting strategy flow

1. Frontend submits country, meeting type, goal, duration, files, and notes.
2. API stores setup metadata.
3. Ingestion pipeline extracts grounded text from uploaded TXT material and simple text-based PDFs.
4. Strategy service retrieves:
   - country package
   - organization context
   - User Twin memory
5. Service returns three strategy prompts.

### 3.2 Live simulation flow

1. Frontend sends user draft text or live ASR transcript.
2. Realtime session orchestration validates the active session and assembles grounding context from simulation setup, generated strategy, lightweight uploaded context summaries/excerpts, and recent transcript lines.
3. Turn generation produces the partner response.
4. Alert analysis extracts language-signal issues from the latest user turn.
5. Alert objects and partner response are returned/streamed.
6. Frontend updates transcript drawer and alerts drawer.
7. When session ends, review service computes module scores and summary.
8. User Twin is updated with repeated issues.

Current implementation note:

- The current backend keeps these live boundaries separate internally:
  - session orchestration
  - uploaded context grounding prep
  - turn generation
  - alert extraction
- Uploaded files now persist extracted summaries and short excerpts so live grounding can use them without changing the public API.
- The current extraction supports:
  - direct `text/plain` body extraction
  - simple text extraction from text-based PDFs
  - safe fallback to lightweight deterministic summaries when extraction is unavailable
- It is still not full document parsing, chunking, embedding, or retrieval.
- The default turn generation and alert extraction logic remain rule-based, but partner replies and review summaries can now reflect grounded uploaded context while the demo and smoke suite stay stable.

### 3.3 Hardware demo state flow

1. Frontend triggers a demo hardware action such as connect, disconnect, or sync.
2. Hardware demo service validates the signed-in user and requested state transition.
3. If the user has no demo device yet, the service may auto-create one default demo device for UI continuity.
4. Demo device state and demo sync events are written to the database.
5. Hardware page and Review Center can read the updated demo record beside simulation records.

## 4. Language-Signal Evaluation Scope

Production scoring should remain limited to language and pragmatic signals:

- wording choice
- directness level
- pause density
- repetition loops
- taboo phrasing
- intensity / forcefulness
- metaphor and idiom transfer risk

This architecture intentionally excludes facial inference as a required production path for the capstone.

## 5. Core Storage Model

### PostgreSQL tables

- `users`
- `organizations`
- `memberships`
- `user_settings`
- `user_twin_memory`
- `simulations`
- `simulation_turns`
- `simulation_alerts`
- `reviews`
- `review_lines`
- `devices`
- `device_sync_events`
- `device_logs` for demo timeline history
- `payments`
- `audit_logs`

### pgvector collections

- uploaded meeting materials
- country knowledge packages
- historical review embeddings for retrieval support

### Redis usage

- active session state
- streaming transcript buffers
- alert throttling
- temporary upload orchestration

## 6. Security and Governance Notes

- Do not store raw face video by default.
- Demo hardware records should stay limited to UI-safe metadata and simulated event history.
- All training or evaluation data must be consented, auditable, and scoped to enterprise-authorized use.

## 6.1 Hardware Scope Note

This repository does not currently target real hardware connectivity. The authoritative boundary is:

- 3D hardware shell / rendered visuals for presentation
- frontend animation for connect / disconnect / upload / download / sync states
- backend persistence for demo device state only

It does not include BLE, USB, firmware, drivers, provisioning, or real wearable ingestion.

## 7. Deployment Shape

Recommended production deployment:

- Static frontend hosted on Vercel
- FastAPI backend hosted on Alibaba Cloud ECS
- Supabase for Postgres + Auth
- Frontend runtime values injected at deploy time through `runtime-config.js`
- Backend health check on `/api/v1/health`
- Strict CORS allow-list based on the deployed frontend origin
- Post-deploy verification through the repository `validate:online` command plus the deployment checklist
- Current live validation uses:
  - frontend `https://miro-vert.vercel.app`
  - backend `https://47-238-228-236.sslip.io/api/v1`

## 8. Prototype-to-Production Gap

What is implemented in this workspace:

- route shell
- UI flows
- rule-based session evaluation
- local memory update behavior
- unified review experience
- production-ready runtime config entrypoints for static frontend + FastAPI backend deploys

What remains for production build:

- richer file parsing beyond `text/plain` and simple PDF text extraction
- richer live provider integration
- vector retrieval / grounding beyond lightweight extracted summaries
- device integration API
- payment provider integration
