/** Placeholder views for sections not yet wired to data. */

export function comingSoonView(): string {
  return `<div class="coming-soon card">
        <div class="coming-soon-inner">
          <div class="coming-soon-graphic" aria-hidden="true">
            <svg viewBox="0 0 120 100" width="120" height="100" fill="none">
              <rect x="28" y="38" width="64" height="48" rx="6" fill="#E8F5EC" stroke="#1F8A65" stroke-width="2"/>
              <path d="M28 38 L60 18 L92 38" stroke="#1F8A65" stroke-width="2" fill="#F0FAF4"/>
              <text x="48" y="58" fill="#1F8A65" font-size="14" font-weight="700">+</text>
              <text x="68" y="52" fill="#E11D48" font-size="12" font-weight="700">×</text>
              <circle cx="78" cy="62" r="3" fill="#3B82F6"/>
              <circle cx="42" cy="48" r="2.5" fill="#3B82F6"/>
            </svg>
          </div>
          <h2 class="coming-soon-title">Coming soon!</h2>
        </div>
      </div>`;
}

export function viewGamesSticky(): string {
  return comingSoonView();
}

export function viewGamesNew(): string {
  return comingSoonView();
}
