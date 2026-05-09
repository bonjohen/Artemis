/**
 * Artemis Calendar — SPA Router and Page Loader
 * Hash-based routing, nav highlighting.
 */

const routes = {
  '/': () => import('./pages/home.js'),
  '/images': () => import('./pages/images.js'),
  '/candidates': () => import('./pages/candidates.js'),
  '/clusters': () => import('./pages/clusters.js'),
  '/stats': () => import('./pages/stats.js'),
  '/selection': () => import('./pages/selection.js'),
  '/lessons': () => import('./pages/lessons.js'),
  '/blend': () => import('./pages/blend.js'),
};

const app = document.getElementById('app');

async function navigate() {
  const hash = location.hash.slice(1) || '/';
  const path = hash.split('?')[0];

  // Update nav highlighting
  document.querySelectorAll('.site-nav .links a').forEach(a => {
    const href = a.getAttribute('href').slice(1);
    if (path === href || path.startsWith(href + '/')) {
      a.setAttribute('aria-current', 'page');
    } else {
      a.removeAttribute('aria-current');
    }
  });

  const loader = routes[path];
  if (loader) {
    app.innerHTML = '<div class="loading">Loading...</div>';
    try {
      const mod = await loader();
      await mod.render(app, hash);
    } catch (err) {
      app.textContent = `Error loading page: ${err.message}`;
      console.error(err);
    }
  } else {
    // Try sub-routes (e.g., /candidates/method_a)
    const base = '/' + path.split('/')[1];
    const subLoader = routes[base];
    if (subLoader) {
      app.innerHTML = '<div class="loading">Loading...</div>';
      try {
        const mod = await subLoader();
        await mod.render(app, hash);
      } catch (err) {
        app.textContent = `Error loading page: ${err.message}`;
        console.error(err);
      }
    } else {
      app.innerHTML = '<p>Page not found.</p>';
    }
  }
}

window.addEventListener('hashchange', navigate);
window.addEventListener('load', navigate);
