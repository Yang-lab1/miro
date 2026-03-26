# Shared Workspace

This folder is the cross-stack source-of-truth area for definitions that should not drift between frontend and backend.

## Current Convention

- `enums/*.json`
  - canonical enum catalogs
- `contracts/*.schema.json`
  - request / response level JSON Schema files
- `schemas/*.schema.json`
  - reusable object or envelope schemas

The files are intentionally language-neutral JSON so the current frontend and the new FastAPI backend can both consume them without locking the repo into Python-only or TypeScript-only definitions too early.

## Frozen Decisions Already Reflected Here

- use `countryKey` with values like `Japan`
- keep `Learning` separate from `Home` and `Live Simulation`
- use Supabase Auth as the authentication source and pass bearer access tokens to FastAPI
- expose `GET /api/v1/auth/session` as the backend auth session snapshot contract
- expose actor-scoped hardware demo state contracts for list/connect/disconnect/sync/log history
- expose actor-scoped billing demo contracts for plans, current summary, plan selection, and credit top-up
- require `learning precheck` before simulation start
- allow skip with strong warning, not silent bypass
- model `Live Simulation` as realtime voice session
- prefer `webrtc` and keep `websocket` as fallback
- separate `voiceStyle` and `voiceProfile`
- keep `voiceProfile` as flat catalog data grouped in UI by country and gender
