# Lesson 033: Vanilla JS SPA Without a Build Step

## The Lesson

A hash-routed single-page application built with vanilla JavaScript, ES modules, and dynamic `import()` can deliver a functional multi-page experience — navigation, pagination, filtering, modals, live API calls — with zero build toolchain. For internal tools and single-user apps, this eliminates npm, webpack, and framework churn at the cost of some conveniences (no JSX, no reactivity, no component state management). The trade-off is strongly favorable when the app is a thin read layer over an API.

## Context

A data platform needed a web UI for browsing 12,217 images, comparing 5 calendar candidates, exploring 25 clusters, viewing stats, and interactively assembling a custom calendar with live scoring. The existing project had a static HTML lessons viewer built with the same Atlas design system (CSS custom properties), proving that vanilla JS + CSS could produce a polished UI. The question was whether to introduce React/Vue or extend the vanilla approach to a multi-page SPA with API integration.

## What Happened

1. Evaluated React (Create React App or Vite) and Vue. Both would add 50-200MB of `node_modules`, a build step, and a second language ecosystem (npm) to a Python data project. The web app is single-user, local-only, and unlikely to grow complex enough to need component reactivity.
2. Chose vanilla JS with hash routing. The router is 30 lines: listen to `hashchange`, parse the hash path, dynamically `import()` the matching page module, call its `render(el, hash)` function. Sub-routes (e.g., `#/candidates/method_b`) are handled by splitting the hash and delegating to the base route's module.
3. Each page is a self-contained ES module that exports a `render(el, hash)` function. The function builds DOM via `innerHTML` templates + `document.createElement`, attaches event listeners, and calls `fetch()` for API data. No shared state management — each page manages its own data.
4. Created a reusable `image-card.js` component — a function that returns a DOM element. Components are functions, not classes or framework constructs.
5. The SPA shell (`index.html`) is 25 lines: nav links with `href="#/images"`, a `<main id="app">` container, and a `<script type="module" src="app.js">`. No bundling, no transpilation, no source maps.
6. Total JavaScript: ~750 lines across 8 files. Delivered 5 pages with pagination, sorting, filtering, modal overlays, live scoring, and sessionStorage-based page-to-page data passing.

## Key Insights

- **Dynamic `import()` is the module bundler.** ES modules with `import('./pages/images.js')` give you code splitting for free. Each page loads only when navigated to. No webpack chunk configuration needed. All modern browsers support this natively.

- **`innerHTML` is fine for read-only UIs.** The security concern with `innerHTML` is XSS from user-supplied content. When all data comes from your own API serving database values (image IDs, scores, labels), `innerHTML` template literals are safe and dramatically simpler than `createElement` chains. The data is your own — there's no user-generated content injection vector.

- **No reactivity means explicit re-renders.** Without React's virtual DOM or Vue's reactivity, changing state means calling a `loadPage()` function that rebuilds the DOM. For a browse-and-click UI this is fine — the re-render is tied to a user action (click, filter change), not to continuous data streams. If the UI needed real-time updates or complex form state, the calculus would change.

- **`sessionStorage` replaces cross-page state management.** The "Use as starting point" button on the candidates page serializes 13 assignments to `sessionStorage`, and the selection page reads them on load. This is simpler than a shared store (Redux, Vuex) and survives a hash navigation. It breaks on page reload — which is acceptable for an ephemeral "starting point" workflow.

- **The build step you don't have can't break.** No `npm audit` advisories, no webpack version conflicts, no Babel polyfill decisions, no CI step that breaks when Node 22 changes its module resolution. For tools that will be maintained by one person alongside a Python data pipeline, this elimination of a second ecosystem is the primary value.

## Examples

```javascript
// Router: 30 lines, no library
const routes = {
  '/images': () => import('./pages/images.js'),
  '/candidates': () => import('./pages/candidates.js'),
};

async function navigate() {
  const path = location.hash.slice(1) || '/images';
  const loader = routes[path];
  if (loader) {
    const mod = await loader();
    await mod.render(document.getElementById('app'), location.hash);
  }
}
window.addEventListener('hashchange', navigate);

// Page module: self-contained, exports render()
export async function render(el) {
  const data = await fetch('/api/images?page=1').then(r => r.json());
  el.innerHTML = `<div class="image-grid">
    ${data.items.map(img => `<div class="image-card">...</div>`).join('')}
  </div>`;
}

// Component: a function that returns a DOM element
export function createImageCard(image, onClick) {
  const card = document.createElement('div');
  card.className = 'image-card';
  card.innerHTML = `<img src="/thumbs/${image.source_image_id}.jpg" loading="lazy">`;
  card.addEventListener('click', () => onClick(image));
  return card;
}
```

## Applicability

This approach works well for: internal tools, single-user apps, read-heavy UIs with simple interactions, projects where adding npm is disproportionate to the frontend complexity, and teams where the developers are primarily backend/data engineers.

It does NOT work well for: apps with complex form interactions, real-time collaborative UIs, apps needing accessibility beyond basic HTML semantics, apps with hundreds of components, or teams with dedicated frontend engineers who already have a framework workflow.

## Related Lessons

- [Design System Portability via Tokens](035_design_system_portability_via_tokens.md) — the CSS token system that makes vanilla JS apps look polished without a component library
