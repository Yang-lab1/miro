export function miroBrandMark({
  className = "",
  idPrefix = "miro-brand",
  title = "Miro"
} = {}) {
  const rootClass = className ? `brand-mark-svg ${className}` : "brand-mark-svg";
  const deepGradientId = `${idPrefix}-deep-gradient`;
  const coreGradientId = `${idPrefix}-core-gradient`;
  const lightGradientId = `${idPrefix}-light-gradient`;
  const glazeGradientId = `${idPrefix}-glaze-gradient`;
  const strokeGradientId = `${idPrefix}-stroke-gradient`;

  return `
    <svg
      class="${rootClass}"
      viewBox="0 0 96 88"
      role="img"
      aria-label="${title}"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="${deepGradientId}" x1="12" y1="18" x2="34" y2="68" gradientUnits="userSpaceOnUse">
          <stop offset="0" stop-color="#113f82"/>
          <stop offset="0.48" stop-color="#1e5ca7"/>
          <stop offset="1" stop-color="#68d0f3"/>
        </linearGradient>
        <linearGradient id="${coreGradientId}" x1="48" y1="10" x2="48" y2="78" gradientUnits="userSpaceOnUse">
          <stop offset="0" stop-color="#96ebff"/>
          <stop offset="0.44" stop-color="#4bc8f4"/>
          <stop offset="1" stop-color="#1b71c8"/>
        </linearGradient>
        <linearGradient id="${lightGradientId}" x1="62" y1="12" x2="88" y2="76" gradientUnits="userSpaceOnUse">
          <stop offset="0" stop-color="#edfaff"/>
          <stop offset="0.55" stop-color="#91ddf5"/>
          <stop offset="1" stop-color="#4caedb"/>
        </linearGradient>
        <linearGradient id="${glazeGradientId}" x1="22" y1="8" x2="76" y2="68" gradientUnits="userSpaceOnUse">
          <stop offset="0" stop-color="rgba(255,255,255,0.95)"/>
          <stop offset="0.5" stop-color="rgba(255,255,255,0.22)"/>
          <stop offset="1" stop-color="rgba(255,255,255,0.05)"/>
        </linearGradient>
        <linearGradient id="${strokeGradientId}" x1="20" y1="12" x2="80" y2="80" gradientUnits="userSpaceOnUse">
          <stop offset="0" stop-color="rgba(255,255,255,0.8)"/>
          <stop offset="0.5" stop-color="rgba(90,178,255,0.5)"/>
          <stop offset="1" stop-color="rgba(9,71,146,0.55)"/>
        </linearGradient>
      </defs>
      <g fill="none" fill-rule="evenodd">
        <path
          d="M13 16.5c0-3.59 4.32-5.38 6.85-2.84l13.14 13.14a11.4 11.4 0 0 1 3.34 8.06v29.88a6.5 6.5 0 0 1-11.09 4.6L16.1 60.2A10.6 10.6 0 0 1 13 52.7V16.5Z"
          fill="url(#${deepGradientId})"
        />
        <path
          d="M36.15 30.3c2.7-8.5 8.95-17.14 19.16-17.14 10.31 0 16.06 9.2 19.4 17.56l7.16 17.95c1.76 4.42-1.48 9.24-6.24 9.24H61.5a7 7 0 0 1-5.37-2.5l-8.04-9.55-8.15 9.59a7 7 0 0 1-5.33 2.46H20.13c-4.83 0-8.07-4.95-6.15-9.37L36.15 30.3Z"
          fill="url(#${coreGradientId})"
        />
        <path
          d="M77.85 16.02c2.46-2.5 6.74-.74 6.74 2.77v34.2c0 2.82-1.12 5.52-3.12 7.52l-9.3 9.3a6.5 6.5 0 0 1-11.1-4.6V35.07c0-3.01 1.2-5.9 3.34-8.03l13.44-13.02Z"
          fill="url(#${lightGradientId})"
        />
        <path
          d="M18.6 17.66c6.8 3.35 11.3 8.29 18.4 17.83 4.32 5.81 8.4 12.94 18.55 13.63 7.17.48 14.4-2.3 21.82-9.58"
          stroke="url(#${glazeGradientId})"
          stroke-width="6.2"
          stroke-linecap="round"
          opacity="0.82"
        />
        <path
          d="M21.3 22.72c7.65 4.07 12.89 12.53 18.91 19.1 3.94 4.3 7.83 8.18 14.37 8.18 6.92 0 12.6-4.6 20.67-13.63"
          stroke="rgba(255,255,255,0.44)"
          stroke-width="2.5"
          stroke-linecap="round"
          opacity="0.8"
        />
        <path
          d="M13 16.5c0-3.59 4.32-5.38 6.85-2.84l13.14 13.14a11.4 11.4 0 0 1 3.34 8.06v29.88a6.5 6.5 0 0 1-11.09 4.6L16.1 60.2A10.6 10.6 0 0 1 13 52.7V16.5Zm23.15 13.8c2.7-8.5 8.95-17.14 19.16-17.14 10.31 0 16.06 9.2 19.4 17.56l7.16 17.95c1.76 4.42-1.48 9.24-6.24 9.24H61.5a7 7 0 0 1-5.37-2.5l-8.04-9.55-8.15 9.59a7 7 0 0 1-5.33 2.46H20.13c-4.83 0-8.07-4.95-6.15-9.37L36.15 30.3Zm41.7-14.28c2.46-2.5 6.74-.74 6.74 2.77v34.2c0 2.82-1.12 5.52-3.12 7.52l-9.3 9.3a6.5 6.5 0 0 1-11.1-4.6V35.07c0-3.01 1.2-5.9 3.34-8.03l13.44-13.02Z"
          stroke="url(#${strokeGradientId})"
          stroke-width="1.4"
          opacity="0.72"
        />
      </g>
    </svg>
  `;
}
