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
const SMOKE_PORT = 4175;
const BASE_URL = buildBaseUrl(SMOKE_HOST, SMOKE_PORT);

let smokeServer = null;

function createDemoState() {
  return {
    device: {
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
    },
    logs: [
      {
        logId: "log-demo-2",
        eventType: "connection",
        severity: "info",
        title: "Demo device initialized",
        detail: "The simulated pin is ready for product playback.",
        reviewId: null,
        createdAt: "2026-03-24T08:59:00.000Z"
      }
    ],
    syncRecords: [
      {
        syncRecordId: "sync-demo-1",
        syncKind: "upload",
        status: "warning",
        title: "Buyer visit upload",
        detail: "Demo sync history retained for UI replay.",
        reviewId: null,
        createdAt: "2026-03-24T08:58:00.000Z"
      }
    ]
  };
}

async function installHardwareApiRoutes(page, serverState, options = {}) {
  const {
    connectError = null,
    disconnectError = null,
    syncError = null,
    onDevicesRequest = null
  } = options;

  await page.route("**/api/v1/hardware/devices", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }
    if (onDevicesRequest) onDevicesRequest();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([serverState.device])
    });
  });

  await page.route(
    `**/api/v1/hardware/devices/${serverState.device.deviceId}/logs`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(serverState.logs)
      });
    }
  );

  await page.route(
    `**/api/v1/hardware/devices/${serverState.device.deviceId}/sync-records`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(serverState.syncRecords)
      });
    }
  );

  await page.route(
    `**/api/v1/hardware/devices/${serverState.device.deviceId}/connect`,
    async (route) => {
      if (connectError) {
        await route.fulfill({
          status: connectError.status || 500,
          contentType: "application/json",
          body: JSON.stringify({
            error: {
              code: connectError.code || "hardware_demo_failed",
              message: connectError.message || "Unable to connect demo device."
            }
          })
        });
        return;
      }

      serverState.device = {
        ...serverState.device,
        connected: true,
        connectionState: "connected"
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(serverState.device)
      });
    }
  );

  await page.route(
    `**/api/v1/hardware/devices/${serverState.device.deviceId}/disconnect`,
    async (route) => {
      if (disconnectError) {
        await route.fulfill({
          status: disconnectError.status || 500,
          contentType: "application/json",
          body: JSON.stringify({
            error: {
              code: disconnectError.code || "hardware_demo_failed",
              message:
                disconnectError.message || "Unable to disconnect demo device."
            }
          })
        });
        return;
      }

      serverState.device = {
        ...serverState.device,
        connected: false,
        connectionState: "disconnected",
        transferState: "idle"
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(serverState.device)
      });
    }
  );

  await page.route(
    `**/api/v1/hardware/devices/${serverState.device.deviceId}/sync`,
    async (route) => {
      if (syncError) {
        await route.fulfill({
          status: syncError.status || 500,
          contentType: "application/json",
          body: JSON.stringify({
            error: {
              code: syncError.code || "hardware_demo_failed",
              message: syncError.message || "Unable to sync demo device."
            }
          })
        });
        return;
      }

      const now = "2026-03-24T10:30:00.000Z";
      serverState.device = {
        ...serverState.device,
        connected: true,
        connectionState: "connected",
        transferState: "healthy",
        batteryPercent: 68,
        lastSyncAt: now,
        capturedSessions: serverState.device.capturedSessions + 1,
        vibrationEvents: serverState.device.vibrationEvents + 1
      };

      const log = {
        logId: `log-${Date.now()}`,
        eventType: "sync",
        severity: "info",
        title: "Demo sync completed",
        detail: "The Hardware page triggered a simulated sync round-trip.",
        reviewId: null,
        createdAt: now
      };
      const vibrationLog = {
        logId: `log-vibration-${Date.now()}`,
        eventType: "vibration",
        severity: "warning",
        title: "Vibration pattern replayed",
        detail: "A demo vibration event was added for timeline playback.",
        reviewId: null,
        createdAt: now
      };
      const syncRecord = {
        syncRecordId: `sync-${Date.now()}`,
        syncKind: "sync_complete",
        status: "healthy",
        title: "Hardware page demo sync",
        detail: "The frontend replayed the persisted backend sync state.",
        reviewId: null,
        createdAt: now
      };

      serverState.logs = [vibrationLog, log, ...serverState.logs];
      serverState.syncRecords = [syncRecord, ...serverState.syncRecords];

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          device: serverState.device,
          log,
          syncRecord
        })
      });
    }
  );
}

function seedAuthenticatedState() {
  return {
    loggedIn: true,
    activeRoute: "hardware",
    pendingRoute: null,
    user: {
      name: "Demo Hardware User",
      email: "demo@miro.local",
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

test("hardware page loads device state from backend endpoints and keeps state after actions", async ({
  page
}) => {
  const serverState = createDemoState();
  let devicesRequests = 0;

  await installHardwareApiRoutes(page, serverState, {
    onDevicesRequest: () => {
      devicesRequests += 1;
    }
  });

  await seedStoredState(page, seedAuthenticatedState(), STORAGE_KEY);

  await page.goto(`${BASE_URL}/index.html#hardware`, {
    waitUntil: "domcontentloaded"
  });

  await expect(page.locator("[data-testid='hardware-device-name']")).toHaveText(
    "Miro Pin 01"
  );
  await expect(
    page.locator("[data-testid='hardware-captured-sessions']")
  ).toHaveText("3");
  await expect(page.locator("[data-testid='hardware-battery']")).toContainText(
    "73%"
  );
  expect(devicesRequests).toBeGreaterThan(0);

  await page.getByTestId("hardware-connect").click();
  await expect(
    page.locator("[data-testid='hardware-connection-state']")
  ).toContainText("Online");

  await page.getByTestId("hardware-sync").click();
  await expect(
    page.locator("[data-testid='hardware-transfer-state']")
  ).toContainText("Healthy");
  await expect(
    page.locator("[data-testid='hardware-captured-sessions']")
  ).toHaveText("4");
  await expect(page.locator("[data-testid='hardware-log-list']")).toContainText(
    "Demo sync completed"
  );
  await expect(
    page.locator("[data-testid='hardware-sync-records']")
  ).toContainText("Hardware page demo sync");

  await page.getByTestId("hardware-disconnect").click();
  await expect(
    page.locator("[data-testid='hardware-connection-state']")
  ).toContainText("Offline");

  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(
    page.locator("[data-testid='hardware-captured-sessions']")
  ).toHaveText("4");
  await expect(page.locator("[data-testid='hardware-log-list']")).toContainText(
    "Demo sync completed"
  );
});

test("hardware page shows a safe error state when backend actions fail", async ({
  page
}) => {
  const serverState = createDemoState();
  await installHardwareApiRoutes(page, serverState, {
    connectError: {
      status: 500,
      code: "hardware_action_failed",
      message: "Temporary backend issue."
    }
  });

  await seedStoredState(page, seedAuthenticatedState(), STORAGE_KEY);

  await page.goto(`${BASE_URL}/index.html#hardware`, {
    waitUntil: "domcontentloaded"
  });

  await page.getByTestId("hardware-connect").click();
  await expect(page.locator("[data-testid='hardware-error']")).toContainText(
    "Temporary backend issue."
  );
});

test("unauthenticated users do not get direct access to the protected hardware workspace", async ({
  page
}) => {
  let hardwareApiHit = false;
  await page.route("**/api/v1/hardware/**", async (route) => {
    hardwareApiHit = true;
    await route.fulfill({
      status: 500,
      body: ""
    });
  });

  await page.goto(`${BASE_URL}/index.html#hardware`, {
    waitUntil: "domcontentloaded"
  });

  await expect(page.locator("button.nav-link.active[data-route='home']")).toHaveCount(
    1
  );
  expect(hardwareApiHit).toBe(false);
});
