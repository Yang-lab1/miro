
import { miroBrandMark } from "./brand-mark.js";

export function navTemplate(ctx) {
  const { state, t, initials } = ctx;
  const routes = [
    { key: "home", protected: false },
    { key: "live", protected: true },
    { key: "hardware", protected: true },
    { key: "review", protected: true },
    { key: "pricing", protected: true },
    { key: "settings", protected: true }
  ];
  const authArea = state.loggedIn
    ? `<div class="account-actions compact"><div class="account-pill minimal" aria-label="${state.user.name}"><span class="account-avatar">${initials(state.user.name)}</span></div><button type="button" class="account-link minimal" data-logout="1">${t().settings.logout}</button></div>`
    : `<div class="auth-actions compact"><button type="button" class="auth-link minimal" data-auth="register">${t().auth.register}</button><button type="button" class="primary-btn nav-cta" data-auth="login">${t().auth.login}</button></div>`;
  return `
    <div class="topbar-wrap">
      <header class="topbar editorial-nav liquid-glass">
        <button
          type="button"
          class="brand brand-icon-only"
          data-route="home"
          aria-label="Miro home"
          title="Miro"
        >
          <span class="brand-mark brand-mark-logo">
            ${miroBrandMark({ className: "brand-mark-art", idPrefix: "nav-logo", title: "Miro" })}
          </span>
        </button>
        <nav class="nav-links editorial-links" aria-label="Primary">
          ${routes.map((item) => `<button type="button" class="nav-link ${state.activeRoute === item.key ? "active" : ""}" data-route="${item.key}" data-protected="${item.protected}" aria-current="${state.activeRoute === item.key ? "page" : "false"}">${t().nav[item.key]}</button>`).join("")}
        </nav>
        <div class="nav-side">${authArea}</div>
      </header>
    </div>`;
}

