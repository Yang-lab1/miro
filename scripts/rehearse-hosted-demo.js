const { chromium } = require("@playwright/test");

const FRONTEND_URL = process.env.MIRO_FRONTEND_URL || "https://miro-vert.vercel.app";
const ACCOUNT_ONE = {
  email: process.env.MIRO_DEMO_EMAIL_1,
  password: process.env.MIRO_DEMO_PASSWORD_1
};
const ACCOUNT_TWO = {
  email: process.env.MIRO_DEMO_EMAIL_2,
  password: process.env.MIRO_DEMO_PASSWORD_2
};
const GENERATED_ACCOUNT_TWO = {
  email: `miro-hosted-rehearsal-${Date.now()}@example.com`,
  password: `Miro!${Date.now()}aB3`
};

function requireCredential(account, label) {
  if (!account.email || !account.password) {
    throw new Error(
      `Missing ${label} credentials. Set MIRO_DEMO_EMAIL_${label} and MIRO_DEMO_PASSWORD_${label}.`
    );
  }
}

async function getProtectedSnapshot(page) {
  return page.evaluate(async () => {
    const { createClient } = await import("https://esm.sh/@supabase/supabase-js@2?bundle");
    const client = createClient(
      globalThis.MIRO_SUPABASE_URL,
      globalThis.MIRO_SUPABASE_PUBLISHABLE_KEY,
      {
        auth: {
          autoRefreshToken: true,
          persistSession: true,
          detectSessionInUrl: true
        }
      }
    );
    const { data, error } = await client.auth.getSession();
    if (error) {
      throw new Error(error.message);
    }
    const accessToken = data.session?.access_token;
    if (!accessToken) {
      throw new Error("No active Supabase session.");
    }

    const fetchJson = async (path) => {
      const response = await fetch(`${globalThis.MIRO_API_BASE}${path}`, {
        headers: {
          Authorization: `Bearer ${accessToken}`
        }
      });
      if (!response.ok) {
        throw new Error(`${path} failed with ${response.status}`);
      }
      return response.json();
    };

    const sessionPayload = await fetchJson("/auth/session");
    const billingSummary = await fetchJson("/billing/summary");
    const devices = await fetchJson("/hardware/devices");
    const activeDevice = devices[0] || null;
    const logs = activeDevice
      ? await fetchJson(`/hardware/devices/${activeDevice.deviceId}/logs`)
      : [];
    const syncRecords = activeDevice
      ? await fetchJson(`/hardware/devices/${activeDevice.deviceId}/sync-records`)
      : [];
    const reviews = await fetchJson("/reviews");

    return {
      userId: sessionPayload.user.id,
      email: sessionPayload.user.email,
      billingBalance: billingSummary.account.creditBalance,
      currentPlanKey: billingSummary.account.currentPlanKey,
      hardwareDeviceId: activeDevice?.deviceId || null,
      hardwareLogCount: logs.length,
      hardwareSyncCount: syncRecords.length,
      reviewCount: reviews.length
    };
  });
}

async function waitForBackendSession(page, timeoutMs = 30000) {
  const startedAt = Date.now();

  while (Date.now() - startedAt < timeoutMs) {
    try {
      return await getProtectedSnapshot(page);
    } catch {}

    const feedback = await page
      .locator("[data-auth-feedback]")
      .textContent()
      .catch(() => "");
    if (String(feedback || "").trim()) {
      throw new Error(String(feedback || "").trim());
    }

    await page.waitForTimeout(500);
  }

  throw new Error("Timed out waiting for authenticated session.");
}

async function openHome(page) {
  await page.goto(`${FRONTEND_URL}/`, {
    waitUntil: "domcontentloaded",
    timeout: 60000
  });
  await page.locator("#mainContent").waitFor({ timeout: 60000 });
}

async function openAuthModal(page, mode) {
  await openHome(page);
  await page.locator(`[data-auth="${mode}"]`).first().click();
  await page.locator("#authForm").waitFor({ timeout: 30000 });
}

async function fillAuthForm(page, email, password) {
  await page.locator("#authEmail").fill(email);
  await page.locator("#authPassword").fill(password);
}

async function signInViaUi(page, email, password) {
  await openAuthModal(page, "login");
  await fillAuthForm(page, email, password);
  await page.locator("[data-auth-email-submit]").click();
  return waitForBackendSession(page);
}

async function registerViaUi(page, email, password) {
  await openAuthModal(page, "register");
  await fillAuthForm(page, email, password);
  await page.locator("[data-auth-email-submit]").click();

  const startedAt = Date.now();
  while (Date.now() - startedAt < 30000) {
    try {
      const session = await getProtectedSnapshot(page);
      return {
        outcome: "signed_in",
        session
      };
    } catch {}

    const feedback = await page
      .locator("[data-auth-feedback]")
      .textContent()
      .catch(() => "");
    const feedbackMessage = String(feedback || "").trim();
    if (feedbackMessage) {
      return {
        outcome: "error",
        message: feedbackMessage
      };
    }

    const body = String((await page.locator("body").textContent()) || "");
    if (
      body.includes("Check your email to confirm your account") ||
      body.includes("注册成功，请前往邮箱完成验证后再登录")
    ) {
      return {
        outcome: "confirmation_required",
        message: "Signup requires email confirmation before login."
      };
    }

    await page.waitForTimeout(500);
  }

  throw new Error("Timed out waiting for register result.");
}

async function inspectAuthUi(page) {
  await openAuthModal(page, "login");
  const emailDisabled = await page.locator("[data-auth-email-submit]").isDisabled();
  const captchaMessage = await page.locator("#authCaptchaState").textContent();
  await page.evaluate(() => {
    document.getElementById("closeAuthBtn")?.click();
  });
  return {
    emailDisabled,
    captchaMessage: String(captchaMessage || "").trim()
  };
}

async function gotoProtectedRoute(page, route, selector) {
  await page.goto(`${FRONTEND_URL}/#${route}`, {
    waitUntil: "domcontentloaded",
    timeout: 60000
  });
  await page.locator(selector).waitFor({ timeout: 30000 });
}

async function logoutFromUi(page) {
  await gotoProtectedRoute(page, "settings", '[data-testid="settings-logout"]');
  await page.locator('[data-testid="settings-logout"]').click();
  await page.waitForFunction(() => {
    const homeVisible = document.body.innerText.includes("Start new simulation");
    return homeVisible || window.location.hash === "#home" || window.location.hash === "";
  });
}

async function ensureLearningCompleted(page, countryKey = "Japan") {
  return page.evaluate(async (countryKeyValue) => {
    const { createClient } = await import("https://esm.sh/@supabase/supabase-js@2?bundle");
    const client = createClient(
      globalThis.MIRO_SUPABASE_URL,
      globalThis.MIRO_SUPABASE_PUBLISHABLE_KEY,
      {
        auth: {
          autoRefreshToken: true,
          persistSession: true,
          detectSessionInUrl: true
        }
      }
    );
    const { data, error } = await client.auth.getSession();
    if (error) {
      throw new Error(error.message);
    }
    const accessToken = data.session?.access_token;
    if (!accessToken) {
      throw new Error("No active Supabase session.");
    }

    const progressResponse = await fetch(
      `${globalThis.MIRO_API_BASE}/learning/progress/${encodeURIComponent(countryKeyValue)}`,
      {
        headers: {
          Authorization: `Bearer ${accessToken}`
        }
      }
    );
    if (!progressResponse.ok) {
      throw new Error(`Learning progress lookup failed with ${progressResponse.status}`);
    }
    const progress = await progressResponse.json();
    if (progress.isUpToDate) {
      return progress;
    }
    const targetVersion = progress.contentVersion || progress.latestContentVersion;
    if (!targetVersion) {
      throw new Error("Learning progress does not expose a contentVersion to complete.");
    }

    const completeResponse = await fetch(
      `${globalThis.MIRO_API_BASE}/learning/progress/${encodeURIComponent(countryKeyValue)}/complete`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          contentVersion: targetVersion
        })
      }
    );
    if (!completeResponse.ok) {
      const payload = await completeResponse.text();
      throw new Error(
        `Learning completion failed with ${completeResponse.status}: ${payload}`
      );
    }
    return completeResponse.json();
  }, countryKey);
}

async function topUpPricing(page) {
  await gotoProtectedRoute(page, "pricing", '[data-testid="pricing-current-plan"]');
  const before = await getProtectedSnapshot(page);
  await page.locator('[data-testid="pricing-topup-500"]').click();
  const startedAt = Date.now();
  let after = await getProtectedSnapshot(page);
  while (after.billingBalance !== before.billingBalance + 500) {
    if (Date.now() - startedAt > 30000) {
      throw new Error(
        `Pricing top-up did not update the backend snapshot in time. Before=${before.billingBalance} After=${after.billingBalance}`
      );
    }
    await page.waitForTimeout(1000);
    after = await getProtectedSnapshot(page);
  }
  return {
    beforeBalance: before.billingBalance,
    afterBalance: after.billingBalance
  };
}

async function syncHardware(page) {
  const before = await getProtectedSnapshot(page);
  await gotoProtectedRoute(page, "hardware", '[data-testid="hardware-device-name"]');
  const connectButton = page.locator('[data-testid="hardware-connect"]');
  if (await connectButton.count()) {
    await connectButton.click();
    await page.waitForFunction(() => {
      const node = document.querySelector('[data-testid="hardware-connection-state"]');
      return node && /online/i.test(node.textContent || "");
    });
  }

  await page.locator('[data-testid="hardware-sync"]').click();
  const startedAt = Date.now();
  let after = await getProtectedSnapshot(page);
  while (
    after.hardwareLogCount <= before.hardwareLogCount &&
    after.hardwareSyncCount <= before.hardwareSyncCount
  ) {
    if (Date.now() - startedAt > 30000) {
      throw new Error("Hardware sync did not update the backend snapshot in time.");
    }
    await page.waitForTimeout(1000);
    after = await getProtectedSnapshot(page);
  }

  return {
    initialLogCount: before.hardwareLogCount,
    initialSyncCount: before.hardwareSyncCount,
    finalLogCount: after.hardwareLogCount,
    finalSyncCount: after.hardwareSyncCount
  };
}

async function maybeHandlePrecheckModal(page) {
  const continueButton = page.locator("#precheckContinueBtn");
  try {
    await continueButton.waitFor({ state: "visible", timeout: 15000 });
    await continueButton.click();
  } catch {}
}

async function runLiveReviewFlow(page) {
  await gotoProtectedRoute(page, "live", '[data-testid="generate-strategy-btn"]');

  await page.locator("#field-files").setInputFiles({
    name: "renewal-notes.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(
      "Renewal timing should stay conservative. Confirm the internal owner before discussing pricing.",
      "utf8"
    )
  });

  await page.locator('[data-testid="generate-strategy-btn"]').click();
  await page.waitForFunction(() => {
    const button = document.querySelector('[data-testid="generate-strategy-btn"]');
    return button && !button.disabled;
  });

  await page.locator('[data-testid="start-simulation-btn"]').click();
  await maybeHandlePrecheckModal(page);
  try {
    await page.locator("#practiceInput").waitFor({ timeout: 30000 });
  } catch (error) {
    const bodyText = await page.locator("body").innerText();
    throw new Error(
      `Live session did not enter practice mode.\n${bodyText.slice(0, 2000)}`
    );
  }
  await page.locator("#practiceInput").fill(
    "Before discussing price, we should confirm the internal owner and the renewal timing."
  );
  await page.locator('[data-testid="evaluate-language-btn"]').click();
  await page.waitForFunction(() =>
    document.body.innerText.toLowerCase().includes("renewal timing")
  );

  await page.locator('[data-testid="end-session-btn"]').click();
  await page.waitForSelector('[data-testid="review-detail-container"]', { timeout: 30000 });
  await page.waitForFunction(() =>
    document.body.innerText.toLowerCase().includes("renewal timing")
  );
}

async function ensureSecondaryAccount(page) {
  const candidates = [];
  if (ACCOUNT_TWO.email && ACCOUNT_TWO.password) {
    candidates.push({
      label: "provided-account-2",
      email: ACCOUNT_TWO.email,
      password: ACCOUNT_TWO.password
    });
  }
  candidates.push({
    label: "generated-account-2",
    email: GENERATED_ACCOUNT_TWO.email,
    password: GENERATED_ACCOUNT_TWO.password
  });

  const failures = [];

  for (const candidate of candidates) {
    try {
      const actor = await signInViaUi(page, candidate.email, candidate.password);
      return {
        actor,
        credential: candidate,
        created: false
      };
    } catch (signInError) {
      const signInMessage =
        signInError instanceof Error ? signInError.message : String(signInError);
      const registerResult = await registerViaUi(
        page,
        candidate.email,
        candidate.password
      );

      if (registerResult.outcome === "signed_in") {
        await logoutFromUi(page);
        const actor = await signInViaUi(page, candidate.email, candidate.password);
        return {
          actor,
          credential: candidate,
          created: true
        };
      }

      failures.push(
        `${candidate.label}: sign-in failed (${signInMessage}); register result ${registerResult.outcome}${registerResult.message ? ` - ${registerResult.message}` : ""}`
      );
    }
  }

  throw new Error(failures.join(" | "));
}

async function main() {
  requireCredential(ACCOUNT_ONE, "1");

  const browser = await chromium.launch({ headless: true });
  const contextOne = await browser.newContext();
  const contextTwo = await browser.newContext();
  const pageOne = await contextOne.newPage();
  const pageTwo = await contextTwo.newPage();

  try {
    await openHome(pageOne);
    const authUi = await inspectAuthUi(pageOne);
    console.log(
      `INFO auth-ui emailDisabled=${authUi.emailDisabled} message="${authUi.captchaMessage}"`
    );

    const accountTwo = await ensureSecondaryAccount(pageTwo);
    const accountTwoBefore = await getProtectedSnapshot(pageTwo);
    console.log(
      `PASS account-2 ${accountTwo.created ? "register+login" : "login"} ${accountTwo.actor.email}`
    );

    const actorOne = await signInViaUi(pageOne, ACCOUNT_ONE.email, ACCOUNT_ONE.password);
    console.log(`PASS account-1 login ${actorOne.email}`);

    const pricing = await topUpPricing(pageOne);
    console.log(`PASS pricing top-up ${pricing.beforeBalance} -> ${pricing.afterBalance}`);

    const hardware = await syncHardware(pageOne);
    console.log(
      `PASS hardware sync logs ${hardware.initialLogCount} -> ${hardware.finalLogCount}, syncs ${hardware.initialSyncCount} -> ${hardware.finalSyncCount}`
    );

    const learning = await ensureLearningCompleted(pageOne, "Japan");
    console.log(`PASS learning precheck ready ${learning.countryKey} ${learning.contentVersion}`);

    await runLiveReviewFlow(pageOne);
    console.log("PASS live -> review grounded rehearsal");

    await logoutFromUi(pageOne);
    console.log("PASS logout route returns to public home");

    const accountTwoAfter = await getProtectedSnapshot(pageTwo);
    if (accountTwoBefore.userId === actorOne.userId) {
      throw new Error("Account isolation failed: both accounts resolved to the same user id.");
    }
    if (accountTwoAfter.billingBalance !== accountTwoBefore.billingBalance) {
      throw new Error("Account isolation failed: account 2 billing changed after account 1 actions.");
    }
    if (accountTwoAfter.hardwareLogCount !== accountTwoBefore.hardwareLogCount) {
      throw new Error("Account isolation failed: account 2 hardware logs changed after account 1 sync.");
    }
    if (accountTwoAfter.hardwareSyncCount !== accountTwoBefore.hardwareSyncCount) {
      throw new Error("Account isolation failed: account 2 sync records changed after account 1 sync.");
    }
    if (accountTwoAfter.reviewCount !== accountTwoBefore.reviewCount) {
      throw new Error("Account isolation failed: account 2 review count changed after account 1 live session.");
    }

    console.log("PASS dual-account isolation snapshot remained stable");
  } finally {
    await contextOne.close();
    await contextTwo.close();
    await browser.close();
  }
}

main().catch((error) => {
  console.error("Hosted rehearsal failed.");
  console.error(error && error.stack ? error.stack : error);
  process.exitCode = 1;
});
