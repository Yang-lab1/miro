const { test, expect } = require("@playwright/test");
const {
  STORAGE_KEY,
  buildBaseUrl,
  seedStoredState,
  startSmokeServer,
  stopSmokeServer,
  waitForSmokeServer
} = require("./helpers/http-smoke");

const SMOKE_HOST = "127.0.0.1";
const SMOKE_PORT = 4177;
const BASE_URL = buildBaseUrl(SMOKE_HOST, SMOKE_PORT);

let smokeServer = null;

function createBillingState() {
  return {
    account: {
      currentPlanKey: "plus",
      creditBalance: 1500,
      renewalAt: "2026-04-25T09:00:00.000Z",
      currencyCode: "USD"
    },
    currentPlan: {
      planId: "plan-plus",
      planKey: "plus",
      displayName: "Plus",
      billingCycle: "monthly",
      currencyCode: "USD",
      amountValue: 20,
      isCurrent: true
    },
    allowedTopUpAmounts: [500, 1500, 3000]
  };
}

function createHardwareState() {
  return {
    deviceId: "device-demo-1",
    deviceName: "Miro Pin 01",
    connected: false,
    connectionState: "disconnected",
    transferState: "idle",
    firmwareVersion: "1.4.2",
    versionPath: "1.3.8 -> 1.4.2",
    batteryPercent: 73,
    lastSyncAt: "2026-03-24T09:00:00.000Z",
    capturedSessions: 3,
    vibrationEvents: 2
  };
}

async function installWorkspaceBootstrapRoutes(page, options = {}) {
  const {
    billingSummary = createBillingState(),
    hardwareDevice = createHardwareState(),
    billingSummaryError = null,
    hardwareDevicesError = null,
    onBillingSummaryRequest = null,
    onHardwareDevicesRequest = null,
    onBillingPlansRequest = null,
    onHardwareLogsRequest = null,
    onHardwareSyncRecordsRequest = null
  } = options;

  await page.route("**/api/v1/billing/summary", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }
    if (onBillingSummaryRequest) onBillingSummaryRequest();
    if (billingSummaryError) {
      await route.fulfill({
        status: billingSummaryError.status || 500,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: billingSummaryError.code || "billing_summary_failed",
            message:
              billingSummaryError.message ||
              "Unable to load billing summary."
          }
        })
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(billingSummary)
    });
  });

  await page.route("**/api/v1/hardware/devices", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }
    if (onHardwareDevicesRequest) onHardwareDevicesRequest();
    if (hardwareDevicesError) {
      await route.fulfill({
        status: hardwareDevicesError.status || 500,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: hardwareDevicesError.code || "hardware_devices_failed",
            message:
              hardwareDevicesError.message ||
              "Unable to load hardware devices."
          }
        })
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([hardwareDevice])
    });
  });

  await page.route("**/api/v1/billing/plans", async (route) => {
    if (onBillingPlansRequest) onBillingPlansRequest();
    await route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "unexpected_billing_plans_request",
          message: "Billing plans should not be fetched during bootstrap."
        }
      })
    });
  });

  await page.route("**/api/v1/hardware/devices/*/logs", async (route) => {
    if (onHardwareLogsRequest) onHardwareLogsRequest();
    await route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "unexpected_hardware_logs_request",
          message:
            "Hardware logs should not be fetched during bootstrap."
        }
      })
    });
  });

  await page.route(
    "**/api/v1/hardware/devices/*/sync-records",
    async (route) => {
      if (onHardwareSyncRecordsRequest) onHardwareSyncRecordsRequest();
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: "unexpected_hardware_sync_records_request",
            message:
              "Hardware sync records should not be fetched during bootstrap."
          }
        })
      });
    }
  );
}

function seedAuthenticatedState(route = "home") {
  return {
    loggedIn: true,
    activeRoute: route,
    pendingRoute: null,
    pricingSelection: "free",
    user: {
      name: "Bootstrap Demo User",
      email: "bootstrap@miro.local",
      company: "Miro",
      role: "Director, Global Partnerships",
      plan: "Enterprise Pilot",
      balance: 4800,
      renewal: "2026-04-12"
    },
    hardware: {
      deviceId: "stale-device",
      deviceName: "Stale Pin",
      connected: true,
      connectionState: "connected",
      transferState: "warning",
      transferHealth: "warning",
      firmware: "1.0.0",
      firmwareVersion: "1.0.0",
      versionPath: "1.0.0",
      battery: 12,
      batteryPercent: 12,
      lastSync: "2026-03-01T09:00:00.000Z",
      lastSyncAt: "2026-03-01T09:00:00.000Z",
      capturedSessions: 99,
      vibrationEvents: 44,
      logs: [
        {
          id: "stale-log",
          logId: "stale-log",
          title: "Stale actor event",
          detail: "Should not remain after logout.",
          time: "2026-03-01T09:00:00.000Z",
          createdAt: "2026-03-01T09:00:00.000Z"
        }
      ],
      syncRecords: [
        {
          id: "stale-sync",
          syncRecordId: "stale-sync",
          title: "Stale actor sync",
          detail: "Should not remain after logout.",
          time: "2026-03-01T09:00:00.000Z",
          createdAt: "2026-03-01T09:00:00.000Z",
          status: "warning"
        }
      ]
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

test("workspace bootstrap hydrates shared billing and hardware snapshots without visiting pricing or hardware", async ({
  page
}) => {
  let billingSummaryRequests = 0;
  let hardwareDevicesRequests = 0;
  let billingPlansRequests = 0;
  let hardwareLogsRequests = 0;
  let hardwareSyncRecordsRequests = 0;

  await installWorkspaceBootstrapRoutes(page, {
    onBillingSummaryRequest: () => {
      billingSummaryRequests += 1;
    },
    onHardwareDevicesRequest: () => {
      hardwareDevicesRequests += 1;
    },
    onBillingPlansRequest: () => {
      billingPlansRequests += 1;
    },
    onHardwareLogsRequest: () => {
      hardwareLogsRequests += 1;
    },
    onHardwareSyncRecordsRequest: () => {
      hardwareSyncRecordsRequests += 1;
    }
  });

  await seedStoredState(page, seedAuthenticatedState("home"), STORAGE_KEY);

  await page.goto(`${BASE_URL}/index.html#home`, {
    waitUntil: "domcontentloaded"
  });

  await expect(
    page.locator("[data-testid='home-captured-sessions']")
  ).toHaveText("3");

  await page.locator("button.nav-link[data-route='settings']").click();
  await expect(page.locator("[data-testid='settings-balance']")).toContainText(
    "1,500"
  );
  await expect(page.locator("[data-testid='settings-plan']")).toContainText(
    "Plus"
  );
  await expect(page.locator("[data-testid='settings-renewal']")).toContainText(
    "2026"
  );
  await expect(
    page.locator("[data-testid='settings-security-activity']")
  ).toContainText("2026");

  expect(billingSummaryRequests).toBeGreaterThan(0);
  expect(hardwareDevicesRequests).toBeGreaterThan(0);
  expect(billingPlansRequests).toBe(0);
  expect(hardwareLogsRequests).toBe(0);
  expect(hardwareSyncRecordsRequests).toBe(0);

  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.locator("[data-testid='settings-balance']")).toContainText(
    "1,500"
  );
  await expect(page.locator("[data-testid='settings-plan']")).toContainText(
    "Plus"
  );
});

test("logout clears protected shared billing and hardware snapshots after bootstrap", async ({
  page
}) => {
  await installWorkspaceBootstrapRoutes(page);

  await seedStoredState(page, seedAuthenticatedState("settings"), STORAGE_KEY);

  await page.goto(`${BASE_URL}/index.html#settings`, {
    waitUntil: "domcontentloaded"
  });

  await expect(page.locator("[data-testid='settings-plan']")).toContainText(
    "Plus"
  );

  await page.locator("[data-testid='settings-logout']").click();
  await expect(
    page.locator("button.nav-link.active[data-route='home']")
  ).toHaveCount(1);

  const storedState = await page.evaluate((storageKey) => {
    return JSON.parse(localStorage.getItem(storageKey));
  }, STORAGE_KEY);

  expect(storedState.loggedIn).toBe(false);
  expect(storedState.user.plan).toBe("Free");
  expect(storedState.user.balance).toBe(0);
  expect(storedState.user.renewal).toBeNull();
  expect(storedState.hardware.deviceId).toBeNull();
});

test("session-expired bootstrap hydration clears protected snapshots and returns to public workspace", async ({
  page
}) => {
  await installWorkspaceBootstrapRoutes(page, {
    billingSummaryError: {
      status: 401,
      code: "auth_token_required",
      message: "Your session expired."
    }
  });

  await seedStoredState(page, seedAuthenticatedState("settings"), STORAGE_KEY);

  await page.goto(`${BASE_URL}/index.html#settings`, {
    waitUntil: "domcontentloaded"
  });

  await expect(
    page.locator("button.nav-link.active[data-route='home']")
  ).toHaveCount(1);

  const storedState = await page.evaluate((storageKey) => {
    return JSON.parse(localStorage.getItem(storageKey));
  }, STORAGE_KEY);

  expect(storedState.loggedIn).toBe(false);
  expect(storedState.user.balance).toBe(0);
  expect(storedState.hardware.deviceId).toBeNull();
});

test("workspace bootstrap degrades safely when one snapshot source fails", async ({
  page
}) => {
  await installWorkspaceBootstrapRoutes(page, {
    hardwareDevicesError: {
      status: 500,
      code: "hardware_devices_failed",
      message: "Temporary hardware issue."
    }
  });

  await seedStoredState(page, seedAuthenticatedState("settings"), STORAGE_KEY);

  await page.goto(`${BASE_URL}/index.html#settings`, {
    waitUntil: "domcontentloaded"
  });

  await expect(page.locator("[data-testid='settings-plan']")).toContainText(
    "Plus"
  );
  await expect(page.locator("[data-testid='settings-balance']")).toContainText(
    "1,500"
  );
  await expect(page.locator("h1")).toContainText("Bootstrap Demo User");
});
