const COUNTRY_DISPLAY = {
  Japan: { en: "Japan", zh: "日本" },
  Germany: { en: "Germany", zh: "德国" },
  UAE: { en: "UAE", zh: "阿联酋" }
};

const MEETING_TYPE_OPTIONS = [
  {
    key: "first_introduction",
    ui: "First Introduction",
    label: { en: "First Introduction", zh: "初次介绍" }
  },
  {
    key: "commercial_alignment",
    ui: "Commercial Alignment",
    label: { en: "Commercial Alignment", zh: "商业对齐" }
  },
  {
    key: "relationship_building",
    ui: "Relationship Building",
    label: { en: "Relationship Building", zh: "关系建立" }
  }
];

const GOAL_OPTIONS = [
  {
    key: "establish_trust_before_pricing",
    ui: "Establish trust before pricing",
    label: { en: "Establish trust before pricing", zh: "先建立信任，再进入价格" }
  },
  {
    key: "clarify_process_and_risk_ownership",
    ui: "Clarify process and risk ownership",
    label: { en: "Clarify process and risk ownership", zh: "对齐流程与风险责任" }
  },
  {
    key: "build_rapport_before_scope_depth",
    ui: "Build rapport before scope depth",
    label: { en: "Build rapport before scope depth", zh: "先建立关系，再深入范围" }
  }
];

const VOICE_STYLE_OPTIONS = [
  {
    key: "formal_measured",
    ui: "Formal / measured",
    label: { en: "Formal / measured", zh: "正式 / 克制" }
  },
  {
    key: "direct_structured",
    ui: "Direct / structured",
    label: { en: "Direct / structured", zh: "直接 / 有结构" }
  },
  {
    key: "warm_relational",
    ui: "Warm / relational",
    label: { en: "Warm / relational", zh: "温和 / 关系导向" }
  }
];

const SIMULATION_STATUS_DISPLAY = {
  draft: { en: "Draft", zh: "草稿" },
  ready_for_strategy: { en: "Ready for strategy", zh: "可生成策略" },
  strategy_ready: { en: "Strategy ready", zh: "策略已就绪" }
};

const SESSION_STATUS_DISPLAY = {
  pending: { en: "Pending", zh: "待启动" },
  active: { en: "Active", zh: "进行中" },
  ended: { en: "Ended", zh: "已结束" },
  failed: { en: "Failed", zh: "已失败" }
};

const SEVERITY_DISPLAY = {
  high: { en: "High", zh: "高" },
  medium: { en: "Medium", zh: "中" }
};

function findOption(options, value) {
  return options.find((item) => item.key === value || item.ui === value);
}

function optionToDisplay(options, value) {
  return (
    findOption(options, value)?.label || {
      en: value || "-",
      zh: value || "-"
    }
  );
}

function optionToUiValue(options, value) {
  return findOption(options, value)?.ui || value || "";
}

function optionToBackendKey(options, value) {
  return findOption(options, value)?.key || value || null;
}

export function getCountryDisplay(countryKey) {
  return COUNTRY_DISPLAY[countryKey] || { en: countryKey, zh: countryKey };
}

export function getMeetingTypeDisplay(value) {
  return optionToDisplay(MEETING_TYPE_OPTIONS, value);
}

export function getGoalDisplay(value) {
  return optionToDisplay(GOAL_OPTIONS, value);
}

export function getVoiceStyleDisplay(value) {
  return optionToDisplay(VOICE_STYLE_OPTIONS, value);
}

export function getSimulationStatusDisplay(value) {
  return (
    SIMULATION_STATUS_DISPLAY[value] || {
      en: value || "-",
      zh: value || "-"
    }
  );
}

export function getSessionStatusDisplay(value) {
  return (
    SESSION_STATUS_DISPLAY[value] || {
      en: value || "-",
      zh: value || "-"
    }
  );
}

export function getSeverityDisplay(value) {
  return (
    SEVERITY_DISPLAY[value] || {
      en: value || "-",
      zh: value || "-"
    }
  );
}

export function getMeetingTypeOptions() {
  return MEETING_TYPE_OPTIONS.map((item) => ({
    value: item.ui,
    key: item.key,
    label: item.label
  }));
}

export function getGoalOptions() {
  return GOAL_OPTIONS.map((item) => ({
    value: item.ui,
    key: item.key,
    label: item.label
  }));
}

export function getVoiceStyleOptions() {
  return VOICE_STYLE_OPTIONS.map((item) => ({
    value: item.ui,
    key: item.key,
    label: item.label
  }));
}

export function mapCurrentSimulationToPayload(simulation) {
  return {
    countryKey: simulation.country,
    meetingType: optionToBackendKey(MEETING_TYPE_OPTIONS, simulation.meetingType),
    goal: optionToBackendKey(GOAL_OPTIONS, simulation.goal),
    durationMinutes: simulation.duration,
    voiceStyle: optionToBackendKey(VOICE_STYLE_OPTIONS, simulation.voiceStyle),
    voiceProfileId: simulation.voiceProfileId || null,
    constraints: simulation.constraint || null
  };
}

export function mapStrategyItems(strategy) {
  if (!strategy || !strategy.items) return [];
  return strategy.items.map((item) => ({
    id: item.id,
    tag: item.tag,
    title: item.title,
    bullets: item.bullets
  }));
}

export function mergeSimulationResponse(currentSimulation, apiSimulation) {
  return {
    ...currentSimulation,
    simulationId: apiSimulation.simulationId,
    simulationStatus: apiSimulation.status,
    setupRevision: apiSimulation.setupRevision,
    country: apiSimulation.countryKey || currentSimulation.country,
    meetingType: apiSimulation.meetingType
      ? optionToUiValue(MEETING_TYPE_OPTIONS, apiSimulation.meetingType)
      : currentSimulation.meetingType,
    goal: apiSimulation.goal
      ? optionToUiValue(GOAL_OPTIONS, apiSimulation.goal)
      : currentSimulation.goal,
    duration:
      typeof apiSimulation.durationMinutes === "number"
        ? apiSimulation.durationMinutes
        : currentSimulation.duration,
    voiceStyle: apiSimulation.voiceStyle
      ? optionToUiValue(VOICE_STYLE_OPTIONS, apiSimulation.voiceStyle)
      : currentSimulation.voiceStyle,
    voiceProfileId:
      apiSimulation.voiceProfileId === undefined
        ? currentSimulation.voiceProfileId
        : apiSimulation.voiceProfileId,
    constraint:
      apiSimulation.constraints === undefined || apiSimulation.constraints === null
        ? currentSimulation.constraint
        : apiSimulation.constraints,
    strategies: mapStrategyItems(apiSimulation.strategy),
    strategySummary: apiSimulation.strategy ? apiSimulation.strategy.summary : null
  };
}

export function mapVoiceProfileOptions(apiItems) {
  return (apiItems || []).map((item) => ({
    value: item.voiceProfileId,
    voiceProfileId: item.voiceProfileId,
    label: item.displayName,
    gender: item.gender,
    locale: item.locale,
    providerVoiceId: item.providerVoiceId
  }));
}

export function pickVoiceProfileId(options, currentId) {
  if (!options.length) return null;
  if (currentId && options.some((item) => item.voiceProfileId === currentId)) {
    return currentId;
  }
  return options[0].voiceProfileId;
}

export function buildFallbackVoiceProfiles(countryKey) {
  return [
    {
      value: `fallback-${countryKey.toLowerCase()}-default`,
      voiceProfileId: `fallback-${countryKey.toLowerCase()}-default`,
      label: `${countryKey} local fallback`,
      gender: "neutral",
      locale: "en",
      providerVoiceId: "fallback-local"
    }
  ];
}

function mapSpeaker(value) {
  if (value === "assistant") return "Partner";
  if (value === "user") return "User";
  return value;
}

export function mapRealtimeTurn(apiTurn) {
  const baseText = apiTurn.sourceText || apiTurn.normalizedText || "";
  return {
    id: apiTurn.turnId,
    turnId: apiTurn.turnId,
    turnIndex: apiTurn.turnIndex,
    speaker: mapSpeaker(apiTurn.speaker),
    inputMode: apiTurn.inputMode,
    sourceText: apiTurn.sourceText,
    normalizedText: apiTurn.normalizedText || baseText,
    language: apiTurn.language || "en",
    parentTurnId: apiTurn.parentTurnId,
    local: baseText,
    en: apiTurn.normalizedText || baseText,
    zh: apiTurn.normalizedText || baseText,
    tags: [],
    issueKey: null,
    createdAt: apiTurn.createdAt
  };
}

export function mapRealtimeTurns(apiTurns) {
  return (apiTurns || []).map((item) => mapRealtimeTurn(item));
}

export function mapRealtimeAlert(apiAlert) {
  return {
    id: apiAlert.alertId,
    alertId: apiAlert.alertId,
    turnId: apiAlert.turnId,
    severity: apiAlert.severity,
    issueKey: apiAlert.issueKey,
    title: apiAlert.title,
    detail: apiAlert.detail,
    createdAt: apiAlert.createdAt
  };
}

export function mapRealtimeAlerts(apiAlerts) {
  return (apiAlerts || []).map((item) => mapRealtimeAlert(item));
}

export function mergeRealtimeSessionResponse(currentSimulation, apiSession) {
  return {
    ...currentSimulation,
    sessionId: apiSession.sessionId,
    realtimeStatus: apiSession.status,
    sessionSummary: currentSimulation.sessionSummary
      ? {
          ...currentSimulation.sessionSummary,
          status: apiSession.status
        }
      : null,
    simulationId: apiSession.simulationId || currentSimulation.simulationId,
    country: apiSession.countryKey || currentSimulation.country,
    meetingType: apiSession.meetingType
      ? optionToUiValue(MEETING_TYPE_OPTIONS, apiSession.meetingType)
      : currentSimulation.meetingType,
    goal: apiSession.goal
      ? optionToUiValue(GOAL_OPTIONS, apiSession.goal)
      : currentSimulation.goal,
    duration:
      typeof apiSession.durationMinutes === "number"
        ? apiSession.durationMinutes
        : currentSimulation.duration,
    voiceStyle: apiSession.voiceStyle
      ? optionToUiValue(VOICE_STYLE_OPTIONS, apiSession.voiceStyle)
      : currentSimulation.voiceStyle,
    voiceProfileId:
      apiSession.voiceProfileId === undefined
        ? currentSimulation.voiceProfileId
        : apiSession.voiceProfileId,
    setupRevision:
      apiSession.setupRevision === undefined
        ? currentSimulation.setupRevision
        : apiSession.setupRevision,
    strategyForSetupRevision:
      apiSession.strategyForSetupRevision === undefined
        ? currentSimulation.strategyForSetupRevision
        : apiSession.strategyForSetupRevision
  };
}

export function mapRealtimeSummary(apiSummary) {
  return {
    status: apiSummary.status,
    turnCount: apiSummary.turnCount,
    alertCount: apiSummary.alertCount,
    lastAlertSeverity: apiSummary.lastAlertSeverity,
    startedAt: apiSummary.startedAt,
    endedAt: apiSummary.endedAt,
    createdAt: apiSummary.createdAt,
    updatedAt: apiSummary.updatedAt
  };
}

export function mapPrecheckModal(precheck) {
  if (precheck.reason === "learning_required") {
    return {
      headline: "Learning check is incomplete",
      detail:
        "This country still needs a learning pass before the live rehearsal. You can continue anyway or go back to setup."
    };
  }

  if (precheck.reason === "learning_outdated") {
    return {
      headline: "Learning content is out of date",
      detail:
        "The learning content was completed before the latest version. You can continue anyway or go back to setup."
    };
  }

  return {
    headline: "Precheck requires attention",
    detail:
      "The session is not fully ready for launch. Review the setup before continuing."
  };
}
