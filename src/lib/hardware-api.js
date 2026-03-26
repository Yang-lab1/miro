import { requestJson } from "./api-client.js";

export function fetchHardwareDevices() {
  return requestJson("/hardware/devices");
}

export function connectHardwareDevice(deviceId) {
  return requestJson(`/hardware/devices/${deviceId}/connect`, {
    method: "POST"
  });
}

export function disconnectHardwareDevice(deviceId) {
  return requestJson(`/hardware/devices/${deviceId}/disconnect`, {
    method: "POST"
  });
}

export function syncHardwareDevice(deviceId, payload) {
  return requestJson(`/hardware/devices/${deviceId}/sync`, {
    method: "POST",
    body: payload
  });
}

export function fetchHardwareDeviceLogs(deviceId) {
  return requestJson(`/hardware/devices/${deviceId}/logs`);
}

export function fetchHardwareDeviceSyncRecords(deviceId) {
  return requestJson(`/hardware/devices/${deviceId}/sync-records`);
}
