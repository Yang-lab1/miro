import { API_BASE, requestJsonFromBase } from "./api-client.js";

export const REVIEW_API_BASE =
  globalThis.MIRO_REVIEW_API_BASE || API_BASE;

export function fetchReviews() {
  return requestJsonFromBase(REVIEW_API_BASE, "/reviews");
}

export function fetchReviewDetail(reviewId) {
  return requestJsonFromBase(REVIEW_API_BASE, `/reviews/${reviewId}`);
}
