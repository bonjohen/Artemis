/**
 * Image browser page — paginated grid with sort, filter, detail overlay,
 * and cluster spotlight view.
 */

import { createImageCard } from '../components/image-card.js';

let currentPage = 1;
let currentSort = 'score';
let currentCluster = '';
let currentMinScore = '';
let viewMode = 'browse'; // 'browse' or 'spotlights'

async function fetchImages(page, sort, clusterId, minScore) {
  const params = new URLSearchParams({ page, per_page: 60, sort });
  if (clusterId) params.set('cluster_id', clusterId);
  if (minScore) params.set('min_score', minScore);
  const r = await fetch(`/api/images?${params}`);
  return r.json();
}

async function fetchDetail(sk) {
  const r = await fetch(`/api/images/${sk}`);
  return r.json();
}

function showDetail(container, image) {
  fetchDetail(image.image_sk).then(detail => {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.addEventListener('click', e => {
      if (e.target === overlay) overlay.remove();
    });

    const scoreRows = [
      ['Preference', detail.preference_score],
      ['Elo', detail.elo_score],
      ['Borda', detail.borda_score],
      ['Broad Appeal', detail.broad_appeal_score],
      ['Uncertainty', detail.uncertainty_score],
      ['Brightness', detail.brightness_score],
      ['Contrast', detail.contrast_score],
      ['Saturation', detail.saturation_score],
    ].filter(([, v]) => v != null)
      .map(([k, v]) => `<tr><td>${k}</td><td>${v.toFixed(4)}</td></tr>`)
      .join('');

    const candidateList = detail.candidates.length
      ? detail.candidates.map(c =>
          `<a href="#/candidates/${c}">${c}</a>`
        ).join(', ')
      : 'None';

    overlay.innerHTML = `
      <div class="modal-content">
        <button class="modal-close" aria-label="Close">&times;</button>
        <div class="detail-grid">
          <div>
            <img src="/thumbs/${detail.source_image_id}.jpg"
                 alt="Image ${detail.image_sk}">
          </div>
          <div>
            <h2 style="font-family:var(--mono);font-size:var(--fs-body);margin:0 0 var(--s-2)">
              #${detail.rank || '—'} &middot; ${detail.source_image_id}
            </h2>
            ${detail.cluster_id != null
              ? `<span class="cluster-pill">Cluster ${detail.cluster_id}</span>`
              : ''}
            <table class="score-table" style="margin-top:var(--s-3)">
              <thead><tr><th>Metric</th><th>Value</th></tr></thead>
              <tbody>${scoreRows}</tbody>
            </table>
            <p style="margin-top:var(--s-3);font-size:var(--fs-small);color:var(--atlas-muted)">
              Candidates: ${candidateList}
            </p>
          </div>
        </div>
      </div>
    `;

    overlay.querySelector('.modal-close').addEventListener('click', () => overlay.remove());
    document.addEventListener('keydown', function handler(e) {
      if (e.key === 'Escape') {
        overlay.remove();
        document.removeEventListener('keydown', handler);
      }
    });

    document.body.appendChild(overlay);
  });
}

async function loadPage(container) {
  const data = await fetchImages(currentPage, currentSort, currentCluster, currentMinScore);

  const grid = container.querySelector('.image-grid');
  grid.innerHTML = '';
  data.items.forEach(img => {
    grid.appendChild(createImageCard(img, () => showDetail(container, img)));
  });

  const pageInfo = container.querySelector('.page-info');
  pageInfo.textContent = `Page ${data.page} of ${data.pages} (${data.total} images)`;

  const prevBtn = container.querySelector('.prev-btn');
  const nextBtn = container.querySelector('.next-btn');
  prevBtn.disabled = data.page <= 1;
  nextBtn.disabled = data.page >= data.pages;
}

async function loadSpotlights(container) {
  const area = container.querySelector('.spotlights-area');
  area.innerHTML = '<div class="loading">Loading cluster spotlights...</div>';

  const r = await fetch('/api/clusters/spotlights?diverse_count=5');
  const spotlights = await r.json();

  area.innerHTML = '';

  for (const spot of spotlights) {
    const section = document.createElement('div');
    section.className = 'spotlight-cluster';

    const rep = spot.representative;
    const label = spot.cluster_label || `Cluster ${spot.cluster_id}`;

    section.innerHTML = `
      <div class="spotlight-header">
        <h3 class="spotlight-title">
          <span class="spotlight-id">C${spot.cluster_id}</span>
          ${label}
          <span class="spotlight-count">${spot.image_count} images</span>
        </h3>
        <button class="btn spotlight-browse-btn" data-cluster="${spot.cluster_id}">Browse all</button>
      </div>
      <div class="spotlight-images">
        <div class="spotlight-rep" title="Representative (closest to centroid)">
          <img src="/thumbs/${rep.source_image_id}.jpg" alt="Representative"
               loading="lazy" data-sk="${rep.image_sk}">
          <div class="spotlight-badge">REP</div>
          <div class="spotlight-img-score">${rep.preference_score?.toFixed(2) ?? ''}</div>
        </div>
        ${spot.diverse.map((img, i) => `
          <div class="spotlight-div" title="Diverse sample ${i + 1}">
            <img src="/thumbs/${img.source_image_id}.jpg" alt="Diverse ${i + 1}"
                 loading="lazy" data-sk="${img.image_sk}">
            <div class="spotlight-img-score">${img.preference_score?.toFixed(2) ?? ''}</div>
          </div>
        `).join('')}
      </div>
    `;

    // Click image to show detail
    section.querySelectorAll('img[data-sk]').forEach(img => {
      img.style.cursor = 'pointer';
      img.addEventListener('click', () => {
        showDetail(container, { image_sk: parseInt(img.dataset.sk) });
      });
    });

    // Browse all button
    section.querySelector('.spotlight-browse-btn').addEventListener('click', () => {
      viewMode = 'browse';
      currentCluster = spot.cluster_id.toString();
      currentPage = 1;
      renderPage(container);
    });

    area.appendChild(section);
  }
}

function renderPage(container) {
  const browseArea = container.querySelector('.browse-area');
  const spotlightsArea = container.querySelector('.spotlights-area');
  const browseBtn = container.querySelector('.view-browse');
  const spotBtn = container.querySelector('.view-spotlights');

  if (viewMode === 'spotlights') {
    browseArea.style.display = 'none';
    spotlightsArea.style.display = '';
    browseBtn.classList.remove('active');
    spotBtn.classList.add('active');
    loadSpotlights(container);
  } else {
    browseArea.style.display = '';
    spotlightsArea.style.display = 'none';
    browseBtn.classList.add('active');
    spotBtn.classList.remove('active');
    container.querySelector('.cluster-input').value = currentCluster;
    loadPage(container);
  }
}

export async function render(el) {
  el.innerHTML = `
    <div class="dedup-banner" style="display:none"></div>
    <div class="page-header">
      <h1>Images</h1>
      <div class="controls">
        <div class="view-toggle">
          <button class="filter-btn view-browse active">Browse</button>
          <button class="filter-btn view-spotlights">Spotlights</button>
        </div>
        <label>Sort
          <select class="sort-select">
            <option value="score">Score</option>
            <option value="brightness">Brightness</option>
            <option value="cluster">Cluster</option>
          </select>
        </label>
        <label>Cluster
          <input type="number" class="cluster-input" placeholder="All" min="0" max="24"
                 style="width:60px">
        </label>
        <label>Min Score
          <input type="number" class="score-input" placeholder="0" step="0.05" min="0" max="1"
                 style="width:70px">
        </label>
      </div>
    </div>
    <div class="browse-area">
      <div class="image-grid"></div>
      <div class="pagination">
        <button class="prev-btn">Prev</button>
        <span class="page-info"></span>
        <button class="next-btn">Next</button>
      </div>
    </div>
    <div class="spotlights-area" style="display:none"></div>
  `;

  // Load dedup banner
  _loadDedupBanner(el);

  // Restore state
  el.querySelector('.sort-select').value = currentSort;
  if (currentCluster) el.querySelector('.cluster-input').value = currentCluster;
  if (currentMinScore) el.querySelector('.score-input').value = currentMinScore;

  // View toggle
  el.querySelector('.view-browse').addEventListener('click', () => {
    viewMode = 'browse';
    renderPage(el);
  });
  el.querySelector('.view-spotlights').addEventListener('click', () => {
    viewMode = 'spotlights';
    renderPage(el);
  });

  // Filter handlers
  el.querySelector('.sort-select').addEventListener('change', e => {
    currentSort = e.target.value;
    currentPage = 1;
    if (viewMode === 'browse') loadPage(el);
  });

  el.querySelector('.cluster-input').addEventListener('change', e => {
    currentCluster = e.target.value;
    currentPage = 1;
    if (viewMode === 'browse') loadPage(el);
  });

  el.querySelector('.score-input').addEventListener('change', e => {
    currentMinScore = e.target.value;
    currentPage = 1;
    if (viewMode === 'browse') loadPage(el);
  });

  el.querySelector('.prev-btn').addEventListener('click', () => {
    if (currentPage > 1) { currentPage--; loadPage(el); }
  });

  el.querySelector('.next-btn').addEventListener('click', () => {
    currentPage++;
    loadPage(el);
  });

  renderPage(el);
}

async function _loadDedupBanner(el) {
  try {
    const r = await fetch('/api/dedup/summary');
    const d = await r.json();
    if (d.suppressed > 0) {
      const pct = ((d.suppressed / d.total) * 100).toFixed(0);
      const banner = el.querySelector('.dedup-banner');
      banner.style.display = '';
      banner.innerHTML = `
        <div class="dedup-banner-inner">
          <strong>${d.active.toLocaleString()}</strong> unique images shown.
          <strong>${d.suppressed.toLocaleString()}</strong> near-duplicates
          (${pct}% of ${d.total.toLocaleString()}) removed by deduplication
          at ${d.threshold} cosine similarity threshold
          across ${d.groups.toLocaleString()} duplicate groups.
        </div>
      `;
    }
  } catch { /* dedup not available */ }
}
