import { requestJson } from "./api-client.js";

export function fetchAuthSession() {
  return requestJson("/auth/session");
}
