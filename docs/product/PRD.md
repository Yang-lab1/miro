# Miro Product Requirements Document

## 1. Product Summary

Miro is a cross-cultural communication AI product for enterprise cross-border negotiation preparation. Its hero innovation is longitudinal coaching for cultural pragmatics: the system remembers repeated language mistakes, warns before the next meeting, and helps the user improve over time.

Core value proposition:

- Beyond translation, towards trust.
- Miro does not stop at literal translation. It focuses on wording, pacing, indirectness, politeness, taboo phrasing, and repeated negotiation mistakes.

## 2. Prototype Boundary

The capstone prototype will actually do:

- Generate pre-meeting strategy prompts from country context, uploaded material, and User Twin memory.
- Run a live language-signal simulation focused on wording, pauses, repetition, taboo cues, intensity, directness, and metaphor fit.
- Produce a unified review workflow that merges simulation records and hardware pin sync records.

The prototype explicitly will not claim:

- Reliable face or emotion inference.
- Real multimodal buying-signal detection.
- Hardware-side AI inference or firmware intelligence.
- Full country-depth coverage for all global markets in v1.

## 3. Target Users

Primary users:

- Enterprise decision makers and strategists in cross-border commerce.
- Business development leaders visiting overseas clients.
- Teams preparing for distributor meetings, buyer visits, and trust-sensitive introductions.

## 4. Core User Journeys

### Journey 1: Prepare for a high-stakes meeting

1. User opens Home.
2. User logs in via Liquid Glass auth modal.
3. User enters Live Simulation.
4. User selects target country, meeting type, goal, duration, and uploads PDF/TXT meeting context.
5. Miro generates three strategy prompts based on country rules and User Twin memory.

Success criteria:

- Strategy is generated in one click.
- Country-specific risks and repeated personal mistakes are visible before the live session starts.

### Journey 2: Run a language-only simulation

1. User enters the live session cabin.
2. User pastes or drafts a response.
3. Miro evaluates language risk in real time.
4. Transcript and alerts appear in the right drawer.
5. User iterates or ends the session.

Success criteria:

- The simulation evaluates only language signals.
- Alerts identify taboo wording, repetition, pause density, intensity, metaphor risk, and directness problems.

### Journey 3: Review and improve over time

1. User ends the session.
2. Miro generates a scored review report.
3. Repeated issues are written back into User Twin memory.
4. User later opens Review Center and compares simulation records with demo hardware-sync records.

Success criteria:

- Review Center contains both Simulation and demo Device records.
- Repeated issues are visible across sessions.

## 5. Navigation and Information Architecture

Top navigation:

- Left: Miro logo
- Center: Home, Live Simulation, Hardware Devices, Review Center, Pricing, Settings
- Right: Register / Log In when signed out, account and Log out when signed in

### Home

Layout order:

1. Fixed top navigation
2. Large hero inspired by modern SaaS landing pages, with product copy and cockpit preview
3. User Twin high-frequency pain points section
4. User testimonials section
5. Footer bar

Home must show:

- Hero copy and CTA
- CQ score and five-dimension ability preview
- User Twin high-frequency pain points
- Social proof / user testimonials

### Live Simulation

Includes:

- Pre-meeting setup form
- Strategy preview panel
- Session cabin with waveform, transcript drawer, and alert drawer

### Hardware Devices

Includes:

- Demo pin connection state
- Demo transfer state
- Firmware version and version path
- Sync records
- Demo event logs

Boundary:

- Hardware is represented as a 3D shell, rendered visual, and simulated state layer.
- The capstone does not require real BLE, USB, chip, firmware, or live wearable ingestion.

### Review Center

Includes:

- Unified list of Simulation and demo Device records
- Filters by source
- Score breakdown
- Line-by-line analysis
- Repeated issue tags

### Pricing

Includes:

- Plan comparison cards
- Credits summary
- Recharge / top-up actions

### Settings

Includes:

- Profile
- Language switch
- Preferences

## 6. Must-Have Features

### 6.1 User Twin Longitudinal Memory

- Track repeated pragmatic failures over time.
- Surface the top recurring issues on Home.
- Inject the same memory into strategy generation and report updates.

### 6.2 Cross-Cultural Strategy + Live Coaching

- Generate country-sensitive pre-meeting prompts.
- Evaluate live draft language against pragmatic risk cues.
- Show partner response and warning feedback in real time.

### 6.3 Unified Review Center

- Merge Simulation and Device records into one review workflow.
- Show score, repeated issues, and line-by-line advice.

## 7. Language-Signal Scope

The simulation should focus only on:

- Wording quality
- Pause density and turn pacing
- Repetition loops
- Taboo phrasing by country
- Intensity / forcefulness
- Directness vs indirectness
- Metaphor / idiom fit

Out of scope for prototype scoring:

- Facial expressions
- Emotion classification
- Intent certainty claims
- Wearable-side AI inference

## 8. Data Needed For Simulation Testing

To test the simulation meaningfully, the following data should be collected and labeled:

- Negotiation transcripts from mock or enterprise-authorized sessions
- Country-specific taboo lexicons and face-threatening phrases
- High-context refusal examples and indirect rejection patterns
- Pause markers and silence-length annotations
- Repetition and pressure-loop annotations
- Intensity markers such as urgency or excessive insistence
- Metaphor and idiom mismatch examples
- Meeting outcomes or expert-rated quality labels for evaluation

## 9. Acceptance Criteria

- User can navigate through Home, Live Simulation, Hardware Devices, Review Center, Pricing, and Settings.
- Language switch exists only in Settings and updates the full UI.
- Pricing contains credits and top-up controls, while Settings stays profile-focused.
- Live simulation evaluates only language signals.
- Review Center merges Simulation and Device records.
- Hardware page shows connection, transfer, firmware, and vibration logs.
- Home follows the requested structure: hero, User Twin, testimonials, footer.


