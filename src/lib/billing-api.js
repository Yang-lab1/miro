import { requestJson } from "./api-client.js";

export function fetchBillingPlans() {
  return requestJson("/billing/plans");
}

export function fetchBillingSummary() {
  return requestJson("/billing/summary");
}

export function selectBillingPlan(planKey) {
  return requestJson("/billing/select-plan", {
    method: "POST",
    body: { planKey }
  });
}

export function topUpBillingCredits(amount) {
  return requestJson("/billing/top-up", {
    method: "POST",
    body: { amount }
  });
}
