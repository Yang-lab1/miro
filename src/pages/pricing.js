export function pricingPage(ctx) {
  const { state, pricingCenter, t, formatBalance, translateByGroup, formatDate } = ctx;
  const plans = pricingCenter.plans || [];
  const summary = pricingCenter.summary || {
    currentPlanKey: state.pricingSelection || "free",
    creditBalance: state.user.balance ?? 0,
    renewalAt: state.user.renewal || null,
    currentPlan: {
      displayName: state.user.plan || "Free"
    },
    allowedTopUpAmounts: [500, 1500, 3000]
  };
  const isHydrating =
    pricingCenter.routeHydrationStatus === "loading" && !pricingCenter.summary;
  const isActionPending = pricingCenter.actionStatus === "pending";
  const error = pricingCenter.actionError || pricingCenter.loadError;
  const renewalLabel = summary.renewalAt
    ? formatDate(summary.renewalAt)
    : "No renewal scheduled";
  const topUpAmounts = summary.allowedTopUpAmounts || [500, 1500, 3000];
  const currentPlanLabel = summary.currentPlan
    ? summary.currentPlan.displayName
    : translateByGroup("plan", state.user.plan);
  const cardsMarkup = plans.length
    ? plans
        .map(
          (card) => `
          <article class="pricing-card ${card.badge ? "recommended" : ""} ${card.isCurrent ? "selected" : ""}" data-plan="${card.planKey}" data-testid="pricing-card-${card.planKey}" role="button" tabindex="0" aria-pressed="${card.isCurrent}">
            <div class="pricing-card-top">
              <div class="pricing-card-head">
                <div class="pricing-card-copy">
                  <h3>${card.name}</h3>
                  <p class="pricing-description">${card.desc}</p>
                </div>
                ${card.badge ? `<span class="pricing-badge">${card.badge}</span>` : ""}
              </div>
              <div class="pricing-price">
                <span>$</span>
                <strong>${card.price}</strong>
                <small>${card.currencyCode} / mo</small>
              </div>
            </div>
            <button class="${card.badge ? "primary-btn" : "secondary-btn"} pricing-action" data-plan="${card.planKey}" data-testid="pricing-action-${card.planKey}" ${card.isCurrent || isActionPending ? "disabled" : ""}>${card.ctaLabel}</button>
            <ul class="pricing-features">${card.features.map((feature) => `<li>${feature}</li>`).join("")}</ul>
          </article>`
        )
        .join("")
    : `<div class="empty-state compact-empty">No demo billing plans are available right now.</div>`;

  return `
    <section class="route-page module-page pricing-clean-page">
      <div class="module-toolbar">
        <div>
          <small>${t().nav.pricing}</small>
          <strong>Upgrade your plan</strong>
        </div>
        <div class="module-toolbar-actions">
          <div class="pricing-toggle">
            <button class="pricing-toggle-btn active">Personal</button>
            <button class="pricing-toggle-btn">Business</button>
          </div>
          <span class="toolbar-note" data-testid="pricing-balance">Available credits: ${formatBalance(summary.creditBalance)}</span>
        </div>
      </div>

      ${isHydrating ? `<div class="empty-state compact-empty">Loading billing workspace...</div>` : ""}
      ${error ? `<div class="empty-state compact-empty" data-testid="pricing-error">${error.message || "Unable to update billing right now."}</div>` : ""}

      <div class="pricing-grid">
        ${cardsMarkup}
      </div>

      <section class="pricing-credit-panel module-panel">
        <div>
          <small>Current workspace plan</small>
          <strong data-testid="pricing-current-plan">${currentPlanLabel}</strong>
          <p class="helper-copy">Demo billing only. Actions update simulated backend state, not real payments.</p>
          <small data-testid="pricing-renewal">Renewal: ${renewalLabel}</small>
        </div>
        <div class="pricing-credit-actions">
          ${topUpAmounts
            .map((amount, index) => {
              const className =
                index === 0 ? "primary-btn" : index === 1 ? "secondary-btn" : "ghost-btn";
              return `<button class="${className}" data-topup="${amount}" data-testid="pricing-topup-${amount}" ${isHydrating || isActionPending ? "disabled" : ""}>Top up +${amount}</button>`;
            })
            .join("")}
        </div>
      </section>
    </section>`;
}
