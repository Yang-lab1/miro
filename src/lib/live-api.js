import { requestJson } from "./api-client.js";

export function createSimulation(payload) {
  return requestJson("/simulations", {
    method: "POST",
    body: payload
  });
}

export function updateSimulation(simulationId, payload) {
  return requestJson(`/simulations/${simulationId}`, {
    method: "PATCH",
    body: payload
  });
}

export function fetchSimulation(simulationId) {
  return requestJson(`/simulations/${simulationId}`);
}

export function generateSimulationStrategy(simulationId) {
  return requestJson(`/simulations/${simulationId}/strategy`, {
    method: "POST"
  });
}

export function runSimulationPrecheck(countryKey) {
  return requestJson("/simulations/precheck", {
    method: "POST",
    body: { countryKey }
  });
}

export function fetchVoiceProfiles(countryKey) {
  return requestJson(
    `/voice-profiles?countryKey=${encodeURIComponent(countryKey)}`
  );
}

export function createRealtimeSession(simulationId, transport = "webrtc") {
  return requestJson("/realtime/sessions", {
    method: "POST",
    body: { simulationId, transport }
  });
}

export function startRealtimeSession(sessionId) {
  return requestJson(`/realtime/sessions/${sessionId}/start`, {
    method: "POST"
  });
}

export function fetchRealtimeSession(sessionId) {
  return requestJson(`/realtime/sessions/${sessionId}`);
}

export function fetchRealtimeSessionSummary(sessionId) {
  return requestJson(`/realtime/sessions/${sessionId}/summary`);
}

export function respondRealtimeTurn(sessionId, payload) {
  return requestJson(`/realtime/sessions/${sessionId}/turns/respond`, {
    method: "POST",
    body: payload
  });
}

export function fetchRealtimeTurns(sessionId) {
  return requestJson(`/realtime/sessions/${sessionId}/turns`);
}

export function fetchRealtimeAlerts(sessionId) {
  return requestJson(`/realtime/sessions/${sessionId}/alerts`);
}

export function endRealtimeSession(sessionId) {
  return requestJson(`/realtime/sessions/${sessionId}/end`, {
    method: "POST"
  });
}

export function bridgeReviewFromRealtime(sessionId) {
  return requestJson(`/reviews/from-realtime/${sessionId}`, {
    method: "POST"
  });
}
