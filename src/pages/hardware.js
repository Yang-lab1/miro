function statusTone(status) {
  return status === "warning" || status === "failed" ? "warn" : "";
}

export function hardwarePage(ctx) {
  const {
    state,
    hardwareCenter,
    t,
    pick,
    formatDate,
    statusLabel,
    hardwareActionLabel
  } = ctx;

  const hardware = state.hardware;
  const isHydrating =
    hardwareCenter.routeHydrationStatus === "loading" && !hardware.deviceId;
  const isActionPending = hardwareCenter.actionStatus === "pending";
  const hasDevice = Boolean(hardware.deviceId);
  const primaryAction = hardware.connected ? "disconnect" : "connect";
  const actionError = hardwareCenter.actionError || hardwareCenter.loadError;
  const lastSyncLabel = hardware.lastSync
    ? formatDate(hardware.lastSync)
    : "—";

  const primaryActionLabel =
    isActionPending && hardwareCenter.actionKind === primaryAction
      ? `${hardwareActionLabel(primaryAction)}...`
      : hardwareActionLabel(primaryAction);
  const syncActionLabel =
    isActionPending && hardwareCenter.actionKind === "sync"
      ? t().hardware.syncing
      : t().hardware.syncAction;

  const logsMarkup = hardware.logs.length
    ? hardware.logs
        .map(
          (log) => `
            <li class="log-row">
              <div>
                <strong>${pick(log.title)}</strong>
                <small>${formatDate(log.time)}</small>
                <div>${pick(log.detail)}</div>
              </div>
              ${
                log.reviewId
                  ? `<button class="route-pill" data-review-id="${log.reviewId}">${t().hardware.openReview}</button>`
                  : ""
              }
            </li>`
        )
        .join("")
    : `<li class="empty-state compact-empty">${t().hardware.emptyLogs}</li>`;

  const syncRecordsMarkup = hardware.syncRecords.length
    ? hardware.syncRecords
        .map(
          (record) => `
            <li class="sync-row">
              <div>
                <strong>${pick(record.title)}</strong>
                <small>${formatDate(record.time)}</small>
                <div>${pick(record.detail)}</div>
              </div>
              <span class="status-pill ${statusTone(record.status)}">${statusLabel(record.status)}</span>
            </li>`
        )
        .join("")
    : `<li class="empty-state compact-empty">${t().hardware.emptySyncRecords}</li>`;

  return `
    <section class="route-page module-page device-clean-page">
      <div class="module-toolbar">
        <div>
          <small>${t().hardware.eyebrow}</small>
          <strong data-testid="hardware-device-name">${hardware.deviceName}</strong>
          <div class="toolbar-note">${t().hardware.demoNote}</div>
        </div>
        <div class="module-toolbar-actions">
          <span class="status-pill ${statusTone(hardware.transferHealth)}" data-testid="hardware-transfer-state">${statusLabel(hardware.transferHealth)}</span>
          <span class="toolbar-note">${t().hardware.synced}: ${lastSyncLabel}</span>
          <div class="inline-actions">
            ${
              hardware.connected
                ? `<button type="button" class="secondary-btn" data-hardware-action="disconnect" data-testid="hardware-disconnect" ${!hasDevice || isHydrating || isActionPending ? "disabled" : ""}>${primaryActionLabel}</button>`
                : `<button type="button" class="secondary-btn" data-hardware-action="connect" data-testid="hardware-connect" ${!hasDevice || isHydrating || isActionPending ? "disabled" : ""}>${primaryActionLabel}</button>`
            }
            <button type="button" class="primary-btn" data-hardware-action="sync" data-testid="hardware-sync" ${!hasDevice || isHydrating || isActionPending ? "disabled" : ""}>${syncActionLabel}</button>
          </div>
        </div>
      </div>

      ${
        isHydrating
          ? `<div class="empty-state compact-empty">${t().hardware.loading}</div>`
          : ""
      }
      ${
        actionError
          ? `<div class="empty-state compact-empty" data-testid="hardware-error">${actionError.message || t().hardware.actionError}</div>`
          : ""
      }

      <div class="device-summary-grid">
        <article class="module-panel device-summary-card device-summary-feature">
          <div class="pin-device"></div>
          <div>
            <small>${t().hardware.connected}</small>
            <strong data-testid="hardware-connection-state">${hardware.connected ? t().misc.online : t().misc.offline}</strong>
            <p>${t().hardware.version}: ${hardware.versionPath}</p>
          </div>
        </article>
        <article class="module-panel device-summary-card">
          <small>${t().hardware.transfer}</small>
          <strong>${statusLabel(hardware.transferHealth)}</strong>
        </article>
        <article class="module-panel device-summary-card">
          <small>${t().hardware.battery}</small>
          <strong data-testid="hardware-battery">${hardware.battery}%</strong>
        </article>
        <article class="module-panel device-summary-card">
          <small>${t().hardware.sessions}</small>
          <strong data-testid="hardware-captured-sessions">${hardware.capturedSessions}</strong>
        </article>
      </div>

      <div class="device-grid clean-device-grid">
        <section class="hardware-log-panel module-panel">
          <div class="panel-head">
            <div>
              <h2>${t().hardware.logTitle}</h2>
              <p>${t().hardware.timelineCopy}</p>
            </div>
          </div>
          <ul class="device-log-list" data-testid="hardware-log-list">
            ${logsMarkup}
          </ul>
        </section>

        <section class="sync-panel module-panel">
          <div class="panel-head">
            <div>
              <h2>${t().hardware.syncTitle}</h2>
              <p>${t().hardware.syncCopy}</p>
            </div>
          </div>
          <ul class="sync-list" data-testid="hardware-sync-records">
            ${syncRecordsMarkup}
          </ul>
          <div class="device-meta-list">
            <div class="device-meta-item"><small>${t().hardware.firmware}</small><strong>${hardware.firmware}</strong></div>
            <div class="device-meta-item"><small>${t().hardware.vibration}</small><strong>${hardware.vibrationEvents}</strong></div>
          </div>
        </section>
      </div>
    </section>`;
}
