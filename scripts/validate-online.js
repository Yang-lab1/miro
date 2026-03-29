const fs = require("fs/promises");
const path = require("path");
const { existsSync } = require("fs");
const { spawn } = require("child_process");

const ROOT_DIR = path.resolve(__dirname, "..");
const BACKEND_DIR = path.join(ROOT_DIR, "backend");
const BACKEND_PYTHON_PATH = path.join(
  BACKEND_DIR,
  ".venv",
  "Scripts",
  "python.exe"
);
const INDEX_PATH = path.join(ROOT_DIR, "index.html");
const RUNTIME_CONFIG_PATH = path.join(ROOT_DIR, "runtime-config.js");
const VERCEL_CONFIG_PATH = path.join(ROOT_DIR, "vercel.json");
const ECS_DEPLOY_GUIDE_PATH = path.join(
  ROOT_DIR,
  "docs",
  "deployment",
  "VERCEL_ECS_DEPLOY.md"
);
const DEFAULT_HEALTH_PATH = "/api/v1/health";
const DEFAULT_AUTH_SESSION_PATH = "/api/v1/auth/session";

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (!value.startsWith("--")) continue;
    const key = value.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith("--")) {
      args[key] = "true";
      continue;
    }
    args[key] = next;
    index += 1;
  }
  return args;
}

function readOption(args, key, envKey = null) {
  const fromArgs = args[key];
  if (typeof fromArgs === "string" && fromArgs.trim()) {
    return fromArgs.trim();
  }
  const envName = envKey || key.toUpperCase().replace(/-/g, "_");
  const fromEnv = process.env[envName];
  return typeof fromEnv === "string" && fromEnv.trim() ? fromEnv.trim() : "";
}

function normalizeOrigin(urlValue) {
  if (!urlValue) return "";
  try {
    const url = new URL(urlValue);
    return url.origin;
  } catch {
    return "";
  }
}

function isLocalOrigin(origin) {
  return /^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/i.test(origin);
}

function parseRuntimeAssignments(scriptText) {
  const assignments = {};
  const pattern = /globalThis\.(MIRO_[A-Z0-9_]+)\s*\?\?=\s*([^;]+);/g;
  let match;
  while ((match = pattern.exec(scriptText))) {
    try {
      assignments[match[1]] = JSON.parse(match[2]);
    } catch {
      assignments[match[1]] = match[2];
    }
  }
  return assignments;
}

async function fetchText(url, options = {}) {
  const response = await fetch(url, options);
  const text = await response.text();
  return { response, text };
}

function pass(label, detail = "") {
  process.stdout.write(`PASS ${label}${detail ? ` - ${detail}` : ""}\n`);
}

function fail(label, detail = "") {
  process.stdout.write(`FAIL ${label}${detail ? ` - ${detail}` : ""}\n`);
}

function info(label, detail = "") {
  process.stdout.write(`INFO ${label}${detail ? ` - ${detail}` : ""}\n`);
}

async function waitForHttp(url, timeoutMs = 20000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(url);
      if (response.status >= 200 && response.status < 500) {
        return;
      }
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 300));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

function pickPythonLauncher() {
  if (existsSync(BACKEND_PYTHON_PATH)) {
    return {
      command: BACKEND_PYTHON_PATH,
      args: [],
    };
  }
  return {
    command: "py",
    args: ["-3"],
  };
}

function spawnBackground(command, args, options = {}) {
  const child = spawn(command, args, {
    stdio: "ignore",
    windowsHide: true,
    ...options,
  });
  child.unref();
  return child;
}

async function generateRuntimeConfig(envOverrides = {}) {
  await new Promise((resolve, reject) => {
    const child = spawn(
      process.execPath,
      [path.join(ROOT_DIR, "scripts", "generate-runtime-config.js")],
      {
        cwd: ROOT_DIR,
        stdio: "ignore",
        windowsHide: true,
        env: {
          ...process.env,
          ...envOverrides,
        },
      }
    );
    child.on("exit", (code) => {
      if (code === 0) {
        resolve();
        return;
      }
      reject(new Error(`runtime config generator exited with code ${code}`));
    });
    child.on("error", reject);
  });
}

async function withLocalDryRun(callback) {
  const frontendPort = process.env.MIRO_VALIDATE_LOCAL_FRONTEND_PORT || "4273";
  const backendPort = process.env.MIRO_VALIDATE_LOCAL_BACKEND_PORT || "8070";
  const frontendUrl = `http://127.0.0.1:${frontendPort}`;
  const backendUrl = `http://127.0.0.1:${backendPort}`;
  const frontendOrigin = normalizeOrigin(frontendUrl);
  const backendOrigin = normalizeOrigin(backendUrl);
  const expectedSupabaseUrl = "https://demo-project.supabase.co";
  const runtimeEnv = {
    MIRO_API_BASE: `${backendOrigin}/api/v1`,
    MIRO_REVIEW_API_BASE: `${backendOrigin}/api/v1`,
    MIRO_SUPABASE_URL: expectedSupabaseUrl,
    MIRO_SUPABASE_PUBLISHABLE_KEY: "sb_publishable_demo",
    MIRO_SUPABASE_AUTH_REDIRECT_TO: frontendOrigin,
  };
  const python = pickPythonLauncher();
  const processes = [];

  try {
    await generateRuntimeConfig(runtimeEnv);

    processes.push(
      spawnBackground(
        python.command,
        [
          ...python.args,
          "-m",
          "uvicorn",
          "app.main:app",
          "--host",
          "127.0.0.1",
          "--port",
          backendPort,
        ],
        {
          cwd: BACKEND_DIR,
          env: {
            ...process.env,
            APP_ENV: "production",
            APP_DEBUG: "false",
            ENABLE_DOCS: "false",
            FRONTEND_SITE_URL: frontendOrigin,
            CORS_ORIGINS: "[]",
            ALLOW_DEMO_ACTOR_FALLBACK: "false",
          },
        }
      )
    );

    processes.push(
      spawnBackground(
        python.command,
        [...python.args, "-m", "http.server", frontendPort],
        { cwd: ROOT_DIR }
      )
    );

    await waitForHttp(`${frontendOrigin}/`);
    await waitForHttp(`${backendOrigin}${DEFAULT_HEALTH_PATH}`);
    info("local dry run services", `${frontendOrigin} + ${backendOrigin}`);

    await callback({
      frontendUrl,
      backendUrl,
      expectedSupabaseUrl,
      expectedFrontendOrigin: frontendOrigin,
    });
  } finally {
    for (const child of processes.reverse()) {
      try {
        process.kill(child.pid);
      } catch {}
    }
    await generateRuntimeConfig();
  }
}

async function checkLocalFiles() {
  const [indexHtml, runtimeConfig, vercelConfig, ecsDeployGuide] = await Promise.all([
    fs.readFile(INDEX_PATH, "utf8"),
    fs.readFile(RUNTIME_CONFIG_PATH, "utf8"),
    fs.readFile(VERCEL_CONFIG_PATH, "utf8"),
    fs.readFile(ECS_DEPLOY_GUIDE_PATH, "utf8"),
  ]);

  if (!indexHtml.includes('src="runtime-config.js"')) {
    throw new Error("index.html does not load runtime-config.js before app.js.");
  }
  pass("local runtime-config hook", "index.html loads runtime-config.js");

  if (runtimeConfig.includes("127.0.0.1:8000")) {
    throw new Error("runtime-config.js still hardcodes localhost backend origin.");
  }
  pass("local runtime-config defaults", "no hardcoded localhost backend");

  if (!vercelConfig.includes('"destination": "/index.html"')) {
    throw new Error("vercel.json is missing the SPA rewrite to index.html.");
  }
  if (!vercelConfig.includes('"/runtime-config.js"')) {
    throw new Error("vercel.json is missing the runtime-config.js cache rule.");
  }
  pass("vercel config", "SPA rewrite + runtime-config cache header");

  if (!ecsDeployGuide.includes("Alibaba Cloud ECS")) {
    throw new Error("VERCEL_ECS_DEPLOY.md is missing the ECS deployment path.");
  }
  if (!ecsDeployGuide.includes("uvicorn")) {
    throw new Error("VERCEL_ECS_DEPLOY.md is missing the uvicorn backend run guidance.");
  }
  pass("ecs deployment guide", "deployment doc matches the current hosted backend path");
}

async function checkFrontendAndRuntime({
  frontendUrl,
  backendUrl,
  expectedSupabaseUrl,
  expectedFrontendOrigin,
}) {
  const indexUrl = new URL("/", frontendUrl).toString();
  const runtimeUrl = new URL("/runtime-config.js", frontendUrl).toString();

  const { response: indexResponse, text: indexHtml } = await fetchText(indexUrl);
  if (!indexResponse.ok) {
    throw new Error(`frontend root returned ${indexResponse.status}`);
  }
  if (!indexHtml.includes('src="runtime-config.js"')) {
    throw new Error("frontend root does not reference runtime-config.js");
  }
  pass("frontend root", indexUrl);

  const { response: runtimeResponse, text: runtimeScript } = await fetchText(runtimeUrl);
  if (!runtimeResponse.ok) {
    throw new Error(`runtime-config.js returned ${runtimeResponse.status}`);
  }
  const runtimeConfig = parseRuntimeAssignments(runtimeScript);
  pass("frontend runtime-config", runtimeUrl);

  const apiBase = runtimeConfig.MIRO_API_BASE || "";
  if (!apiBase) {
    throw new Error("MIRO_API_BASE is missing from runtime-config.js");
  }

  const frontendOrigin = expectedFrontendOrigin || normalizeOrigin(frontendUrl);
  const backendOrigin = normalizeOrigin(backendUrl);
  if (apiBase.startsWith("http")) {
    if (normalizeOrigin(apiBase) !== backendOrigin) {
      throw new Error(`MIRO_API_BASE origin ${normalizeOrigin(apiBase)} does not match backend origin ${backendOrigin}`);
    }
  } else if (apiBase.startsWith("/")) {
    if (frontendOrigin !== backendOrigin) {
      throw new Error("MIRO_API_BASE is relative, but frontend and backend origins differ.");
    }
  } else {
    throw new Error(`MIRO_API_BASE has unsupported shape: ${apiBase}`);
  }

  if (!isLocalOrigin(frontendOrigin) && /127\.0\.0\.1|localhost/i.test(apiBase)) {
    throw new Error("MIRO_API_BASE still points at localhost for a non-local frontend origin.");
  }
  pass("frontend API base", apiBase);

  if (expectedSupabaseUrl) {
    if (runtimeConfig.MIRO_SUPABASE_URL !== expectedSupabaseUrl) {
      throw new Error(
        `MIRO_SUPABASE_URL mismatch. Expected ${expectedSupabaseUrl}, got ${runtimeConfig.MIRO_SUPABASE_URL || "<empty>"}`
      );
    }
    pass("frontend Supabase URL", expectedSupabaseUrl);
  }

  const redirectTarget = runtimeConfig.MIRO_SUPABASE_AUTH_REDIRECT_TO || "";
  if (redirectTarget) {
    if (normalizeOrigin(redirectTarget) !== frontendOrigin) {
      throw new Error(
        `MIRO_SUPABASE_AUTH_REDIRECT_TO origin ${normalizeOrigin(redirectTarget)} does not match frontend origin ${frontendOrigin}`
      );
    }
    pass("frontend auth redirect", redirectTarget);
  } else {
    fail("frontend auth redirect", "MIRO_SUPABASE_AUTH_REDIRECT_TO is empty; verify signup email redirect manually.");
  }
}

async function checkBackend({
  frontendUrl,
  backendUrl,
}) {
  const frontendOrigin = normalizeOrigin(frontendUrl);
  const healthUrl = new URL(DEFAULT_HEALTH_PATH, backendUrl).toString();
  const authSessionUrl = new URL(DEFAULT_AUTH_SESSION_PATH, backendUrl).toString();

  const { response: healthResponse, text: healthText } = await fetchText(healthUrl);
  if (!healthResponse.ok) {
    throw new Error(`backend health returned ${healthResponse.status}`);
  }
  if (!healthText.includes('"status":"ok"')) {
    throw new Error("backend health response does not contain status=ok");
  }
  pass("backend health", healthUrl);

  const authResponse = await fetch(authSessionUrl, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
  });
  if (authResponse.status !== 401) {
    throw new Error(`unauthenticated auth/session returned ${authResponse.status} instead of 401`);
  }
  pass("backend auth boundary", "unauthenticated auth/session returns 401");

  const corsResponse = await fetch(authSessionUrl, {
    method: "OPTIONS",
    headers: {
      Origin: frontendOrigin,
      "Access-Control-Request-Method": "GET",
      "Access-Control-Request-Headers": "authorization",
    },
  });
  const allowOrigin = corsResponse.headers.get("access-control-allow-origin");
  const allowCredentials = corsResponse.headers.get("access-control-allow-credentials");
  if (!corsResponse.ok) {
    throw new Error(`CORS preflight returned ${corsResponse.status}`);
  }
  if (allowOrigin !== frontendOrigin) {
    throw new Error(`CORS allow-origin mismatch. Expected ${frontendOrigin}, got ${allowOrigin || "<empty>"}`);
  }
  if (allowCredentials !== "true") {
    throw new Error("CORS allow-credentials is not true");
  }
  pass("backend CORS preflight", `${frontendOrigin} -> ${authSessionUrl}`);
}

function printManualChecklist(frontendUrl) {
  const frontendOrigin = normalizeOrigin(frontendUrl);
  process.stdout.write("\nINFO online manual checklist\n");
  process.stdout.write(`- Confirm Supabase Site URL is ${frontendOrigin}\n`);
  process.stdout.write(`- Confirm Supabase Redirect URLs include ${frontendOrigin}\n`);
  process.stdout.write("- Register or log in through the deployed frontend, then verify logout returns to a public route.\n");
  process.stdout.write("- Pricing: switch plan, top up credits, refresh, and confirm values persist.\n");
  process.stdout.write("- Hardware: connect, sync, refresh, and confirm logs/sync records persist.\n");
  process.stdout.write("- Live -> Review: start a live session, submit at least one turn, end session, bridge to review, and verify review detail loads.\n");
  process.stdout.write("- Account isolation: repeat with a second account and confirm Pricing/Hardware/Review data do not leak across users.\n");
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const localDryRun = readOption(
    args,
    "local-dry-run",
    "MIRO_VALIDATE_LOCAL_DRY_RUN"
  );
  const frontendUrl = readOption(args, "frontend-url", "MIRO_VALIDATE_FRONTEND_URL");
  const backendUrl = readOption(args, "backend-url", "MIRO_VALIDATE_BACKEND_URL");
  const expectedSupabaseUrl = readOption(
    args,
    "expected-supabase-url",
    "MIRO_VALIDATE_SUPABASE_URL"
  );
  const expectedFrontendOrigin = readOption(
    args,
    "expected-frontend-origin",
    "MIRO_VALIDATE_FRONTEND_ORIGIN"
  );

  await checkLocalFiles();

  if (localDryRun === "true") {
    await withLocalDryRun(async (options) => {
      await checkFrontendAndRuntime(options);
      await checkBackend(options);
      printManualChecklist(options.frontendUrl);
    });
    return;
  }

  if (!frontendUrl || !backendUrl) {
    process.stdout.write(
      "INFO remote checks skipped - provide --frontend-url and --backend-url for a deployed dry run, or use --local-dry-run.\n"
    );
    process.stdout.write(
      "INFO example: npm run validate:online -- --frontend-url https://miro.example.com --backend-url https://api.miro.example.com --expected-supabase-url https://<project-ref>.supabase.co\n"
    );
    process.stdout.write(
      "INFO local example: npm run validate:online -- --local-dry-run\n"
    );
    return;
  }

  await checkFrontendAndRuntime({
    frontendUrl,
    backendUrl,
    expectedSupabaseUrl,
    expectedFrontendOrigin,
  });
  await checkBackend({ frontendUrl, backendUrl });
  printManualChecklist(frontendUrl);
}

main().catch((error) => {
  fail("validate:online", error.message);
  process.exitCode = 1;
});
