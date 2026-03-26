const PLAN_ORDER = ["free", "go", "plus", "pro"];

const PRICING_CARD_META = {
  free: {
    desc: "Understand the language workflow.",
    features: [
      "Basic simulation access",
      "Single-session review",
      "Limited memory preview",
      "Read-only hardware page"
    ]
  },
  go: {
    desc: "Unlock longer practice and more prep material.",
    features: [
      "Longer practice windows",
      "More uploaded context",
      "Expanded review history",
      "More reminders"
    ]
  },
  plus: {
    desc: "Unlock the full rehearsal flow.",
    badge: "Popular",
    features: [
      "Deeper strategy prompts",
      "Longer simulation history",
      "Richer review center",
      "Higher local allowance"
    ]
  },
  pro: {
    desc: "Best fit for enterprise pilots.",
    features: [
      "Full review depth",
      "Priority hardware sync view",
      "Expanded memory retention",
      "Enterprise workspace framing"
    ]
  }
};

function getPlanOrder(planKey) {
  const index = PLAN_ORDER.indexOf(planKey);
  return index === -1 ? PLAN_ORDER.length : index;
}

function buildPlanActionLabel(plan, currentPlanKey) {
  if (plan.planKey === currentPlanKey) return "Current plan";
  return getPlanOrder(plan.planKey) > getPlanOrder(currentPlanKey)
    ? `Upgrade to ${plan.displayName}`
    : `Switch to ${plan.displayName}`;
}

export function mapBillingSummary(summary) {
  return {
    currentPlanKey: summary.account.currentPlanKey,
    creditBalance: summary.account.creditBalance,
    renewalAt: summary.account.renewalAt,
    currencyCode: summary.account.currencyCode,
    currentPlan: {
      planId: summary.currentPlan.planId,
      planKey: summary.currentPlan.planKey,
      displayName: summary.currentPlan.displayName,
      billingCycle: summary.currentPlan.billingCycle,
      currencyCode: summary.currentPlan.currencyCode,
      amountValue: summary.currentPlan.amountValue,
      isCurrent: summary.currentPlan.isCurrent
    },
    allowedTopUpAmounts: [...summary.allowedTopUpAmounts]
  };
}

export function mapBillingPlan(plan, currentPlanKey) {
  const meta = PRICING_CARD_META[plan.planKey] || {
    desc: "Demo billing plan.",
    features: []
  };

  return {
    id: plan.planKey,
    planId: plan.planId,
    planKey: plan.planKey,
    name: plan.displayName,
    price: plan.amountValue,
    desc: meta.desc,
    badge: meta.badge || null,
    features: [...meta.features],
    billingCycle: plan.billingCycle,
    currencyCode: plan.currencyCode,
    isCurrent: plan.planKey === currentPlanKey || Boolean(plan.isCurrent),
    ctaLabel: buildPlanActionLabel(plan, currentPlanKey)
  };
}

export function composePricingCards(apiPlans, currentPlanKey) {
  return [...apiPlans]
    .sort((left, right) => {
      const planOrder = getPlanOrder(left.planKey) - getPlanOrder(right.planKey);
      if (planOrder !== 0) return planOrder;
      return String(left.displayName).localeCompare(String(right.displayName));
    })
    .map((plan) => mapBillingPlan(plan, currentPlanKey));
}

export function applyBillingSummaryToUserSnapshot(state, summary) {
  state.pricingSelection = summary.currentPlanKey;
  state.user.plan = summary.currentPlan.displayName;
  state.user.balance = summary.creditBalance;
  state.user.renewal = summary.renewalAt || null;
}
