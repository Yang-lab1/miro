const { test, expect } = require("@playwright/test");
const {
  STORAGE_KEY,
  buildBaseUrl,
  installSharedBootstrapRoutes,
  seedStoredState,
  startSmokeServer,
  stopSmokeServer,
  waitForSmokeServer
} = require("./helpers/http-smoke");

const SMOKE_HOST = "127.0.0.1";
const SMOKE_PORT = 4179;
const BASE_URL = buildBaseUrl(SMOKE_HOST, SMOKE_PORT);
const INITIAL_ALERT_TITLE = "Soften the ask";
const INITIAL_ALERT_DETAIL = "Keep giving more pause before pricing.";
const TURN_ONE_INPUT = "We can finalize the price today if you decide now.";
const TURN_ONE_ASSISTANT_REPLY =
  "Let's pause on price and align on the next step first.";
const TURN_TWO_INPUT =
  "This is still the best offer, and we need a fast answer today.";
const TURN_TWO_ASSISTANT_REPLY =
  "Repeating the urgency will make the pressure heavier than intended.";
const DELTA_ONE_ALERT_TITLE = "Price pressure too early";
const DELTA_ONE_ALERT_DETAIL =
  "The price ask landed before trust was established.";
const DELTA_TWO_ALERT_TITLE = "Repetition loop detected";
const DELTA_TWO_ALERT_DETAIL =
  "The urgency cue was repeated again after the earlier pressure signal.";
const REVIEW_HEADLINE = "Multi-turn alert aggregation carried into review";
const REVIEW_SUMMARY =
  "The second follow-up repeated the urgency after the earlier price-pressure turn, and the review captured the final aggregated risk picture.";
const REVIEW_NEXT_STEP =
  "Drop the repeated urgency cue, acknowledge hesitation, and shift to a lighter written follow-up.";
const REVIEW_ISSUES = ["Price pressure", "Soft refusal", "Repetition"];
const FINAL_REVIEW_LINE = TURN_TWO_INPUT;

let smokeServer = null;

function trackClientDiagnostics(page) {
  const consoleErrors = [];
  const pageErrors = [];

  page.on("console", (message) => {
    if (message.type() !== "error") return;
    if (message.text().includes("favicon")) return;
    consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => {
    pageErrors.push(error.message || String(error));
  });

  return {
    consoleErrors,
    pageErrors
  };
}

function assertNoClientDiagnostics(diagnostics) {
  expect(
    diagnostics.consoleErrors,
    `Console errors:\n${diagnostics.consoleErrors.join("\n") || "none"}`
  ).toEqual([]);
  expect(
    diagnostics.pageErrors,
    `Page errors:\n${diagnostics.pageErrors.join("\n") || "none"}`
  ).toEqual([]);
}

function seedLiveSessionState() {
  return {
    loggedIn: true,
    activeRoute: "live",
    pendingRoute: null,
    user: {
      name: "Bridge Smoke User",
      email: "bridge@miro.local",
      company: "Miro",
      role: "Director, Global Partnerships"
    },
    currentSimulation: {
      country: "Japan",
      meetingType: "First Introduction",
      goal: "Establish trust before pricing",
      duration: 8,
      constraint: "",
      files: [],
      voiceStyle: "Formal / measured",
      voiceProfileId: "voice-japan-1",
      strategies: [],
      phase: "session",
      practiceText: "",
      transcript: [],
      alerts: [],
      countdown: 480,
      sessionId: "session-bridge-1",
      realtimeStatus: "active",
      simulationId: null,
      simulationStatus: "strategy_ready",
      recentReviewId: null,
      recentCompletedSessionId: null,
      lastCompletionStatus: null,
      setupRevision: 2,
      strategyForSetupRevision: 2,
      strategySummary: null,
      sessionSummary: {
        status: "active",
        turnCount: 2,
        alertCount: 1,
        lastAlertSeverity: "medium"
      }
    }
  };
}

function createRealtimeTurn({
  turnId,
  turnIndex,
  speaker,
  sourceText,
  parentTurnId,
  createdAt
}) {
  return {
    turnId,
    turnIndex,
    speaker,
    inputMode: "text",
    sourceText,
    normalizedText: sourceText,
    language: "en",
    parentTurnId: parentTurnId || null,
    createdAt
  };
}

function createRealtimeAlert({
  alertId,
  turnId,
  severity,
  issueKey,
  title,
  detail,
  createdAt
}) {
  return {
    alertId,
    turnId,
    severity,
    issueKey,
    title,
    detail,
    createdAt
  };
}

function createBridgeScenario() {
  return {
    session: {
      sessionId: "session-bridge-1",
      simulationId: null,
      status: "active",
      countryKey: "Japan",
      meetingType: "first_introduction",
      goal: "establish_trust_before_pricing",
      durationMinutes: 8,
      voiceStyle: "formal_measured",
      voiceProfileId: "voice-japan-1",
      setupRevision: 2,
      strategyForSetupRevision: 2
    },
    summary: {
      status: "active",
      turnCount: 2,
      alertCount: 1,
      lastAlertSeverity: "medium",
      startedAt: "2026-03-26T09:00:00.000Z",
      endedAt: null,
      createdAt: "2026-03-26T09:00:00.000Z",
      updatedAt: "2026-03-26T09:03:00.000Z"
    },
    turns: [
      createRealtimeTurn({
        turnId: "turn-1",
        turnIndex: 1,
        speaker: "assistant",
        sourceText: "Thank you for joining today.",
        createdAt: "2026-03-26T09:00:00.000Z"
      }),
      createRealtimeTurn({
        turnId: "turn-2",
        turnIndex: 2,
        speaker: "user",
        sourceText: "We want to understand your priorities first.",
        parentTurnId: "turn-1",
        createdAt: "2026-03-26T09:01:00.000Z"
      })
    ],
    alerts: [
      createRealtimeAlert({
        alertId: "alert-1",
        turnId: "turn-2",
        severity: "medium",
        issueKey: "soft_refusal_missed",
        title: INITIAL_ALERT_TITLE,
        detail: INITIAL_ALERT_DETAIL,
        createdAt: "2026-03-26T09:01:30.000Z"
      })
    ],
    deltas: [
      {
        userTurnId: "turn-3",
        userTurnIndex: 3,
        assistantTurnId: "turn-4",
        assistantTurnIndex: 4,
        assistantReply: TURN_ONE_ASSISTANT_REPLY,
        alertId: "alert-2",
        alertSeverity: "high",
        alertIssueKey: "price_pressure",
        alertTitle: DELTA_ONE_ALERT_TITLE,
        alertDetail: DELTA_ONE_ALERT_DETAIL,
        createdAt: "2026-03-26T09:03:45.000Z",
        summaryUpdate: {
          turnCount: 4,
          alertCount: 2,
          lastAlertSeverity: "high",
          updatedAt: "2026-03-26T09:04:00.000Z"
        }
      },
      {
        userTurnId: "turn-5",
        userTurnIndex: 5,
        assistantTurnId: "turn-6",
        assistantTurnIndex: 6,
        assistantReply: TURN_TWO_ASSISTANT_REPLY,
        alertId: "alert-3",
        alertSeverity: "medium",
        alertIssueKey: "repetition_loop",
        alertTitle: DELTA_TWO_ALERT_TITLE,
        alertDetail: DELTA_TWO_ALERT_DETAIL,
        createdAt: "2026-03-26T09:04:45.000Z",
        summaryUpdate: {
          turnCount: 6,
          alertCount: 3,
          lastAlertSeverity: "medium",
          updatedAt: "2026-03-26T09:05:00.000Z"
        }
      }
    ]
  };
}

function applyTurnDelta(scenario, sourceText) {
  const delta = scenario.deltas.shift();
  if (!delta) {
    throw new Error("No more bridge deltas configured for this smoke scenario.");
  }

  const userTurn = createRealtimeTurn({
    turnId: delta.userTurnId,
    turnIndex: delta.userTurnIndex,
    speaker: "user",
    sourceText,
    parentTurnId: scenario.turns[scenario.turns.length - 1]?.turnId || null,
    createdAt: delta.createdAt
  });
  const assistantTurn = createRealtimeTurn({
    turnId: delta.assistantTurnId,
    turnIndex: delta.assistantTurnIndex,
    speaker: "assistant",
    sourceText: delta.assistantReply,
    parentTurnId: delta.userTurnId,
    createdAt: delta.summaryUpdate.updatedAt
  });
  const alert = createRealtimeAlert({
    alertId: delta.alertId,
    turnId: delta.userTurnId,
    severity: delta.alertSeverity,
    issueKey: delta.alertIssueKey,
    title: delta.alertTitle,
    detail: delta.alertDetail,
    createdAt: delta.createdAt
  });

  scenario.turns = [...scenario.turns, userTurn, assistantTurn];
  scenario.alerts = [alert, ...scenario.alerts];
  scenario.summary = {
    ...scenario.summary,
    ...delta.summaryUpdate
  };

  return {
    userTurn,
    assistantTurn,
    alert
  };
}

async function installLiveBridgeRoutes(page, counters) {
  const scenario = createBridgeScenario();

  await page.route("**/api/v1/voice-profiles*", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          voiceProfileId: "voice-japan-1",
          displayName: "Japan Demo Voice",
          gender: "neutral",
          locale: "ja-JP",
          providerVoiceId: "demo-japan-1"
        }
      ])
    });
  });

  await page.route("**/api/v1/realtime/sessions/session-bridge-1", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(scenario.session)
    });
  });

  await page.route(
    "**/api/v1/realtime/sessions/session-bridge-1/summary",
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          sessionId: scenario.session.sessionId,
          transport: "webrtc",
          countryKey: scenario.session.countryKey,
          meetingType: scenario.session.meetingType,
          goal: scenario.session.goal,
          durationMinutes: scenario.session.durationMinutes,
          voiceStyle: scenario.session.voiceStyle,
          voiceProfileId: scenario.session.voiceProfileId,
          setupRevision: scenario.session.setupRevision,
          strategyForSetupRevision: scenario.session.strategyForSetupRevision,
          lastUserTurnAt:
            scenario.turns.filter((turn) => turn.speaker === "user").slice(-1)[0]
              ?.createdAt || null,
          lastAssistantTurnAt:
            scenario.turns
              .filter((turn) => turn.speaker === "assistant")
              .slice(-1)[0]?.createdAt || null,
          ...scenario.summary
        })
      });
    }
  );

  await page.route(
    "**/api/v1/realtime/sessions/session-bridge-1/turns",
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(scenario.turns)
      });
    }
  );

  await page.route(
    "**/api/v1/realtime/sessions/session-bridge-1/alerts",
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(scenario.alerts)
      });
    }
  );

  await page.route(
    "**/api/v1/realtime/sessions/session-bridge-1/turns/respond",
    async (route) => {
      counters.respondRequests += 1;
      const payload = route.request().postDataJSON() || {};
      const sourceText = payload.sourceText || TURN_ONE_INPUT;
      const exchange = applyTurnDelta(scenario, sourceText);

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          sessionId: scenario.session.sessionId,
          userTurn: exchange.userTurn,
          assistantTurn: exchange.assistantTurn,
          alerts: [exchange.alert],
          turnCount: scenario.summary.turnCount
        })
      });
    }
  );

  await page.route(
    "**/api/v1/realtime/sessions/session-bridge-1/end",
    async (route) => {
      counters.endRequests += 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...scenario.session,
          status: "ended",
        })
      });
    }
  );

  await page.route(
    "**/api/v1/reviews/from-realtime/session-bridge-1",
    async (route) => {
      counters.bridgeRequests += 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          reviewId: "review-bridge-1",
          sourceType: "realtime_session",
          countryKey: scenario.session.countryKey,
          meetingType: scenario.session.meetingType,
          goal: scenario.session.goal,
          createdAt: "2026-03-26T09:05:00.000Z",
          endedAt: "2026-03-26T09:05:00.000Z",
          status: "ready",
          overallAssessment: "promising",
          voiceStyle: scenario.session.voiceStyle,
          voiceProfileId: scenario.session.voiceProfileId,
          durationMinutes: scenario.session.durationMinutes,
          setupRevision: scenario.session.setupRevision,
          strategyForSetupRevision: scenario.session.strategyForSetupRevision,
          summary: {
            headline: REVIEW_HEADLINE,
            coachSummary: REVIEW_SUMMARY,
            nextStep: REVIEW_NEXT_STEP
          },
          metrics: {
            turnCount: scenario.summary.turnCount,
            alertCount: scenario.summary.alertCount,
            highSeverityCount: 1,
            mediumSeverityCount: 2,
            topIssueKeys: [
              "price_pressure",
              "soft_refusal_missed",
              "repetition_loop"
            ]
          },
          lines: scenario.turns.map((turn) => ({
            lineIndex: turn.turnIndex,
            speaker: turn.speaker,
            turnIndex: turn.turnIndex,
            text: turn.sourceText,
            alertIssueKeys:
              turn.turnId === "turn-2"
                ? ["soft_refusal_missed"]
                : turn.turnId === "turn-3"
                  ? ["price_pressure"]
                  : turn.turnId === "turn-5"
                    ? ["repetition_loop"]
                  : [],
            createdAt: turn.createdAt
          }))
        })
      });
    }
  );
}

test.beforeAll(async () => {
  smokeServer = startSmokeServer({
    host: SMOKE_HOST,
    port: SMOKE_PORT
  });
});

test.afterAll(async () => {
  stopSmokeServer(smokeServer);
});

test.beforeEach(async ({ page }) => {
  await waitForSmokeServer(page, BASE_URL);
});

test("live multi-turn alert aggregation bridges into stable review detail over unified HTTP smoke", async ({
  page
}) => {
  const diagnostics = trackClientDiagnostics(page);
  const counters = {
    respondRequests: 0,
    endRequests: 0,
    bridgeRequests: 0
  };

  await installSharedBootstrapRoutes(page);
  await installLiveBridgeRoutes(page, counters);
  await seedStoredState(page, seedLiveSessionState(), STORAGE_KEY);

  await page.goto(`${BASE_URL}/index.html#live`, {
    waitUntil: "domcontentloaded"
  });

  await expect(
    page.locator("button.nav-link.active[data-route='live']")
  ).toHaveCount(1);
  await expect(page.getByTestId("end-session-btn")).toBeVisible();
  await expect(page.locator(".meeting-focus-alert")).toContainText(
    INITIAL_ALERT_TITLE
  );
  await expect(page.locator(".meeting-focus-alert")).toContainText(
    INITIAL_ALERT_DETAIL
  );
  await expect(page.locator(".meeting-focus-alert")).toContainText("Turns 2");
  await expect(page.locator(".meeting-focus-alert")).toContainText("Alerts 1");
  await page.locator("#practiceInput").fill(TURN_ONE_INPUT);
  await page.getByTestId("evaluate-language-btn").click();
  await expect(page.locator(".meeting-focus-alert")).toContainText(
    DELTA_ONE_ALERT_TITLE
  );
  await expect(page.locator(".meeting-focus-alert")).toContainText(
    DELTA_ONE_ALERT_DETAIL
  );
  await expect(page.locator(".meeting-focus-alert")).toContainText("Turns 4");
  await expect(page.locator(".meeting-focus-alert")).toContainText("Alerts 2");
  await expect(page.locator(".transcript-scroll")).toContainText(TURN_ONE_INPUT);
  await expect(page.locator(".transcript-scroll")).toContainText(
    TURN_ONE_ASSISTANT_REPLY
  );
  await page.locator("#practiceInput").fill(TURN_TWO_INPUT);
  await page.getByTestId("evaluate-language-btn").click();
  await expect(page.locator(".meeting-focus-alert")).toContainText(
    DELTA_TWO_ALERT_TITLE
  );
  await expect(page.locator(".meeting-focus-alert")).toContainText(
    DELTA_TWO_ALERT_DETAIL
  );
  await expect(page.locator(".meeting-focus-alert")).toContainText("Turns 6");
  await expect(page.locator(".meeting-focus-alert")).toContainText("Alerts 3");
  await expect(page.locator(".transcript-scroll")).toContainText(TURN_TWO_INPUT);
  await expect(page.locator(".transcript-scroll")).toContainText(
    TURN_TWO_ASSISTANT_REPLY
  );

  await page.getByTestId("end-session-btn").click();

  await expect(
    page.locator("button.nav-link.active[data-route='review']")
  ).toHaveCount(1);
  await expect(
    page.locator("[data-testid='review-detail-container']")
  ).toContainText(REVIEW_HEADLINE);
  await expect(
    page.locator("[data-testid='review-detail-container']")
  ).toContainText(REVIEW_SUMMARY);
  await expect(
    page.locator("[data-testid='review-detail-container']")
  ).toContainText(REVIEW_NEXT_STEP);
  await expect(
    page.locator("[data-testid='review-detail-container'] .kpi-card").nth(0)
  ).toContainText("Turns");
  await expect(
    page.locator("[data-testid='review-detail-container'] .kpi-card").nth(0)
  ).toContainText("6");
  await expect(
    page.locator("[data-testid='review-detail-container'] .kpi-card").nth(1)
  ).toContainText("Alerts");
  await expect(
    page.locator("[data-testid='review-detail-container'] .kpi-card").nth(1)
  ).toContainText("3");
  await expect(
    page
      .locator("[data-testid='review-detail-container'] .inline-actions")
      .first()
      .locator(".route-pill.active")
  ).toHaveText(REVIEW_ISSUES);
  await expect(
    page.locator("[data-testid='review-detail-container']")
  ).toContainText(FINAL_REVIEW_LINE);
  await expect(
    page.locator("[data-testid='review-list-container']")
  ).toContainText("Japan");

  expect(counters.respondRequests).toBe(2);
  expect(counters.endRequests).toBe(1);
  expect(counters.bridgeRequests).toBe(1);

  assertNoClientDiagnostics(diagnostics);
});
