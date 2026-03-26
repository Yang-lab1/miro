function renderIssues(ctx, issueKeys) {
  const { t, issueText } = ctx;
  if (!issueKeys.length) return `<span class="route-pill">${t().review.none}</span>`;
  return issueKeys
    .map((issueKey) => {
      const issue = issueText(issueKey);
      return `<span class="route-pill active" title="${issue.detail}">${issue.short}</span>`;
    })
    .join("");
}

function renderListState(ctx, filtered, selectedCard) {
  const { t, pick, formatDate, reviewCenter, getCountry } = ctx;

  if (reviewCenter.listStatus === "loading") {
    return `<div class="empty-state">${t().review.loading}</div>`;
  }

  if (!filtered.length && reviewCenter.listError) {
    return `<div class="empty-state">${t().review.loadError}</div>`;
  }

  if (!filtered.length) {
    return `<div class="empty-state">${t().review.empty}</div>`;
  }

  return filtered
    .map(
      (item) => `
        <article class="review-card ${selectedCard && selectedCard.id === item.id ? "active" : ""}">
          <button data-review-select="${item.id}">
            <div class="review-card-top">
              <span class="source-pill">${item.source === "simulation" ? t().misc.sourceSimulation : t().misc.sourceDevice}</span>
              <span>${formatDate(item.date)}</span>
            </div>
            <h3>${pick(item.title)}</h3>
            <p class="helper-copy">${pick(item.summary)}</p>
            <div class="review-card-top">
              <span class="route-pill active">${pick(item.assessmentLabel)}</span>
              <span>${pick(getCountry(item.country).label)}</span>
            </div>
          </button>
        </article>`
    )
    .join("");
}

function renderDetailState(ctx, selectedCard, review) {
  const { t, pick, reviewCenter } = ctx;

  if (!selectedCard) {
    return `<div class="empty-state">${t().review.empty}</div>`;
  }

  if (!reviewCenter.fallbackActive && reviewCenter.detailStatus === "loading") {
    return `<div class="empty-state">${t().review.loading}</div>`;
  }

  if (!reviewCenter.fallbackActive && reviewCenter.detailStatus === "error") {
    return `<div class="empty-state">${t().review.detailError}</div>`;
  }

  if (!review) {
    return `<div class="empty-state">${t().review.detailError}</div>`;
  }

  return `
    <div class="review-card-top">
      <div>
        <span class="source-pill">${review.source === "simulation" ? t().misc.sourceSimulation : t().misc.sourceDevice}</span>
        <h2>${pick(review.title)}</h2>
        <p>${pick(review.headline)}</p>
      </div>
      <span class="route-pill active">${pick(review.assessmentLabel)}</span>
    </div>
    <div class="review-lines">
      <article class="review-line">
        <div class="line-head">
          <strong>${t().review.transcriptSummary}</strong>
        </div>
        <div>${pick(review.summary)}</div>
      </article>
      <article class="review-line">
        <div class="line-head">
          <strong>${t().review.nextStep}</strong>
        </div>
        <div>${pick(review.nextStep)}</div>
      </article>
    </div>
    <div class="review-stats">
      ${review.stats
        .map(
          (item) => `
            <div class="kpi-card">
              <small>${pick(item.label)}</small>
              <strong>${item.value}</strong>
            </div>`
        )
        .join("")}
    </div>
    <div>
      <h3>${t().review.repeated}</h3>
      <div class="inline-actions">${renderIssues(ctx, review.repeatedIssues)}</div>
    </div>
    <div>
      <h3>${t().review.lines}</h3>
      <div class="review-lines">
        ${review.lines
          .map(
            (line) => `
              <article class="review-line ${line.alertIssueKeys.length ? "issue" : ""}">
                <div class="line-head">
                  <strong>${ctx.speakerLabel(line.speaker)}</strong>
                  <span>#${line.turnIndex}</span>
                </div>
                <div>${line.sourceText}</div>
                ${
                  line.alertIssueKeys.length
                    ? `<div class="line-tags">${renderIssues(ctx, line.alertIssueKeys)}</div>`
                    : ""
                }
              </article>`
          )
          .join("")}
      </div>
    </div>`;
}

export function reviewPage(ctx) {
  const { t, reviewCenter, getSelectedReview, getSelectedReviewCard, getFilteredReviews } = ctx;
  const filtered = getFilteredReviews();
  const selectedCard = getSelectedReviewCard();
  const review = getSelectedReview();

  const banner = reviewCenter.listError
    ? `<div class="empty-state">${reviewCenter.fallbackActive ? t().review.fallback : t().review.loadError}</div>`
    : "";

  return `
    <section class="route-page module-page review-clean-page">
      <div class="module-toolbar">
        <div>
          <small>${t().review.eyebrow}</small>
          <strong>${filtered.length ? `${filtered.length} ${t().review.records}` : t().review.title}</strong>
        </div>
      </div>

      ${banner}

      <div class="review-layout review-clean-layout">
        <section class="review-list module-panel" data-testid="review-list-container">
          <div class="panel-head">
            <div>
              <h2>${t().review.title}</h2>
              <p>${filtered.length ? `${filtered.length} ${t().review.records}` : t().review.empty}</p>
            </div>
          </div>
          <div class="review-card-list">${renderListState(ctx, filtered, selectedCard)}</div>
        </section>

        <section class="review-detail module-panel" data-testid="review-detail-container">
          ${renderDetailState(ctx, selectedCard, review)}
        </section>
      </div>
    </section>`;
}
