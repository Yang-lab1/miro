# Miro Project Handoff

This file must be updated after every meaningful UI or product change.
Its purpose is to let another AI or developer resume work quickly without re-discovering the project context.

## 1. Why This Project Exists

Miro is a capstone prototype for cross-cultural communication coaching in cross-border commerce.
The core idea is not generic translation. The hero innovation is longitudinal coaching for cultural pragmatics:
- remember repeated language mistakes
- warn before the next meeting
- generate a review after each rehearsal
- help users reduce repeated pragmatic failure over time

The prototype intentionally focuses on language only:
- wording
- pauses
- repetition
- taboo phrasing
- intensity / forcefulness
- metaphor fit

It does not claim reliable face-reading, emotion inference, or wearable-side AI reasoning.

## 2. Current Product Scope

Confirmed modules in the prototype:
- `Home`
- `Live Simulation`
- `Hardware Devices`
- `Review Center`
- `Pricing`
- `Settings`
- `Auth Modal`

Current information architecture:
- `Home` is the public-facing strategic cockpit landing page
- `Live Simulation` is two-step: setup first, interview window second
- `Hardware Devices` shows a demo pin surface with simulated connection / transfer / firmware / event history
- `Review Center` merges simulation and demo hardware records
- `Pricing` is now separate from `Settings`
- `Settings` now focuses on profile, language, and preferences only

## 3. Current Prototype Boundary

What the prototype currently does:
- generate pre-meeting strategy prompts from country context and User Twin memory
- run a language-only interview simulation
- evaluate typed responses and trigger pragmatic warnings
- generate a review report
- write repeated issues back into User Twin memory
- show demo hardware support-layer logs
- show a separate pricing page with plan cards and recharge actions

What it still does not do:
- real hardware transport or wearable integration
- real ASR / TTS
- real PDF parsing
- real vector retrieval
- real payment
- real device sync

## 4. Current UI Direction

Latest UI direction as of 2026-03-09:
- overall theme switched toward black-and-white minimalism
- `Home` uses a lighter editorial SaaS feel instead of the earlier dark enterprise dashboard feel
- `Pricing` is visually separate and inspired by modern dark plan-comparison layouts
- `Auth Modal` is redesigned toward a centered dark login/register card
- `Live Simulation` keeps the large central interview window with a right-side assistant drawer

## 5. Progress Snapshot

Implemented now:
- top nav includes `Pricing`
- pricing page is separated from settings
- settings page no longer carries the payment module
- auth modal has been restyled toward the new reference direction
- live simulation remains two-step and language-only
- Chinese / English switching has been cleaned further in the UI shell

Still needs verification:
- browser-level visual QA for the new black/white theme
- browser-level visual QA for the new pricing page
- browser-level visual QA for the new auth modal
- check whether any residual English remains in Chinese mode beyond brand names / sample proper nouns

## 6. Files That Matter

Core prototype files:
- `index.html`: app entry
- `app.js`: routing, state, rendering, interaction logic
- `styles.css`: all page styles and theme styling
- `data.js`: mock countries, reviews, device logs, and seed state

Enterprise docs:
- `docs/product/PRD.md`
- `docs/architecture/TECHNICAL_ARCHITECTURE.md`
- `docs/architecture/AI_DATA_GOVERNANCE.md`
- `docs/api/API_SCHEMA_SPEC.md`

This handoff file:
- `docs/handoff/PROJECT_HANDOFF.md`

## 7. Most Recent Change Log

### 2026-03-09 / Iteration Update
User requested:
- maintain a dedicated handoff/progress file after each iteration
- split pricing from settings
- add `Pricing` to the top nav
- restyle auth modal using the new login/register reference
- shift the overall UI toward a black/white visual direction

Changes applied:
- added top-nav `Pricing`
- created a separate `pricingPage()` in `app.js`
- simplified `settingsPage()` so it only holds profile, language, and preference content
- restyled `authModal()` structure in `app.js`
- appended a black/white theme override and pricing/auth styles in `styles.css`
- updated text so recharge messages now point to `Pricing`

## 8. Next Safe Steps

If continuing from here, the safest next steps are:
1. open `index.html` in a browser and visually QA `Home`, `Pricing`, `Auth Modal`, and `Live Simulation`
2. fix any remaining Chinese/English mismatches discovered in actual rendering
3. if the UI is accepted, begin the next phase: front/back separation skeleton
4. only after that, define the minimal backend API and database tables

## 9. Important Constraints

Keep following these constraints unless the user changes them explicitly:
- do not add features that are not in the requirements
- follow minimal development principles
- prioritize functional completion over expansion
- keep front-end and back-end concerns separable
- treat wearable intelligence as a support layer, not the hero innovation

### 2026-03-09 / Iteration Update 2
User requested:
- fully remove the remaining inconsistent dark/yellow visual fragments
- tighten global spacing and button-to-content padding
- move the design system closer to Apple's visual language
- use an `SF Pro` family stack
- treat buttons as liquid-glass controls
- standardize card and control geometry toward smooth squircle-like corners

Changes applied:
- added a second-stage global style refinement at the end of `styles.css`
- unified core surfaces, cards, settings panels, review panels, hardware panels, and pricing panels under the same light black/white glass system
- converted `Pricing` from the earlier dark comparison block into the same light system as the rest of the product
- refined nav, buttons, pills, drawer controls, and meeting controls into a shared glass-material rule set
- updated the global font stack to prefer `SF Pro Display` / `SF Pro Text` with safe fallbacks
- increased consistency of spacing around hero text, cards, forms, and action rows
- localized the `Business` toggle label inside `pricingPage()` so Chinese mode no longer shows this leftover English string

Still needs verification:
- visual QA in a real browser for the updated Apple-style spacing and glass depth
- confirm whether the user wants the auth modal to remain dark, or also move to a lighter glass card
### 2026-03-10 / Iteration Update 3
User requested:
- continue from the last UI iteration

Changes applied:
- performed a static QA pass in `app.js` to catch obvious UI text defects without adding new product scope
- replaced three corrupted inline separators that were rendering as `路` in testimonials, uploaded file pills, and the live-session header
- added a small `joinMeta()` helper so these inline meta rows now use a stable ASCII separator
- persisted live-setup changes for country, duration, and uploaded files, so refreshing the prototype no longer drops those edits immediately
- updated this handoff file to record the latest safe continuation point

Still needs verification:
- browser-level QA to confirm the cleaned separators and live-setup persistence behave correctly in actual rendering
- visual confirmation of whether the current light auth modal styling is accepted, since earlier notes still mention the old dark-card direction



### 2026-03-10 / Iteration Update 4
User requested:
- redesign the product visually instead of continuing minor cleanup
- remove most card borders across pages and move the product toward a cleaner editorial layout
- rebuild `Settings` into a centered profile/account page
- rebuild the live interview surface into a more familiar meeting-style interface
- stop showing large module hero banners when entering internal pages
- make the fixed nav fade away while scrolling so it no longer blocks the live simulation layout

Changes applied:
- replaced the previous homepage hero with a large editorial landing layout in `app.js`
- rebuilt `liveSetupPage()`, `liveSessionPage()`, `hardwarePage()`, `reviewPage()`, `pricingPage()`, and `settingsPage()` into compact module-toolbar based layouts
- converted the live session into a Zoom/Tencent-style stage with participant panels, transcript sidebar, and bottom compose dock
- reworked `settingsPage()` into a centered avatar/profile stack with account, password, language, credits, plan, and security rows
- appended a large 2026-03-10 visual rewrite block to `styles.css` to remove heavy borders, flatten most panels, and unify the new layout language
- kept the nav fixed but made it fade out of the way after scrolling past the top threshold so module content is not covered

Still needs verification:
- browser-level visual QA for spacing and responsive behavior across `Home`, `Live`, `Review`, `Pricing`, and `Settings`
- confirm whether the user wants any further typography or color changes after seeing the new editorial direction
