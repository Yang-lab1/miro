export function authModal(ctx) {
  const { state, t } = ctx;
  const isRegister = state.authMode === "register";
  const heading = isRegister ? "Create your Miro account" : "Log in to Miro";
  const intro =
    "Use Supabase email authentication to unlock live rehearsal, synced reviews, and workspace history.";
  const helper = isRegister
    ? "Register sends a confirmation email if your Supabase project requires email verification."
    : "Use the email and password from your Supabase account.";
  const submitLabel = isRegister ? t().auth.register : t().auth.login;

  return `
    <div class="modal-backdrop ${state.authOpen ? "open" : ""}">
      <div class="auth-modal" role="dialog" aria-modal="true" aria-label="${heading}">
        <button class="auth-close" type="button" id="closeAuthBtn" aria-label="Close dialog">&times;</button>
        <div class="auth-head">
          <h2>${heading}</h2>
          <p>${intro}</p>
        </div>
        <div class="auth-tabs">
          <button class="segment-btn ${state.authMode === "login" ? "active" : ""}" data-auth-switch="login">${t().auth.login}</button>
          <button class="segment-btn ${state.authMode === "register" ? "active" : ""}" data-auth-switch="register">${t().auth.register}</button>
        </div>
        <form class="auth-form" id="authForm">
          <label class="auth-row">
            <span>${t().auth.email}</span>
            <input id="authEmail" type="email" placeholder="name@company.com" autocomplete="email" />
          </label>
          <label class="auth-row">
            <span>${t().auth.password}</span>
            <input id="authPassword" type="password" placeholder="Password" autocomplete="${isRegister ? "new-password" : "current-password"}" />
          </label>
          <div class="auth-actions-row">
            <small class="helper-inline">${helper}</small>
            <button type="submit" class="primary-btn auth-submit">${submitLabel}</button>
          </div>
        </form>
      </div>
    </div>`;
}
