/**
 * Image browser page — paginated grid with sort, filter, detail overlay,
 * and cluster spotlight view.
 */

import { createImageCard } from '../components/image-card.js';
import { showImageDetail } from '../components/image-detail.js';

let currentPage = 1;
let currentSort = 'score';
let currentCluster = '';
let currentMinScore = '';
let viewMode = 'browse'; // 'browse', 'spotlights', or 'timeline'

async function fetchImages(page, sort, clusterId, minScore) {
  const params = new URLSearchParams({ page, per_page: 60, sort });
  if (clusterId) params.set('cluster_id', clusterId);
  if (minScore) params.set('min_score', minScore);
  const r = await fetch(`/api/images?${params}`);
  return r.json();
}


async function loadPage(container) {
  const data = await fetchImages(currentPage, currentSort, currentCluster, currentMinScore);

  const grid = container.querySelector('.image-grid');
  grid.innerHTML = '';
  data.items.forEach(img => {
    grid.appendChild(createImageCard(img, () => showImageDetail(img.image_sk)));
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
        showImageDetail(parseInt(img.dataset.sk));
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
  const timelineArea = container.querySelector('.timeline-area');
  const browseBtn = container.querySelector('.view-browse');
  const spotBtn = container.querySelector('.view-spotlights');
  const timeBtn = container.querySelector('.view-timeline');

  // Hide all
  browseArea.style.display = 'none';
  spotlightsArea.style.display = 'none';
  timelineArea.style.display = 'none';
  browseBtn.classList.remove('active');
  spotBtn.classList.remove('active');
  timeBtn.classList.remove('active');

  if (viewMode === 'spotlights') {
    spotlightsArea.style.display = '';
    spotBtn.classList.add('active');
    loadSpotlights(container);
  } else if (viewMode === 'timeline') {
    timelineArea.style.display = '';
    timeBtn.classList.add('active');
    loadTimeline(container);
  } else {
    browseArea.style.display = '';
    browseBtn.classList.add('active');
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
          <button class="filter-btn view-timeline">Timeline</button>
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
    <div class="timeline-area" style="display:none"></div>
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
  el.querySelector('.view-timeline').addEventListener('click', () => {
    viewMode = 'timeline';
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

async function loadTimeline(container) {
  const area = container.querySelector('.timeline-area');
  area.innerHTML = '<div class="loading">Loading timeline...</div>';

  const r = await fetch('/api/images/timeline/segments?segment_size=2000');
  const data = await r.json();

  if (!data.segments?.length) {
    area.innerHTML = '<p style="color:var(--atlas-muted)">No timeline data available.</p>';
    return;
  }

  // Build the overview bar
  const maxCount = Math.max(...data.segments.map(s => s.image_count));

  area.innerHTML = `
    <div class="tl-header">
      <h3 class="sb-section-title">Mission Timeline</h3>
      <p style="font-size:var(--fs-small);color:var(--atlas-muted);margin-bottom:var(--s-4)">
        ${data.total_images.toLocaleString()} unique images across frames
        E-${data.frame_range[0]} to E-${data.frame_range[1]}.
        Each segment shows the top-scoring images and dominant content attributes.
      </p>
    </div>
    <div class="tl-bar">
      ${data.segments.map(seg => {
        const pct = (seg.image_count / maxCount) * 100;
        return `<div class="tl-bar-seg" style="flex:${seg.image_count}" title="${seg.label}: ${seg.image_count} images">
          <div class="tl-bar-fill" style="height:${Math.max(pct, 8)}%"></div>
          <span class="tl-bar-label">${seg.image_count}</span>
        </div>`;
      }).join('')}
    </div>
    <div class="tl-segments"></div>
  `;

  const segContainer = area.querySelector('.tl-segments');

  for (const seg of data.segments) {
    const section = document.createElement('div');
    section.className = 'tl-segment';

    const attrTags = seg.top_attributes.map(a =>
      `<span class="tl-attr-tag">${a.code.replace(/_/g, ' ')} <em>${a.count}</em></span>`
    ).join('');

    section.innerHTML = `
      <div class="tl-segment-header">
        <div>
          <h4 class="tl-segment-title">${seg.label}</h4>
          <span class="tl-segment-count">${seg.image_count} images</span>
        </div>
        <div class="tl-attrs">${attrTags}</div>
      </div>
      <div class="tl-thumbs">
        ${seg.thumbnails.map(t => `
          <div class="tl-thumb" data-sk="${t.image_sk}">
            <img src="/thumbs/${t.source_image_id}.jpg" alt="${t.source_image_id}" loading="lazy">
            <div class="tl-thumb-id">${t.source_image_id.replace('ART002-E-', 'E-')}</div>
          </div>
        `).join('')}
      </div>
    `;

    // Click thumbnails to show detail
    section.querySelectorAll('.tl-thumb').forEach(thumb => {
      thumb.style.cursor = 'pointer';
      thumb.addEventListener('click', () => {
        showImageDetail(parseInt(thumb.dataset.sk));
      });
    });

    segContainer.appendChild(section);
  }
}

async function _loadDedupBanner(el) {
  try {
    const r = await fetch('/api/dedup/summary?top_groups=6');
    const d = await r.json();
    if (d.suppressed > 0) {
      const pct = ((d.suppressed / d.total) * 100).toFixed(0);
      const thumbs = (d.top_groups || []).map(g =>
        `<div class="dedup-thumb" title="${g.member_count} near-identical images consolidated">
          <img src="/thumbs/${g.source_image_id}.jpg" alt="${g.source_image_id}" loading="lazy">
          <span class="dedup-thumb-count">${g.member_count}</span>
        </div>`
      ).join('');

      const banner = el.querySelector('.dedup-banner');
      banner.style.display = '';
      banner.innerHTML = `
        <div class="dedup-banner-inner">
          <div class="dedup-banner-text">
            <strong>${d.active.toLocaleString()}</strong> unique images shown.
            <strong>${d.suppressed.toLocaleString()}</strong> near-duplicates
            (${pct}% of ${d.total.toLocaleString()}) removed at
            ${d.threshold} cosine similarity
            across ${d.groups.toLocaleString()} groups.
          </div>
          ${thumbs ? `<div class="dedup-banner-thumbs">${thumbs}</div>` : ''}
        </div>
      `;
    }
  } catch { /* dedup not available */ }
}
