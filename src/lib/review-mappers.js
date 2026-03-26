const COUNTRY_DISPLAY = {
  Japan: { en: "Japan", zh: "\u65e5\u672c" },
  Germany: { en: "Germany", zh: "\u5fb7\u56fd" },
  UAE: { en: "UAE", zh: "\u963f\u8054\u914b" }
};

const MEETING_TYPE_DISPLAY = {
  first_introduction: {
    en: "First Introduction",
    zh: "\u521d\u6b21\u4ecb\u7ecd"
  },
  commercial_alignment: {
    en: "Commercial Alignment",
    zh: "\u5546\u4e1a\u5bf9\u9f50"
  },
  relationship_building: {
    en: "Relationship Building",
    zh: "\u5173\u7cfb\u5efa\u7acb"
  }
};

const GOAL_DISPLAY = {
  establish_trust_before_pricing: {
    en: "Establish trust before pricing",
    zh: "\u5148\u5efa\u7acb\u4fe1\u4efb\uff0c\u518d\u8fdb\u5165\u4ef7\u683c"
  },
  clarify_process_and_risk_ownership: {
    en: "Clarify process and risk ownership",
    zh: "\u5bf9\u9f50\u6d41\u7a0b\u4e0e\u98ce\u9669\u8d23\u4efb"
  },
  build_rapport_before_scope_depth: {
    en: "Build rapport before scope depth",
    zh: "\u5148\u5efa\u7acb\u5173\u7cfb\uff0c\u518d\u6df1\u5165\u8303\u56f4"
  }
};

const ASSESSMENT_DISPLAY = {
  needs_work: {
    en: "Needs work",
    zh: "\u9700\u8981\u52a0\u5f3a"
  },
  mixed: {
    en: "Mixed",
    zh: "\u8868\u73b0\u4e0d\u4e00"
  },
  promising: {
    en: "Promising",
    zh: "\u6709\u826f\u597d\u57fa\u7840"
  }
};

const STAT_LABELS = {
  turnCount: { en: "Turns", zh: "\u8f6e\u6b21" },
  alertCount: { en: "Alerts", zh: "\u63d0\u9192" },
  highSeverityCount: { en: "High severity", zh: "\u9ad8\u98ce\u9669" },
  mediumSeverityCount: { en: "Medium severity", zh: "\u4e2d\u98ce\u9669" }
};

function localizeText(text) {
  return { en: text, zh: text };
}

function getCountryDisplay(countryKey) {
  return COUNTRY_DISPLAY[countryKey] || { en: countryKey, zh: countryKey };
}

function getMeetingTypeDisplay(meetingType) {
  return (
    MEETING_TYPE_DISPLAY[meetingType] || { en: meetingType, zh: meetingType }
  );
}

function getGoalDisplay(goalKey) {
  return GOAL_DISPLAY[goalKey] || { en: goalKey, zh: goalKey };
}

function getAssessmentDisplay(overallAssessment) {
  return (
    ASSESSMENT_DISPLAY[overallAssessment] || {
      en: overallAssessment,
      zh: overallAssessment
    }
  );
}

function buildReviewTitle(countryKey, meetingType) {
  const country = getCountryDisplay(countryKey);
  const meeting = getMeetingTypeDisplay(meetingType);
  return {
    en: `${country.en} / ${meeting.en}`,
    zh: `${country.zh} / ${meeting.zh}`
  };
}

function buildFallbackSummaryFromList(item) {
  if (item.topIssueKeys && item.topIssueKeys.length) {
    return localizeText(`Top issues: ${item.topIssueKeys.join(", ")}.`);
  }

  return getAssessmentDisplay(item.overallAssessment);
}

function normalizeUiSource(sourceType) {
  return sourceType === "realtime_session" ? "simulation" : sourceType;
}

function buildDetailStats(metrics) {
  return [
    {
      key: "turnCount",
      label: STAT_LABELS.turnCount,
      value: metrics.turnCount
    },
    {
      key: "alertCount",
      label: STAT_LABELS.alertCount,
      value: metrics.alertCount
    },
    {
      key: "highSeverityCount",
      label: STAT_LABELS.highSeverityCount,
      value: metrics.highSeverityCount
    },
    {
      key: "mediumSeverityCount",
      label: STAT_LABELS.mediumSeverityCount,
      value: metrics.mediumSeverityCount
    }
  ];
}

export function mapReviewListItem(apiItem) {
  return {
    id: apiItem.reviewId,
    sourceType: apiItem.sourceType,
    source: normalizeUiSource(apiItem.sourceType),
    title: buildReviewTitle(apiItem.countryKey, apiItem.meetingType),
    country: apiItem.countryKey,
    meetingType: apiItem.meetingType,
    goal: apiItem.goal,
    date: apiItem.createdAt,
    createdAt: apiItem.createdAt,
    endedAt: apiItem.endedAt,
    status: apiItem.status,
    overallAssessment: apiItem.overallAssessment,
    assessmentLabel: getAssessmentDisplay(apiItem.overallAssessment),
    repeatedIssues: apiItem.topIssueKeys || [],
    summary: buildFallbackSummaryFromList(apiItem)
  };
}

export function mapReviewDetail(apiDetail) {
  const metrics = {
    turnCount: apiDetail.metrics.turnCount,
    alertCount: apiDetail.metrics.alertCount,
    highSeverityCount: apiDetail.metrics.highSeverityCount,
    mediumSeverityCount: apiDetail.metrics.mediumSeverityCount,
    topIssueKeys: apiDetail.metrics.topIssueKeys || []
  };

  return {
    id: apiDetail.reviewId,
    sourceType: apiDetail.sourceType,
    source: normalizeUiSource(apiDetail.sourceType),
    title: buildReviewTitle(apiDetail.countryKey, apiDetail.meetingType),
    country: apiDetail.countryKey,
    meetingType: apiDetail.meetingType,
    meetingTypeLabel: getMeetingTypeDisplay(apiDetail.meetingType),
    goal: apiDetail.goal,
    goalLabel: getGoalDisplay(apiDetail.goal),
    date: apiDetail.createdAt,
    createdAt: apiDetail.createdAt,
    endedAt: apiDetail.endedAt,
    status: apiDetail.status,
    overallAssessment: apiDetail.overallAssessment,
    assessmentLabel: getAssessmentDisplay(apiDetail.overallAssessment),
    voiceStyle: apiDetail.voiceStyle,
    voiceProfileId: apiDetail.voiceProfileId,
    durationMinutes: apiDetail.durationMinutes,
    setupRevision: apiDetail.setupRevision,
    strategyForSetupRevision: apiDetail.strategyForSetupRevision,
    headline: localizeText(apiDetail.summary.headline),
    summary: localizeText(apiDetail.summary.coachSummary),
    nextStep: localizeText(apiDetail.summary.nextStep),
    repeatedIssues: metrics.topIssueKeys,
    metrics,
    stats: buildDetailStats(metrics),
    lines: apiDetail.lines.map((line) => ({
      lineIndex: line.lineIndex,
      speaker: line.speaker,
      turnIndex: line.turnIndex,
      sourceText: line.text,
      alertIssueKeys: line.alertIssueKeys || [],
      createdAt: line.createdAt
    }))
  };
}

function mapLegacyLine(line, index, fallbackDate) {
  return {
    lineIndex: index + 1,
    speaker:
      line.speaker === "User"
        ? "user"
        : line.speaker === "Partner"
          ? "assistant"
          : "assistant",
    turnIndex: index + 1,
    sourceText: line.sourceText,
    alertIssueKeys: line.issueKey ? [line.issueKey] : [],
    createdAt: fallbackDate
  };
}

function buildLegacySummary(review) {
  const firstIssue = review.repeatedIssues && review.repeatedIssues[0];
  return {
    headline:
      review.source === "device"
        ? "Device review snapshot."
        : "Realtime review snapshot.",
    coachSummary:
      typeof review.summary === "string"
        ? review.summary
        : review.summary && review.summary.en
          ? review.summary.en
          : "",
    nextStep: firstIssue
      ? `Focus on ${firstIssue.replaceAll("_", " ")} in the next rehearsal.`
      : "Keep the next rehearsal practical and specific."
  };
}

export function mapLegacyReviewListItem(review) {
  return {
    id: review.id,
    sourceType: review.source,
    source: review.source,
    title: review.title,
    country: review.country,
    meetingType: null,
    goal: null,
    date: review.date,
    createdAt: review.date,
    endedAt: review.date,
    status: "ready",
    overallAssessment: "mixed",
    assessmentLabel: getAssessmentDisplay("mixed"),
    repeatedIssues: review.repeatedIssues || [],
    summary:
      typeof review.summary === "string"
        ? localizeText(review.summary)
        : review.summary
  };
}

export function mapLegacyReviewDetail(review) {
  const summary = buildLegacySummary(review);
  const lines = (review.lines || []).map((line, index) =>
    mapLegacyLine(line, index, review.date)
  );
  const metrics = {
    turnCount: lines.length,
    alertCount: lines.filter((line) => line.alertIssueKeys.length).length,
    highSeverityCount: 0,
    mediumSeverityCount: lines.filter((line) => line.alertIssueKeys.length).length,
    topIssueKeys: review.repeatedIssues || []
  };

  return {
    id: review.id,
    sourceType: review.source,
    source: review.source,
    title: review.title,
    country: review.country,
    meetingType: null,
    meetingTypeLabel: null,
    goal: null,
    goalLabel: null,
    date: review.date,
    createdAt: review.date,
    endedAt: review.date,
    status: "ready",
    overallAssessment: "mixed",
    assessmentLabel: getAssessmentDisplay("mixed"),
    voiceStyle: null,
    voiceProfileId: null,
    durationMinutes: null,
    setupRevision: null,
    strategyForSetupRevision: null,
    headline: localizeText(summary.headline),
    summary: localizeText(summary.coachSummary),
    nextStep: localizeText(summary.nextStep),
    repeatedIssues: review.repeatedIssues || [],
    metrics,
    stats: buildDetailStats(metrics),
    lines
  };
}
