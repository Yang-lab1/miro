# Miro Interview Simulation Development Blueprint

## 1. Purpose

This document is the working development blueprint for Miro's core product loop.

It exists to answer five questions before more frontend or backend changes are made:

1. What exact problem is Miro solving for the user?
2. What end-to-end system flow should the product follow?
3. Which algorithm layers should be used at each step?
4. Why are those algorithm choices better than a generic chat model alone?
5. What practical training result should the interviewee or business user get?

This document is intentionally narrower than a PRD and more product-driven than a pure architecture note. It is the bridge between product intent and implementation.

## 2. Product Thesis

Miro should not behave like a general-purpose AI chat tool.

Its core value is:

- simulate a specific interview or meeting scenario
- ground the simulation in the user's uploaded preparation material
- inject country and culture-specific communication rules
- score the user's performance against scenario-specific criteria
- return feedback that is concrete, explainable, and actionable

If Miro only exposes a large model with a text box, users can get similar value from OpenAI, Gemini, or DeepSeek directly. The product is only differentiated when it adds:

- scenario structure
- culture rules
- targeted retrieval from uploaded material
- rehearsal-specific scoring
- longitudinal review value

## 3. User Goal Backward Map

### 3.1 What the user wants

From the interviewee or meeting participant perspective, the desired outcome is not "talk with an AI."

The desired outcome is closer to:

- "I want to rehearse tomorrow's meeting or interview."
- "I want the simulated counterpart to behave like someone who has actually read the background material."
- "I want the simulation to reflect the target country's communication style and taboo zones."
- "I want feedback that explains what I did wrong in this exact scenario, not generic communication advice."

### 3.2 What the system must therefore do

| User wants | System must do | Why it matters |
|---|---|---|
| A realistic counterpart | Generate a role-specific response grounded in uploaded material, target scenario, and recent transcript | Prevents generic chat behavior |
| Country-specific realism | Apply culture and taboo rules for the target country | Creates differentiated rehearsal value |
| Targeted challenge | Ask or respond with pressure, hesitation, objections, or follow-up tied to the meeting goal | Trains for the real conversation rather than generic speaking |
| Actionable feedback | Score performance by scenario rubric and explain misses with evidence | Turns the tool into a coach, not only a simulator |
| Better future performance | Persist repeated issues and use them in future prep | Creates longitudinal training value |

## 3.3 Memory model

Miro should use exactly three memory layers.

### Memory Layer A: User long-term memory

This belongs to the user account, not to any one interview or client thread.

It stores:

- repeated mistakes
- habitual communication style problems
- recurring taboo or directness issues
- long-term improvement trends

This layer answers:

- what kind of communicator is this user across all scenarios?

### Memory Layer B: Case memory

This belongs to one client thread, one interview thread, or one negotiation thread.

It stores:

- who the counterpart is
- what has already happened in this thread
- prior simulations
- prior real meetings
- uploaded material and supplementary material
- unresolved concerns
- relationship and progress state

This layer answers:

- what has already happened with this specific client or interview case?

### Memory Layer C: Single-session memory

This belongs only to the current simulation or current imported real meeting record.

It stores:

- transcript
- alerts
- per-session review
- current-turn signals

This layer answers:

- what happened in this one run?

### How the three layers work together

At generation time, the system should combine:

- user long-term memory for personal recurring issues
- case memory for continuity and history
- single-session memory for the immediate conversation state

This keeps the product useful in both modes:

- one-off simulation
- multi-round rehearsal for the same client or interview case

## 4. End-to-End System Flow

## 4.1 Step 1: Scenario setup

The user provides:

- target country
- meeting or interview type
- goal
- uploaded files
- notes
- optional constraints

Backend responsibilities:

- store scenario metadata
- register files
- extract usable text
- compute strategy prompts
- prepare grounding inputs

## 4.2 Step 2: Uploaded content processing

The system should extract usable text from the uploaded files and convert it into:

- extracted summary
- extracted excerpts
- chunk-level retrieval candidates
- retrieval metadata

Current implemented state:

- `text/plain` extraction
- simple text-based PDF extraction
- deterministic summary / excerpt fallback

Target next state:

- chunk generation
- chunk ranking metadata
- stronger PDF text stability

## 4.3 Step 3: Scenario and culture shaping

Before the live turn starts, the system should build a scenario context from:

- meeting type
- target country
- user goal
- strategy summary
- uploaded context
- prior transcript turns
- longitudinal user issues

This is the layer that turns the product from "chat" into "targeted rehearsal."

## 4.4 Step 4: Live turn generation

On every turn, the system should:

1. take the latest user input
2. retrieve the most relevant uploaded chunks or excerpts
3. apply scenario and culture constraints
4. generate the counterpart reply
5. extract alerts or mistakes from the user's turn

The counterpart reply should feel like:

- a real interview or meeting participant
- with a concrete role
- in a concrete cultural setting
- discussing a concrete agenda

## 4.5 Step 5: Scoring and review

After the session, the system should score the user's performance on dimensions such as:

- communication clarity
- goal alignment
- objection handling
- culture fit
- taboo avoidance
- pacing and pressure control
- use of uploaded context

The feedback should explain:

- what happened
- why it was a problem in this scenario
- what better behavior would look like

## 4.6 Step 6: Re-entry and continued rehearsal

The system must support multiple user entry paths into rehearsal.

### Entry path A: Start a one-off simulation from Home

The user lands on Home and starts a new simulation immediately.

This path should:

- create a fresh case if needed
- use user long-term memory
- use only the current setup and uploaded material

Best for:

- first-time rehearsal
- a single upcoming interview or meeting

### Entry path B: Re-enter from prior history

The user browses prior simulations, reviews, or case history, then starts another round.

This path should:

- reopen the existing case
- use user long-term memory
- use case memory
- optionally reuse previous uploaded material
- optionally attach new focus goals from the last review

Best for:

- second round rehearsal
- improving weak dimensions from the previous attempt

### Entry path C: Re-enter after hardware-imported real meeting data

The user finishes a real meeting, imports or syncs the record through the hardware/device path, and then wants to rehearse again.

This path should:

- attach the imported real meeting record to the existing case
- update case memory with real-world signals
- let the next simulation use:
  - prior uploaded documents
  - the real meeting record
  - newly added supplementary material if any

Best for:

- preparing for round two or round three of the same client thread
- turning real meeting outcomes into the next rehearsal input

### Entry path D: Re-enter after supplementary material upload

After a real meeting or a prior simulation, the user may add more files.

This path should:

- keep the same case
- attach the new material as additional case artifacts
- re-run extraction and retrieval inputs
- let the next simulation reflect both old and new material

Best for:

- updated requirements
- new agenda details
- new stakeholder information
- post-meeting follow-up preparation

### Product rule for entry logic

The product should not force all users into a single flow.

It should support:

- single-round rehearsal only
- multi-round rehearsal across the same case
- rehearsal after real-world meeting import
- rehearsal after supplementary material upload

The unifying rule is:

- if the user is continuing the same client or interview thread, reuse the same case memory
- if the user is starting something unrelated, create a new case

## 5. Algorithm Stack

Miro's target quality does not come from a single algorithm. It comes from a layered system.

## 5.1 Extraction layer

Purpose:

- convert uploaded user material into usable text

Recommended methods:

- direct text extraction for `text/plain`
- text extraction for simple PDFs
- safe fallback when extraction fails

Why:

- without extracted text, there is nothing real to ground on
- this layer replaces "file name driven simulation" with "content driven simulation"

## 5.2 Chunking layer

Purpose:

- split long material into retrievable units

Recommended methods:

- paragraph-aware chunking
- heading-aware chunking when possible
- overlap-based chunk windows for long text

Why:

- raw documents are too large and noisy to pass into the model each turn
- chunking is the basis of practical RAG without requiring model training

## 5.3 Retrieval layer

Purpose:

- find the most relevant uploaded content for the current turn

Recommended methods:

- first step: keyword or BM25-style retrieval plus metadata filters
- next step: embedding retrieval or hybrid retrieval
- optional reranking for top candidates

Why:

- this is what makes the counterpart respond to the actual material instead of vaguely paraphrasing the whole document
- retrieval is the main answer to "how is this different from a generic large model chat"

## 5.4 Scenario engine

Purpose:

- make the counterpart behave like a specific role in a specific meeting type

Recommended inputs:

- target country
- meeting type
- goal
- counterpart role
- objections / constraints
- user memory

Why:

- users are not training for generic conversation
- they are training for a specific situation with a specific objective

## 5.5 Culture rule engine

Purpose:

- inject country-sensitive communication rules into both generation and scoring

Recommended rule types:

- taboo topics
- directness tolerance
- pace and politeness expectations
- hierarchy sensitivity
- whether hard push is appropriate
- relationship-first vs task-first communication style

Why:

- this is one of the strongest product differentiators
- a generic model can imitate tone, but it will not reliably apply your product's explicit culture rubric without a dedicated rule layer

## 5.6 Generation layer

Purpose:

- produce realistic counterpart replies and review summaries

Recommended implementation:

- use a strong model API for generation
- combine:
  - retrieved chunks
  - scenario context
  - culture rules
  - recent transcript

Why:

- this layer makes the system feel human and adaptive
- it should not replace retrieval and rules; it should sit on top of them

## 5.7 Scoring layer

Purpose:

- turn a conversation into a usable coaching output

Recommended implementation:

- rule-driven checks for taboo, directness, timing, repetition, and scenario misses
- model-assisted synthesis for explanation and summary

Why:

- fully model-generated scoring is hard to trust
- fully rule-only scoring is too rigid
- a hybrid approach is more stable and explainable

## 6. Why Not Train a Custom Model First

At the current stage, training a custom model is not the best next step.

It is not required to build a strong version of this product.

The practical path is:

- extraction
- chunking
- retrieval
- culture rules
- strong API-based generation

Reasons:

- faster implementation
- lower complexity
- easier iteration
- easier debugging
- enough quality gain for the next product step

Custom training should only be considered later if:

- the product accumulates enough high-quality proprietary data
- general APIs stop meeting quality needs
- the team wants custom classifiers or domain-specific scoring models

## 7. What This System Can Achieve for the User

If the stack above is built correctly, the system can produce the following training effect.

## 7.1 Simulation quality

The user uploads:

- client or company profile
- interview brief
- meeting goal
- likely agenda
- notes on pain points or priorities

Then the live session can:

- act like a counterpart who "knows the background"
- ask scenario-specific follow-ups
- raise likely objections
- react differently depending on the user's tone and strategy
- enforce country-specific communication constraints

## 7.2 Coaching quality

The system can then explain things like:

- you addressed the agenda but ignored the client's main risk concern
- your answer was structurally clear but culturally too direct for a Japanese counterpart
- you pushed for commitment too early
- you failed to use the uploaded context that highlighted delivery concerns
- your phrasing increased pressure instead of building trust

This is much more valuable than generic advice such as:

- be more confident
- be clearer
- speak more politely

## 7.3 Training value for the interviewee

The user should leave the rehearsal with:

- clearer awareness of likely questions
- better awareness of culture-specific mistakes
- better control over pacing and phrasing
- improved ability to handle objections
- a concrete understanding of what to change before the real conversation

## 8. Current State vs Target State

| Layer | Current state | Target state |
|---|---|---|
| Extraction | `text/plain` + text-based PDF + deterministic fallback | OCR, Office layout, and broader content robustness |
| Chunking | in-process source-text chunking | persisted, versioned chunks with lifecycle controls |
| Retrieval | per-turn lexical top-k retrieval from uploaded source text | embedding/vector retrieval with lexical fallback |
| Scenario engine | present but still lightweight | stronger role shaping and objective shaping |
| Culture rules | partial / implicit | explicit rule library by country and scenario |
| Generation | configurable OpenAI-compatible provider plus explicit rule-based fallback | production provider routing, latency controls, and quality guardrails |
| Scoring | partial hybrid | explicit rubric + grounded evidence + stable scoring dimensions |

## 9. Recommended Next Development Order

## 9.1 Phase A: Retrieval hardening

Current implementation:

- source-text extraction
- in-process chunk generation
- per-turn top-k lexical retrieval

Next hardening:

- persist chunk versions and source offsets
- add embeddings/vector retrieval behind the same interface
- measure retrieval hit rate against review evidence

This is the fastest way to make uploaded files more useful.

## 9.2 Phase B: Scenario and culture rule engine

Build:

- structured country rule library
- scenario-specific rule sets
- taboo and directness constraints
- role behavior profiles

This is the fastest way to differentiate Miro from generic model chat.

## 9.3 Phase C: Provider generation productionization

Current implementation:

- OpenAI-compatible provider path
- explicit rule-based fallback for local/demo runs

Next hardening:

- configure and monitor a production model provider
- add latency, token, timeout, retry, and prompt-injection controls
- evaluate groundedness and cultural appropriateness on a fixed test set

This is the fastest way to improve conversational realism.

## 9.4 Phase D: Stronger scoring

Build:

- rubric-based scoring framework
- evidence-linked feedback
- confidence or severity grading

This is what turns the product into a training system rather than only a simulator.

## 9.5 Phase E: Case-based rehearsal loop

Build:

- case entity and lifecycle
- history-driven re-entry logic
- review-to-retry logic
- hardware-import-to-case linkage

This is what turns isolated simulations into a longitudinal coaching system.

## 10. Acceptance Questions Before More Feature Work

Before expanding frontend or backend scope, future changes should answer these questions:

1. Does this feature make the simulation more scenario-specific?
2. Does it improve grounding quality?
3. Does it improve cultural realism?
4. Does it improve scoring usefulness?
5. Does it make the rehearsal more valuable than a generic model chat?

If the answer is no, the feature should usually be deprioritized.

## 11. Working Product Definition

Miro should be developed as:

- not a generic AI chat website
- not only a "large model wrapper"
- but a scenario-driven, culturally aware, document-grounded rehearsal system

Its core value is:

- targeted simulation
- targeted challenge
- targeted scoring
- targeted improvement

That is the standard future frontend and backend work should follow.
