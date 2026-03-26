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
const SMOKE_PORT = 4176;
const BASE_URL = buildBaseUrl(SMOKE_HOST, SMOKE_PORT);

let smokeServer = null;

function createBillingState() {
  return {
    plans: [
      {
        planId: "plan-free",
        planKey: "free",
        displayName: "Free",
        billingCycle: "monthly",
        currencyCode: "USD",
        amountValue: 0,
        isCurrent: false
      },
      {
        planId: "plan-go",
        planKey: "go",
        displayName: "Go",
        billingCycle: "monthly",
        currencyCode: "USD",
        amountValue: 8,
        isCurrent: false
      },
      {
        planId: "plan-plus",
        planKey: "plus",
        displayName: "Plus",
        billingCycle: "monthly",
        currencyCode: "USD",
        amountValue: 20,
        isCurrent: true
      },
      {
        planId: "plan-pro",
        planKey: "pro",
        displayName: "Pro",
        billingCycle: "monthly",
        currencyCode: "USD",
        amountValue: 200,
        isCurrent: false
      }
    ],
    summary: {
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
    }
  };
}

function syncCurrentFlags(serverState) {
  const currentPlanKey = serverState.summary.account.currentPlanKey;
  serverState.plans = serverState.plans.map((plan) => ({
    ...plan,
    isCurrent: plan.planKey === currentPlanKey
  }));
  const currentPlan = serverState.plans.find((plan) => plan.planKey === currentPlanKey);
  serverState.summary = {
    ...serverState.summary,
    currentPlan
  };
}

async function installBillingApiRoutes(page, serverState, options = {}) {
  const {
    summaryError = null,
    plansError = null,
    selectPlanError = null,
    topUpError = null,
    onSummaryRequest = null,
    onPlansRequest = null
  } = options;

  await page.route("**/api/v1/billing/summary", async (route) => {
    const method = route.request().method();
    if (method !== "GET") {
      await route.fallback();
      return;
    }
    if (onSummaryRequest) onSummaryRequest();
    if (summaryError) {
      await route.fulfill({
        status: summaryError.status || 500,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: summaryError.code || "billing_summary_failed",
            message: summaryError.message || "Unable to load billing summary."
          }
        })
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(serverState.summary)
    });
  });

  await page.route("**/api/v1/billing/plans", async (route) => {
    const method = route.request().method();
    if (method !== "GET") {
      await route.fallback();
      return;
    }
    if (onPlansRequest) onPlansRequest();
    if (plansError) {
      await route.fulfill({
        status: plansError.status || 500,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: plansError.code || "billing_plans_failed",
            message: plansError.message || "Unable to load billing plans."
          }
        })
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(serverState.plans)
    });
  });

  await page.route("**/api/v1/billing/select-plan", async (route) => {
    if (selectPlanError) {
      await route.fulfill({
        status: selectPlanError.status || 500,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: selectPlanError.code || "billing_select_plan_failed",
            message: selectPlanError.message || "Unable to select the plan."
          }
        })
      });
      return;
    }

    const body = route.request().postDataJSON();
    serverState.summary.account.currentPlanKey = body.planKey;
    serverState.summary.account.renewalAt =
      body.planKey === "free" ? null : "2026-05-10T09:00:00.000Z";
    syncCurrentFlags(serverState);

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(serverState.summary)
    });
  });

  await page.route("**/api/v1/billing/top-up", async (route) => {
    if (topUpError) {
      await route.fulfill({
        status: topUpError.status || 500,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: topUpError.code || "billing_top_up_failed",
            message: topUpError.message || "Unable to top up demo credits."
          }
        })
      });
      return;
    }

    const body = route.request().postDataJSON();
    serverState.summary.account.creditBalance += body.amount;

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        summary: serverState.summary,
        payment: {
          paymentId: `payment-${Date.now()}`,
          eventType: "top_up",
          amountValue: body.amount,
          currencyCode: "CREDIT",
          paymentStatus: "demo_completed",
          createdAt: "2026-03-26T09:30:00.000Z"
        }
      })
    });
  });
}

function seedAuthenticatedState() {
  return {
    loggedIn: true,
    activeRoute: "pricing",
    pendingRoute: null,
    pricingSelection: "free",
    user: {
      name: "Demo Billing User",
      email: "demo@miro.local",
      company: "Miro",
      role: "Director, Global Partnerships",
      plan: "Enterprise Pilot",
      balance: 4800,
      renewal: "2026-04-12"
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

test("pricing page loads plans and summary from backend and keeps persisted state after actions", async ({
  page
}) => {
  const serverState = createBillingState();
  let summaryRequests = 0;
  let plansRequests = 0;

  await installBillingApiRoutes(page, serverState, {
    onSummaryRequest: () => {
      summaryRequests += 1;
    },
    onPlansRequest: () => {
      plansRequests += 1;
    }
  });

  await seedStoredState(page, seedAuthenticatedState(), STORAGE_KEY);

  await page.goto(`${BASE_URL}/index.html#pricing`, {
    waitUntil: "domcontentloaded"
  });

  await expect(page.locator("[data-testid='pricing-current-plan']")).toContainText(
    "Plus"
  );
  await expect(page.locator("[data-testid='pricing-balance']")).toContainText(
    "1,500"
  );
  await expect(page.locator("[data-testid='pricing-renewal']")).toContainText(
    "2026"
  );
  await expect(
    page.locator("[data-testid='pricing-card-plus']")
  ).toHaveAttribute("aria-pressed", "true");
  expect(summaryRequests).toBeGreaterThan(0);
  expect(plansRequests).toBeGreaterThan(0);

  await page.getByTestId("pricing-action-pro").click();
  await expect(page.locator("[data-testid='pricing-current-plan']")).toContainText(
    "Pro"
  );
  await expect(
    page.locator("[data-testid='pricing-card-pro']")
  ).toHaveAttribute("aria-pressed", "true");

  await page.getByTestId("pricing-topup-500").click();
  await expect(page.locator("[data-testid='pricing-balance']")).toContainText(
    "2,000"
  );

  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.locator("[data-testid='pricing-current-plan']")).toContainText(
    "Pro"
  );
  await expect(page.locator("[data-testid='pricing-balance']")).toContainText(
    "2,000"
  );
});

test("pricing page shows a safe error when billing backend actions fail", async ({
  page
}) => {
  const serverState = createBillingState();
  await installBillingApiRoutes(page, serverState, {
    selectPlanError: {
      status: 500,
      code: "billing_select_plan_failed",
      message: "Temporary billing issue."
    }
  });

  await seedStoredState(page, seedAuthenticatedState(), STORAGE_KEY);

  await page.goto(`${BASE_URL}/index.html#pricing`, {
    waitUntil: "domcontentloaded"
  });

  await page.getByTestId("pricing-action-pro").click();
  await expect(page.locator("[data-testid='pricing-error']")).toContainText(
    "Temporary billing issue."
  );
});

test("unauthenticated users do not get direct access to the protected pricing workspace", async ({
  page
}) => {
  let billingApiHit = false;

  await page.route("**/api/v1/billing/**", async (route) => {
    billingApiHit = true;
    await route.fulfill({
      status: 500,
      body: ""
    });
  });

  await page.goto(`${BASE_URL}/index.html#pricing`, {
    waitUntil: "domcontentloaded"
  });

  await expect(
    page.locator("button.nav-link.active[data-route='home']")
  ).toHaveCount(1);
  expect(billingApiHit).toBe(false);
});
