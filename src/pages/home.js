export function homePage(ctx) {
  const { state, t, pick, joinMeta, translateByGroup, getCountry, issueText, TESTIMONIALS, METRIC_LABELS, metricLabel } = ctx;
  const totalRepeats = state.userTwin.reduce((sum, item) => sum + item.count, 0);
  const featuredMemory = [...state.userTwin].sort((a, b) => b.count - a.count).slice(0, 3);
  const featuredQuote = TESTIMONIALS[0];
  const secondaryQuotes = TESTIMONIALS.slice(1, 4);

  return `
    <section class="route-page home-editorial-page">
      <section class="home-editorial-hero">
        <div class="home-editorial-copy">
          <span class="home-overline">${t().home.eyebrow}</span>
          <h1 class="home-editorial-title is-en">The future of<br />cross-border trust,<br />powered by<br /><span>Miro.</span></h1>
          <p class="home-editorial-subtitle">${t().home.subtitle}</p>
          <div class="home-editorial-actions">
            <button class="primary-btn" data-start-live="1">${t().home.primary}</button>
            <button class="secondary-btn" data-open-review="home">${t().home.secondary}</button>
          </div>
        </div>
        <aside class="module-panel home-editorial-aside">
          <small class="home-aside-label">About</small>
          <p>Miro is not a generic translation demo. It helps teams rehearse wording, pauses, politeness, and deal pacing before the real client conversation starts.</p>
          <div class="home-aside-person">
            <span class="quote-avatar">${featuredQuote.initials}</span>
            <div>
              <strong>${featuredQuote.name}</strong>
              <div class="testimonial-company">${joinMeta(featuredQuote.company, featuredQuote.role)}</div>
            </div>
          </div>
          <p class="home-aside-quote">${pick(featuredQuote.quote)}</p>
          <button class="ghost-btn home-watch-btn" data-open-review="home">Open review trail</button>
        </aside>
      </section>

      <section class="home-number-band">
        <small class="home-number-label">Miro in numbers</small>
        <div class="home-number-display"><span data-testid="home-captured-sessions">${state.hardware.capturedSessions}</span><span>+</span></div>
        <div class="home-number-caption">captured sessions</div>
        <div class="home-number-meta">
          <article>
            <small>${t().home.metric1}</small>
            <strong>${state.user.cqScore}</strong>
            <span>${translateByGroup("role", state.user.role)}</span>
          </article>
          <article>
            <small>${t().home.metric2}</small>
            <strong>${Object.keys(METRIC_LABELS.en).length}</strong>
            <span>${Object.keys(METRIC_LABELS.en).map((key) => metricLabel(key)).join(" / ")}</span>
          </article>
          <article>
            <small>${t().home.metric3}</small>
            <strong>${totalRepeats}</strong>
            <span>User Twin keeps tracking repeats</span>
          </article>
        </div>
      </section>

      <section class="home-content-grid">
        <section class="module-panel home-memory-column">
          <div class="module-toolbar compact">
            <div>
              <small>${t().home.twinTitle}</small>
              <strong>Resolve these repeated issues before the next meeting</strong>
            </div>
            <button class="route-pill" data-route="review" data-protected="true">${t().nav.review}</button>
          </div>
          <div class="home-memory-list">
            ${featuredMemory.map((item) => `
              <article class="home-memory-item">
                <div class="home-memory-top">
                  <span class="pain-tag">${issueText(item.issueKey).short}</span>
                  <strong>${item.count}x</strong>
                </div>
                <h3>${issueText(item.issueKey).title}</h3>
                <p>${pick(item.coach)}</p>
                <span>${joinMeta(pick(getCountry(item.country).label), pick(item.lastContext))}</span>
              </article>`).join("")}
          </div>
        </section>

        <section class="module-panel home-proof-column">
          <div class="module-toolbar compact">
            <div>
              <small>${t().home.voicesTitle}</small>
              <strong>From rehearsal to real meetings, review stays on the same line</strong>
            </div>
          </div>
          <div class="home-proof-list">
            ${secondaryQuotes.map((item) => `
              <article class="home-proof-item">
                <div class="home-proof-head">
                  <strong>${item.name}</strong>
                  <span>${joinMeta(item.company, item.role)}</span>
                </div>
                <p>${pick(item.quote)}</p>
              </article>`).join("")}
          </div>
          <div class="home-proof-note">
            <small>${t().home.footerHeadline}</small>
            <p>${t().home.footerCopy}</p>
          </div>
        </section>
      </section>

      <section class="home-footer-note">
        <p>The landing page stays editorial, but it still keeps the product skeleton close enough to jump straight into simulation, devices, and review.</p>
        <div class="footer-links">
          <button data-route="live" data-protected="true">${t().home.footerLink1}</button>
          <button data-route="hardware" data-protected="true">${t().home.footerLink2}</button>
          <button data-route="review" data-protected="true">${t().home.footerLink3}</button>
        </div>
      </section>
    </section>`;
}
