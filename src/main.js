import { navTemplate } from "./components/nav.js";
import { authModal } from "./components/auth-modal.js";
import { homePage } from "./pages/home.js";
import { livePage } from "./pages/live.js";
import { hardwarePage } from "./pages/hardware.js";
import { reviewPage } from "./pages/review.js";
import { pricingPage } from "./pages/pricing.js";
import { settingsPage } from "./pages/settings.js";
import { fetchAuthSession } from "./lib/auth-api.js";
import {
  fetchBillingPlans,
  fetchBillingSummary,
  selectBillingPlan,
  topUpBillingCredits
} from "./lib/billing-api.js";
import {
  applyBillingSummaryToUserSnapshot,
  composePricingCards,
  mapBillingSummary
} from "./lib/billing-mappers.js";
import {
  connectHardwareDevice,
  disconnectHardwareDevice,
  fetchHardwareDeviceLogs,
  fetchHardwareDeviceSyncRecords,
  fetchHardwareDevices,
  syncHardwareDevice
} from "./lib/hardware-api.js";
import { composeHardwareState, mapHardwareDevice } from "./lib/hardware-mappers.js";
import { fetchReviewDetail, fetchReviews } from "./lib/review-api.js";
import {
  getAccessToken,
  isSupabaseConfigured,
  onAuthStateChange,
  signInWithPassword,
  signOut as signOutOfSupabase,
  signUpWithPassword
} from "./lib/supabase-client.js";
import {
  mapLegacyReviewDetail,
  mapLegacyReviewListItem,
  mapReviewDetail,
  mapReviewListItem
} from "./lib/review-mappers.js";
import {
  bridgeReviewFromRealtime,
  createRealtimeSession,
  createSimulation,
  endRealtimeSession,
  fetchRealtimeAlerts,
  fetchRealtimeSession,
  fetchRealtimeSessionSummary,
  fetchRealtimeTurns,
  fetchSimulation,
  fetchVoiceProfiles,
  generateSimulationStrategy,
  respondRealtimeTurn,
  runSimulationPrecheck,
  startRealtimeSession,
  updateSimulation
} from "./lib/live-api.js";
import {
  buildFallbackVoiceProfiles,
  getCountryDisplay,
  getGoalDisplay,
  getGoalOptions,
  getMeetingTypeDisplay,
  getMeetingTypeOptions,
  getSessionStatusDisplay,
  getSeverityDisplay,
  getSimulationStatusDisplay,
  getVoiceStyleDisplay,
  getVoiceStyleOptions,
  mapCurrentSimulationToPayload,
  mapPrecheckModal,
  mapRealtimeAlert,
  mapRealtimeAlerts,
  mapRealtimeSummary,
  mapRealtimeTurn,
  mapRealtimeTurns,
  mapVoiceProfileOptions,
  mergeRealtimeSessionResponse,
  mergeSimulationResponse,
  pickVoiceProfileId
} from "./lib/live-mappers.js";

const STORAGE_KEY = "miro-prototype-state-v4";
const PUBLIC_ROUTES = new Set(["home"]);
const { ISSUE_LIBRARY, COUNTRY_LIBRARY, TESTIMONIALS, seedState } = window.MIRO_DATA;

const COPY = {
  en: {
    nav: { home: "Home", live: "Live Simulation", hardware: "Hardware Devices", review: "Review Center", pricing: "Pricing", settings: "Settings" },
    auth: { register: "Register", login: "Log In", email: "Work email", password: "Password" },
    home: {
      eyebrow: "Enterprise cross-cultural coaching",
      subtitle: "Miro helps cross-border teams rehearse high-stakes client conversations before the real meeting starts.",
      primary: "Start new simulation",
      secondary: "Open Review Center",
      metric1: "CQ score",
      metric2: "Tracked signals",
      metric3: "Repeated risks",
      twinTitle: "User Twin high-frequency pain points",
      voicesTitle: "What our users are saying",
      footerHeadline: "Prototype boundary",
      footerCopy: "Language only: wording, pauses, repetition, taboo cues, intensity, and metaphor fit.",
      footerLink1: "Live Simulation",
      footerLink2: "Hardware Devices",
      footerLink3: "Review Center"
    },
    live: {
      setupTitle: "Pre-meeting setup",
      readyCopy: "Select the country, review the strategy, and enter the meeting room when ready.",
      country: "Target country",
      meeting: "Meeting type",
      goal: "Core goal",
      duration: "Simulation duration",
      voice: "Voice style",
      constraint: "Extra constraints",
      upload: "Context injection",
      uploadHelp: "Upload PDF or TXT notes, previous emails, or meeting prep docs.",
      generate: "Generate strategy",
      generating: "Generating strategy...",
      start: "Start simulation",
      starting: "Starting simulation...",
      trackedCopy: "The current demo uses rule-based cues for language and pragmatic signals.",
      noStrategy: "Generate strategy to reveal country-specific prompts and User Twin reminders.",
      readyTitle: "Session ready",
      generated: "Generated coaching prompts",
      latestPartner: "Latest partner line",
      latestUser: "Latest user line",
      backToSetup: "Back to setup",
      liveStatus: "In session",
      countdown: "Countdown",
      roomMode: "Client simulation",
      meetingGoal: "Meeting goal",
      practice: "Practice response",
      evaluate: "Evaluate language",
      evaluating: "Evaluating...",
      end: "End session & analyze",
      ending: "Ending session...",
      drawerTitle: "Assistant drawer",
      reminders: "Reminders",
      translation: "Translation",
      transcript: "Transcript",
      toggleDrawer: "Collapse drawer",
      expandDrawer: "Expand drawer",
      emptyTranscript: "No turns yet. Evaluate a draft to begin.",
      emptyAlerts: "No alerts yet. Language warnings will appear here.",
      voiceProfile: "Voice profile",
      noVoiceProfiles: "No voice profiles are available for this country yet.",
      loadingVoices: "Loading voice profiles...",
      loadError: "Unable to load live simulation data right now.",
      fallbackMode:
        "Live API is unavailable in this mode. Using local fallback for development only.",
      continueAnyway: "Continue anyway",
      setupRevision: "Setup revision"
    },
    hardware: {
      eyebrow: "Support layer",
      connected: "Connection",
      transfer: "Data transfer",
      synced: "Last sync",
      battery: "Battery",
      sessions: "Captured sessions",
      version: "Version path",
      logTitle: "Vibration event log",
      syncTitle: "Sync records",
      openReview: "Open in Review Center",
      firmware: "Firmware",
      vibration: "Vibration events",
      loading: "Loading hardware demo state...",
      loadError: "Unable to load hardware demo state right now.",
      actionError: "Unable to update the hardware demo state right now.",
      connectAction: "Connect",
      disconnectAction: "Disconnect",
      syncAction: "Sync",
      syncing: "Syncing...",
      timelineCopy:
        "Events raised by the simulated pin during demo playback.",
      syncCopy: "Sync state, firmware path, and demo upload history.",
      demoNote:
        "This is a simulated device state for product demos, not a real connected device.",
      emptyLogs: "No hardware timeline events yet.",
      emptySyncRecords: "No sync records yet."
    },
    review: {
      eyebrow: "Unified review",
      title: "Review Center",
      records: "records",
      empty: "No review snapshots yet.",
      repeated: "Repeated issues",
      lines: "Line-by-line analysis",
      none: "None",
      loading: "Loading reviews...",
      loadError: "Unable to load reviews right now.",
      detailError: "Unable to load this review detail.",
      fallback: "Live review API is unavailable. Showing local fallback data.",
      nextStep: "Next step",
      transcriptSummary: "Session summary",
      metrics: "Session signals"
    },
    settings: {
      language: "Language",
      focus: "Prototype focus",
      dataNote: "Simulation testing data coverage",
      dataCoverage: "Collect and label transcripts, taboo lexicons, pause markers, repetition loops, intensity cues, metaphor lists, and outcomes.",
      logout: "Log out"
    },
    misc: {
      brandSub: "cultural strategist",
      sourceSimulation: "Simulation",
      sourceDevice: "Device",
      memoryUpdate: "User Twin updated with new coaching memory.",
      topupDone: "Credits added in Pricing.",
      strategyReady: "Strategy preview generated.",
      loginDone: "Signed in with Supabase.",
      logoutDone: "Signed out from Supabase.",
      requireAuth: "Log in to open this workspace.",
      online: "Online",
      offline: "Offline",
      idle: "Idle",
      healthy: "Healthy",
      warning: "Warning",
      failed: "Failed",
      syncing: "Syncing",
      high: "High",
      medium: "Medium",
      low: "Low",
      user: "User",
      partner: "Partner",
      deviceNote: "Device note"
    }
  },
  zh: null
};
COPY.zh = JSON.parse(JSON.stringify(COPY.en));
COPY.zh.nav = { home: "Home", live: "Live Simulation", hardware: "Hardware Devices", review: "Review Center", pricing: "Pricing", settings: "Settings" };
COPY.zh.auth = { register: "Register", login: "Log In", email: "Work email", password: "Password" };
COPY.zh.review.empty = "\u8fd8\u6ca1\u6709 review snapshot\u3002";
COPY.zh.review.loading = "\u6b63\u5728\u52a0\u8f7d reviews...";
COPY.zh.review.loadError = "\u65e0\u6cd5\u52a0\u8f7d review \u5217\u8868\u3002";
COPY.zh.review.detailError = "\u65e0\u6cd5\u52a0\u8f7d review \u8be6\u60c5\u3002";
COPY.zh.review.fallback =
  "\u540e\u7aef review API \u4e0d\u53ef\u7528\uff0c\u6b63\u5728\u4f7f\u7528\u672c\u5730 fallback \u6570\u636e\u3002";
COPY.zh.review.nextStep = "\u4e0b\u4e00\u6b65";
COPY.zh.review.transcriptSummary = "\u4f1a\u8bdd\u6458\u8981";
COPY.zh.review.metrics = "\u4f1a\u8bdd\u6307\u6807";
COPY.zh.misc.brandSub = "cultural strategist";

const REVIEW_MODULES = {
  en: ["Trust Building", "Pragmatic Accuracy", "Etiquette Compliance", "Pressure Management"],
  zh: ["Trust Building", "Pragmatic Accuracy", "Etiquette Compliance", "Pressure Management"]
};

const METRIC_LABELS = {
  en: { wording: "Wording", pauses: "Pauses", repetition: "Repetition", taboo: "Taboo", intensity: "Intensity", metaphor: "Metaphor" },
  zh: { wording: "Wording", pauses: "Pauses", repetition: "Repetition", taboo: "Taboo", intensity: "Intensity", metaphor: "Metaphor" }
};

const METRIC_VALUES = {
  wording: { calibrated: { en: "Calibrated", zh: "Calibrated" }, watch: { en: "Watch closely", zh: "Watch closely" }, risky: { en: "Risky", zh: "Risky" } },
  pauses: { needs_room: { en: "Needs room", zh: "Needs room" }, balanced: { en: "Balanced", zh: "Balanced" }, too_dense: { en: "Too dense", zh: "Too dense" } },
  repetition: { low: { en: "Low", zh: "Low" }, repeated: { en: "Repeated", zh: "Repeated" } },
  taboo: { clear: { en: "Clear", zh: "Clear" }, triggered: { en: "Triggered", zh: "Triggered" } },
  intensity: { measured: { en: "Measured", zh: "Measured" }, high: { en: "High", zh: "High" } },
  metaphor: { concrete: { en: "Concrete", zh: "Concrete" }, needs_simplification: { en: "Needs simplification", zh: "Needs simplification" } }
};

const TAG_LABELS = {
  "High-context": { en: "High-context", zh: "High-context" },
  "Trust-building": { en: "Trust-building", zh: "Trust-building" },
  Price: { en: "Price", zh: "Price" },
  Directness: { en: "Directness", zh: "Directness" },
  "Soft refusal": { en: "Soft refusal", zh: "Soft refusal" },
  Indirectness: { en: "Indirectness", zh: "Indirectness" },
  Pressure: { en: "Pressure", zh: "Pressure" },
  "Taboo cue": { en: "Taboo cue", zh: "Taboo cue" },
  Wearable: { en: "Wearable", zh: "Wearable" },
  Urgency: { en: "Urgency", zh: "Urgency" },
  Opening: { en: "Opening", zh: "Opening" },
  Context: { en: "Context", zh: "Context" },
  Practice: { en: "Practice", zh: "Practice" },
  Language: { en: "Language", zh: "Language" },
  "Partner response": { en: "Partner response", zh: "Partner response" }
};

const TEXT_SWITCH = {
  meetingType: {
    "First Introduction": { en: "First Introduction", zh: "First Introduction" },
    "Commercial Alignment": { en: "Commercial Alignment", zh: "Commercial Alignment" },
    "Relationship Building": { en: "Relationship Building", zh: "Relationship Building" }
  },
  goal: {
    "Establish trust before pricing": { en: "Establish trust before pricing", zh: "Establish trust before pricing" },
    "Clarify process and risk ownership": { en: "Clarify process and risk ownership", zh: "Clarify process and risk ownership" },
    "Build rapport before scope depth": { en: "Build rapport before scope depth", zh: "Build rapport before scope depth" }
  },
  voice: {
    "Formal / measured": { en: "Formal / measured", zh: "Formal / measured" },
    "Direct / structured": { en: "Direct / structured", zh: "Direct / structured" },
    "Warm / relational": { en: "Warm / relational", zh: "Warm / relational" }
  },
  plan: {
    "Enterprise Pilot": { en: "Enterprise Pilot", zh: "Enterprise Pilot" }
  },
  role: {
    "Director, Global Partnerships": { en: "Director, Global Partnerships", zh: "Director, Global Partnerships" }
  }
};

function defaultMetrics() {
  return { wording: "calibrated", pauses: "needs_room", repetition: "low", taboo: "clear", intensity: "measured", metaphor: "concrete" };
}

function normalizeMetricValue(metricKey, value) {
  if (!value) return defaultMetrics()[metricKey];
  const aliases = {
    Calibrated: "calibrated",
    "Watch closely": "watch",
    Risky: "risky",
    "Needs room": "needs_room",
    Balanced: "balanced",
    "Too dense": "too_dense",
    Low: "low",
    Repeated: "repeated",
    Clear: "clear",
    Triggered: "triggered",
    Measured: "measured",
    High: "high",
    Concrete: "concrete",
    "Needs simplification": "needs_simplification",
    "标准": "calibrated",
    "注意观察": "watch",
    "风险较高": "risky",
    "需要留白": "needs_room",
    "平衡": "balanced",
    "过于密集": "too_dense",
    "低": "low",
    "重复": "repeated",
    "清晰": "clear",
    "已触发": "triggered",
    "克制": "measured",
    "高": "high",
    "具体": "concrete",
    "需要简化": "needs_simplification"
  };
  return aliases[value] || value;
}

function normalizeMetrics(metrics) {
  const base = defaultMetrics();
  const next = { ...base };
  Object.keys(base).forEach((key) => {
    next[key] = normalizeMetricValue(key, metrics && metrics[key]);
  });
  return next;
}

function normalizeTransferHealth(value) {
  if (value === "Healthy" || value === "healthy") return "healthy";
  if (value === "warn" || value === "warning" || value === "Warning") return "warning";
  if (value === "Idle" || value === "idle") return "idle";
  if (value === "Failed" || value === "failed") return "failed";
  if (value === "Syncing" || value === "syncing") return "syncing";
  return value || "healthy";
}

function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

function defaultUserProfile() {
  return deepClone(seedState().user);
}

function defaultHardwareState() {
  const seedHardware = deepClone(seedState().hardware);
  const transferHealth = normalizeTransferHealth(seedHardware.transferHealth);
  return {
    ...seedHardware,
    deviceId: null,
    connectionState: seedHardware.connected ? "connected" : "disconnected",
    transferState: transferHealth,
    transferHealth,
    firmware: seedHardware.firmware || "-",
    firmwareVersion: seedHardware.firmware || "-",
    battery: seedHardware.battery ?? 0,
    batteryPercent: seedHardware.battery ?? 0,
    lastSync: seedHardware.lastSync || null,
    lastSyncAt: seedHardware.lastSync || null,
    capturedSessions: seedHardware.capturedSessions ?? 0,
    vibrationEvents: seedHardware.vibrationEvents ?? 0,
    logs: (seedHardware.logs || []).map((item) => ({
      ...item,
      time: item.time || item.createdAt || null,
      createdAt: item.createdAt || item.time || null
    })),
    syncRecords: (seedHardware.syncRecords || []).map((item) => ({
      ...item,
      status: normalizeTransferHealth(item.status),
      time: item.time || item.createdAt || null,
      createdAt: item.createdAt || item.time || null
    }))
  };
}

function normalizeHardwareState(hardware) {
  const base = defaultHardwareState();
  const next = {
    ...base,
    ...(hardware || {})
  };
  const transferState = normalizeTransferHealth(
    next.transferState || next.transferHealth
  );
  const lastSync = next.lastSyncAt || next.lastSync || null;
  return {
    ...next,
    connected:
      typeof next.connected === "boolean"
        ? next.connected
        : next.connectionState === "connected",
    connectionState:
      next.connectionState ||
      (next.connected ? "connected" : "disconnected"),
    transferState,
    transferHealth: transferState,
    firmware: next.firmware || next.firmwareVersion || "-",
    firmwareVersion: next.firmwareVersion || next.firmware || "-",
    battery: next.batteryPercent ?? next.battery ?? 0,
    batteryPercent: next.batteryPercent ?? next.battery ?? 0,
    lastSync,
    lastSyncAt: lastSync,
    capturedSessions: next.capturedSessions ?? 0,
    vibrationEvents: next.vibrationEvents ?? 0,
    logs: (next.logs || []).map((item) => ({
      ...item,
      time: item.time || item.createdAt || null,
      createdAt: item.createdAt || item.time || null
    })),
    syncRecords: (next.syncRecords || []).map((item) => ({
      ...item,
      status: normalizeTransferHealth(item.status),
      time: item.time || item.createdAt || null,
      createdAt: item.createdAt || item.time || null
    }))
  };
}

function isPublicRoute(route) {
  return PUBLIC_ROUTES.has(route);
}

function deriveUserNameFromEmail(email) {
  return (
    email
      .split("@")[0]
      .split(/[._-]/)
      .filter(Boolean)
      .map((item) => item.charAt(0).toUpperCase() + item.slice(1))
      .join(" ") || defaultUserProfile().name
  );
}

function createReviewCenterState() {
  return {
    listStatus: "idle",
    detailStatus: "idle",
    items: [],
    detailsById: {},
    listError: null,
    detailError: null,
    fallbackActive: false
  };
}

function createLiveCenterState() {
  return {
    routeHydrationStatus: "idle",
    voiceProfiles: [],
    voiceProfilesStatus: "idle",
    voiceProfilesError: null,
    loadedCountryKey: null,
    syncedSimulationId: null,
    simulationHydrateStatus: "idle",
    simulationHydrateError: null,
    syncedSessionId: null,
    sessionHydrateStatus: "idle",
    sessionHydrateError: null,
    bridgeRetryStatus: "idle",
    bridgeRetryError: null,
    requestStatus: {
      generate: "idle",
      start: "idle",
      respond: "idle",
      end: "idle"
    },
    listError: null,
    sessionError: null,
    fallbackActive: false,
    fallbackMode: "none",
    precheckModal: null,
    recoveryNotice: null
  };
}

function createHardwareCenterState() {
  return {
    routeHydrationStatus: "idle",
    activeDeviceId: null,
    devices: [],
    loadError: null,
    actionStatus: "idle",
    actionKind: null,
    actionError: null
  };
}

function createPricingCenterState() {
  return {
    routeHydrationStatus: "idle",
    plans: [],
    summary: null,
    loadError: null,
    actionStatus: "idle",
    actionKind: null,
    actionError: null
  };
}

let reviewListRequestVersion = 0;
let reviewDetailRequestVersion = 0;
let liveVoiceProfilesRequestVersion = 0;
let liveSimulationRequestVersion = 0;
let liveSessionRequestVersion = 0;
let hardwareRouteRequestVersion = 0;
let pricingRouteRequestVersion = 0;

function createWorkspaceBootstrapState() {
  return {
    actorKey: null,
    requestVersion: 0,
    billingStatus: "idle",
    hardwareStatus: "idle"
  };
}

let workspaceBootstrapState = createWorkspaceBootstrapState();
let authBootstrapReady = !isSupabaseConfigured();

function prefersLocalReviewFallback() {
  return window.location.protocol === "file:";
}

function prefersLocalLiveFallback() {
  return window.location.protocol === "file:";
}

function normalizeCurrentSimulation(simulation) {
  return {
    ...simulation,
    simulationId: simulation.simulationId || null,
    simulationStatus: simulation.simulationStatus || "draft",
    sessionId: simulation.sessionId || null,
    realtimeStatus: simulation.realtimeStatus || null,
    recentReviewId: simulation.recentReviewId || null,
    recentCompletedSessionId: simulation.recentCompletedSessionId || null,
    lastCompletionStatus: simulation.lastCompletionStatus || null,
    voiceProfileId: simulation.voiceProfileId || null,
    setupRevision: simulation.setupRevision || 0,
    strategyForSetupRevision: simulation.strategyForSetupRevision || null,
    strategySummary: simulation.strategySummary || null,
    sessionSummary: simulation.sessionSummary || null
  };
}

function loadState() {
  const seed = seedState();
  const normalizeSeed = {
    ...seed,
    hardware: normalizeHardwareState(seed.hardware),
    currentSimulation: normalizeCurrentSimulation({
      ...seed.currentSimulation,
      metrics: normalizeMetrics(seed.currentSimulation.metrics),
      phase: "setup"
    }),
    pricingSelection: seed.pricingSelection || "free",
    reviewCenter: createReviewCenterState(),
    liveCenter: createLiveCenterState(),
    hardwareCenter: createHardwareCenterState(),
    pricingCenter: createPricingCenterState()
  };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return normalizeSeed;
    const parsed = JSON.parse(raw);
    const merged = {
      ...normalizeSeed,
      ...parsed,
      user: { ...normalizeSeed.user, ...(parsed.user || {}) },
      hardware: normalizeHardwareState({
        ...normalizeSeed.hardware,
        ...(parsed.hardware || {})
      }),
      currentSimulation: { ...normalizeSeed.currentSimulation, ...(parsed.currentSimulation || {}) },
      userTwin: parsed.userTwin && parsed.userTwin.length ? parsed.userTwin : normalizeSeed.userTwin,
      reviews: parsed.reviews && parsed.reviews.length ? parsed.reviews : normalizeSeed.reviews
    };
    merged.currentSimulation = normalizeCurrentSimulation({
      ...merged.currentSimulation,
      metrics: normalizeMetrics(merged.currentSimulation.metrics),
      phase: merged.currentSimulation.phase || "setup"
    });
    merged.reviewCenter = createReviewCenterState();
    merged.liveCenter = createLiveCenterState();
    merged.hardwareCenter = createHardwareCenterState();
    merged.pricingCenter = createPricingCenterState();
    return merged;
  } catch (error) {
    return normalizeSeed;
  }
}

let state = loadState();

function saveState() {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      ...state,
      reviewCenter: undefined,
      liveCenter: undefined,
      hardwareCenter: undefined,
      pricingCenter: undefined,
      toast: null,
      authOpen: false,
      pendingRoute: null
    })
  );
}

function resetProtectedWorkspace() {
  state.reviewCenter = createReviewCenterState();
  state.liveCenter = createLiveCenterState();
  state.hardwareCenter = createHardwareCenterState();
  state.pricingCenter = createPricingCenterState();
}

function getProtectedActorKey() {
  if (!state.loggedIn) return null;
  return state.user.email || "__authenticated__";
}

function resetWorkspaceBootstrapState({
  actorKey = getProtectedActorKey()
} = {}) {
  workspaceBootstrapState.actorKey = actorKey;
  workspaceBootstrapState.requestVersion += 1;
  workspaceBootstrapState.billingStatus = "idle";
  workspaceBootstrapState.hardwareStatus = "idle";
}

function syncWorkspaceBootstrapActorKey() {
  const actorKey = getProtectedActorKey();
  if (workspaceBootstrapState.actorKey !== actorKey) {
    workspaceBootstrapState.actorKey = actorKey;
    workspaceBootstrapState.billingStatus = "idle";
    workspaceBootstrapState.hardwareStatus = "idle";
  }
  return actorKey;
}

function canApplyWorkspaceBootstrap(actorKey, requestVersion) {
  return Boolean(actorKey) &&
    state.loggedIn &&
    workspaceBootstrapState.actorKey === actorKey &&
    workspaceBootstrapState.requestVersion === requestVersion;
}

function markWorkspaceBootstrapReady(domain) {
  workspaceBootstrapState.actorKey = getProtectedActorKey();
  workspaceBootstrapState[`${domain}Status`] = "ready";
}

function applyAuthenticatedUser(authSession) {
  const fallbackUser = defaultUserProfile();
  const previousActorKey = getProtectedActorKey();
  const nextName =
    authSession.user.fullName ||
    state.user.name ||
    deriveUserNameFromEmail(authSession.user.email);
  const nextActorKey = authSession.user.email || "__authenticated__";
  const actorChanged = previousActorKey !== nextActorKey;

  if (!state.loggedIn || actorChanged) {
    state.hardware = defaultHardwareState();
    resetProtectedWorkspace();
    resetWorkspaceBootstrapState({ actorKey: nextActorKey });
  } else {
    syncWorkspaceBootstrapActorKey();
  }

  state.loggedIn = true;
  state.authOpen = false;
  state.user = {
    ...fallbackUser,
    ...state.user,
    name: nextName,
    email: authSession.user.email,
    company: authSession.user.companyName || state.user.company || fallbackUser.company,
    role: authSession.user.roleTitle || state.user.role || fallbackUser.role,
    plan: fallbackUser.plan,
    balance: fallbackUser.balance,
    renewal: fallbackUser.renewal
  };
  state.pricingSelection = seedState().pricingSelection || "free";
  workspaceBootstrapState.actorKey = nextActorKey;
  authBootstrapReady = true;

  if (authSession.user.preferredLanguage === "zh") state.lang = "zh";
  if (authSession.user.preferredLanguage === "en") state.lang = "en";
}

function clearAuthenticatedUser() {
  const fallbackUser = defaultUserProfile();
  state.loggedIn = false;
  state.authOpen = false;
  state.authMode = "login";
  state.pendingRoute = null;
  state.user = { ...fallbackUser };
  state.pricingSelection = seedState().pricingSelection || "free";
  state.hardware = defaultHardwareState();
  resetProtectedWorkspace();
  resetWorkspaceBootstrapState({ actorKey: null });
}

function ensurePublicRouteForLoggedOutUser() {
  if (!state.loggedIn && !isPublicRoute(state.activeRoute)) {
    state.pendingRoute = state.activeRoute;
    state.activeRoute = "home";
  }
}

function t() {
  return COPY[state.lang];
}

function pick(text) {
  if (typeof text === "string") return text;
  return state.lang === "zh" ? text.zh : text.en;
}

function translateByGroup(group, value) {
  return TEXT_SWITCH[group][value] ? TEXT_SWITCH[group][value][state.lang] : value;
}

function metricLabel(metricKey) {
  return METRIC_LABELS[state.lang][metricKey];
}

function metricValueLabel(metricKey, metricValue) {
  const normalized = normalizeMetricValue(metricKey, metricValue);
  return METRIC_VALUES[metricKey][normalized] ? METRIC_VALUES[metricKey][normalized][state.lang] : normalized;
}

function riskLabel(value) {
  const key = value ? value.toLowerCase() : "medium";
  return t().misc[key] || value;
}

function statusLabel(value) {
  const key = normalizeTransferHealth(value);
  return t().misc[key] || value;
}

function speakerLabel(value) {
  if (value === "user") return t().misc.user;
  if (value === "assistant") return t().misc.partner;
  if (value === "User") return t().misc.user;
  if (value === "Partner") return t().misc.partner;
  if (value === "Device note") return t().misc.deviceNote;
  return value;
}

function tagLabel(tag) {
  return TAG_LABELS[tag] ? TAG_LABELS[tag][state.lang] : tag;
}

function issueText(issueKey) {
  if (!ISSUE_LIBRARY[issueKey]) {
    return {
      title: issueKey,
      short: issueKey,
      detail: issueKey
    };
  }
  return ISSUE_LIBRARY[issueKey][state.lang];
}

function formatDate(value) {
  if (!value) return "—";
  const parsedDate = new Date(value);
  if (Number.isNaN(parsedDate.getTime())) return "—";
  return new Intl.DateTimeFormat(state.lang === "zh" ? "zh-CN" : "en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(parsedDate);
}

function formatBalance(value) {
  return new Intl.NumberFormat(state.lang === "zh" ? "zh-CN" : "en-US").format(value);
}

function initials(name) {
  return name.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase();
}

function joinMeta(...parts) {
  return parts.filter(Boolean).join(" / ");
}
function getCountry(key) {
  return COUNTRY_LIBRARY[key] || COUNTRY_LIBRARY.Japan;
}

function mapFallbackReviewItems() {
  return (state.reviews || []).map((review) => mapLegacyReviewListItem(review));
}

function mapFallbackReviewDetails() {
  return Object.fromEntries(
    (state.reviews || []).map((review) => [review.id, mapLegacyReviewDetail(review)])
  );
}

function getReviewItems() {
  return state.reviewCenter.items;
}

function getSelectedReviewCard() {
  const items = getReviewItems();
  return items.find((item) => item.id === state.selectedReviewId) || items[0] || null;
}

function getSelectedReview() {
  const selected = getSelectedReviewCard();
  if (!selected) return null;
  return state.reviewCenter.detailsById[selected.id] || null;
}

async function loadReviewDetail(reviewId) {
  if (!reviewId) return;

  state.selectedReviewId = reviewId;

  if (state.reviewCenter.fallbackActive) {
    render();
    return;
  }

  const cachedDetail = state.reviewCenter.detailsById[reviewId];
  if (cachedDetail) {
    state.reviewCenter.detailStatus = "ready";
    state.reviewCenter.detailError = null;
    render();
    return;
  }

  const requestVersion = ++reviewDetailRequestVersion;
  state.reviewCenter.detailStatus = "loading";
  state.reviewCenter.detailError = null;
  render();

  try {
    const apiDetail = await fetchReviewDetail(reviewId);
    if (requestVersion !== reviewDetailRequestVersion) return;

    const mappedDetail = mapReviewDetail(apiDetail);
    state.reviewCenter.detailsById[reviewId] = mappedDetail;
    state.reviewCenter.items = state.reviewCenter.items.map((item) =>
      item.id === reviewId ? { ...item, summary: mappedDetail.summary } : item
    );
    state.reviewCenter.detailStatus = "ready";
    state.reviewCenter.detailError = null;
    render();
  } catch (error) {
    if (requestVersion !== reviewDetailRequestVersion) return;
    console.error("Failed to load review detail", error);
    state.reviewCenter.detailStatus = "error";
    state.reviewCenter.detailError = error;
    render();
  }
}

async function ensureReviewCenterLoaded({ force = false } = {}) {
  if (!state.loggedIn) return;

  if (
    !force &&
    (state.reviewCenter.listStatus === "loading" ||
      (state.reviewCenter.listStatus === "ready" && state.reviewCenter.items.length) ||
      state.reviewCenter.listStatus === "empty")
  ) {
    if (state.activeRoute === "review" && state.selectedReviewId) {
      await loadReviewDetail(state.selectedReviewId);
    }
    return;
  }

  const requestVersion = ++reviewListRequestVersion;
  state.reviewCenter.listStatus = "loading";
  state.reviewCenter.listError = null;
  state.reviewCenter.detailError = null;
  state.reviewCenter.fallbackActive = false;
  state.reviewCenter.items = [];
  state.reviewCenter.detailsById = {};
  render();

  if (prefersLocalReviewFallback()) {
    const fallbackItems = mapFallbackReviewItems();
    state.reviewCenter.items = fallbackItems;
    state.reviewCenter.detailsById = mapFallbackReviewDetails();
    state.reviewCenter.fallbackActive = fallbackItems.length > 0;
    state.reviewCenter.listError = new Error(
      "Review API is not used in file preview mode."
    );
    state.reviewCenter.listStatus = fallbackItems.length ? "ready" : "error";
    state.reviewCenter.detailStatus = fallbackItems.length ? "ready" : "idle";
    state.selectedReviewId =
      fallbackItems.find((item) => item.id === state.selectedReviewId)?.id ||
      fallbackItems[0]?.id ||
      null;
    render();
    return;
  }

  try {
    const apiItems = await fetchReviews();
    if (requestVersion !== reviewListRequestVersion) return;

    const mappedItems = apiItems.map((item) => mapReviewListItem(item));
    state.reviewCenter.items = mappedItems;
    state.reviewCenter.listStatus = mappedItems.length ? "ready" : "empty";
    state.reviewCenter.listError = null;
    state.reviewCenter.fallbackActive = false;
    state.selectedReviewId =
      mappedItems.find((item) => item.id === state.selectedReviewId)?.id ||
      mappedItems[0]?.id ||
      null;
    state.reviewCenter.detailStatus = state.selectedReviewId ? "loading" : "idle";
    render();

    if (state.selectedReviewId) {
      await loadReviewDetail(state.selectedReviewId);
    }
  } catch (error) {
    if (requestVersion !== reviewListRequestVersion) return;
    console.error("Failed to load review list", error);
    const fallbackItems = mapFallbackReviewItems();
    state.reviewCenter.items = fallbackItems;
    state.reviewCenter.detailsById = mapFallbackReviewDetails();
    state.reviewCenter.fallbackActive = fallbackItems.length > 0;
    state.reviewCenter.listError = error;
    state.reviewCenter.listStatus = fallbackItems.length ? "ready" : "error";
    state.reviewCenter.detailStatus = fallbackItems.length ? "ready" : "idle";
    state.selectedReviewId =
      fallbackItems.find((item) => item.id === state.selectedReviewId)?.id ||
      fallbackItems[0]?.id ||
      null;
    render();
  }
}

function createReviewListItemFromDetail(detail) {
  return {
    id: detail.id,
    sourceType: detail.sourceType,
    source: detail.source,
    title: detail.title,
    country: detail.country,
    meetingType: detail.meetingType,
    goal: detail.goal,
    date: detail.createdAt,
    createdAt: detail.createdAt,
    endedAt: detail.endedAt,
    status: detail.status,
    overallAssessment: detail.overallAssessment,
    assessmentLabel: detail.assessmentLabel,
    repeatedIssues: detail.repeatedIssues,
    summary: detail.summary
  };
}

function createLiveFallbackOpeningTurn() {
  const country = getCountry(state.currentSimulation.country);
  const turnId = `fallback-opening-${Date.now()}`;
  return {
    id: turnId,
    turnId,
    turnIndex: 1,
    speaker: "Partner",
    local: country.localOpening,
    en: country.openingEn,
    zh: country.openingZh,
    tags: ["Opening", "Context"],
    issueKey: null
  };
}

function setLiveRequestStatus(key, status) {
  state.liveCenter.requestStatus[key] = status;
}

function setLiveListError(error) {
  state.liveCenter.listError = error;
}

function setLiveSessionError(error) {
  state.liveCenter.sessionError = error;
}

function setVoiceProfilesError(error) {
  state.liveCenter.voiceProfilesError = error;
}

function setSimulationHydrateError(error) {
  state.liveCenter.simulationHydrateError = error;
}

function setSessionHydrateError(error) {
  state.liveCenter.sessionHydrateError = error;
}

function setBridgeRetryError(error) {
  state.liveCenter.bridgeRetryError = error;
}

function clearLiveHydrationErrors() {
  setVoiceProfilesError(null);
  setSimulationHydrateError(null);
  setSessionHydrateError(null);
}

function isHardLiveFallback() {
  return state.liveCenter.fallbackActive && state.liveCenter.fallbackMode === "hard";
}

function clearLiveFallback() {
  state.liveCenter.fallbackActive = false;
  state.liveCenter.fallbackMode = "none";
  state.liveCenter.listError = null;
}

function syncLiveRecoveryNotice() {
  if (state.liveCenter.bridgeRetryError && state.currentSimulation.recentCompletedSessionId) {
    state.liveCenter.recoveryNotice = {
      kind: "bridge_failed",
      sessionId: state.currentSimulation.recentCompletedSessionId,
      reviewId: state.currentSimulation.recentReviewId || null
    };
    return;
  }

  if (
    state.currentSimulation.phase !== "session" &&
    state.currentSimulation.sessionId &&
    state.currentSimulation.realtimeStatus === "active"
  ) {
    state.liveCenter.recoveryNotice = {
      kind: "active_session_hidden",
      sessionId: state.currentSimulation.sessionId
    };
    return;
  }

  if (
    state.currentSimulation.sessionId &&
    state.currentSimulation.realtimeStatus === "pending"
  ) {
    state.liveCenter.recoveryNotice = {
      kind: "pending_session",
      sessionId: state.currentSimulation.sessionId
    };
    return;
  }

  if (
    state.currentSimulation.lastCompletionStatus &&
    state.currentSimulation.recentCompletedSessionId
  ) {
    state.liveCenter.recoveryNotice = {
      kind: "completed_session",
      status: state.currentSimulation.lastCompletionStatus,
      sessionId: state.currentSimulation.recentCompletedSessionId,
      reviewId: state.currentSimulation.recentReviewId || null
    };
    return;
  }

  state.liveCenter.recoveryNotice = null;
}

function clearLiveRuntime({
  preserveSimulation = true,
  preserveSessionLink = false,
  preserveRealtimeStatus = false
} = {}) {
  const preservedSessionId = preserveSessionLink
    ? state.currentSimulation.sessionId
    : null;
  const preservedRealtimeStatus = preserveRealtimeStatus
    ? state.currentSimulation.realtimeStatus
    : null;
  state.currentSimulation.phase = "setup";
  state.currentSimulation.sessionId = preservedSessionId;
  state.currentSimulation.realtimeStatus = preservedRealtimeStatus;
  state.currentSimulation.transcript = [];
  state.currentSimulation.alerts = [];
  state.currentSimulation.practiceText = "";
  state.currentSimulation.sessionSummary = null;
  state.currentSimulation.countdown = state.currentSimulation.duration * 60;
  state.drawerCollapsed = false;
  state.liveCenter.syncedSessionId = preserveSessionLink
    ? preservedSessionId
    : null;
  state.liveCenter.sessionHydrateStatus = preserveSessionLink ? "ready" : "idle";
  setSessionHydrateError(null);
  if (!preserveSimulation) {
    state.currentSimulation.simulationId = null;
    state.liveCenter.syncedSimulationId = null;
  }
}

function markLiveSetupDirty() {
  state.currentSimulation.strategies = [];
  state.currentSimulation.strategySummary = null;
  state.currentSimulation.simulationStatus =
    state.currentSimulation.simulationId || state.currentSimulation.setupRevision
      ? "draft"
      : state.currentSimulation.simulationStatus;
  state.liveCenter.syncedSimulationId = null;
}

function activateLiveFallback(message, { mode = "soft" } = {}) {
  state.liveCenter.fallbackActive = true;
  state.liveCenter.fallbackMode = mode;
  state.liveCenter.listError = message ? new Error(message) : null;

  if (mode === "soft") {
    if (
      !state.liveCenter.voiceProfiles.length ||
      state.liveCenter.loadedCountryKey !== state.currentSimulation.country
    ) {
      state.liveCenter.voiceProfiles = buildFallbackVoiceProfiles(
        state.currentSimulation.country
      );
      state.liveCenter.voiceProfilesStatus = state.liveCenter.voiceProfiles.length
        ? "ready"
        : "empty";
      state.liveCenter.loadedCountryKey = state.currentSimulation.country;
      if (!state.currentSimulation.voiceProfileId) {
        state.currentSimulation.voiceProfileId = pickVoiceProfileId(
          state.liveCenter.voiceProfiles,
          null
        );
      }
    }
    syncLiveRecoveryNotice();
    return;
  }

  state.liveCenter.sessionError = null;
  state.liveCenter.voiceProfilesError = null;
  state.liveCenter.simulationHydrateError = null;
  state.liveCenter.sessionHydrateError = null;
  state.liveCenter.bridgeRetryError = null;
  state.liveCenter.recoveryNotice = null;
  state.currentSimulation.simulationId = null;
  state.currentSimulation.sessionId = null;
  state.currentSimulation.simulationStatus = "draft";
  state.currentSimulation.realtimeStatus = null;
  state.currentSimulation.setupRevision = 0;
  state.currentSimulation.strategyForSetupRevision = null;
  state.currentSimulation.recentCompletedSessionId = null;
  state.currentSimulation.recentReviewId = null;
  state.currentSimulation.lastCompletionStatus = null;
  state.currentSimulation.strategies = [];
  state.currentSimulation.strategySummary = null;
  state.currentSimulation.transcript = [];
  state.currentSimulation.alerts = [];
  state.currentSimulation.sessionSummary = null;
  state.currentSimulation.phase = "setup";
  state.liveCenter.voiceProfiles = buildFallbackVoiceProfiles(
    state.currentSimulation.country
  );
  state.liveCenter.voiceProfilesStatus = state.liveCenter.voiceProfiles.length
    ? "ready"
    : "empty";
  state.liveCenter.loadedCountryKey = state.currentSimulation.country;
  state.currentSimulation.voiceProfileId = pickVoiceProfileId(
    state.liveCenter.voiceProfiles,
    state.currentSimulation.voiceProfileId
  );
}

function upsertTranscriptTurns(turns) {
  const nextTurns = [...state.currentSimulation.transcript];
  const turnMap = new Map(
    nextTurns.map((turn) => [turn.turnId || turn.id, turn])
  );

  turns.forEach((turn) => {
    turnMap.set(turn.turnId || turn.id, turn);
  });

  state.currentSimulation.transcript = Array.from(turnMap.values()).sort(
    (left, right) => (left.turnIndex || 0) - (right.turnIndex || 0)
  );
}

function upsertAlerts(alerts, { prepend = false } = {}) {
  const alertMap = new Map(
    state.currentSimulation.alerts.map((alert) => [alert.alertId || alert.id, alert])
  );

  alerts.forEach((alert) => {
    alertMap.set(alert.alertId || alert.id, alert);
  });

  const merged = Array.from(alertMap.values()).sort((left, right) => {
    return new Date(right.createdAt || 0) - new Date(left.createdAt || 0);
  });

  state.currentSimulation.alerts = prepend ? merged : merged;
}

function applySessionSummary(summary) {
  if (!summary) return;
  state.currentSimulation.sessionSummary = mapRealtimeSummary(summary);
  state.currentSimulation.realtimeStatus = summary.status;
}

function applySimulationSnapshot(apiSimulation) {
  state.currentSimulation = mergeSimulationResponse(
    state.currentSimulation,
    apiSimulation
  );
}

function applyRealtimeSessionSnapshot(apiSession) {
  state.currentSimulation = mergeRealtimeSessionResponse(
    state.currentSimulation,
    apiSession
  );
}

function hydrateReviewCenterFromApiDetail(apiDetail) {
  const mappedDetail = mapReviewDetail(apiDetail);
  const mappedItem = createReviewListItemFromDetail(mappedDetail);
  const existingIndex = state.reviewCenter.items.findIndex(
    (item) => item.id === mappedItem.id
  );

  if (existingIndex >= 0) {
    state.reviewCenter.items[existingIndex] = mappedItem;
  } else {
    state.reviewCenter.items = [mappedItem, ...state.reviewCenter.items];
  }

  state.reviewCenter.detailsById[mappedDetail.id] = mappedDetail;
  state.reviewCenter.listStatus = "ready";
  state.reviewCenter.detailStatus = "ready";
  state.reviewCenter.listError = null;
  state.reviewCenter.detailError = null;
  state.reviewCenter.fallbackActive = false;
  state.selectedReviewId = mappedDetail.id;
}

function openPrecheckModal(precheck) {
  const modalCopy = mapPrecheckModal(precheck);
  return new Promise((resolve) => {
    state.liveCenter.precheckModal = {
      open: true,
      ...modalCopy,
      resolve
    };
    render();
  });
}

function closePrecheckModal(choice) {
  const modal = state.liveCenter.precheckModal;
  if (!modal) return;
  state.liveCenter.precheckModal = null;
  render();
  if (typeof modal.resolve === "function") {
    modal.resolve(choice);
  }
}

async function ensureVoiceProfilesLoaded({ force = false, allowFallback = false } = {}) {
  if (!state.loggedIn) return;

  if (prefersLocalLiveFallback()) {
    if (!state.liveCenter.fallbackActive || force) {
      activateLiveFallback("Live API is not used in file preview mode.", {
        mode: "hard"
      });
      render();
    }
    return;
  }

  if (
    !force &&
    !state.liveCenter.fallbackActive &&
    state.liveCenter.loadedCountryKey === state.currentSimulation.country &&
    (state.liveCenter.voiceProfilesStatus === "ready" ||
      state.liveCenter.voiceProfilesStatus === "empty" ||
      state.liveCenter.voiceProfilesStatus === "loading")
  ) {
    return;
  }

  const requestVersion = ++liveVoiceProfilesRequestVersion;
  state.liveCenter.voiceProfilesStatus = "loading";
  state.liveCenter.loadedCountryKey = state.currentSimulation.country;
  clearLiveFallback();
  setVoiceProfilesError(null);
  render();

  try {
    const apiProfiles = await fetchVoiceProfiles(state.currentSimulation.country);
    if (requestVersion !== liveVoiceProfilesRequestVersion) return;

    state.liveCenter.voiceProfiles = mapVoiceProfileOptions(apiProfiles);
    state.liveCenter.voiceProfilesStatus = state.liveCenter.voiceProfiles.length
      ? "ready"
      : "empty";
    clearLiveFallback();
    setVoiceProfilesError(null);
    state.currentSimulation.voiceProfileId = pickVoiceProfileId(
      state.liveCenter.voiceProfiles,
      state.currentSimulation.voiceProfileId
    );
    syncLiveRecoveryNotice();
    saveState();
    render();
  } catch (error) {
    if (requestVersion !== liveVoiceProfilesRequestVersion) return;
    console.error("Failed to load live voice profiles", error);
    if (allowFallback) {
      setVoiceProfilesError(error);
      activateLiveFallback(error.message, { mode: "soft" });
    } else {
      state.liveCenter.voiceProfiles = [];
      state.liveCenter.voiceProfilesStatus = "error";
      setVoiceProfilesError(error);
    }
    syncLiveRecoveryNotice();
    saveState();
    render();
  }
}

async function hydrateSimulationSnapshot(simulationId, { force = false } = {}) {
  if (!simulationId || isHardLiveFallback()) return;
  if (!force && state.liveCenter.syncedSimulationId === simulationId) return;

  const requestVersion = ++liveSimulationRequestVersion;
  state.liveCenter.simulationHydrateStatus = "loading";
  setSimulationHydrateError(null);
  render();

  try {
    const apiSimulation = await fetchSimulation(simulationId);
    if (requestVersion !== liveSimulationRequestVersion) return;
    applySimulationSnapshot(apiSimulation);
    clearLiveFallback();
    if (state.liveCenter.loadedCountryKey !== state.currentSimulation.country) {
      state.liveCenter.loadedCountryKey = null;
      state.liveCenter.voiceProfiles = [];
      state.liveCenter.voiceProfilesStatus = "idle";
    }
    state.liveCenter.syncedSimulationId = simulationId;
    state.liveCenter.simulationHydrateStatus = "ready";
    setSimulationHydrateError(null);
    syncLiveRecoveryNotice();
    saveState();
    render();
  } catch (error) {
    if (requestVersion !== liveSimulationRequestVersion) return;
    console.error("Failed to hydrate simulation snapshot", error);
    state.liveCenter.simulationHydrateStatus = "error";
    setSimulationHydrateError(error);
    syncLiveRecoveryNotice();
    render();
  }
}

async function hydrateRealtimeSession(sessionId, { force = false } = {}) {
  if (!sessionId || isHardLiveFallback()) return;
  if (!force && state.liveCenter.syncedSessionId === sessionId) return;

  const requestVersion = ++liveSessionRequestVersion;
  state.liveCenter.sessionHydrateStatus = "loading";
  setSessionHydrateError(null);
  render();

  try {
    const apiSession = await fetchRealtimeSession(sessionId);
    if (requestVersion !== liveSessionRequestVersion) return;

    applyRealtimeSessionSnapshot(apiSession);
    clearLiveFallback();

    const [summaryResult, turnsResult, alertsResult] = await Promise.allSettled([
      fetchRealtimeSessionSummary(sessionId),
      fetchRealtimeTurns(sessionId),
      fetchRealtimeAlerts(sessionId)
    ]);
    if (requestVersion !== liveSessionRequestVersion) return;

    const hydrateErrors = [];

    if (summaryResult.status === "fulfilled") {
      applySessionSummary(summaryResult.value);
    } else {
      hydrateErrors.push(summaryResult.reason);
    }

    if (turnsResult.status === "fulfilled") {
      state.currentSimulation.transcript = mapRealtimeTurns(turnsResult.value);
    } else {
      hydrateErrors.push(turnsResult.reason);
    }

    if (alertsResult.status === "fulfilled") {
      state.currentSimulation.alerts = mapRealtimeAlerts(alertsResult.value);
    } else {
      hydrateErrors.push(alertsResult.reason);
    }

    if (apiSession.status === "active") {
      state.currentSimulation.phase = "session";
      state.liveCenter.syncedSessionId = sessionId;
    } else if (apiSession.status === "pending") {
      clearLiveRuntime({
        preserveSimulation: true,
        preserveSessionLink: true,
        preserveRealtimeStatus: true
      });
      state.currentSimulation.sessionId = apiSession.sessionId;
      state.currentSimulation.realtimeStatus = apiSession.status;
      state.liveCenter.syncedSessionId = sessionId;
    } else {
      state.currentSimulation.recentCompletedSessionId = apiSession.sessionId;
      state.currentSimulation.lastCompletionStatus = apiSession.status;
      clearLiveRuntime();
    }

    state.liveCenter.sessionHydrateStatus = hydrateErrors.length
      ? apiSession.status === "active"
        ? "partial"
        : "ready"
      : "ready";
    setSessionHydrateError(hydrateErrors[0] || null);
    syncLiveRecoveryNotice();

    saveState();
    render();
  } catch (error) {
    if (requestVersion !== liveSessionRequestVersion) return;
    console.error("Failed to hydrate realtime session", error);
    state.liveCenter.sessionHydrateStatus = "error";
    setSessionHydrateError(error);
    if (state.currentSimulation.realtimeStatus === "active") {
      state.currentSimulation.phase = "session";
    }
    syncLiveRecoveryNotice();
    render();
  }
}

async function ensureLiveRouteReady({ force = false } = {}) {
  if (!state.loggedIn || state.activeRoute !== "live") return;
  if (!force && state.liveCenter.routeHydrationStatus === "loading") return;

  state.liveCenter.routeHydrationStatus = "loading";
  setLiveListError(null);
  setLiveSessionError(null);
  try {
    await ensureVoiceProfilesLoaded({ force, allowFallback: true });
    if (isHardLiveFallback()) {
      state.liveCenter.routeHydrationStatus = "ready";
      return;
    }

    if (state.currentSimulation.simulationId) {
      const countryBeforeHydrate = state.currentSimulation.country;
      await hydrateSimulationSnapshot(state.currentSimulation.simulationId, { force });
      if (
        countryBeforeHydrate !== state.currentSimulation.country ||
        state.liveCenter.loadedCountryKey !== state.currentSimulation.country ||
        state.liveCenter.voiceProfilesStatus === "idle"
      ) {
        await ensureVoiceProfilesLoaded({ force: true, allowFallback: true });
        if (isHardLiveFallback()) {
          state.liveCenter.routeHydrationStatus = "ready";
          return;
        }
      }
    }

    if (state.currentSimulation.sessionId) {
      await hydrateRealtimeSession(state.currentSimulation.sessionId, { force });
    }

    syncLiveRecoveryNotice();
    state.liveCenter.routeHydrationStatus = "ready";
    render();
  } catch (error) {
    state.liveCenter.routeHydrationStatus = "error";
    throw error;
  }
}

async function syncSimulationSetupToBackend() {
  if (isHardLiveFallback()) return null;

  const payload = mapCurrentSimulationToPayload(state.currentSimulation);
  const apiSimulation = state.currentSimulation.simulationId
    ? await updateSimulation(state.currentSimulation.simulationId, payload)
    : await createSimulation(payload);

  applySimulationSnapshot(apiSimulation);
  clearLiveFallback();
  state.liveCenter.syncedSimulationId = apiSimulation.simulationId;
  state.liveCenter.simulationHydrateStatus = "ready";
  setSimulationHydrateError(null);
  syncLiveRecoveryNotice();
  saveState();
  return apiSimulation;
}

async function generateLiveStrategy() {
  if (isHardLiveFallback()) {
    buildStrategies();
    pushToast(t().misc.strategyReady);
    render();
    return;
  }

  setLiveRequestStatus("generate", "loading");
  setLiveSessionError(null);
  render();

  try {
    const syncedSimulation = await syncSimulationSetupToBackend();
    const apiSimulation = await generateSimulationStrategy(
      syncedSimulation.simulationId
    );
    applySimulationSnapshot(apiSimulation);
    state.liveCenter.syncedSimulationId = apiSimulation.simulationId;
    saveState();
    pushToast(t().misc.strategyReady);
  } catch (error) {
    console.error("Failed to generate live strategy", error);
    setLiveSessionError(error);
    pushToast(error.message || t().live.loadError);
  } finally {
    setLiveRequestStatus("generate", "idle");
    render();
  }
}

async function confirmPrecheckIfNeeded(precheck) {
  if (precheck.ready) return true;

  if (
    precheck.reason === "learning_required" ||
    precheck.reason === "learning_outdated"
  ) {
    const decision = await openPrecheckModal(precheck);
    return decision === "continue";
  }

  throw new Error("This setup is not ready for live simulation yet.");
}

async function startLiveSession() {
  if (isHardLiveFallback()) {
    if (!state.currentSimulation.strategies.length) {
      buildStrategies();
    }
    state.currentSimulation.phase = "session";
    state.currentSimulation.sessionId = `fallback-session-${Date.now()}`;
    state.currentSimulation.transcript = [createLiveFallbackOpeningTurn()];
    state.currentSimulation.alerts = [];
    state.currentSimulation.sessionSummary = {
      status: "active",
      turnCount: 1,
      alertCount: 0,
      lastAlertSeverity: null
    };
    saveState();
    render();
    return;
  }

  setLiveRequestStatus("start", "loading");
  setLiveSessionError(null);
  render();

  try {
    let syncedSimulation = await syncSimulationSetupToBackend();
    if (!syncedSimulation.strategy) {
      syncedSimulation = await generateSimulationStrategy(
        syncedSimulation.simulationId
      );
      applySimulationSnapshot(syncedSimulation);
    }

    const precheck = await runSimulationPrecheck(state.currentSimulation.country);
    const shouldContinue = await confirmPrecheckIfNeeded(precheck);
    if (!shouldContinue) {
      return;
    }

    const createdSession = await createRealtimeSession(
      syncedSimulation.simulationId,
      "webrtc"
    );
    const startedSession = await startRealtimeSession(createdSession.sessionId);
    applyRealtimeSessionSnapshot(startedSession);
    state.currentSimulation.phase = "session";
    state.currentSimulation.sessionId = startedSession.sessionId;
    state.currentSimulation.realtimeStatus = startedSession.status;
    state.currentSimulation.countdown = state.currentSimulation.duration * 60;
    state.currentSimulation.lastCompletionStatus = null;
    state.liveCenter.bridgeRetryStatus = "idle";
    setBridgeRetryError(null);
    syncLiveRecoveryNotice();
    saveState();
    await hydrateRealtimeSession(startedSession.sessionId, { force: true });
  } catch (error) {
    console.error("Failed to start live simulation", error);
    setLiveSessionError(error);
    pushToast(error.message || t().live.loadError);
  } finally {
    setLiveRequestStatus("start", "idle");
    render();
  }
}

async function respondToLiveSession() {
  const text = state.currentSimulation.practiceText.trim();
  if (!text) {
    pushToast(
      state.lang === "zh"
        ? "请先输入一段练习回复。"
        : "Enter a practice response first."
    );
    return;
  }

  if (state.currentSimulation.phase !== "session") {
    pushToast("Start a live session before evaluating language.");
    return;
  }

  if (isHardLiveFallback()) {
    const result = analyzeDraft(text);
    state.currentSimulation.metrics = result.metrics;
    state.currentSimulation.transcript.push({
      id: `fallback-user-${Date.now()}`,
      speaker: "User",
      local: text,
      en: text,
      zh: text,
      tags: ["Practice", "Language"],
      issueKey: result.issues[0] || null,
      turnIndex: state.currentSimulation.transcript.length + 1
    });
    result.issues.forEach((key) => {
      state.currentSimulation.issueCounts[key] =
        (state.currentSimulation.issueCounts[key] || 0) + 1;
      state.currentSimulation.alerts.unshift({
        id: `fallback-alert-${key}-${Date.now()}`,
        severity:
          key === "taboo_wording" || key === "price_pressure" ? "high" : "medium",
        issueKey: key,
        title: issueText(key).title,
        detail: issueText(key).detail
      });
    });
    state.currentSimulation.transcript.push({
      id: `fallback-assistant-${Date.now()}`,
      speaker: "Partner",
      local: result.partner.local,
      en: result.partner.en,
      zh: result.partner.zh,
      tags: ["Partner response", "Context"],
      issueKey: null,
      turnIndex: state.currentSimulation.transcript.length + 1
    });
    state.currentSimulation.practiceText = "";
    state.currentSimulation.sessionSummary = {
      status: "active",
      turnCount: state.currentSimulation.transcript.length,
      alertCount: state.currentSimulation.alerts.length,
      lastAlertSeverity: state.currentSimulation.alerts[0]?.severity || null
    };
    saveState();
    render();
    return;
  }

  setLiveRequestStatus("respond", "loading");
  setLiveSessionError(null);
  render();

  try {
    const exchange = await respondRealtimeTurn(state.currentSimulation.sessionId, {
      inputMode: "text",
      sourceText: text,
      language: "en"
    });
    upsertTranscriptTurns([
      mapRealtimeTurn(exchange.userTurn),
      mapRealtimeTurn(exchange.assistantTurn)
    ]);
    upsertAlerts(exchange.alerts.map((item) => mapRealtimeAlert(item)), {
      prepend: true
    });
    state.currentSimulation.sessionSummary = {
      ...(state.currentSimulation.sessionSummary || {}),
      status: state.currentSimulation.realtimeStatus || "active",
      turnCount: exchange.turnCount,
      alertCount: state.currentSimulation.alerts.length,
      lastAlertSeverity:
        state.currentSimulation.alerts[0]?.severity ||
        state.currentSimulation.sessionSummary?.lastAlertSeverity ||
        null
    };
    state.currentSimulation.realtimeStatus = "active";
    state.currentSimulation.practiceText = "";
    saveState();
    render();

    const [summary, turns, alerts] = await Promise.all([
      fetchRealtimeSessionSummary(state.currentSimulation.sessionId),
      fetchRealtimeTurns(state.currentSimulation.sessionId),
      fetchRealtimeAlerts(state.currentSimulation.sessionId)
    ]);

    applySessionSummary(summary);
    state.currentSimulation.transcript = mapRealtimeTurns(turns);
    state.currentSimulation.alerts = mapRealtimeAlerts(alerts);
    saveState();
  } catch (error) {
    console.error("Failed to evaluate live turn", error);
    setLiveSessionError(error);
    pushToast(error.message || t().live.loadError);
  } finally {
    setLiveRequestStatus("respond", "idle");
    render();
  }
}

async function bridgeReviewForCompletedSession(sessionId, { navigateOnSuccess = true } = {}) {
  if (!sessionId) return null;

  state.liveCenter.bridgeRetryStatus = "loading";
  setBridgeRetryError(null);
  syncLiveRecoveryNotice();
  render();

  try {
    const reviewDetail = await bridgeReviewFromRealtime(sessionId);
    hydrateReviewCenterFromApiDetail(reviewDetail);
    state.currentSimulation.recentReviewId =
      reviewDetail.reviewId || reviewDetail.id || null;
    state.liveCenter.bridgeRetryStatus = "idle";
    setBridgeRetryError(null);
    syncLiveRecoveryNotice();
    saveState();
    if (navigateOnSuccess) {
      setRoute("review");
    } else {
      render();
    }
    return reviewDetail;
  } catch (error) {
    console.error("Failed to bridge live session into review", error);
    state.liveCenter.bridgeRetryStatus = "error";
    setBridgeRetryError(error);
    syncLiveRecoveryNotice();
    saveState();
    render();
    throw error;
  }
}

async function endLiveSessionAndBridge() {
  if (isHardLiveFallback()) {
    createSimulationReview();
    state.activeRoute = "review";
    saveState();
    pushToast(t().misc.memoryUpdate);
    render();
    return;
  }

  setLiveRequestStatus("end", "loading");
  setLiveSessionError(null);
  render();

  try {
    const sessionId = state.currentSimulation.sessionId;
    await endRealtimeSession(sessionId);
    state.currentSimulation.recentCompletedSessionId = sessionId;
    state.currentSimulation.lastCompletionStatus = "ended";
    state.currentSimulation.recentReviewId = null;
    clearLiveRuntime();
    syncLiveRecoveryNotice();
    saveState();
    render();

    try {
      await bridgeReviewForCompletedSession(sessionId);
    } catch (error) {
      pushToast(error.message || t().live.loadError);
    }
  } catch (error) {
    console.error("Failed to end live session or bridge review", error);
    setLiveSessionError(error);
    pushToast(error.message || t().live.loadError);
    render();
  } finally {
    setLiveRequestStatus("end", "idle");
    render();
  }
}

function clearLocalSimulationLink() {
  state.currentSimulation.simulationId = null;
  state.currentSimulation.simulationStatus = state.currentSimulation.strategies.length
    ? "strategy_ready"
    : "draft";
  state.currentSimulation.setupRevision = 0;
  state.currentSimulation.strategyForSetupRevision = null;
  state.liveCenter.syncedSimulationId = null;
  state.liveCenter.simulationHydrateStatus = "idle";
  setSimulationHydrateError(null);
  syncLiveRecoveryNotice();
  saveState();
  render();
}

function openLatestReviewFromLive() {
  if (!state.currentSimulation.recentReviewId) return;
  state.selectedReviewId = state.currentSimulation.recentReviewId;
  setRoute("review");
}

async function resumeHiddenLiveSession() {
  if (!state.currentSimulation.sessionId) return;

  try {
    setLiveSessionError(null);
    await hydrateRealtimeSession(state.currentSimulation.sessionId, {
      force: true
    });
  } catch (error) {
    console.error("Failed to resume hidden live session", error);
    setLiveSessionError(error);
    pushToast(error.message || t().live.loadError);
    render();
  }
}

async function retryLiveReviewBridge() {
  const sessionId = state.currentSimulation.recentCompletedSessionId;
  if (!sessionId) return;

  try {
    await bridgeReviewForCompletedSession(sessionId);
  } catch (error) {
    pushToast(error.message || t().live.loadError);
  }
}

function prefersLocalHardwareFallback() {
  return window.location.protocol === "file:";
}

function hardwareActionLabel(action) {
  if (action === "connect") return t().hardware.connectAction;
  if (action === "disconnect") return t().hardware.disconnectAction;
  if (action === "sync") return t().hardware.syncAction;
  return t().hardware.syncAction;
}

function clearHardwareErrors() {
  state.hardwareCenter.loadError = null;
  state.hardwareCenter.actionError = null;
}

function clearPricingErrors() {
  state.pricingCenter.loadError = null;
  state.pricingCenter.actionError = null;
}

function handleProtectedApiError(error, fallbackMessage) {
  if (error && error.status === 401) {
    clearAuthenticatedUser();
    ensurePublicRouteForLoggedOutUser();
    saveState();
    pushToast(
      state.lang === "zh"
        ? "登录状态已失效，请重新登录。"
        : "Your session expired. Please log in again."
    );
    return true;
  }

  pushToast(error.message || fallbackMessage);
  return false;
}

function handleWorkspaceBootstrapError(error, fallbackMessage) {
  if (error && error.status === 401) {
    return handleProtectedApiError(error, fallbackMessage);
  }
  return false;
}

function shouldBootstrapWorkspaceSnapshots() {
  return state.loggedIn &&
    authBootstrapReady &&
    window.location.protocol !== "file:" &&
    state.activeRoute !== "pricing" &&
    state.activeRoute !== "hardware";
}

function applySharedHardwareSnapshot(device) {
  const nextDevice = mapHardwareDevice(device);
  const preserveDeviceDetails = state.hardware.deviceId === nextDevice.deviceId;
  state.hardware = normalizeHardwareState({
    ...state.hardware,
    ...nextDevice,
    logs: preserveDeviceDetails ? state.hardware.logs : [],
    syncRecords: preserveDeviceDetails ? state.hardware.syncRecords : []
  });
}

async function hydrateSharedBillingSnapshot(actorKey, requestVersion) {
  try {
    const apiSummary = await fetchBillingSummary();
    if (!canApplyWorkspaceBootstrap(actorKey, requestVersion)) return;

    const summary = mapBillingSummary(apiSummary);
    applyBillingSummaryToUserSnapshot(state, summary);
    workspaceBootstrapState.billingStatus = "ready";
    saveState();
    render();
  } catch (error) {
    if (
      !state.loggedIn ||
      workspaceBootstrapState.actorKey !== actorKey ||
      workspaceBootstrapState.requestVersion !== requestVersion
    ) {
      return;
    }

    console.error("Failed to hydrate shared billing snapshot", error);
    workspaceBootstrapState.billingStatus = "error";
    if (
      !handleWorkspaceBootstrapError(
        error,
        "Unable to refresh the demo billing snapshot right now."
      )
    ) {
      saveState();
      render();
    }
  }
}

async function hydrateSharedHardwareSnapshot(actorKey, requestVersion) {
  try {
    const apiDevices = await fetchHardwareDevices();
    if (!canApplyWorkspaceBootstrap(actorKey, requestVersion)) return;

    const mappedDevices = apiDevices.map((item) => mapHardwareDevice(item));
    const activeDevice = mappedDevices[0] || null;

    if (!activeDevice) {
      state.hardware = defaultHardwareState();
    } else {
      applySharedHardwareSnapshot(activeDevice);
    }

    workspaceBootstrapState.hardwareStatus = "ready";
    saveState();
    render();
  } catch (error) {
    if (
      !state.loggedIn ||
      workspaceBootstrapState.actorKey !== actorKey ||
      workspaceBootstrapState.requestVersion !== requestVersion
    ) {
      return;
    }

    console.error("Failed to hydrate shared hardware snapshot", error);
    workspaceBootstrapState.hardwareStatus = "error";
    if (
      !handleWorkspaceBootstrapError(
        error,
        t().hardware.loadError
      )
    ) {
      saveState();
      render();
    }
  }
}

async function ensureWorkspaceSharedSnapshots({ force = false } = {}) {
  if (!shouldBootstrapWorkspaceSnapshots()) return;

  const actorKey = syncWorkspaceBootstrapActorKey();
  const shouldHydrateBilling =
    force || workspaceBootstrapState.billingStatus === "idle";
  const shouldHydrateHardware =
    force || workspaceBootstrapState.hardwareStatus === "idle";

  if (!shouldHydrateBilling && !shouldHydrateHardware) return;

  const requestVersion = workspaceBootstrapState.requestVersion;
  if (shouldHydrateBilling) workspaceBootstrapState.billingStatus = "loading";
  if (shouldHydrateHardware) workspaceBootstrapState.hardwareStatus = "loading";

  const tasks = [];
  if (shouldHydrateBilling) {
    tasks.push(hydrateSharedBillingSnapshot(actorKey, requestVersion));
  }
  if (shouldHydrateHardware) {
    tasks.push(hydrateSharedHardwareSnapshot(actorKey, requestVersion));
  }
  await Promise.all(tasks);
}

function getActiveHardwareDevice(devices) {
  if (!devices.length) return null;
  const activeDeviceId = state.hardwareCenter.activeDeviceId;
  if (activeDeviceId) {
    const matched = devices.find((item) => item.deviceId === activeDeviceId);
    if (matched) return matched;
  }
  return devices[0];
}

async function ensureHardwareRouteReady({ force = false } = {}) {
  if (!state.loggedIn || state.activeRoute !== "hardware") return;
  if (!force && state.hardwareCenter.routeHydrationStatus === "loading") return;
  if (
    !force &&
    state.hardwareCenter.routeHydrationStatus === "ready" &&
    state.hardware.deviceId
  ) {
    return;
  }

  if (prefersLocalHardwareFallback()) {
    state.hardwareCenter.routeHydrationStatus = "ready";
    state.hardwareCenter.activeDeviceId = state.hardware.deviceId || null;
    state.hardwareCenter.devices = state.hardware.deviceId
      ? [mapHardwareDevice(state.hardware)]
      : [];
    markWorkspaceBootstrapReady("hardware");
    clearHardwareErrors();
    render();
    return;
  }

  const requestVersion = ++hardwareRouteRequestVersion;
  state.hardwareCenter.routeHydrationStatus = "loading";
  state.hardwareCenter.loadError = null;
  render();

  try {
    const apiDevices = await fetchHardwareDevices();
    if (requestVersion !== hardwareRouteRequestVersion) return;

    const mappedDevices = apiDevices.map((item) => mapHardwareDevice(item));
    const activeDevice = getActiveHardwareDevice(mappedDevices);

    state.hardwareCenter.devices = mappedDevices;
    state.hardwareCenter.activeDeviceId = activeDevice ? activeDevice.deviceId : null;

    if (!activeDevice) {
      state.hardware = defaultHardwareState();
      state.hardwareCenter.routeHydrationStatus = "ready";
      markWorkspaceBootstrapReady("hardware");
      clearHardwareErrors();
      saveState();
      render();
      return;
    }

    const [logs, syncRecords] = await Promise.all([
      fetchHardwareDeviceLogs(activeDevice.deviceId),
      fetchHardwareDeviceSyncRecords(activeDevice.deviceId)
    ]);
    if (requestVersion !== hardwareRouteRequestVersion) return;

    state.hardware = normalizeHardwareState(
      composeHardwareState(activeDevice, logs, syncRecords)
    );
    state.hardwareCenter.routeHydrationStatus = "ready";
    markWorkspaceBootstrapReady("hardware");
    clearHardwareErrors();
    saveState();
    render();
  } catch (error) {
    if (requestVersion !== hardwareRouteRequestVersion) return;
    console.error("Failed to hydrate hardware route", error);
    state.hardwareCenter.routeHydrationStatus = "error";
    state.hardwareCenter.loadError = error;
    if (!handleProtectedApiError(error, t().hardware.loadError)) {
      render();
    }
  }
}

async function ensurePricingRouteReady({ force = false } = {}) {
  if (!state.loggedIn || state.activeRoute !== "pricing") return;
  if (!force && state.pricingCenter.routeHydrationStatus === "loading") return;
  if (
    !force &&
    state.pricingCenter.routeHydrationStatus === "ready" &&
    state.pricingCenter.summary &&
    state.pricingCenter.plans.length
  ) {
    return;
  }

  const requestVersion = ++pricingRouteRequestVersion;
  state.pricingCenter.routeHydrationStatus = "loading";
  state.pricingCenter.loadError = null;
  render();

  try {
    const apiSummary = await fetchBillingSummary();
    if (requestVersion !== pricingRouteRequestVersion) return;

    const apiPlans = await fetchBillingPlans();
    if (requestVersion !== pricingRouteRequestVersion) return;

    const summary = mapBillingSummary(apiSummary);
    state.pricingCenter.summary = summary;
    state.pricingCenter.plans = composePricingCards(
      apiPlans,
      summary.currentPlanKey
    );
    state.pricingCenter.routeHydrationStatus = "ready";
    markWorkspaceBootstrapReady("billing");
    clearPricingErrors();
    applyBillingSummaryToUserSnapshot(state, summary);
    saveState();
    render();
  } catch (error) {
    if (requestVersion !== pricingRouteRequestVersion) return;
    console.error("Failed to hydrate pricing route", error);
    state.pricingCenter.routeHydrationStatus = "error";
    state.pricingCenter.loadError = error;
    if (
      !handleProtectedApiError(
        error,
        "Unable to load the demo billing workspace right now."
      )
    ) {
      render();
    }
  }
}

function buildHardwareSyncPayload() {
  return {
    syncKind: "sync_complete",
    healthStatus: "healthy",
    summaryText: "Demo sync completed from Hardware page",
    detailText: "Frontend-triggered demo sync for UI playback.",
    firmwareVersion: state.hardware.firmwareVersion || state.hardware.firmware || "1.4.2",
    batteryPercent: state.hardware.batteryPercent ?? state.hardware.battery ?? 84,
    vibrationEventCount: 0,
    payload: {
      source: "hardware-page",
      mode: "ui-demo"
    }
  };
}

async function performHardwareAction(action) {
  const deviceId = state.hardware.deviceId || state.hardwareCenter.activeDeviceId;
  if (!deviceId) return;

  state.hardwareCenter.actionStatus = "pending";
  state.hardwareCenter.actionKind = action;
  state.hardwareCenter.actionError = null;

  if (action === "sync") {
    state.hardware = normalizeHardwareState({
      ...state.hardware,
      connected: true,
      connectionState: "connected",
      transferState: "syncing",
      transferHealth: "syncing"
    });
  }

  render();

  try {
    if (action === "connect") {
      await connectHardwareDevice(deviceId);
    } else if (action === "disconnect") {
      await disconnectHardwareDevice(deviceId);
    } else if (action === "sync") {
      await syncHardwareDevice(deviceId, buildHardwareSyncPayload());
    }

    await ensureHardwareRouteReady({ force: true });
    state.hardwareCenter.actionStatus = "idle";
    state.hardwareCenter.actionKind = null;
    state.hardwareCenter.actionError = null;
    render();
  } catch (error) {
    console.error(`Failed to ${action} hardware device`, error);
    state.hardwareCenter.actionStatus = "idle";
    state.hardwareCenter.actionKind = null;
    state.hardwareCenter.actionError = error;
    if (!handleProtectedApiError(error, t().hardware.actionError)) {
      render();
    }
  }
}

async function performPricingPlanSelection(planKey) {
  const currentPlanKey =
    state.pricingCenter.summary?.currentPlanKey || state.pricingSelection;
  if (!planKey || planKey === currentPlanKey) return;

  state.pricingCenter.actionStatus = "pending";
  state.pricingCenter.actionKind = "select-plan";
  state.pricingCenter.actionError = null;
  render();

  try {
    await selectBillingPlan(planKey);
    await ensurePricingRouteReady({ force: true });
    state.pricingCenter.actionStatus = "idle";
    state.pricingCenter.actionKind = null;
    state.pricingCenter.actionError = null;
    render();
  } catch (error) {
    console.error("Failed to select billing plan", error);
    state.pricingCenter.actionStatus = "idle";
    state.pricingCenter.actionKind = null;
    state.pricingCenter.actionError = error;
    if (
      !handleProtectedApiError(
        error,
        "Unable to update the demo billing plan right now."
      )
    ) {
      render();
    }
  }
}

async function performPricingTopUp(amount) {
  if (!amount) return;

  state.pricingCenter.actionStatus = "pending";
  state.pricingCenter.actionKind = "top-up";
  state.pricingCenter.actionError = null;
  render();

  try {
    await topUpBillingCredits(Number(amount));
    await ensurePricingRouteReady({ force: true });
    state.pricingCenter.actionStatus = "idle";
    state.pricingCenter.actionKind = null;
    state.pricingCenter.actionError = null;
    render();
  } catch (error) {
    console.error("Failed to top up demo billing credits", error);
    state.pricingCenter.actionStatus = "idle";
    state.pricingCenter.actionKind = null;
    state.pricingCenter.actionError = error;
    if (
      !handleProtectedApiError(
        error,
        "Unable to top up demo credits right now."
      )
    ) {
      render();
    }
  }
}

function pushToast(message) {
  const id = Date.now();
  state.toast = { id, message };
  render();
  window.setTimeout(() => {
    if (state.toast && state.toast.id === id) {
      state.toast = null;
      render();
    }
  }, 2600);
}

async function syncAuthSessionFromBackend({
  redirectPending = false,
  silent = false,
  renderAfter = true
} = {}) {
  try {
    const authSession = await fetchAuthSession();
    applyAuthenticatedUser(authSession);
    authBootstrapReady = true;
    saveState();

    if (redirectPending && state.pendingRoute) {
      const target = state.pendingRoute;
      state.pendingRoute = null;
      if (target === "live") resetSimulationToSetup();
      setRoute(target);
      return authSession;
    }

    if (renderAfter) render();
    return authSession;
  } catch (error) {
    if (error && error.status === 401) {
      clearAuthenticatedUser();
      ensurePublicRouteForLoggedOutUser();
      authBootstrapReady = true;
      saveState();
      if (!silent) {
        pushToast(
          state.lang === "zh"
            ? "登录状态已失效，请重新登录。"
            : "Your session expired. Please log in again."
        );
      } else if (renderAfter) {
        render();
      }
      return null;
    }

    if (!silent) {
      pushToast(
        state.lang === "zh"
          ? "暂时无法同步账户信息。"
          : "Unable to sync your account right now."
      );
    }
    if (renderAfter) render();
    throw error;
  }
}

async function initializeAuthState() {
  if (!isSupabaseConfigured()) {
    authBootstrapReady = true;
    return;
  }

  onAuthStateChange(async (event, session) => {
    if (event === "SIGNED_OUT" || !session) {
      clearAuthenticatedUser();
      ensurePublicRouteForLoggedOutUser();
      authBootstrapReady = true;
      saveState();
      render();
      return;
    }

    try {
      await syncAuthSessionFromBackend({
        redirectPending: Boolean(state.pendingRoute),
        silent: true
      });
    } catch (error) {
      console.error("Failed to synchronize Supabase auth state", error);
    }
  });

  const accessToken = await getAccessToken().catch(() => null);
  if (!accessToken) {
    clearAuthenticatedUser();
    ensurePublicRouteForLoggedOutUser();
    authBootstrapReady = true;
    saveState();
    return;
  }

  try {
    await syncAuthSessionFromBackend({
      redirectPending: Boolean(state.pendingRoute),
      silent: true,
      renderAfter: false
    });
  } catch (error) {
    console.error("Failed to initialize Supabase auth state", error);
  } finally {
    authBootstrapReady = true;
  }
}

function setRoute(route) {
  state.activeRoute = route;
  if (route === "live") {
    state.liveCenter.routeHydrationStatus = "idle";
  }
  if (route === "hardware") {
    state.hardwareCenter.routeHydrationStatus = "idle";
    clearHardwareErrors();
  }
  if (route === "pricing") {
    state.pricingCenter.routeHydrationStatus = "idle";
    clearPricingErrors();
  }
  window.location.hash = route;
  window.scrollTo({ top: 0, behavior: "smooth" });
  render();
  if (route === "review" && state.loggedIn) {
    void ensureReviewCenterLoaded({
      force:
        state.reviewCenter.fallbackActive || state.reviewCenter.listStatus === "error"
    });
  }
}

function openAuth(mode, route) {
  state.authMode = mode;
  state.authOpen = true;
  state.pendingRoute = route || null;
  render();
}

function requireAuth(route) {
  if (state.loggedIn) {
    setRoute(route);
    return;
  }
  pushToast(t().misc.requireAuth);
  openAuth("login", route);
}

function resetSimulationToSetup() {
  state.currentSimulation.phase = "setup";
  state.drawerCollapsed = false;
  state.liveCenter.precheckModal = null;
  state.liveCenter.syncedSimulationId = null;
  state.liveCenter.syncedSessionId = null;
}

function getFilteredReviews() {
  return getReviewItems();
}

function radarSvg(values) {
  const labels =
    state.lang === "zh"
      ? ["共情", "语境", "礼仪", "情绪", "直接度"]
      : ["Empathy", "Context", "Etiquette", "Emotion", "Directness"];
  const center = 100;
  const radius = 72;
  const points = values.map((value, index) => {
    const angle = (Math.PI * 2 * index) / values.length - Math.PI / 2;
    const currentRadius = (radius * value) / 100;
    return `${center + Math.cos(angle) * currentRadius},${center + Math.sin(angle) * currentRadius}`;
  }).join(" ");
  const axes = labels.map((label, index) => {
    const angle = (Math.PI * 2 * index) / labels.length - Math.PI / 2;
    const x = center + Math.cos(angle) * radius;
    const y = center + Math.sin(angle) * radius;
    const textX = center + Math.cos(angle) * 92;
    const textY = center + Math.sin(angle) * 92;
    return `<line x1="${center}" y1="${center}" x2="${x}" y2="${y}" stroke="rgba(29,29,31,0.12)" /><text x="${textX}" y="${textY}" fill="rgba(29,29,31,0.62)" font-size="10" text-anchor="middle">${label}</text>`;
  }).join("");
  return `<svg viewBox="0 0 200 200" width="180" height="180"><polygon points="100,28 168,78 142,158 58,158 32,78" fill="rgba(255,255,255,0.84)" stroke="rgba(29,29,31,0.08)" /><polygon points="100,46 151,84 132,144 68,144 49,84" fill="rgba(255,255,255,0.62)" stroke="rgba(29,29,31,0.05)" /><polygon points="${points}" fill="rgba(0,122,255,0.14)" stroke="rgba(0,122,255,0.92)" stroke-width="2" />${axes}<circle cx="100" cy="100" r="4" fill="rgba(29,29,31,0.88)" /></svg>`;
}
function repeatedWordDetected(text) {
  const tokens = text.toLowerCase().match(/[a-z']+/g) || [];
  const counts = {};
  for (const token of tokens) {
    counts[token] = (counts[token] || 0) + 1;
    if (token.length > 3 && counts[token] >= 3) return true;
  }
  return false;
}

function hasSoftener(country, text) {
  return country.softeners.some((pattern) => pattern.test(text));
}

function pickPartner(country, riskScore) {
  return riskScore >= 3 ? country.partnerResponses.high : riskScore >= 1 ? country.partnerResponses.medium : country.partnerResponses.low;
}

function buildStrategies() {
  const country = getCountry(state.currentSimulation.country);
  const ranked = [...state.userTwin]
    .sort((a, b) => b.count - a.count)
    .slice(0, 1)
    .map((item) => ({
      tag: { en: "User Twin", zh: "鐢ㄦ埛闀滃儚" },
      title: { en: ISSUE_LIBRARY[item.issueKey].en.title, zh: ISSUE_LIBRARY[item.issueKey].zh.title },
      bullets: {
        en: [pick(item.coach), `${country.label.en} context: ${pick(item.lastContext)}.`],
        zh: [pick(item.coach), `${country.label.zh} 璇锛?{pick(item.lastContext)}`]
      }
    }));
  state.currentSimulation.strategies = [...country.strategies.slice(0, 2), ranked[0] || country.strategies[2]];
  saveState();
}
function analyzeDraft(text) {
  const country = getCountry(state.currentSimulation.country);
  const issues = [];
  const words = text.toLowerCase().trim().split(/\s+/).filter(Boolean);
  const taboo = country.tabooPatterns.some((pattern) => pattern.test(text));
  const strong = country.strongPatterns.some((pattern) => pattern.test(text));
  const pricePush = country.pricePatterns.some((pattern) => pattern.test(text));
  const metaphor = country.metaphorPatterns.some((pattern) => pattern.test(text));
  const repetition = repeatedWordDetected(text);
  const noSoftener = !hasSoftener(country, text);
  const noPause = words.length > 22 && !/[,.!?;:]|\.\.\.|\[pause\]/i.test(text);
  if (taboo) issues.push("taboo_wording");
  if (strong) issues.push("intensity_spike");
  if (pricePush && (strong || noSoftener)) issues.push("price_pressure");
  if (repetition) issues.push("repetition_loop");
  if (noPause) issues.push("pause_control");
  if (metaphor) issues.push("metaphor_risk");
  if (noSoftener && state.currentSimulation.country === "Japan" && (pricePush || strong)) issues.push("soft_refusal_missed");
  const uniqueIssues = [...new Set(issues)];
  return {
    issues: uniqueIssues,
    metrics: {
      wording: uniqueIssues.length >= 3 ? "risky" : uniqueIssues.length ? "watch" : "calibrated",
      pauses: uniqueIssues.includes("pause_control") ? "too_dense" : "balanced",
      repetition: uniqueIssues.includes("repetition_loop") ? "repeated" : "low",
      taboo: uniqueIssues.includes("taboo_wording") ? "triggered" : "clear",
      intensity: uniqueIssues.includes("intensity_spike") ? "high" : "measured",
      metaphor: uniqueIssues.includes("metaphor_risk") ? "needs_simplification" : "concrete"
    },
    partner: pickPartner(country, uniqueIssues.length)
  };
}
function createSimulationReview() {
  const issueCounts = state.currentSimulation.issueCounts;
  const repeatedIssues = Object.keys(issueCounts).sort((a, b) => issueCounts[b] - issueCounts[a]).slice(0, 3);
  const score = Math.max(55, 88 - repeatedIssues.reduce((sum, key) => sum + issueCounts[key] * 5, 0) - state.currentSimulation.alerts.length * 2);
  const contextEn = `${state.currentSimulation.country} / ${translateByGroup("meetingType", state.currentSimulation.meetingType)}`;
  const contextZh = `${pick(getCountry(state.currentSimulation.country).label)} / ${translateByGroup("meetingType", state.currentSimulation.meetingType)}`;
  const review = {
    id: `review-sim-${Date.now()}`,
    source: "simulation",
    title: { en: contextEn, zh: contextZh },
    country: state.currentSimulation.country,
    date: new Date().toISOString(),
    score,
    modules: [Math.max(52, score + 3), Math.max(48, score - 4), Math.max(55, score + 1), Math.max(50, score - 2)],
    repeatedIssues,
    summary: {
      en: repeatedIssues.length ? `Primary risks: ${repeatedIssues.map((key) => ISSUE_LIBRARY[key].en.short).join(", ")}.` : "No major language risks were triggered.",
      zh: repeatedIssues.length
        ? `主要风险：${repeatedIssues.map((key) => ISSUE_LIBRARY[key].zh.short).join(" / ")}。`
        : "未触发明显语言风险。"
    },
    lines: state.currentSimulation.transcript.map((turn) => ({
      speaker: turn.speaker,
      sourceText: turn.local,
      translation: { en: turn.en, zh: turn.zh },
      tags: turn.tags,
      issueKey: turn.issueKey || null,
      advice: turn.issueKey ? { en: ISSUE_LIBRARY[turn.issueKey].en.detail, zh: ISSUE_LIBRARY[turn.issueKey].zh.detail } : null
    }))
  };

  repeatedIssues.forEach((key) => {
    const existing = state.userTwin.find((item) => item.issueKey === key);
    if (existing) {
      existing.count += 1;
      existing.lastContext = { en: contextEn, zh: contextZh };
    } else {
      state.userTwin.push({
        id: `tw-${Date.now()}-${key}`,
        issueKey: key,
        count: 1,
        risk: "Medium",
        country: state.currentSimulation.country,
        lastContext: { en: contextEn, zh: contextZh },
        coach: { en: ISSUE_LIBRARY[key].en.detail, zh: ISSUE_LIBRARY[key].zh.detail }
      });
    }
  });

  state.reviews = [review, ...state.reviews];
  state.selectedReviewId = review.id;
  state.reviewFilter = "all";
  state.currentSimulation.phase = "setup";
  state.currentSimulation.transcript = [];
  state.currentSimulation.alerts = [];
  state.currentSimulation.issueCounts = {};
  state.currentSimulation.practiceText = "";
  state.currentSimulation.metrics = defaultMetrics();
  saveState();
}

function createViewContext() {
  return {
    state,
    reviewCenter: state.reviewCenter,
    liveCenter: state.liveCenter,
    hardwareCenter: state.hardwareCenter,
    pricingCenter: state.pricingCenter,
    t,
    pick,
    translateByGroup,
    metricLabel,
    metricValueLabel,
    riskLabel,
    statusLabel,
    hardwareActionLabel,
    speakerLabel,
    tagLabel,
    issueText,
    formatDate,
    formatBalance,
    initials,
    joinMeta,
    getCountry,
    getFilteredReviews,
    getSelectedReview,
    getSelectedReviewCard,
    meetingTypeOptions: getMeetingTypeOptions(),
    goalOptions: getGoalOptions(),
    voiceStyleOptions: getVoiceStyleOptions(),
    getCountryDisplay,
    getMeetingTypeDisplay,
    getGoalDisplay,
    getVoiceStyleDisplay,
    getSimulationStatusDisplay,
    getSessionStatusDisplay,
    getSeverityDisplay,
    TESTIMONIALS,
    COUNTRY_LIBRARY,
    METRIC_LABELS,
    REVIEW_MODULES
  };
}

function currentPage() {
  const view = createViewContext();
  if (state.activeRoute === "live") return livePage(view);
  if (state.activeRoute === "hardware") return hardwarePage(view);
  if (state.activeRoute === "review") return reviewPage(view);
  if (state.activeRoute === "pricing") return pricingPage(view);
  if (state.activeRoute === "settings") return settingsPage(view);
  return homePage(view);
}

function syncNavVisibility() {
  const hideThreshold = 56;
  document.body.classList.toggle("nav-hidden", window.scrollY > hideThreshold);
}

function render() {
  const view = createViewContext();
  document.documentElement.lang = state.lang === "zh" ? "zh-CN" : "en";
  document.body.classList.toggle("session-mode", state.activeRoute === "live" && state.currentSimulation.phase === "session");
  document.getElementById("app").innerHTML = `<div class="app-shell"><a class="skip-link" href="#mainContent">${state.lang === "zh" ? "璺冲埌涓昏鍐呭" : "Skip to main content"}</a><div class="ambient a1"></div><div class="ambient a2"></div><div class="ambient a3"></div>${navTemplate(view)}<main id="mainContent" class="main-wrap ${state.activeRoute === "live" && state.currentSimulation.phase === "session" ? "main-wrap-session" : ""}">${currentPage()}</main>${authModal(view)}${state.toast ? `<div class="toast-stack" role="status" aria-live="polite"><div class="toast">${state.toast.message}</div></div>` : ""}</div>`;
  bindEvents();
  syncNavVisibility();
  if (
    state.activeRoute === "review" &&
    state.loggedIn &&
    state.reviewCenter.listStatus === "idle"
  ) {
    void ensureReviewCenterLoaded();
  }
  if (
    state.activeRoute === "live" &&
    state.loggedIn &&
    state.liveCenter.routeHydrationStatus === "idle"
  ) {
    void ensureLiveRouteReady();
  }
  if (
    state.activeRoute === "hardware" &&
    state.loggedIn &&
    state.hardwareCenter.routeHydrationStatus === "idle"
  ) {
    void ensureHardwareRouteReady();
  }
  if (
    state.activeRoute === "pricing" &&
    state.loggedIn &&
    state.pricingCenter.routeHydrationStatus === "idle"
  ) {
    void ensurePricingRouteReady();
  }
  if (shouldBootstrapWorkspaceSnapshots()) {
    void ensureWorkspaceSharedSnapshots();
  }
}

function bindEvents() {
  document.querySelectorAll("[data-route]").forEach((button) => button.addEventListener("click", () => {
    const route = button.dataset.route;
    if (route === "live") resetSimulationToSetup();
    const protectedRoute = button.dataset.protected === "true";
    if (protectedRoute) requireAuth(route);
    else setRoute(route);
  }));
  document.querySelectorAll("[data-auth]").forEach((button) => button.addEventListener("click", () => openAuth(button.dataset.auth, null)));
  document.querySelectorAll("[data-auth-switch]").forEach((button) => button.addEventListener("click", () => { state.authMode = button.dataset.authSwitch; render(); }));
  document.querySelectorAll("[data-review-select]").forEach((button) => button.addEventListener("click", () => {
    void loadReviewDetail(button.dataset.reviewSelect);
  }));
  document.querySelectorAll("[data-review-id]").forEach((button) => button.addEventListener("click", () => {
    state.selectedReviewId = button.dataset.reviewId;
    requireAuth("review");
  }));
  document.querySelectorAll("[data-hardware-action]").forEach((button) =>
    button.addEventListener("click", async () => {
      await performHardwareAction(button.dataset.hardwareAction);
    })
  );
  document.querySelectorAll("[data-lang]").forEach((button) => button.addEventListener("click", () => { state.lang = button.dataset.lang; saveState(); render(); }));
  document.querySelectorAll("[data-topup]").forEach((button) =>
    button.addEventListener("click", async () => {
      await performPricingTopUp(Number(button.dataset.topup));
    })
  );

  const selectPlan = async (plan) => {
    await performPricingPlanSelection(plan);
  };

  document.querySelectorAll(".pricing-card[data-plan]").forEach((card) => {
    card.addEventListener("click", () => {
      void selectPlan(card.dataset.plan);
    });
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        void selectPlan(card.dataset.plan);
      }
    });
  });

  document.querySelectorAll(".pricing-action[data-plan]").forEach((button) =>
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      void selectPlan(button.dataset.plan);
    })
  );
  document.querySelectorAll("[data-logout]").forEach((button) => button.addEventListener("click", async () => {
    try {
      await signOutOfSupabase();
    } catch (error) {
      console.error("Supabase sign out failed", error);
    }
    clearAuthenticatedUser();
    state.activeRoute = "home";
    saveState();
    pushToast(t().misc.logoutDone);
  }));

  const startLive = document.querySelector("[data-start-live]");
  if (startLive) startLive.addEventListener("click", () => { resetSimulationToSetup(); requireAuth("live"); });

  const reviewHome = document.querySelector("[data-open-review='home']");
  if (reviewHome) reviewHome.addEventListener("click", () => requireAuth("review"));

  const closeAuthBtn = document.getElementById("closeAuthBtn");
  if (closeAuthBtn) closeAuthBtn.addEventListener("click", () => { state.authOpen = false; render(); });

  const authForm = document.getElementById("authForm");
  if (authForm) authForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = document.getElementById("authEmail").value.trim();
    const password = document.getElementById("authPassword").value.trim();
    if (!email || !password) {
      pushToast(state.lang === "zh" ? "请输入邮箱和密码。" : "Enter email and password.");
      return;
    }

    try {
      if (state.authMode === "register") {
        const signUpResult = await signUpWithPassword(email, password);
        if (signUpResult.session) {
          await syncAuthSessionFromBackend({
            redirectPending: true,
            renderAfter: false
          });
          pushToast(
            state.lang === "zh"
              ? "注册成功，已完成登录。"
              : "Account created and signed in."
          );
          return;
        }

        state.authOpen = false;
        state.pendingRoute = null;
        saveState();
        render();
        pushToast(
          state.lang === "zh"
            ? "注册成功，请前往邮箱完成验证后再登录。"
            : "Check your email to confirm your account, then log in."
        );
        return;
      }

      await signInWithPassword(email, password);
      await syncAuthSessionFromBackend({
        redirectPending: true,
        renderAfter: false
      });
      pushToast(t().misc.loginDone);
    } catch (error) {
      console.error("Supabase auth flow failed", error);
      pushToast(error.message || (state.lang === "zh" ? "登录失败，请重试。" : "Unable to sign in right now."));
      render();
    }
  });

  const countryField = document.getElementById("field-country");
  if (countryField) countryField.addEventListener("change", async () => {
    const country = getCountry(countryField.value);
    state.currentSimulation.country = countryField.value;
    state.currentSimulation.meetingType = country.defaultMeeting;
    state.currentSimulation.goal = country.defaultGoal;
    state.currentSimulation.voiceStyle = "Formal / measured";
    state.currentSimulation.voiceProfileId = null;
    markLiveSetupDirty();
    saveState();
    render();
    await ensureVoiceProfilesLoaded({ force: true, allowFallback: true });
  });

  const meetingField = document.getElementById("field-meeting");
  if (meetingField) meetingField.addEventListener("change", () => {
    state.currentSimulation.meetingType = meetingField.value;
    markLiveSetupDirty();
    saveState();
    render();
  });

  const goalField = document.getElementById("field-goal");
  if (goalField) goalField.addEventListener("change", () => {
    state.currentSimulation.goal = goalField.value;
    markLiveSetupDirty();
    saveState();
    render();
  });

  const voiceField = document.getElementById("field-voice");
  if (voiceField) voiceField.addEventListener("change", () => {
    state.currentSimulation.voiceStyle = voiceField.value;
    markLiveSetupDirty();
    saveState();
    render();
  });

  const voiceProfileField = document.getElementById("field-voice-profile");
  if (voiceProfileField) voiceProfileField.addEventListener("change", () => {
    state.currentSimulation.voiceProfileId = voiceProfileField.value || null;
    markLiveSetupDirty();
    saveState();
    render();
  });

  const durationField = document.getElementById("field-duration");
  if (durationField) durationField.addEventListener("input", () => {
    state.currentSimulation.duration = Number(durationField.value);
    markLiveSetupDirty();
    saveState();
    render();
  });

  const constraintField = document.getElementById("field-constraint");
  if (constraintField) constraintField.addEventListener("input", () => {
    state.currentSimulation.constraint = constraintField.value;
    saveState();
  });

  const filesField = document.getElementById("field-files");
  if (filesField) filesField.addEventListener("change", () => { state.currentSimulation.files = Array.from(filesField.files || []).map((file) => ({ name: file.name, size: `${Math.max(1, Math.round(file.size / 1024))} KB` })); saveState(); render(); });

  const generateStrategyBtn = document.getElementById("generateStrategyBtn");
  if (generateStrategyBtn) generateStrategyBtn.addEventListener("click", async () => {
    await generateLiveStrategy();
  });

  const startSessionBtn = document.getElementById("startSessionBtn");
  if (startSessionBtn) startSessionBtn.addEventListener("click", async () => {
    await startLiveSession();
  });

  const backToSetupBtn = document.getElementById("backToSetupBtn");
  if (backToSetupBtn) backToSetupBtn.addEventListener("click", () => {
    if (
      state.currentSimulation.sessionId &&
      state.currentSimulation.realtimeStatus === "active"
    ) {
      clearLiveRuntime({
        preserveSessionLink: true,
        preserveRealtimeStatus: true
      });
    } else {
      clearLiveRuntime();
    }
    syncLiveRecoveryNotice();
    saveState();
    render();
  });

  const precheckContinueBtn = document.getElementById("precheckContinueBtn");
  if (precheckContinueBtn) {
    precheckContinueBtn.addEventListener("click", () => closePrecheckModal("continue"));
  }

  const precheckBackBtn = document.getElementById("precheckBackBtn");
  if (precheckBackBtn) {
    precheckBackBtn.addEventListener("click", () => closePrecheckModal("back"));
  }

  const practiceInput = document.getElementById("practiceInput");
  if (practiceInput) practiceInput.addEventListener("input", () => { state.currentSimulation.practiceText = practiceInput.value; saveState(); });

  const micBtn = document.getElementById("micBtn");
  if (micBtn) micBtn.addEventListener("click", () => pushToast(state.lang === "zh" ? "当前原型使用文本评估，不接入实时语音识别。" : "Prototype mode uses text evaluation instead of live speech recognition."));

  const evaluateBtn = document.getElementById("evaluateBtn");
  if (evaluateBtn) evaluateBtn.addEventListener("click", async () => {
    await respondToLiveSession();
  });

  const drawerToggleBtn = document.getElementById("drawerToggleBtn");
  if (drawerToggleBtn) drawerToggleBtn.addEventListener("click", () => { state.drawerCollapsed = !state.drawerCollapsed; render(); });

  const endSessionBtn = document.getElementById("endSessionBtn");
  if (endSessionBtn) endSessionBtn.addEventListener("click", async () => {
    await endLiveSessionAndBridge();
  });

  document.querySelectorAll("[data-live-action]").forEach((button) =>
    button.addEventListener("click", async () => {
      const action = button.dataset.liveAction;

      if (action === "retry-voice-profiles") {
        await ensureVoiceProfilesLoaded({ force: true, allowFallback: false });
        return;
      }

      if (action === "retry-simulation") {
        if (state.currentSimulation.simulationId) {
          await hydrateSimulationSnapshot(state.currentSimulation.simulationId, {
            force: true
          });
        }
        return;
      }

      if (action === "clear-simulation-link") {
        clearLocalSimulationLink();
        return;
      }

      if (action === "retry-session") {
        if (state.currentSimulation.sessionId) {
          await hydrateRealtimeSession(state.currentSimulation.sessionId, {
            force: true
          });
        }
        return;
      }

      if (action === "resume-live-session") {
        await resumeHiddenLiveSession();
        return;
      }

      if (action === "retry-bridge") {
        await retryLiveReviewBridge();
        return;
      }

      if (action === "open-latest-review") {
        openLatestReviewFromLive();
      }
    })
  );
}

window.addEventListener("scroll", syncNavVisibility, { passive: true });

window.addEventListener("hashchange", () => {
  const route = window.location.hash.replace("#", "");
  if (["home", "live", "hardware", "review", "pricing", "settings"].includes(route)) {
    if (isPublicRoute(route)) {
      state.activeRoute = route;
      render();
    } else {
      if (route === "live") resetSimulationToSetup();
      requireAuth(route);
    }
  }
});

const initialHash = window.location.hash.replace("#", "");
if (["home", "live", "hardware", "review", "pricing", "settings"].includes(initialHash)) {
  state.activeRoute = initialHash;
}

ensurePublicRouteForLoggedOutUser();
render();
void initializeAuthState().then(() => {
  render();
});





























