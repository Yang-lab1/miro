const fs = require("fs/promises");
const path = require("path");
const assert = require("assert/strict");
const { spawn } = require("child_process");
const { chromium } = require("@playwright/test");

const FRONTEND_ORIGIN =
  process.env.MIRO_FRONTEND_URL || "http://127.0.0.1:4175";
const BACKEND_ORIGIN =
  process.env.MIRO_BACKEND_URL || "http://127.0.0.1:8000";
const OUTPUT_DIR = path.resolve(
  __dirname,
  "..",
  "output",
  "playwright",
  "live-smoke"
);
const PROGRESS_LOG = path.join(OUTPUT_DIR, "progress.log");
const SUMMARY_PATH = path.join(OUTPUT_DIR, "run-summary.json");
const FRONTEND_SERVER_LOG = path.join(OUTPUT_DIR, "frontend-smoke-server.log");
const FRONTEND_SERVER_ERR_LOG = path.join(
  OUTPUT_DIR,
  "frontend-smoke-server.err.log"
);
const STORAGE_KEY = "miro-prototype-state-v4";
const TARGET_COUNTRY = "Japan";
const TARGET_VOICE_PROFILE_ID = "vp_japan_female_01";
const TARGET_RESPONSE =
  "We should align on process before discussing price in detail.";
const OPTIONAL_SCENARIOS = [
  "05-review-back-to-live",
  "06-soft-fallback-preserve-state"
];

async function main() {
  await fs.mkdir(OUTPUT_DIR, { recursive: true });
  await fs.writeFile(PROGRESS_LOG, "", "utf8");

  const coreScenarioNames = [
    "01-setup-refresh-restore",
    "02-active-session-refresh-restore",
    "03-back-to-setup-resume-live-session",
    "04-end-review-bridge-review"
  ];
  const summary = {
    startedAt: new Date().toISOString(),
    frontendOrigin: FRONTEND_ORIGIN,
    backendOrigin: BACKEND_ORIGIN,
    artifactsDir: OUTPUT_DIR,
    requiredScenarios: coreScenarioNames.length,
    optionalScenarios: OPTIONAL_SCENARIOS,
    scenarios: []
  };

  let browser = null;
  let context = null;
  let page = null;
  let frontendServerProcess = null;
  const diagnostics = createDiagnostics();

  try {
    await logProgress("ensuring frontend smoke server");
    frontendServerProcess = await ensureFrontendSmokeServer();
    await logProgress("frontend service ok");

    await logProgress("checking backend service");
    await ensureService(
      `${BACKEND_ORIGIN}/api/v1/learning/countries`,
      "backend"
    );
    await logProgress("backend service ok");

    const launched = await launchBrowser(summary);
    browser = launched.browser;
    summary.browser = launched.browserName;
    await logProgress(`browser ready via ${launched.browserName}`);

    context = await browser.newContext({
      viewport: { width: 1440, height: 1200 },
      ignoreHTTPSErrors: true,
      storageState: buildSmokeStorageState()
    });
    page = await context.newPage();
    attachDiagnostics(page, diagnostics);

    await bootstrapLive(page);
    await logProgress("live route bootstrapped");

    const runState = {
      sessionId: null,
      reviewId: null
    };

    await runScenario(summary, diagnostics, page, "01-setup-refresh-restore", async () => {
      await waitForVoiceProfilesReady(page);
      await selectVoiceProfile(page, TARGET_VOICE_PROFILE_ID);

      await expectState(
        page,
        (state, args) =>
          state?.currentSimulation?.voiceProfileId === args.voiceProfileId,
        "selected voice profile stored",
        { voiceProfileId: TARGET_VOICE_PROFILE_ID }
      );

      await click(page, '[data-testid="generate-strategy-btn"]');
      await expectState(
        page,
        (state) =>
          Boolean(state?.currentSimulation?.simulationId) &&
          (state.currentSimulation.strategies || []).length > 0 &&
          state.currentSimulation.setupRevision > 0,
        "strategy generation persisted"
      );

      await page.locator(".strategy-item").first().waitFor({ state: "visible" });

      const beforeRefresh = await readAppState(page);
      assert.ok(
        beforeRefresh.currentSimulation.simulationId,
        "simulationId should exist after Generate strategy"
      );
      assert.equal(
        beforeRefresh.currentSimulation.voiceProfileId,
        TARGET_VOICE_PROFILE_ID,
        "voiceProfileId should stay on the real backend profile"
      );

      await reloadPage(page, "scenario 01");
      await waitForSelector(page, "#setupForm", 30000, "setup form after refresh");
      await waitForVoiceProfilesReady(page);
      await expectState(
        page,
        (state, args) =>
          state?.currentSimulation?.simulationId === args.simulationId &&
          state.currentSimulation.phase === "setup" &&
          (state.currentSimulation.strategies || []).length > 0,
        "setup and strategy restored after refresh",
        { simulationId: beforeRefresh.currentSimulation.simulationId }
      );

      const afterRefresh = await readAppState(page);
      assert.equal(
        afterRefresh.currentSimulation.simulationId,
        beforeRefresh.currentSimulation.simulationId,
        "simulationId should survive setup refresh"
      );
      assert.equal(
        afterRefresh.currentSimulation.voiceProfileId,
        TARGET_VOICE_PROFILE_ID,
        "voiceProfileId should survive setup refresh"
      );
    });

    await runScenario(
      summary,
      diagnostics,
      page,
      "02-active-session-refresh-restore",
      async () => {
        await click(page, '[data-testid="start-simulation-btn"]');
        await maybeContinuePrecheck(page);
        await waitForSessionPhase(page);

        await expectState(
          page,
          (state) =>
            state?.currentSimulation?.realtimeStatus === "active" &&
            Boolean(state.currentSimulation.sessionId),
          "active session stored"
        );

        const afterStart = await readAppState(page);
        runState.sessionId = afterStart.currentSimulation.sessionId;
        assert.ok(runState.sessionId, "sessionId should exist after Start simulation");

        await page.locator("#practiceInput").fill(TARGET_RESPONSE);
        await click(page, '[data-testid="evaluate-language-btn"]');
        await expectState(
          page,
          (state) =>
            (state?.currentSimulation?.transcript || []).length >= 2 &&
            (state.currentSimulation.sessionSummary?.turnCount || 0) >= 2 &&
            state.currentSimulation.realtimeStatus === "active",
          "turn exchange persisted after evaluate"
        );

        const beforeRefresh = await readAppState(page);
        assert.equal(
          beforeRefresh.currentSimulation.sessionId,
          runState.sessionId,
          "sessionId should remain stable before refresh"
        );
        assert.equal(
          beforeRefresh.currentSimulation.realtimeStatus,
          "active",
          "session must be active before refresh"
        );

        await reloadPage(page, "scenario 02");
        await waitForSessionPhase(page);
        await expectState(
          page,
          (state, args) =>
            state?.currentSimulation?.sessionId === args.sessionId &&
            state.currentSimulation.realtimeStatus === "active" &&
            (state.currentSimulation.transcript || []).length >= 2 &&
            (state.currentSimulation.alerts || []).length >= 1 &&
            (state.currentSimulation.sessionSummary?.turnCount || 0) >= 2,
          "active session restored after refresh",
          { sessionId: runState.sessionId }
        );

        const afterRefresh = await readAppState(page);
        assert.equal(
          afterRefresh.currentSimulation.sessionId,
          runState.sessionId,
          "same sessionId should survive active refresh"
        );
      }
    );

    await runScenario(
      summary,
      diagnostics,
      page,
      "03-back-to-setup-resume-live-session",
      async () => {
        await click(page, '[data-testid="back-to-setup-btn"]');
        await waitForSelector(page, "#setupForm", 30000, "setup form after back to setup");
        await waitForSelector(
          page,
          '[data-testid="live-action-resume-live-session"]',
          30000,
          "resume live session action"
        );

        const setupState = await readAppState(page);
        assert.equal(
          setupState.currentSimulation.sessionId,
          runState.sessionId,
          "sessionId should remain linked after Back to setup"
        );
        assert.equal(
          setupState.currentSimulation.realtimeStatus,
          "active",
          "realtimeStatus should remain active after Back to setup"
        );

        await click(page, '[data-testid="live-action-resume-live-session"]');
        await waitForSessionPhase(page);
        await expectState(
          page,
          (state, args) =>
            state?.currentSimulation?.sessionId === args.sessionId &&
            state.currentSimulation.realtimeStatus === "active" &&
            (state.currentSimulation.transcript || []).length >= 2 &&
            (state.currentSimulation.sessionSummary?.turnCount || 0) >= 2,
          "hidden active session resumed",
          { sessionId: runState.sessionId }
        );
      }
    );

    await runScenario(
      summary,
      diagnostics,
      page,
      "04-end-review-bridge-review",
      async () => {
        const apiTrafficStart = diagnostics.apiTraffic.length;

        await click(page, '[data-testid="end-session-btn"]');
        await waitForSelector(
          page,
          '[data-testid="review-detail-container"]',
          30000,
          "review detail after bridge"
        );

        await expectState(
          page,
          (state) =>
            Boolean(state?.currentSimulation?.recentReviewId) &&
            Boolean(state.selectedReviewId),
          "reviewId persisted after review bridge"
        );

        const reviewState = await readAppState(page);
        runState.reviewId = reviewState.currentSimulation.recentReviewId;
        assert.ok(runState.reviewId, "reviewId should exist after review bridge");
        assert.equal(
          reviewState.currentSimulation.lastCompletionStatus,
          "ended",
          "completion status should be ended after bridge"
        );
        assert.equal(
          reviewState.currentSimulation.sessionId,
          null,
          "sessionId should be cleared after end"
        );
        assert.equal(
          reviewState.currentSimulation.realtimeStatus,
          null,
          "realtimeStatus should be cleared after end"
        );
        assert.equal(
          reviewState.selectedReviewId,
          runState.reviewId,
          "selectedReviewId should match recentReviewId after bridge"
        );

        const bridgeCalls = diagnostics.apiTraffic.slice(apiTrafficStart).filter((entry) =>
          entry.url.includes("/api/v1/reviews/from-realtime/")
        );
        assert.ok(
          bridgeCalls.some((entry) => entry.status === 200),
          "review bridge must hit the real backend successfully"
        );

        const reviewDetailText = await page
          .locator('[data-testid="review-detail-container"]')
          .innerText();
        assert.ok(
          !/Live review API is unavailable/i.test(reviewDetailText),
          "review page should not be showing fallback copy after bridge"
        );

        await captureScreenshot(
          page,
          path.join(OUTPUT_DIR, "04-review-opened.png")
        );
      }
    );

    await runScenario(
      summary,
      diagnostics,
      page,
      "05-review-back-to-live",
      async () => {
        await click(page, '[data-route="live"]');
        await waitForSelector(page, "#setupForm", 30000, "live setup after review backflow");
        await waitForSelector(
          page,
          '[data-testid="live-action-open-latest-review"]',
          30000,
          "open latest review action"
        );

        await expectState(
          page,
          (state, args) =>
            state?.activeRoute === "live" &&
            state.currentSimulation.phase === "setup" &&
            state.currentSimulation.sessionId === null &&
            state.currentSimulation.realtimeStatus === null &&
            state.currentSimulation.lastCompletionStatus === "ended" &&
            state.currentSimulation.recentReviewId === args.reviewId &&
            (state.currentSimulation.strategies || []).length > 0,
          "review backflow restored setup state",
          { reviewId: runState.reviewId }
        );

        const liveState = await readAppState(page);
        assert.equal(
          liveState.currentSimulation.recentReviewId,
          runState.reviewId,
          "recentReviewId should survive the return from Review Center"
        );
        assert.equal(
          liveState.currentSimulation.sessionId,
          null,
          "sessionId should stay cleared after returning from Review Center"
        );
      }
    );

    await runScenario(
      summary,
      diagnostics,
      page,
      "06-soft-fallback-preserve-state",
      async () => {
        const beforeFailureState = await readAppState(page);
        const failOnce = await installOneShotVoiceProfilesFailure(
          page,
          "Smoke forced voice profiles failure."
        );

        try {
          await reloadPage(page, "scenario 06");
          await waitForSelector(page, "#setupForm", 30000, "setup form after forced voice profile failure");
          await waitForSelector(
            page,
            '[data-testid="live-action-retry-voice-profiles"]',
            30000,
            "retry voice profiles action after soft fallback"
          );

          await expectState(
            page,
            (state, args) =>
              state?.currentSimulation?.simulationId === args.simulationId &&
              state.currentSimulation.sessionId === args.sessionId &&
              state.currentSimulation.recentReviewId === args.reviewId &&
              state.currentSimulation.voiceProfileId === args.voiceProfileId &&
              (state.currentSimulation.strategies || []).length === args.strategyCount &&
              state.currentSimulation.phase === "setup",
            "soft fallback preserved recoverable live state",
            {
              simulationId: beforeFailureState.currentSimulation.simulationId,
              sessionId: beforeFailureState.currentSimulation.sessionId,
              reviewId: beforeFailureState.currentSimulation.recentReviewId,
              voiceProfileId: beforeFailureState.currentSimulation.voiceProfileId,
              strategyCount: (beforeFailureState.currentSimulation.strategies || []).length
            }
          );

          await click(page, '[data-testid="live-action-retry-voice-profiles"]');
          await waitForVoiceProfilesReady(page);
          await expectState(
            page,
            (state, args) =>
              state?.currentSimulation?.voiceProfileId === args.voiceProfileId &&
              state.currentSimulation.sessionId === args.sessionId &&
              state.currentSimulation.recentReviewId === args.reviewId &&
              state.currentSimulation.phase === "setup",
            "real voice profiles restored after retry",
            {
              voiceProfileId: beforeFailureState.currentSimulation.voiceProfileId,
              sessionId: beforeFailureState.currentSimulation.sessionId,
              reviewId: beforeFailureState.currentSimulation.recentReviewId
            }
          );
        } finally {
          await failOnce();
        }
      }
    );

    const passedScenarioNames = summary.scenarios
      .filter((item) => item.passed)
      .map((item) => item.name);
    summary.coreStableScenarioCount = coreScenarioNames.filter((name) =>
      passedScenarioNames.includes(name)
    ).length;
    summary.optionalStableScenarioCount = OPTIONAL_SCENARIOS.filter((name) =>
      passedScenarioNames.includes(name)
    ).length;
    summary.corePassed =
      summary.coreStableScenarioCount === coreScenarioNames.length;
    summary.optionalPassed =
      summary.optionalStableScenarioCount === OPTIONAL_SCENARIOS.length;
    summary.passed = summary.corePassed && summary.optionalPassed;
    summary.finishedAt = new Date().toISOString();
    summary.stableScenarioCount = passedScenarioNames.length;
    summary.unstableScenarioCount =
      coreScenarioNames.length +
      OPTIONAL_SCENARIOS.length -
      summary.stableScenarioCount;
    summary.remainingOptionalScenarios = OPTIONAL_SCENARIOS.filter(
      (name) => !passedScenarioNames.includes(name)
    );

    await fs.writeFile(SUMMARY_PATH, JSON.stringify(summary, null, 2), "utf8");

    for (const scenario of summary.scenarios) {
      console.log(`PASS ${scenario.name}`);
    }
    console.log(`PASS core smoke stable: ${summary.coreStableScenarioCount}/${summary.requiredScenarios}`);
    if (summary.optionalPassed) {
      console.log(
        `PASS optional smoke stable: ${summary.optionalStableScenarioCount}/${OPTIONAL_SCENARIOS.length}`
      );
    }
  } catch (error) {
    summary.passed = false;
    summary.finishedAt = new Date().toISOString();
    summary.error = {
      message: error.message,
      stack: error.stack
    };
    const passedScenarioNames = summary.scenarios
      .filter((item) => item.passed)
      .map((item) => item.name);
    summary.stableScenarioCount = passedScenarioNames.length;
    summary.coreStableScenarioCount = coreScenarioNames.filter((name) =>
      passedScenarioNames.includes(name)
    ).length;
    summary.optionalStableScenarioCount = OPTIONAL_SCENARIOS.filter((name) =>
      passedScenarioNames.includes(name)
    ).length;
    summary.corePassed =
      summary.coreStableScenarioCount === coreScenarioNames.length;
    summary.optionalPassed =
      summary.optionalStableScenarioCount === OPTIONAL_SCENARIOS.length;
    summary.unstableScenarioCount =
      coreScenarioNames.length +
      OPTIONAL_SCENARIOS.length -
      summary.stableScenarioCount;
    summary.remainingOptionalScenarios = OPTIONAL_SCENARIOS.filter(
      (name) => !passedScenarioNames.includes(name)
    );

    if (page) {
      try {
        await captureFailureArtifacts(page, diagnostics, "bootstrap");
      } catch (captureError) {
        await fs.writeFile(
          path.join(OUTPUT_DIR, "bootstrap-capture-error.txt"),
          captureError.stack || captureError.message,
          "utf8"
        );
      }
    }

    await fs.writeFile(SUMMARY_PATH, JSON.stringify(summary, null, 2), "utf8");
    console.error(`FAIL ${error.message}`);
    process.exitCode = 1;
  } finally {
    if (context) {
      try {
        await context.close();
      } catch {}
    }
    if (browser) {
      try {
        await browser.close();
      } catch {}
    }
    if (frontendServerProcess) {
      try {
        frontendServerProcess.kill("SIGTERM");
      } catch {}
    }
  }
}

function createDiagnostics() {
  return {
    apiTraffic: [],
    consoleMessages: [],
    pageErrors: []
  };
}

function attachDiagnostics(page, diagnostics) {
  page.on("console", (message) => {
    diagnostics.consoleMessages.push({
      type: message.type(),
      text: message.text()
    });
    trimDiagnostics(diagnostics.consoleMessages);
  });

  page.on("pageerror", (error) => {
    diagnostics.pageErrors.push({
      message: error.message,
      stack: error.stack
    });
    trimDiagnostics(diagnostics.pageErrors);
  });

  page.on("response", async (response) => {
    if (!response.url().includes("/api/v1/")) return;

    diagnostics.apiTraffic.push({
      url: response.url(),
      status: response.status(),
      method: response.request().method()
    });
    trimDiagnostics(diagnostics.apiTraffic);
  });
}

function trimDiagnostics(bucket, limit = 250) {
  if (bucket.length > limit) {
    bucket.splice(0, bucket.length - limit);
  }
}

async function launchBrowser(summary) {
  const attempts = buildBrowserAttempts();
  const launchErrors = [];

  for (const attempt of attempts) {
    try {
      const browser = await attempt.launch();
      return { browser, browserName: attempt.name };
    } catch (error) {
      launchErrors.push({
        name: attempt.name,
        message: error.message
      });
      await logProgress(`browser launch failed ${attempt.name}: ${error.message}`);
    }
  }

  summary.launchErrors = launchErrors;
  throw new Error(
    `Unable to launch a stable Playwright browser. Attempts: ${launchErrors
      .map((item) => `${item.name}: ${item.message}`)
      .join(" | ")}`
  );
}

function buildBrowserAttempts() {
  return [
    {
      name: "chromium-default",
      launch: () => chromium.launch({ headless: true })
    },
    {
      name: "msedge-channel",
      launch: () => chromium.launch({ channel: "msedge", headless: true })
    }
  ];
}

async function bootstrapLive(page) {
  await logProgress("bootstrap goto live route");
  await page.goto(`${FRONTEND_ORIGIN}/`, {
    waitUntil: "commit"
  });
  await waitForSelector(page, "#setupForm", 30000, "live setup form");
  const bootstrapSnapshot = await buildBootstrapSnapshot(page);
  await logProgress(`bootstrap snapshot ${JSON.stringify(bootstrapSnapshot)}`);
  if (!bootstrapSnapshot.setupCount) {
    throw new Error("Bootstrap did not render the live setup form.");
  }
  await expectState(
    page,
    (state) => state?.loggedIn === true && state.activeRoute === "live",
    "logged in live route state"
  );
}

async function buildBootstrapSnapshot(page) {
  const state = await readAppState(page);
  return {
    url: page.url(),
    hash: new URL(page.url()).hash,
    setupCount: 1,
    setupVisible: true,
    bodyPreview: "",
    state
  };
}

function buildSmokeStorageState() {
  return {
    cookies: [],
    origins: [
      {
        origin: FRONTEND_ORIGIN,
        localStorage: [
          {
            name: STORAGE_KEY,
            value: JSON.stringify(createSmokeSeedState())
          }
        ]
      }
    ]
  };
}

function createSmokeSeedState() {
  return {
    lang: "en",
    activeRoute: "live",
    loggedIn: true,
    authOpen: false,
    authMode: "login",
    pendingRoute: null
  };
}

async function runScenario(summary, diagnostics, page, name, fn) {
  const record = {
    name,
    startedAt: new Date().toISOString()
  };
  summary.scenarios.push(record);
  console.log(`RUN  ${name}`);
  await logProgress(`scenario start ${name}`);

  try {
    await fn();
    record.passed = true;
    record.finishedAt = new Date().toISOString();
    await logProgress(`scenario pass ${name}`);
  } catch (error) {
    record.passed = false;
    record.finishedAt = new Date().toISOString();
    record.error = {
      message: error.message,
      stack: error.stack
    };
    await logProgress(`scenario fail ${name}: ${error.message}`);
    await captureFailureArtifacts(
      page,
      diagnostics,
      name.replace(/[^a-z0-9-]+/gi, "_").toLowerCase()
    );
    throw error;
  }
}

async function ensureService(url, label) {
  let response;
  try {
    response = await fetch(url);
  } catch (error) {
    throw new Error(`${label} service is unreachable at ${url}: ${error.message}`);
  }

  if (!response.ok) {
    throw new Error(
      `${label} service at ${url} returned ${response.status}.`
    );
  }
}

async function ensureFrontendSmokeServer() {
  const existing = await fetchSmokeHealth();
  if (existing?.ok) {
    return null;
  }

  await fs.writeFile(FRONTEND_SERVER_LOG, "", "utf8");
  await fs.writeFile(FRONTEND_SERVER_ERR_LOG, "", "utf8");

  const serverScript = path.resolve(__dirname, "live-smoke-server.js");
  const child = spawn(process.execPath, [serverScript], {
    cwd: path.resolve(__dirname, ".."),
    env: {
      ...process.env,
      MIRO_SMOKE_HOST: "127.0.0.1",
      MIRO_SMOKE_PORT: "4175",
      MIRO_BACKEND_URL: BACKEND_ORIGIN
    },
    stdio: [
      "ignore",
      "pipe",
      "pipe"
    ]
  });

  child.stdout.on("data", async (chunk) => {
    await fs.appendFile(FRONTEND_SERVER_LOG, chunk.toString(), "utf8");
  });
  child.stderr.on("data", async (chunk) => {
    await fs.appendFile(FRONTEND_SERVER_ERR_LOG, chunk.toString(), "utf8");
  });

  const started = await waitForSmokeHealth(15000);
  if (!started) {
    throw new Error(
      `frontend smoke server did not become healthy at ${FRONTEND_ORIGIN}`
    );
  }
  return child;
}

async function fetchSmokeHealth() {
  try {
    const response = await fetch(`${FRONTEND_ORIGIN}/__smoke_health`);
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

async function waitForSmokeHealth(timeoutMs) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    const health = await fetchSmokeHealth();
    if (health?.ok && health.server === "miro-live-smoke-proxy") {
      return true;
    }
    await delay(250);
  }
  return false;
}

async function waitForVoiceProfilesReady(page, timeout = 60000) {
  await waitForSelector(
    page,
    `#field-voice-profile option[value="${TARGET_VOICE_PROFILE_ID}"]`,
    timeout,
    "voice profiles to load"
  );
}

async function selectVoiceProfile(page, voiceProfileId) {
  await page.selectOption("#field-voice-profile", voiceProfileId);
}

async function click(page, selector) {
  await waitForSelector(page, selector, 20000, `click target ${selector}`);
  await page.locator(selector).first().click({ noWaitAfter: true });
}

async function maybeContinuePrecheck(page) {
  const startTime = Date.now();
  while (Date.now() - startTime < 15000) {
    const continueButton = page.locator("#precheckContinueBtn");
    if (await continueButton.count()) {
      if (await continueButton.isVisible()) {
        await continueButton.click();
        return;
      }
    }

    if (await page.locator("#practiceInput").count()) {
      if (await page.locator("#practiceInput").first().isVisible()) {
        return;
      }
    }

    await page.waitForTimeout(250);
  }
}

async function waitForSessionPhase(page) {
  await waitForSelector(page, "#practiceInput", 60000, "live session composer");
  await expectState(
    page,
    (state) =>
      state?.currentSimulation?.phase === "session" &&
      state.currentSimulation.realtimeStatus === "active" &&
      Boolean(state.currentSimulation.sessionId),
    "active session phase"
  );
}

async function waitForSelector(page, selector, timeout, description) {
  await page.waitForSelector(selector, {
    timeout,
    state: "attached"
  });
  await logProgress(`selector ok ${description}`);
}

async function readAppState(page) {
  const storage = await page.context().storageState();
  const origin = storage.origins.find((entry) => entry.origin === FRONTEND_ORIGIN);
  if (!origin) return null;
  const item = origin.localStorage.find((entry) => entry.name === STORAGE_KEY);
  return item ? JSON.parse(item.value) : null;
}

async function expectState(page, predicate, description, args = {}, timeout = 60000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeout) {
    const state = await readAppState(page);
    if (state && predicate(state, args)) {
      await logProgress(`state ok ${description}`);
      return;
    }
    await page.waitForTimeout(250);
  }

  const latestState = await readAppState(page);
  throw new Error(
    `Timed out waiting for state ${description}. Latest state: ${JSON.stringify(
      latestState
    )}`
  );
}

async function reloadPage(page, description) {
  await logProgress(`reload ${description}`);
  await page.reload({ waitUntil: "commit" });
  await logProgress(`state ok ${description}`);
}

async function installOneShotVoiceProfilesFailure(
  page,
  message = "Smoke forced voice profiles failure."
) {
  const pattern = /\/api\/v1\/voice-profiles(\?|$)/;
  let used = false;

  const handler = async (route) => {
    if (used) {
      await route.continue();
      return;
    }

    used = true;
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "smoke_forced_failure",
          message
        }
      })
    });
  };

  await page.route(pattern, handler);

  return async () => {
    await page.unroute(pattern, handler);
  };
}

async function captureScreenshot(page, filePath) {
  await page.screenshot({
    path: filePath,
    fullPage: true
  });
}

async function captureFailureArtifacts(page, diagnostics, slug) {
  const screenshotPath = path.join(OUTPUT_DIR, `${slug}-failure.png`);
  const htmlPath = path.join(OUTPUT_DIR, `${slug}-failure.html`);
  const statePath = path.join(OUTPUT_DIR, `${slug}-state.json`);
  const consolePath = path.join(OUTPUT_DIR, `${slug}-console.json`);

  await safeCapture(`${slug}-screenshot`, () =>
    captureScreenshot(page, screenshotPath)
  );
  await safeCapture(`${slug}-html`, async () => {
    await fs.writeFile(htmlPath, await page.content(), "utf8");
  });
  await safeCapture(`${slug}-state`, async () => {
    await fs.writeFile(
      statePath,
      JSON.stringify(await readAppState(page), null, 2),
      "utf8"
    );
  });
  await safeCapture(`${slug}-console`, async () => {
    await fs.writeFile(consolePath, JSON.stringify(diagnostics, null, 2), "utf8");
  });
}

async function safeCapture(label, work) {
  try {
    await work();
  } catch (error) {
    await fs.writeFile(
      path.join(OUTPUT_DIR, `${label}-error.txt`),
      error.stack || error.message,
      "utf8"
    );
  }
}

async function logProgress(message) {
  const line = `[${new Date().toISOString()}] ${message}\n`;
  await fs.appendFile(PROGRESS_LOG, line, "utf8");
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

main();
