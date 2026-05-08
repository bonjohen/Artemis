# Lesson 035: Design System Portability via Tokens

## The Lesson

A design system built on CSS custom properties (design tokens) can be shared across completely independent frontends — static HTML pages, vanilla JS SPAs, embedded widgets — by copying two files. The tokens provide visual consistency without requiring a shared component library, a build system, or a framework. When the tokens cover color, typography, spacing, and responsive behavior, a new frontend gets a polished look for free.

## Context

A data platform had a static lessons-learned viewer (`docs/lessons/lessons.html`) built with an "Atlas" design system: `tokens.css` (CSS custom properties for colors, fonts, spacing, radii, shadows, transitions) and `system.css` (base typography, layout primitives, navigation bar). The viewer had dark mode, a serif+sans+mono font stack, and a distinctive warm-paper-on-dark aesthetic. A new FastAPI web app needed to look like it belonged to the same project without rebuilding the design system or introducing a component library like Material UI.

## What Happened

1. The Atlas design system was already split into two files by design: `tokens.css` defines ~50 custom properties (colors, font stacks, font sizes, spacing scale, border radii, shadows, transition timings); `system.css` applies them to base elements (`html`, `body`, `a`, `.shell`, `.site-nav`, `.brand`).
2. Copied both files from `docs/lessons/system/` into `src/artemis_calendar/web/static/css/`. No modifications needed — the token values work in any HTML context.
3. Created `app.css` for the web app's own components (image grid, cards, modal, scorecard, pagination). Every color reference uses a token (`var(--atlas-accent)`, `var(--atlas-paper-2)`), every spacing uses the scale (`var(--s-3)`, `var(--s-5)`), every font uses a stack variable (`var(--mono)`, `var(--serif)`).
4. Dark mode worked automatically. `tokens.css` defines a `[data-theme="dark"]` selector and a `@media (prefers-color-scheme: dark)` fallback that override every color token. Since `app.css` only references tokens (never hard-coded colors), dark mode applied to all new components with zero additional CSS.
5. The nav bar (`.site-nav`, `.brand`, `.links`) was reused directly from `system.css`. The web app's navigation looks identical to the lessons viewer.

## Key Insights

- **Tokens are the portability layer, not components.** A React component library can't be reused in a vanilla JS app. CSS custom properties can. The tokens carry the design decisions (this shade of blue, this spacing scale, this font pairing) without carrying implementation decisions (React vs. Vue vs. vanilla).

- **Dark mode is a token-level concern.** When every color is a custom property and the dark theme overrides those properties, dark mode is free for all consumers. Any new CSS that references `var(--atlas-ink)` instead of `#1A1D24` automatically responds to theme changes. The moment you hard-code a hex color, you break dark mode for that element.

- **Two files is the right granularity.** Splitting tokens (values) from system (base styles) means a consumer can take just the tokens if they want to apply their own base styles, or both if they want the full look. A monolithic `styles.css` would force all-or-nothing adoption.

- **The font stack import belongs in system.css, not tokens.css.** Google Fonts `@import` is a side effect (network request). Keeping it in `system.css` means a consumer that only wants token values for programmatic use (e.g., a chart library reading CSS variables) doesn't trigger a font download.

- **Copy, don't symlink or package.** For a single-project design system used by 2-3 frontends, copying the files is simpler than creating an npm package or managing symlinks across platforms. The files change rarely (design tokens stabilize early), so drift risk is low. If the system grew to 10+ consumers, packaging would be worth the overhead.

## Examples

```css
/* tokens.css — portable values, no side effects */
:root {
  --atlas-ink: #1A1D24;
  --atlas-paper: #F6F4EF;
  --atlas-accent: #2F5DA8;
  --s-3: 12px;
  --r-md: 10px;
  --mono: 'JetBrains Mono', ui-monospace, monospace;
}
[data-theme="dark"] {
  --atlas-ink: #F2EEE3;
  --atlas-paper: #0F1014;
  --atlas-accent: #6FA0E8;
}

/* app.css — new components use tokens, never hard-coded values */
.image-card {
  background: var(--atlas-paper-2);
  border-radius: var(--r-md);
  box-shadow: var(--shadow-1);
}
.score-badge {
  font-family: var(--mono);
  font-size: var(--fs-meta);
}
```

## Applicability

This pattern works for: project-internal tools sharing a visual identity, small teams where the design system author and consumers are the same people, and frontends that don't use a component framework's built-in theming (e.g., Material UI's `ThemeProvider`).

It does NOT work for: design systems that need to ship components with behavior (dropdown, modal, date picker) — those require a framework-specific component library. It also breaks down at scale: 20+ consumers of a design system need versioning, changelogs, and a package registry, not file copies.

## Related Lessons

- [Vanilla JS SPA Without a Build Step](033_vanilla_js_spa_no_build_step.md) — the frontend architecture that consumes the design tokens without a framework or build system
