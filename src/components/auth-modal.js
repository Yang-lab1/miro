import { miroBrandMark } from "./brand-mark.js";

function googleMark() {
  return `
    <svg class="auth-social-mark google-mark" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path fill="#4285F4" d="M23.49 12.27c0-.79-.07-1.55-.2-2.27H12v4.3h6.46a5.52 5.52 0 0 1-2.4 3.62v3h3.88c2.27-2.09 3.55-5.18 3.55-8.65Z"/>
      <path fill="#34A853" d="M12 24c3.24 0 5.95-1.07 7.93-2.91l-3.88-3c-1.07.72-2.44 1.15-4.05 1.15-3.11 0-5.75-2.1-6.69-4.92H1.3v3.1A12 12 0 0 0 12 24Z"/>
      <path fill="#FBBC04" d="M5.31 14.32A7.2 7.2 0 0 1 4.94 12c0-.8.14-1.57.37-2.32v-3.1H1.3A12 12 0 0 0 0 12c0 1.93.46 3.76 1.3 5.42l4.01-3.1Z"/>
      <path fill="#EA4335" d="M12 4.77c1.76 0 3.33.61 4.57 1.8l3.43-3.43C17.95 1.16 15.24 0 12 0A12 12 0 0 0 1.3 6.58l4.01 3.1C6.25 6.86 8.89 4.77 12 4.77Z"/>
    </svg>`;
}

export function authModal(ctx) {
  const { state, t } = ctx;
  const isRegister = state.authMode === "register";
  const heading = isRegister ? t().auth.registerHeading : t().auth.loginHeading;
  const intro = isRegister ? t().auth.registerIntro : t().auth.loginIntro;
  const switchCopy = isRegister ? t().auth.switchToLogin : t().auth.switchToRegister;
  const switchLabel = isRegister ? t().auth.login : t().auth.register;
  const submitLabel = isRegister ? t().auth.emailRegister : t().auth.emailLogin;
  const emailDisabled = Boolean(state.turnstile?.emailDisabled);
  const authPending = Boolean(state.authPending);
  const captchaState = state.turnstile?.uiState || "idle";
  const captchaMessage = state.turnstile?.message || t().auth.turnstileIdle;
  const authFeedback = state.authFeedback?.message || "";
  const turnstileAvailable =
    captchaState !== "unavailable" && captchaState !== "bypassed";

  return `
    <div class="modal-backdrop ${state.authOpen ? "open" : ""}">
      <div class="auth-modal" role="dialog" aria-modal="true" aria-label="${heading}">
        <button class="auth-close" type="button" id="closeAuthBtn" aria-label="Close dialog">&times;</button>
        <div class="auth-brand">
          <span class="auth-brand-logo">
            ${miroBrandMark({ className: "auth-brand-art", idPrefix: "auth-logo", title: "Miro" })}
          </span>
        </div>
        <div class="auth-head">
          <h2>${heading}</h2>
          <p>${intro}</p>
        </div>
        <div class="auth-socials">
          <button type="button" class="auth-social auth-social-google" data-auth-oauth="google">
            ${googleMark()}
            <span>${t().auth.google}</span>
          </button>
        </div>
        <div class="auth-divider"><span>${t().auth.emailDivider}</span></div>
        <form class="auth-form" id="authForm">
          <label class="auth-row">
            <span>${t().auth.email}</span>
            <input
              id="authEmail"
              type="email"
              name="email"
              placeholder="you@company.com"
              autocomplete="email"
              required
            />
          </label>
          <label class="auth-row">
            <span>${t().auth.password}</span>
            <input
              id="authPassword"
              type="password"
              name="password"
              placeholder="********"
              autocomplete="${isRegister ? "new-password" : "current-password"}"
              required
            />
          </label>
          <div class="auth-captcha-shell" data-turnstile-state="${captchaState}">
            <div class="auth-captcha-meta">
              <span class="auth-captcha-indicator" aria-hidden="true"></span>
              <div class="auth-captcha-copy">
                <strong>${t().auth.turnstileTitle}</strong>
                <small id="authCaptchaState" data-turnstile-message>${captchaMessage}</small>
              </div>
              <span class="auth-captcha-brand">Turnstile</span>
            </div>
            <div
              id="authTurnstile"
              class="auth-turnstile"
              data-turnstile
              data-turnstile-available="${turnstileAvailable ? "true" : "false"}"
              aria-live="polite"
            ></div>
          </div>
          <p
            class="auth-feedback"
            id="authFeedback"
            data-auth-feedback
            data-tone="${state.authFeedback?.tone || "error"}"
            ${authFeedback ? "" : "hidden"}
          >
            ${authFeedback}
          </p>
          <button
            type="submit"
            class="primary-btn auth-submit"
            data-auth-email-submit
            ${emailDisabled || authPending ? "disabled" : ""}
          >
            ${authPending ? t().auth.emailWorking : submitLabel}
          </button>
        </form>
        <div class="auth-actions-row">
          <button type="button" class="auth-link minimal auth-switch-link" data-auth-switch="${isRegister ? "login" : "register"}">
            ${switchCopy} ${switchLabel}
          </button>
        </div>
      </div>
    </div>`;
}
