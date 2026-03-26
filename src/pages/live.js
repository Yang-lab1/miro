const LIVE_COPY = {
  activeSessionHiddenTitle: {
    en: "An active session is still available.",
    zh: "当前仍有一个 active session 可恢复。"
  },
  activeSessionHiddenDetail: {
    en: "The session is hidden from the main stage, but it has not ended. You can resume it at any time.",
    zh: "当前会话只是从主舞台隐藏，并未结束。你可以随时恢复。"
  },
  resumeLiveSession: {
    en: "Resume live session",
    zh: "恢复 live session"
  },
  pendingSessionTitle: {
    en: "A pending session is ready to resume.",
    zh: "存在一个待启动会话。"
  },
  pendingSessionDetail: {
    en: "The previous launch did not fully start. You can continue by pressing Start simulation again.",
    zh: "上一次启动尚未完全进入会话态。你可以再次点击 Start simulation 继续。"
  },
  lastEndedTitle: {
    en: "Your last rehearsal has ended.",
    zh: "上一次 rehearsal 已结束。"
  },
  lastEndedDetail: {
    en: "Setup and strategy are still here, so you can start another round when ready.",
    zh: "当前 setup 和 strategy 已保留，可以直接开始下一轮。"
  },
  lastFailedTitle: {
    en: "The last live session failed to continue.",
    zh: "上一次 live session 未能正常继续。"
  },
  lastFailedDetail: {
    en: "The session is no longer active. Review the setup before starting another rehearsal.",
    zh: "该会话已不再进行中，请检查 setup 后再开始下一轮。"
  },
  bridgeFailedTitle: {
    en: "Review bridge did not finish.",
    zh: "Review bridge 未完成。"
  },
  bridgeFailedDetail: {
    en: "The session has already ended. You can retry creating the review snapshot from this completed session.",
    zh: "会话已经结束。你可以重试为这次已完成会话创建 review snapshot。"
  },
  voiceProfilesErrorTitle: {
    en: "Voice profiles could not be loaded.",
    zh: "Voice profiles 加载失败。"
  },
  simulationHydrateErrorTitle: {
    en: "Saved setup could not be restored.",
    zh: "已保存的 setup 无法恢复。"
  },
  sessionHydrateErrorTitle: {
    en: "The live session could not fully refresh.",
    zh: "当前 live session 未能完整刷新。"
  },
  retryVoiceProfiles: {
    en: "Retry voice profiles",
    zh: "重试 voice profiles"
  },
  retrySetup: {
    en: "Retry setup",
    zh: "重试 setup"
  },
  clearSetupLink: {
    en: "Clear setup link",
    zh: "清除 setup 链接"
  },
  retryLiveSession: {
    en: "Retry live session",
    zh: "重试 live session"
  },
  retryReviewBridge: {
    en: "Retry review bridge",
    zh: "重试 review bridge"
  },
  openLatestReview: {
    en: "Open latest review",
    zh: "打开最新 review"
  },
  preservedVoiceProfileLabel: {
    en: "Saved backend selection (temporarily unavailable)",
    zh: "已保存的后端语音档暂时不可用"
  },
  sessionFocusTitle: {
    en: "Coaching focus",
    zh: "Coaching focus"
  },
  sessionFocusFallback: {
    en: "Keep the pace calm, soften the ask, and let the relationship lead before you push for commitment.",
    zh: "Keep the pace calm, soften the ask, and let the relationship lead before you push for commitment."
  },
  liveSessionPrefix: {
    en: "Live",
    zh: "Live"
  },
  turnsLabel: {
    en: "Turns",
    zh: "Turns"
  },
  alertsLabel: {
    en: "Alerts",
    zh: "Alerts"
  },
  partnerTyping: {
    en: "Partner is preparing a response...",
    zh: "Partner is preparing a response..."
  },
  responsePromptHint: {
    en: "Draft your next response here before you evaluate the language.",
    zh: "Draft your next response here before you evaluate the language."
  }
};

export function livePage(ctx) {
  const {
    state,
    liveCenter,
    t,
    pick,
    joinMeta,
    getCountry,
    speakerLabel,
    COUNTRY_LIBRARY,
    initials,
    meetingTypeOptions,
    goalOptions,
    voiceStyleOptions,
    getMeetingTypeDisplay,
    getGoalDisplay,
    getVoiceStyleDisplay,
    getSimulationStatusDisplay,
    getSessionStatusDisplay,
    getSeverityDisplay
  } = ctx;

  function setupStrategiesTemplate() {
    if (!state.currentSimulation.strategies.length) {
      return `<div class="empty-state">${t().live.noStrategy}</div>`;
    }

    return state.currentSimulation.strategies
      .map(
        (item) =>
          `<article class="strategy-item"><small>${pick(item.tag)}</small><h3>${pick(item.title)}</h3><ul>${item.bullets[state.lang]
            .map((bullet) => `<li>${bullet}</li>`)
            .join("")}</ul></article>`
      )
      .join("");
  }

  function l(copy) {
    return state.lang === "zh" ? copy.zh : copy.en;
  }

  function renderNotice({ title, detail, actions = [] }) {
    return `
      <div class="empty-state compact-empty">
        <strong>${title}</strong>
        ${detail ? `<div>${detail}</div>` : ""}
        ${
          actions.length
            ? `<div class="inline-actions">${actions
                .map(
                  (action) =>
                    `<button type="button" class="${action.primary ? "primary-btn" : "secondary-btn"}" data-live-action="${action.action}" data-testid="live-action-${action.action}">${action.label}</button>`
                )
                .join("")}</div>`
            : ""
        }
      </div>`;
  }

  function renderSetupBanners() {
    const notices = [];
    const recovery = liveCenter.recoveryNotice;
    const isHardFallback =
      liveCenter.fallbackActive && liveCenter.fallbackMode === "hard";

    if (isHardFallback) {
      notices.push(`<div class="empty-state">${t().live.fallbackMode}</div>`);
    }

    if (recovery?.kind === "active_session_hidden") {
      notices.push(
        renderNotice({
          title: l(LIVE_COPY.activeSessionHiddenTitle),
          detail: l(LIVE_COPY.activeSessionHiddenDetail),
          actions: [
            {
              action: "resume-live-session",
              label: l(LIVE_COPY.resumeLiveSession),
              primary: true
            }
          ]
        })
      );
    }

    if (recovery?.kind === "pending_session") {
      notices.push(
        renderNotice({
          title: l(LIVE_COPY.pendingSessionTitle),
          detail: l(LIVE_COPY.pendingSessionDetail)
        })
      );
    }

    if (recovery?.kind === "completed_session" && recovery.status === "ended") {
      notices.push(
        renderNotice({
          title: l(LIVE_COPY.lastEndedTitle),
          detail: l(LIVE_COPY.lastEndedDetail),
          actions: recovery.reviewId
            ? [
                {
                  action: "open-latest-review",
                  label: l(LIVE_COPY.openLatestReview)
                }
              ]
            : []
        })
      );
    }

    if (recovery?.kind === "completed_session" && recovery.status === "failed") {
      notices.push(
        renderNotice({
          title: l(LIVE_COPY.lastFailedTitle),
          detail: l(LIVE_COPY.lastFailedDetail),
          actions: recovery.reviewId
            ? [
                {
                  action: "open-latest-review",
                  label: l(LIVE_COPY.openLatestReview)
                }
              ]
            : []
        })
      );
    }

    if (recovery?.kind === "bridge_failed") {
      notices.push(
        renderNotice({
          title: l(LIVE_COPY.bridgeFailedTitle),
          detail:
            (liveCenter.bridgeRetryError &&
              (liveCenter.bridgeRetryError.message || l(LIVE_COPY.bridgeFailedDetail))) ||
            l(LIVE_COPY.bridgeFailedDetail),
          actions: [
            {
              action: "retry-bridge",
              label:
                liveCenter.bridgeRetryStatus === "loading"
                  ? `${l(LIVE_COPY.retryReviewBridge)}...`
                  : l(LIVE_COPY.retryReviewBridge),
              primary: true
            },
            ...(state.currentSimulation.recentReviewId
              ? [
                  {
                    action: "open-latest-review",
                    label: l(LIVE_COPY.openLatestReview)
                  }
                ]
              : [])
          ]
        })
      );
    }

    if (liveCenter.voiceProfilesError) {
      notices.push(
        renderNotice({
          title: l(LIVE_COPY.voiceProfilesErrorTitle),
          detail: liveCenter.voiceProfilesError.message || t().live.loadError,
          actions: [
            {
              action: "retry-voice-profiles",
              label: l(LIVE_COPY.retryVoiceProfiles)
            }
          ]
        })
      );
    }

    if (liveCenter.simulationHydrateError) {
      notices.push(
        renderNotice({
          title: l(LIVE_COPY.simulationHydrateErrorTitle),
          detail: liveCenter.simulationHydrateError.message || t().live.loadError,
          actions: [
            {
              action: "retry-simulation",
              label: l(LIVE_COPY.retrySetup)
            },
            ...(state.currentSimulation.simulationId
              ? [
                  {
                    action: "clear-simulation-link",
                    label: l(LIVE_COPY.clearSetupLink)
                  }
                ]
              : [])
          ]
        })
      );
    }

    if (
      !isHardFallback &&
      liveCenter.listError &&
      !liveCenter.voiceProfilesError &&
      !liveCenter.simulationHydrateError
    ) {
      notices.push(
        `<div class="empty-state compact-empty">${liveCenter.listError.message || t().live.loadError}</div>`
      );
    }

    if (liveCenter.sessionError) {
      notices.push(
        `<div class="empty-state compact-empty">${liveCenter.sessionError.message || t().live.loadError}</div>`
      );
    }

    return notices.join("");
  }

  function renderSessionBanner() {
    const notices = [];
    const isHardFallback =
      liveCenter.fallbackActive && liveCenter.fallbackMode === "hard";

    if (isHardFallback) {
      notices.push(`<div class="empty-state">${t().live.fallbackMode}</div>`);
    }

    if (liveCenter.sessionHydrateError) {
      notices.push(
        renderNotice({
          title: l(LIVE_COPY.sessionHydrateErrorTitle),
          detail: liveCenter.sessionHydrateError.message || t().live.loadError,
          actions: [
            {
              action: "retry-session",
              label: l(LIVE_COPY.retryLiveSession)
            }
          ]
        })
      );
    }

    if (liveCenter.sessionError) {
      notices.push(
        `<div class="empty-state compact-empty">${liveCenter.sessionError.message || t().live.loadError}</div>`
      );
    }

    return notices.join("");
  }

  function renderOptionList(options, currentValue) {
    return options
      .map(
        (item) =>
          `<option value="${item.value}" ${item.value === currentValue ? "selected" : ""}>${pick(item.label)}</option>`
      )
      .join("");
  }

  function renderVoiceProfileOptions() {
    if (liveCenter.voiceProfilesStatus === "loading") {
      return `<option value="">${t().live.loadingVoices}</option>`;
    }

    if (!liveCenter.voiceProfiles.length) {
      return `<option value="">${t().live.noVoiceProfiles}</option>`;
    }

    const currentVoiceProfileId = state.currentSimulation.voiceProfileId;
    const hasCurrentOption =
      currentVoiceProfileId &&
      liveCenter.voiceProfiles.some(
        (profile) => profile.voiceProfileId === currentVoiceProfileId
      );
    const preservedOption =
      currentVoiceProfileId && !hasCurrentOption
        ? `<option value="${currentVoiceProfileId}" selected>${l(
            LIVE_COPY.preservedVoiceProfileLabel
          )}</option>`
        : "";

    return `${preservedOption}${liveCenter.voiceProfiles
      .map(
        (profile) =>
          `<option value="${profile.voiceProfileId}" ${profile.voiceProfileId === currentVoiceProfileId ? "selected" : ""}>${profile.label}</option>`
      )
      .join("")}`;
  }

  function renderPrecheckModal() {
    const modal = liveCenter.precheckModal;
    if (!modal || !modal.open) return "";

    return `
      <div class="modal-backdrop open">
        <div class="auth-modal" role="dialog" aria-modal="true" aria-label="${modal.headline}">
          <div class="auth-head">
            <h2>${modal.headline}</h2>
            <p>${modal.detail}</p>
          </div>
          <div class="inline-actions">
            <button type="button" class="secondary-btn" id="precheckBackBtn">${t().live.backToSetup}</button>
            <button type="button" class="primary-btn" id="precheckContinueBtn">${t().live.continueAnyway}</button>
          </div>
        </div>
      </div>`;
  }

  function liveSetupPage() {
    const country = getCountry(state.currentSimulation.country);
    const countries = Object.keys(COUNTRY_LIBRARY)
      .map(
        (key) =>
          `<option value="${key}" ${state.currentSimulation.country === key ? "selected" : ""}>${pick(COUNTRY_LIBRARY[key].label)}</option>`
      )
      .join("");

    const files = state.currentSimulation.files.length
      ? `<div class="file-list">${state.currentSimulation.files
          .map((file) => `<span class="file-pill">${joinMeta(file.name, file.size)}</span>`)
          .join("")}</div>`
      : `<div class="empty-state compact-empty">No supporting context files yet.</div>`;

    const durationLabel = `${state.currentSimulation.duration} min`;
    const selectedVoiceProfile =
      liveCenter.voiceProfiles.find(
        (item) => item.voiceProfileId === state.currentSimulation.voiceProfileId
      ) || null;
    const hasPreservedBackendVoiceProfile =
      state.currentSimulation.voiceProfileId && !selectedVoiceProfile;
    const disablePrimaryActions =
      !state.currentSimulation.voiceProfileId ||
      liveCenter.voiceProfilesStatus === "loading" ||
      liveCenter.requestStatus.generate === "loading" ||
      liveCenter.requestStatus.start === "loading";

    const strategyButtonLabel =
      liveCenter.requestStatus.generate === "loading"
        ? t().live.generating
        : t().live.generate;
    const startButtonLabel =
      liveCenter.requestStatus.start === "loading"
        ? t().live.starting
        : t().live.start;

    return `
      <section class="route-page live-workspace-page module-page">
        ${renderSetupBanners()}
        <div class="module-toolbar live-toolbar">
          <div>
            <small>Pre-meeting workspace</small>
            <strong>Prepare a new live rehearsal</strong>
          </div>
          <div class="module-toolbar-actions">
            <span class="toolbar-note">${joinMeta(
              pick(country.label),
              pick(getMeetingTypeDisplay(state.currentSimulation.meetingType))
            )}</span>
            <span class="toolbar-note">${durationLabel}</span>
          </div>
        </div>

        <div class="live-workspace-grid">
          <section class="module-panel live-form-panel">
            <div class="panel-head">
              <div>
                <h2>${t().live.setupTitle}</h2>
                <p>${t().live.readyCopy}</p>
              </div>
            </div>
            <form id="setupForm" class="live-setup-form">
              <div class="field-grid">
                <label class="field">
                  <span class="field-label">${t().live.country}</span>
                  <select class="select" id="field-country">${countries}</select>
                </label>
                <label class="field">
                  <span class="field-label">${t().live.meeting}</span>
                  <select class="select" id="field-meeting">${renderOptionList(
                    meetingTypeOptions,
                    state.currentSimulation.meetingType
                  )}</select>
                </label>
              </div>
              <div class="field-grid">
                <label class="field">
                  <span class="field-label">${t().live.goal}</span>
                  <select class="select" id="field-goal">${renderOptionList(
                    goalOptions,
                    state.currentSimulation.goal
                  )}</select>
                </label>
                <label class="field">
                  <span class="field-label">${t().live.voice}</span>
                  <select class="select" id="field-voice">${renderOptionList(
                    voiceStyleOptions,
                    state.currentSimulation.voiceStyle
                  )}</select>
                </label>
              </div>
              <div class="field-grid">
                <label class="field">
                  <span class="field-label">${t().live.voiceProfile}</span>
                  <select class="select" id="field-voice-profile" ${!liveCenter.voiceProfiles.length ? "disabled" : ""}>${renderVoiceProfileOptions()}</select>
                </label>
                <label class="field">
                  <span class="field-label">${t().live.duration}</span>
                  <div class="range-wrap">
                    <input type="range" min="5" max="20" step="1" id="field-duration" value="${state.currentSimulation.duration}" />
                    <span>${durationLabel}</span>
                  </div>
                </label>
              </div>
              <label class="textarea-field">
                <span class="field-label">${t().live.constraint}</span>
                <textarea class="textarea" id="field-constraint">${state.currentSimulation.constraint || ""}</textarea>
              </label>
              <label class="upload-field">
                <span class="field-label">${t().live.upload}</span>
                <span class="field-help">${t().live.uploadHelp}</span>
                <input type="file" id="field-files" accept=".pdf,.txt" multiple />
                ${files}
              </label>
            </form>
          </section>

          <aside class="module-panel live-brief-panel">
            <div class="panel-head">
              <div>
                <h2>Meeting brief</h2>
                <p>${t().live.trackedCopy}</p>
              </div>
              <span class="route-pill active">${pick(
                getSimulationStatusDisplay(
                  state.currentSimulation.simulationStatus || "draft"
                )
              )}</span>
            </div>
            <div class="live-brief-summary">
              <div>
                <small>${t().live.country}</small>
                <strong>${pick(country.label)}</strong>
              </div>
              <div>
                <small>${t().live.goal}</small>
                <strong>${pick(getGoalDisplay(state.currentSimulation.goal))}</strong>
              </div>
              <div>
                <small>${t().live.voice}</small>
                <strong>${pick(
                  getVoiceStyleDisplay(state.currentSimulation.voiceStyle)
                )}</strong>
              </div>
              <div>
                <small>${t().live.voiceProfile}</small>
                <strong>${selectedVoiceProfile ? selectedVoiceProfile.label : hasPreservedBackendVoiceProfile ? l(LIVE_COPY.preservedVoiceProfileLabel) : t().live.noVoiceProfiles}</strong>
              </div>
              <div>
                <small>${t().live.duration}</small>
                <strong>${durationLabel}</strong>
              </div>
              <div>
                <small>${t().live.setupRevision}</small>
                <strong>${state.currentSimulation.setupRevision || "-"}</strong>
              </div>
            </div>
            ${
              !liveCenter.voiceProfiles.length
                ? `<div class="empty-state compact-empty">${t().live.noVoiceProfiles}</div>`
                : ""
            }
            <div class="live-strategy-stack">
              <div class="panel-subhead">${t().live.generated}</div>
              ${setupStrategiesTemplate()}
            </div>
            <div class="inline-actions live-primary-actions">
              <button type="button" class="secondary-btn" id="generateStrategyBtn" data-testid="generate-strategy-btn" ${
                disablePrimaryActions ? "disabled" : ""
              }>${strategyButtonLabel}</button>
              <button type="button" class="primary-btn" id="startSessionBtn" data-testid="start-simulation-btn" ${
                disablePrimaryActions ? "disabled" : ""
              }>${startButtonLabel}</button>
            </div>
          </aside>
        </div>
        ${renderPrecheckModal()}
      </section>`;
  }

  function latestTurnBySpeaker(speaker) {
    const reversed = [...state.currentSimulation.transcript].reverse();
    return reversed.find((item) => item.speaker === speaker) || null;
  }

  function liveSessionPage() {
    const country = getCountry(state.currentSimulation.country);
    const summary = state.currentSimulation.sessionSummary || {};
    const liveStatus = summary.status || state.currentSimulation.realtimeStatus || "active";
    const turnCount = summary.turnCount ?? state.currentSimulation.transcript.length;
    const alertCount = summary.alertCount ?? state.currentSimulation.alerts.length;
    const latestAlert = state.currentSimulation.alerts[0] || null;
    const focusPrompt =
      state.currentSimulation.strategies[0]?.bullets?.[state.lang]?.[0] ||
      l(LIVE_COPY.sessionFocusFallback);
    const alertTitle = latestAlert ? latestAlert.title : l(LIVE_COPY.sessionFocusTitle);
    const alertDetail = latestAlert ? latestAlert.detail : focusPrompt;
    const alertSeverity = latestAlert?.severity || "neutral";
    const liveSessionLabel = `${l(LIVE_COPY.liveSessionPrefix)}: ${pick(
      getMeetingTypeDisplay(state.currentSimulation.meetingType)
    )} (${pick(country.label)})`;
    const transcriptTurns = state.currentSimulation.transcript.length
      ? state.currentSimulation.transcript
      : [
          {
            speaker: "Partner",
            local: country.localOpening,
            en: country.openingEn,
            zh: country.openingZh,
            tags: ["Opening"]
          }
        ];
    const metaPills = [
      {
        label: t().live.meetingGoal,
        value: pick(getGoalDisplay(state.currentSimulation.goal))
      },
      {
        label: l(LIVE_COPY.turnsLabel),
        value: turnCount
      },
      {
        label: l(LIVE_COPY.alertsLabel),
        value: alertCount
      },
      {
        label: "Status",
        value: pick(getSessionStatusDisplay(liveStatus))
      }
    ];

    const transcriptMarkup = transcriptTurns
      .map((turn) => {
        const role =
          turn.speaker === "User"
            ? "user"
            : turn.speaker === "Partner"
              ? "partner"
              : "assistant";
        const translated = state.lang === "zh" ? turn.zh : turn.en;
        const showTranslation = translated && translated !== turn.local;
        const tags = Array.isArray(turn.tags) ? turn.tags.slice(0, 2) : [];
        const isUser = role === "user";
        const avatarLabel = isUser
          ? initials(state.user.name)
          : pick(country.label).slice(0, 2).toUpperCase();

        return `
          <article class="meeting-bubble-row ${role}">
            ${
              isUser
                ? ""
                : `<div class="meeting-focus-avatar ${role}">${avatarLabel}</div>`
            }
            <div class="meeting-bubble-stack ${role}">
              <span class="meeting-bubble-label">${speakerLabel(turn.speaker)}</span>
              <div class="meeting-bubble ${role}">
                <p>${turn.local}</p>
                ${
                  showTranslation
                    ? `<small class="meeting-bubble-translation">${translated}</small>`
                    : ""
                }
                ${
                  tags.length
                    ? `<div class="meeting-bubble-tags">${tags
                        .map((tag) => `<span class="meeting-bubble-tag">${tag}</span>`)
                        .join("")}</div>`
                    : ""
                }
              </div>
            </div>
            ${
              isUser
                ? `<div class="meeting-focus-avatar ${role}">${avatarLabel}</div>`
                : ""
            }
          </article>`;
      })
      .join("");

    const typingMarkup =
      liveCenter.requestStatus.respond === "loading"
        ? `
          <article class="meeting-bubble-row partner typing">
            <div class="meeting-focus-avatar partner">${pick(country.label)
              .slice(0, 2)
              .toUpperCase()}</div>
            <div class="meeting-bubble-stack partner">
              <span class="meeting-bubble-label">${speakerLabel("Partner")}</span>
              <div class="meeting-bubble typing">
                <div class="meeting-typing-dots" aria-hidden="true">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                <small class="meeting-bubble-translation">${l(
                  LIVE_COPY.partnerTyping
                )}</small>
              </div>
            </div>
          </article>`
        : "";

    return `
      <section class="route-page meeting-focus-page">
        ${renderSessionBanner()}
        <div class="meeting-focus-shell">
          <header class="meeting-focus-header">
            <div class="meeting-focus-header-left">
              <button class="meeting-back-btn" id="backToSetupBtn" data-testid="back-to-setup-btn">${t().live.backToSetup}</button>
              <div class="meeting-focus-session-pill liquid-glass">
                <span class="meeting-focus-live-dot"></span>
                <strong>${liveSessionLabel}</strong>
              </div>
            </div>
            <div class="meeting-focus-header-right">
              <span class="meeting-status-chip">${pick(
                getSessionStatusDisplay(liveStatus)
              )}</span>
              <span class="meeting-timer">${t().live.countdown}: ${Math.floor(
                state.currentSimulation.countdown / 60
              )}:00</span>
            </div>
          </header>

          <aside class="meeting-focus-alert ${alertSeverity}" aria-live="polite">
            <div class="meeting-focus-alert-mark">${latestAlert ? "!" : "+"}</div>
            <div class="meeting-focus-alert-copy">
              <div class="meeting-focus-alert-top">
                <strong>${alertTitle}</strong>
                ${
                  latestAlert
                    ? `<span class="meeting-focus-alert-severity">${pick(
                        getSeverityDisplay(latestAlert.severity)
                      )}</span>`
                    : ""
                }
              </div>
              <p>${alertDetail}</p>
              <small>${joinMeta(
                `${l(LIVE_COPY.turnsLabel)} ${turnCount}`,
                `${l(LIVE_COPY.alertsLabel)} ${alertCount}`
              )}</small>
            </div>
          </aside>

          <div class="meeting-focus-stage">
            <div class="meeting-focus-meta">
              ${metaPills
                .map(
                  (item, index) => `
                    <span class="meeting-focus-meta-pill ${index === 0 ? "emphasis" : ""}">
                      <small>${item.label}</small>
                      <strong>${item.value}</strong>
                    </span>`
                )
                .join("")}
            </div>
            <div class="meeting-focus-stream transcript-scroll">
              ${transcriptMarkup}
              ${typingMarkup}
            </div>
          </div>

          <div class="meeting-focus-dock-wrap">
            <div class="meeting-focus-dock liquid-glass">
              <label class="meeting-focus-input-shell">
                <span class="meeting-focus-input-label">${t().live.practice}</span>
                <textarea class="meeting-focus-input" id="practiceInput" placeholder="${l(
                  LIVE_COPY.responsePromptHint
                )}">${state.currentSimulation.practiceText}</textarea>
              </label>
              <div class="meeting-focus-controls">
                <button class="meeting-focus-mic" id="micBtn">Mic</button>
                <span class="meeting-focus-divider" aria-hidden="true"></span>
                <button class="secondary-btn meeting-focus-evaluate-btn" id="evaluateBtn" data-testid="evaluate-language-btn" ${
                  liveCenter.requestStatus.respond === "loading" ? "disabled" : ""
                }>${liveCenter.requestStatus.respond === "loading" ? t().live.evaluating : t().live.evaluate}</button>
                <button class="ghost-btn meeting-focus-end-btn" id="endSessionBtn" data-testid="end-session-btn" ${
                  liveCenter.requestStatus.end === "loading" ? "disabled" : ""
                }>${liveCenter.requestStatus.end === "loading" ? t().live.ending : t().live.end}</button>
              </div>
            </div>
          </div>
        </div>
      </section>`;
  }

  return state.currentSimulation.phase === "session" ? liveSessionPage() : liveSetupPage();
}
