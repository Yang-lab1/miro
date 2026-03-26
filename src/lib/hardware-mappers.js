function normalizeTransferState(value) {
  if (!value) return "idle";
  if (value === "warn") return "warning";
  return value;
}

export function mapHardwareDevice(device) {
  const transferState = normalizeTransferState(device.transferState);
  return {
    deviceId: device.deviceId,
    deviceName: device.deviceName,
    connected: Boolean(device.connected),
    connectionState: device.connectionState || "disconnected",
    transferState,
    transferHealth: transferState,
    firmware: device.firmwareVersion || "-",
    firmwareVersion: device.firmwareVersion || "-",
    versionPath: device.versionPath || device.firmwareVersion || "-",
    battery: device.batteryPercent ?? 0,
    batteryPercent: device.batteryPercent ?? 0,
    lastSync: device.lastSyncAt,
    lastSyncAt: device.lastSyncAt,
    capturedSessions: device.capturedSessions ?? 0,
    vibrationEvents: device.vibrationEvents ?? 0
  };
}

export function mapHardwareLog(log) {
  return {
    id: log.logId,
    logId: log.logId,
    eventType: log.eventType,
    severity: log.severity,
    title: log.title,
    detail: log.detail,
    reviewId: log.reviewId,
    time: log.createdAt,
    createdAt: log.createdAt
  };
}

export function mapHardwareSyncRecord(record) {
  const status = normalizeTransferState(record.status);
  return {
    id: record.syncRecordId,
    syncRecordId: record.syncRecordId,
    syncKind: record.syncKind,
    status,
    title: record.title,
    detail: record.detail,
    reviewId: record.reviewId,
    time: record.createdAt,
    createdAt: record.createdAt
  };
}

export function composeHardwareState(device, logs = [], syncRecords = []) {
  return {
    ...mapHardwareDevice(device),
    logs: logs.map((item) => mapHardwareLog(item)),
    syncRecords: syncRecords.map((item) => mapHardwareSyncRecord(item))
  };
}
