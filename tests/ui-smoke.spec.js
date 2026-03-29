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
const SMOKE_PORT = 4178;
const BASE_URL = buildBaseUrl(SMOKE_HOST, SMOKE_PORT);

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

async function installMockTurnstile(page) {
  await page.addInitScript(() => {
    globalThis.MIRO_TURNSTILE_SITE_KEY = "turnstile-site-key";
    const calls = {
      render: 0,
      reset: 0,
      remove: 0
    };

    globalThis.__turnstileMock = {
      calls,
      lastOptions: null
    };

    globalThis.turnstile = {
      render(container, options) {
        calls.render += 1;
        const widgetId = `widget-${calls.render}`;
        globalThis.__turnstileMock.lastOptions = options;
        container.innerHTML = `<div data-mock-turnstile="${widgetId}">Mock Turnstile ${widgetId}</div>`;
        return widgetId;
      },
      reset(widgetId) {
        calls.reset += 1;
        calls.lastReset = widgetId;
      },
      remove(widgetId) {
        calls.remove += 1;
        calls.lastRemove = widgetId;
      }
    };
  });
}

function createReviewFixture() {
  return {
    list: [
      {
        reviewId: "review-http-1",
        sourceType: "realtime_session",
        countryKey: "Japan",
        meetingType: "first_introduction",
        goal: "establish_trust_before_pricing",
        createdAt: "2026-03-20T09:00:00.000Z",
        endedAt: "2026-03-20T09:08:00.000Z",
        status: "ready",
        overallAssessment: "promising",
        topIssueKeys: ["soft_refusal_missed"]
      }
    ],
    detail: {
      reviewId: "review-http-1",
      sourceType: "realtime_session",
      countryKey: "Japan",
      meetingType: "first_introduction",
      goal: "establish_trust_before_pricing",
      createdAt: "2026-03-20T09:00:00.000Z",
      endedAt: "2026-03-20T09:08:00.000Z",
      status: "ready",
      overallAssessment: "promising",
      voiceStyle: "formal_measured",
      voiceProfileId: "voice-japan-1",
      durationMinutes: 8,
      setupRevision: 2,
      strategyForSetupRevision: 2,
      summary: {
        headline: "High trust opening",
        coachSummary: "You softened the ask at the right moment.",
        nextStep: "Keep giving more pause before pricing."
      },
      metrics: {
        turnCount: 6,
        alertCount: 1,
        highSeverityCount: 0,
        mediumSeverityCount: 1,
        topIssueKeys: ["soft_refusal_missed"]
      },
      lines: [
        {
          lineIndex: 1,
          speaker: "assistant",
          turnIndex: 1,
          text: "Thank you for taking the time to meet today.",
          alertIssueKeys: [],
          createdAt: "2026-03-20T09:00:00.000Z"
        },
        {
          lineIndex: 2,
          speaker: "user",
          turnIndex: 2,
          text: "We would like to understand your current priorities first.",
          alertIssueKeys: ["soft_refusal_missed"],
          createdAt: "2026-03-20T09:01:00.000Z"
        }
      ]
    }
  };
}

async function installReviewApiRoutes(page, fixture = createReviewFixture()) {
  await page.route("**/api/v1/reviews", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(fixture.list)
    });
  });

  await page.route("**/api/v1/reviews/review-http-1", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(fixture.detail)
    });
  });
}

async function installLiveApiRoutes(page) {
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
}

function seedAuthenticatedState(route) {
  return {
    loggedIn: true,
    activeRoute: route,
    pendingRoute: null,
    user: {
      name: "HTTP Smoke User",
      email: "smoke@miro.local",
      company: "Miro",
      role: "Director, Global Partnerships"
    }
  };
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

test("home page loads under unified HTTP smoke", async ({ page }) => {
  const diagnostics = trackClientDiagnostics(page);

  await page.goto(`${BASE_URL}/index.html#home`, {
    waitUntil: "domcontentloaded"
  });

  await expect(
    page.locator("button.nav-link.active[data-route='home']")
  ).toHaveCount(1);
  await expect(page.locator("#mainContent")).toContainText(
    "cross-border trust"
  );

  assertNoClientDiagnostics(diagnostics);
});

test("protected live and review routes stay gated when unauthenticated", async ({
  page
}) => {
  const diagnostics = trackClientDiagnostics(page);
  let protectedApiHit = false;

  await page.route("**/api/v1/**", async (route) => {
    protectedApiHit = true;
    await route.fulfill({
      status: 500,
      body: ""
    });
  });

  for (const route of ["review", "live"]) {
    await page.goto(`${BASE_URL}/index.html#${route}`, {
      waitUntil: "domcontentloaded"
    });
    await expect(
      page.locator("button.nav-link.active[data-route='home']")
    ).toHaveCount(1);
  }

  expect(protectedApiHit).toBe(false);
  assertNoClientDiagnostics(diagnostics);
});

test("auth modal shows disabled email fallback when Turnstile is not configured", async ({
  page
}) => {
  const diagnostics = trackClientDiagnostics(page);

  await page.goto(`${BASE_URL}/index.html#home`, {
    waitUntil: "domcontentloaded"
  });

  await page.locator("button[data-auth='register']").click();

  await expect(
    page.getByRole("button", { name: "Continue with Google" })
  ).toBeVisible();
  await expect(
    page.getByLabel("Work email")
  ).toBeVisible();
  await expect(
    page.getByLabel("Password")
  ).toBeVisible();
  await expect(
    page.locator("[data-turnstile-message]")
  ).toHaveText("Email is temporarily unavailable until Turnstile is configured.");
  await expect(
    page.getByRole("button", { name: "Create account with email" })
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Continue with Apple" })
  ).toHaveCount(0);

  assertNoClientDiagnostics(diagnostics);
});

test("auth modal remounts mocked Turnstile across mode switches and reopen", async ({
  page
}) => {
  const diagnostics = trackClientDiagnostics(page);

  await installMockTurnstile(page);
  await page.goto(`${BASE_URL}/index.html#home`, {
    waitUntil: "domcontentloaded"
  });

  await page.locator("button[data-auth='login']").click();

  await expect(page.locator("[data-mock-turnstile='widget-1']")).toBeVisible();
  await page.getByLabel("Work email").fill("user@example.com");
  await page.getByLabel("Password").fill("password123");
  await page.getByRole("button", { name: "Continue with email" }).click();
  await expect(page.locator("[data-auth-feedback]")).toHaveText(
    "Complete verification before continuing with email."
  );

  await page.locator("[data-auth-switch='register']").click();
  await expect(page.locator("[data-mock-turnstile='widget-2']")).toBeVisible();

  let calls = await page.evaluate(() => window.__turnstileMock.calls);
  expect(calls.render).toBe(2);
  expect(calls.reset).toBeGreaterThanOrEqual(1);
  expect(calls.remove).toBeGreaterThanOrEqual(1);

  await page.locator("#closeAuthBtn").click();
  await page.locator("button[data-auth='login']").click();
  await expect(page.locator("[data-mock-turnstile='widget-3']")).toBeVisible();

  calls = await page.evaluate(() => window.__turnstileMock.calls);
  expect(calls.render).toBe(3);
  expect(calls.reset).toBeGreaterThanOrEqual(2);
  expect(calls.remove).toBeGreaterThanOrEqual(2);

  assertNoClientDiagnostics(diagnostics);
});

test("review workspace loads over unified HTTP smoke", async ({ page }) => {
  const diagnostics = trackClientDiagnostics(page);

  await installSharedBootstrapRoutes(page);
  await installReviewApiRoutes(page);
  await seedStoredState(page, seedAuthenticatedState("review"), STORAGE_KEY);

  await page.goto(`${BASE_URL}/index.html#review`, {
    waitUntil: "domcontentloaded"
  });

  await expect(
    page.locator("button.nav-link.active[data-route='review']")
  ).toHaveCount(1);
  await expect(
    page.locator("[data-testid='review-list-container']")
  ).toContainText("Japan");
  await expect(
    page.locator("[data-testid='review-detail-container']")
  ).toContainText("You softened the ask at the right moment.");

  assertNoClientDiagnostics(diagnostics);
});

test("live workspace loads setup state over unified HTTP smoke", async ({
  page
}) => {
  const diagnostics = trackClientDiagnostics(page);

  await installSharedBootstrapRoutes(page);
  await installLiveApiRoutes(page);
  await seedStoredState(page, seedAuthenticatedState("live"), STORAGE_KEY);

  await page.goto(`${BASE_URL}/index.html#live`, {
    waitUntil: "domcontentloaded"
  });

  await expect(
    page.locator("button.nav-link.active[data-route='live']")
  ).toHaveCount(1);
  await expect(page.locator("#field-voice-profile")).toContainText(
    "Japan Demo Voice"
  );
  await expect(page.getByTestId("generate-strategy-btn")).toBeVisible();
  await expect(page.getByTestId("start-simulation-btn")).toBeVisible();

  assertNoClientDiagnostics(diagnostics);
});
