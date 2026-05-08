/**
 * Image browser page — paginated grid with sort, filter, and detail overlay.
 */

import { createImageCard } from '../components/image-card.js';

let currentPage = 1;
let currentSort = 'score';
let currentCluster = '';
let currentMinScore = '';

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
            <img src="https://pub-1f1ce68455c0432ea65ac3155a6b2409.r2.dev/thumbs/${detail.source_image_id}.jpg"
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

  // Build grid
  const grid = container.querySelector('.image-grid');
  grid.innerHTML = '';
  data.items.forEach(img => {
    grid.appendChild(createImageCard(img, () => showDetail(container, img)));
  });

  // Update pagination
  const pageInfo = container.querySelector('.page-info');
  pageInfo.textContent = `Page ${data.page} of ${data.pages} (${data.total} images)`;

  const prevBtn = container.querySelector('.prev-btn');
  const nextBtn = container.querySelector('.next-btn');
  prevBtn.disabled = data.page <= 1;
  nextBtn.disabled = data.page >= data.pages;
}

export async function render(el) {
  el.innerHTML = `
    <div class="page-header">
      <h1>Images</h1>
      <div class="controls">
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
    <div class="image-grid"></div>
    <div class="pagination">
      <button class="prev-btn">Prev</button>
      <span class="page-info"></span>
      <button class="next-btn">Next</button>
    </div>
  `;

  // Restore state
  el.querySelector('.sort-select').value = currentSort;
  if (currentCluster) el.querySelector('.cluster-input').value = currentCluster;
  if (currentMinScore) el.querySelector('.score-input').value = currentMinScore;

  // Event handlers
  el.querySelector('.sort-select').addEventListener('change', e => {
    currentSort = e.target.value;
    currentPage = 1;
    loadPage(el);
  });

  el.querySelector('.cluster-input').addEventListener('change', e => {
    currentCluster = e.target.value;
    currentPage = 1;
    loadPage(el);
  });

  el.querySelector('.score-input').addEventListener('change', e => {
    currentMinScore = e.target.value;
    currentPage = 1;
    loadPage(el);
  });

  el.querySelector('.prev-btn').addEventListener('click', () => {
    if (currentPage > 1) { currentPage--; loadPage(el); }
  });

  el.querySelector('.next-btn').addEventListener('click', () => {
    currentPage++;
    loadPage(el);
  });

  await loadPage(el);
}
