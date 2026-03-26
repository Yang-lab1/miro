import { getAccessToken } from "./supabase-client.js";
import { API_BASE } from "./runtime-config.js";

export { API_BASE };

export async function requestJsonFromBase(base, path, options = {}) {
  const { method = "GET", body, headers = {}, signal } = options;
  const requestHeaders = {
    Accept: "application/json",
    ...headers
  };
  if (!requestHeaders.Authorization) {
    const accessToken = await getAccessToken().catch(() => null);
    if (accessToken) {
      requestHeaders.Authorization = `Bearer ${accessToken}`;
    }
  }

  let payload = body;
  if (body !== undefined && body !== null && !(body instanceof FormData)) {
    requestHeaders["Content-Type"] =
      requestHeaders["Content-Type"] || "application/json";
    payload = JSON.stringify(body);
  }

  const response = await fetch(`${base}${path}`, {
    method,
    body: payload,
    headers: requestHeaders,
    signal
  });

  const rawText = await response.text();
  let data = null;

  if (rawText) {
    try {
      data = JSON.parse(rawText);
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    const error = new Error(
      data && data.error && data.error.message
        ? data.error.message
        : `API request failed with status ${response.status}.`
    );
    error.status = response.status;
    error.code = data && data.error ? data.error.code : null;
    error.payload = data;
    throw error;
  }

  return data;
}

export async function requestJson(path, options = {}) {
  return requestJsonFromBase(API_BASE, path, options);
}
