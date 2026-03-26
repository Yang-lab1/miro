const http = require("http");
const fs = require("fs/promises");
const path = require("path");
const { Readable } = require("stream");

const HOST = process.env.MIRO_SMOKE_HOST || "127.0.0.1";
const PORT = Number(process.env.MIRO_SMOKE_PORT || "4175");
const BACKEND_ORIGIN =
  process.env.MIRO_BACKEND_URL || "http://127.0.0.1:8000";
const ROOT_DIR = path.resolve(__dirname, "..");

const MIME_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".txt": "text/plain; charset=utf-8"
};

function getContentType(filePath) {
  return MIME_TYPES[path.extname(filePath).toLowerCase()] || "application/octet-stream";
}

function injectSmokeConfig(html) {
  const disableSupabase =
    process.env.MIRO_SMOKE_DISABLE_SUPABASE === "1" ||
    process.env.MIRO_SMOKE_DISABLE_SUPABASE === "true";
  const configScript = disableSupabase
    ? '<script>globalThis.MIRO_API_BASE="/api/v1";globalThis.MIRO_REVIEW_API_BASE="/api/v1";globalThis.MIRO_SUPABASE_URL="";globalThis.MIRO_SUPABASE_PUBLISHABLE_KEY="";</script>'
    : '<script>globalThis.MIRO_API_BASE="/api/v1";globalThis.MIRO_REVIEW_API_BASE="/api/v1";</script>';
  return html.includes(configScript)
    ? html
    : html.replace("</head>", `${configScript}</head>`);
}

function toFilePath(urlPathname) {
  const normalized = decodeURIComponent(urlPathname.split("?")[0]);
  const stripped = normalized === "/" ? "/index.html" : normalized;
  const safePath = path.normalize(stripped).replace(/^(\.\.[/\\])+/, "");
  return path.join(ROOT_DIR, safePath);
}

async function serveStatic(req, res, urlPathname) {
  const filePath = toFilePath(urlPathname);
  let payload;
  try {
    payload = await fs.readFile(filePath);
  } catch {
    res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("Not found");
    return;
  }

  if (filePath.endsWith("index.html")) {
    payload = Buffer.from(injectSmokeConfig(payload.toString("utf8")), "utf8");
  }

  res.writeHead(200, { "Content-Type": getContentType(filePath) });
  res.end(payload);
}

async function proxyApi(req, res) {
  const upstream = new URL(req.url, BACKEND_ORIGIN);
  const headers = new Headers();
  for (const [key, value] of Object.entries(req.headers)) {
    if (value === undefined) continue;
    if (key.toLowerCase() === "host") continue;
    headers.set(key, value);
  }

  const init = {
    method: req.method,
    headers
  };
  if (!["GET", "HEAD"].includes(req.method || "GET")) {
    init.body = req;
    init.duplex = "half";
  }

  try {
    const upstreamResponse = await fetch(upstream, init);
    const responseHeaders = {};
    upstreamResponse.headers.forEach((value, key) => {
      if (key.toLowerCase() === "content-encoding") return;
      responseHeaders[key] = value;
    });
    res.writeHead(upstreamResponse.status, responseHeaders);
    if (!upstreamResponse.body) {
      res.end();
      return;
    }
    Readable.fromWeb(upstreamResponse.body).pipe(res);
  } catch (error) {
    res.writeHead(502, { "Content-Type": "application/json; charset=utf-8" });
    res.end(
      JSON.stringify({
        error: {
          code: "smoke_proxy_failed",
          message: error.message
        }
      })
    );
  }
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || `${HOST}:${PORT}`}`);

  if (url.pathname === "/__smoke_health") {
    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
    res.end(
      JSON.stringify({
        ok: true,
        server: "miro-live-smoke-proxy",
        backendOrigin: BACKEND_ORIGIN
      })
    );
    return;
  }

  if (url.pathname === "/api/v1" || url.pathname.startsWith("/api/v1/")) {
    await proxyApi(req, res);
    return;
  }

  await serveStatic(req, res, url.pathname);
});

server.listen(PORT, HOST, () => {
  process.stdout.write(
    JSON.stringify({
      ok: true,
      server: "miro-live-smoke-proxy",
      host: HOST,
      port: PORT,
      backendOrigin: BACKEND_ORIGIN
    }) + "\n"
  );
});
