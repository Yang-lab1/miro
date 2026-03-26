const { spawn } = require("child_process");

const STORAGE_KEY = "miro-prototype-state-v4";

function buildBaseUrl(host, port) {
  return `http://${host}:${port}`;
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function startSmokeServer({
  host = "127.0.0.1",
  port,
  disableSupabase = true
}) {
  const env = {
    ...process.env,
    MIRO_SMOKE_HOST: host,
    MIRO_SMOKE_PORT: String(port)
  };
  if (disableSupabase) {
    env.MIRO_SMOKE_DISABLE_SUPABASE = "1";
  }

  return spawn("node", ["scripts/live-smoke-server.js"], {
    cwd: process.cwd(),
    env,
    stdio: "ignore"
  });
}

function stopSmokeServer(server) {
  if (!server) return;
  server.kill("SIGTERM");
}

async function waitForSmokeServer(page, baseUrl, maxAttempts = 50) {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    try {
      const response = await page.request.get(`${baseUrl}/__smoke_health`);
      if (response.ok()) return;
    } catch {}
    await wait(100);
  }
  throw new Error("Smoke server did not become ready in time.");
}

async function seedStoredState(page, snapshot, storageKey = STORAGE_KEY) {
  await page.addInitScript(
    ({ nextStorageKey, nextSnapshot }) => {
      localStorage.setItem(nextStorageKey, JSON.stringify(nextSnapshot));
    },
    { nextStorageKey: storageKey, nextSnapshot: snapshot }
  );
}

function createBootstrapBillingState() {
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

function createBootstrapHardwareDevice() {
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

async function installSharedBootstrapRoutes(
  page,
  {
    billingSummary = createBootstrapBillingState(),
    hardwareDevices = [createBootstrapHardwareDevice()]
  } = {}
) {
  await page.route("**/api/v1/billing/summary", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
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

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(hardwareDevices)
    });
  });
}

module.exports = {
  STORAGE_KEY,
  buildBaseUrl,
  createBootstrapBillingState,
  createBootstrapHardwareDevice,
  installSharedBootstrapRoutes,
  startSmokeServer,
  stopSmokeServer,
  waitForSmokeServer,
  seedStoredState
};
