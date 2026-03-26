const DEFAULT_API_PATH = "/api/v1";

function readRuntimeConfig(key) {
  return Object.prototype.hasOwnProperty.call(globalThis, key)
    ? globalThis[key]
    : undefined;
}

function cleanRuntimeValue(value) {
  return typeof value === "string" && value.trim() ? value.trim() : "";
}

function isHttpOrigin(origin) {
  return typeof origin === "string" && /^https?:\/\//i.test(origin);
}

function deriveSameOriginApiBase() {
  if (typeof window !== "undefined" && isHttpOrigin(window.location.origin)) {
    return `${window.location.origin}${DEFAULT_API_PATH}`;
  }
  return DEFAULT_API_PATH;
}

function deriveAuthRedirectUrl() {
  if (typeof window !== "undefined" && isHttpOrigin(window.location.origin)) {
    return window.location.origin;
  }
  return "";
}

const configuredApiBase = cleanRuntimeValue(readRuntimeConfig("MIRO_API_BASE"));
const configuredReviewApiBase = cleanRuntimeValue(
  readRuntimeConfig("MIRO_REVIEW_API_BASE")
);
const configuredSupabaseUrl = cleanRuntimeValue(
  readRuntimeConfig("MIRO_SUPABASE_URL")
);
const configuredSupabasePublishableKey = cleanRuntimeValue(
  readRuntimeConfig("MIRO_SUPABASE_PUBLISHABLE_KEY")
);
const configuredSupabaseRedirect = cleanRuntimeValue(
  readRuntimeConfig("MIRO_SUPABASE_AUTH_REDIRECT_TO")
);

export const API_BASE =
  configuredApiBase || configuredReviewApiBase || deriveSameOriginApiBase();

export const SUPABASE_URL = configuredSupabaseUrl;

export const SUPABASE_PUBLISHABLE_KEY = configuredSupabasePublishableKey;

export const SUPABASE_AUTH_REDIRECT_TO =
  configuredSupabaseRedirect || deriveAuthRedirectUrl();

export const SUPABASE_AUTH_ENABLED = Boolean(
  SUPABASE_URL && SUPABASE_PUBLISHABLE_KEY
);
