export function settingsPage(ctx) {
  const { state, t, initials, joinMeta, translateByGroup, formatBalance, formatDate, METRIC_LABELS, metricLabel } = ctx;
  const renewalLabel = state.user.renewal
    ? new Intl.DateTimeFormat("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric"
      }).format(new Date(state.user.renewal))
    : "No renewal scheduled";

  return `
    <section class="route-page settings-profile-page module-page">
      <div class="settings-profile-header">
        <div class="settings-profile-avatar">${initials(state.user.name)}</div>
        <h1>${state.user.name}</h1>
        <p>${state.user.email}</p>
        <div class="settings-profile-meta">${joinMeta(translateByGroup("role", state.user.role), state.user.company)}</div>
      </div>

      <section class="settings-group">
        <div class="module-toolbar compact">
          <div>
            <small>Account & security</small>
            <strong>Manage identity, password, and sign-in methods</strong>
          </div>
        </div>
        <div class="settings-card-stack">
          <article class="settings-item">
            <div>
              <strong>Account info</strong>
              <p>${joinMeta(state.user.email, state.user.company)}</p>
            </div>
            <span class="settings-item-value">Supabase identity</span>
          </article>
          <article class="settings-item">
            <div>
              <strong>Password</strong>
              <p>Password, session, and email confirmation are managed by Supabase Auth.</p>
            </div>
            <span class="settings-item-value">Managed externally</span>
          </article>
          <article class="settings-item settings-item-language">
            <div>
              <strong>${t().settings.language}</strong>
              <p>Switch the interface language for the whole workspace.</p>
            </div>
            <div class="segmented settings-language-toggle">
              <button class="segment-btn ${state.lang === "en" ? "active" : ""}" data-lang="en">English</button>
              <button class="segment-btn ${state.lang === "zh" ? "active" : ""}" data-lang="zh">English fallback</button>
            </div>
          </article>
          <article class="settings-item">
            <div>
              <strong>Available credits</strong>
              <p>Used for rehearsal time, context uploads, and future pilot expansion.</p>
            </div>
            <div class="settings-item-side"><span class="settings-item-value" data-testid="settings-balance">${formatBalance(state.user.balance)}</span><button class="route-pill" data-route="pricing">${t().nav.pricing}</button></div>
          </article>
          <article class="settings-item">
            <div>
              <strong>Plan & renewal</strong>
              <p data-testid="settings-plan">${translateByGroup("plan", state.user.plan)}</p>
            </div>
            <span class="settings-item-value" data-testid="settings-renewal">${renewalLabel}</span>
          </article>
        </div>
      </section>

      <section class="settings-group">
        <div class="module-toolbar compact">
          <div>
            <small>Workspace preferences</small>
            <strong>Keep the training priorities you use most often</strong>
          </div>
        </div>
        <div class="settings-card-stack">
          <article class="settings-item settings-item-stack">
            <div>
              <strong>${t().settings.focus}</strong>
              <p>The prototype currently trains and records around these language signals.</p>
            </div>
            <div class="settings-signal-tags">${Object.keys(METRIC_LABELS.en).map((key) => `<span class="route-pill">${metricLabel(key)}</span>`).join("")}</div>
          </article>
          <article class="settings-item">
            <div>
              <strong>Security activity</strong>
              <p>The latest Supabase-authenticated access has been synced to this browser.</p>
            </div>
            <span class="settings-item-value" data-testid="settings-security-activity">${formatDate(state.hardware.lastSync)}</span>
          </article>
          <article class="settings-item settings-item-stack">
            <div>
              <strong>${t().settings.dataNote}</strong>
              <p>${t().settings.dataCoverage}</p>
            </div>
          </article>
        </div>
      </section>

      <div class="settings-actions">
        <button class="secondary-btn" data-route="pricing">View pricing</button>
        <button class="ghost-btn" data-logout="1" data-testid="settings-logout">${t().settings.logout}</button>
      </div>
    </section>`;
}
