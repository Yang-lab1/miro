# Miro AI and Data Governance Specification

## 1. Scope

This document defines what data Miro should collect, how it should be governed, and what is needed to test and improve the language-signal simulation safely.

The prototype focuses on language and pragmatic coaching only.

## 2. What Data To Collect For Simulation Testing

The simulation should be validated on structured, labeled data across the following categories.

### 2.1 Transcript Data

Collect:

- enterprise-authorized mock negotiation transcripts
- enterprise-authorized training role-play transcripts
- de-identified post-meeting summaries where permission exists

Label:

- direct ask
- soft refusal
- indirect hesitation
- taboo phrase
- repetition loop
- premature price push
- escalation cue
- trust-building cue

### 2.2 Pause and Pacing Data

Collect:

- pause timestamps from audio or transcript alignment
- silence length per turn
- interruptions and overlap markers

Label:

- healthy pause
- no pause window
- interruption
- over-compressed turn
- delayed response after a sensitive ask

### 2.3 Language Intensity Data

Collect:

- urgency phrases
- forceful commitment requests
- repeated insistence patterns
- capitalization or emphasis cues in text channels when available

Label:

- neutral
- firm
- forceful
- face-threatening

### 2.4 Taboo and Pragmatic Failure Data

Collect:

- country-specific taboo terms and face-threatening expressions
- examples of language that sounds low-value, dismissive, or disrespectful
- expert examples of inappropriate early price pressure

Label:

- taboo wording
- face threat
- low-value framing
- timing mismatch

### 2.5 Metaphor and Idiom Data

Collect:

- culture-specific idioms and metaphors from source language
- examples where idioms reduce clarity in negotiation
- corrected equivalents that travel better cross-culturally

Label:

- safe metaphor
- risky metaphor
- non-transferable idiom
- recommended replacement

### 2.6 Outcome and Coaching Data

Collect:

- expert scorecards
- meeting quality ratings
- whether the user repeated a previously flagged issue
- whether coaching changed behavior in later sessions

Label:

- improved after coaching
- unchanged
- repeated issue
- newly introduced issue

## 3. Data Sources

Recommended sources:

- internal enterprise sales training sessions
- role-play workshops with explicit consent
- annotated scripts created with cross-cultural business experts
- country-specific etiquette and negotiation guidance corpora
- synthetic training cases created from expert-reviewed templates

Avoid for prototype training:

- scraped private conversations
- unconsented customer data
- raw face video used for intent claims

## 4. Responsible Boundary

Miro must not over-claim:

- The product should not state that it can accurately infer true emotion or true intent from faces.
- Face, gaze, or expression signals, if explored later, should be treated as weak optional signals and future work.
- The capstone claim should remain: longitudinal, culturally-aware language coaching reduces repeated pragmatic failures better than generic translation support.

## 5. Governance Rules

- Every dataset must have a source record, permission status, and retention policy.
- Training and evaluation sets must be versioned.
- Sensitive enterprise content must be de-identified where possible.
- Raw audio and raw video should have separate retention rules from derived labels.
- Device data must be scoped to transfer logs, vibration events, and meeting metadata unless stronger consent exists.

## 6. Recommended Evaluation Sets

Build at least these evaluation slices:

- Japan high-context refusal test set
- Germany clarity/process test set
- UAE relationship-first phrasing test set
- repeated-issue regression set across multiple sessions
- taboo wording challenge set
- pause-density challenge set
- metaphor transfer challenge set

## 7. Metrics

Track:

- precision/recall of alert categories
- repeated-issue detection accuracy
- expert agreement on line-by-line advice
- false positive rate for taboo and intensity alerts
- session-over-session improvement rate for the same user

## 8. Data Retention Recommendation

- User Twin memory: retain as user-linked coaching artifacts
- Simulation transcript: retain per organizational policy
- Device sync metadata: retain unless the org requests deletion
- Raw sensitive media: shortest retention window by default
