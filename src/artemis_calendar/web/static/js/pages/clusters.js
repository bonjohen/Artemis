/**
 * Cluster explorer page — cluster cards and member grid.
 */

import { createImageCard } from '../components/image-card.js';
import { showImageDetail } from '../components/image-detail.js';
import { renderContextBlock } from '../components/context-block.js';

export async function render(el, hash) {
  const parts = hash.split('/');
  if (parts.length >= 3 && parts[2]) {
    await renderClusterDetail(el, parseInt(parts[2]));
  } else {
    await renderClusterList(el);
  }
}

async function renderClusterList(el) {
  const [clustersResp, spotlightsResp] = await Promise.all([
    fetch('/api/clusters').then(r => r.json()).catch(() => []),
    fetch('/api/clusters/spotlights').then(r => r.json()).catch(() => []),
  ]);

  const spotlightMap = {};
  for (const s of spotlightsResp) spotlightMap[s.cluster_id] = s;

  el.innerHTML = `
    ${renderContextBlock('Why this page matters', '25 visual clusters from CLIP embeddings \u2014 each grouping images by scene content and composition. Demonstrates unsupervised visual similarity analysis.')}
    <div class="page-header"><h1>Clusters</h1></div>
    <p class="cluster-explainer">
      Each cluster groups visually similar images by CLIP embedding proximity.
      The <strong>spotlight</strong> shows the image closest to the cluster center (most typical)
      plus five diverse images selected by greedy max-min distance within the cluster.
    </p>
    <div class="cluster-spotlights" id="cluster-spotlights"></div>
  `;

  const container = el.querySelector('#cluster-spotlights');

  clustersResp.forEach(c => {
    const spot = spotlightMap[c.cluster_id];
    const card = document.createElement('div');
    card.className = 'cluster-spotlight-card';

    const rep = spot?.representative;
    const diverse = spot?.diverse || [];

    card.innerHTML = `
      <div class="cluster-spot-header" style="cursor:pointer" title="Click to browse all ${c.image_count} images">
        <span class="cluster-spot-label">Cluster ${c.cluster_id}</span>
        <span class="cluster-spot-meta">${c.image_count} images${c.mean_preference_score != null ? ` · Score ${c.mean_preference_score.toFixed(3)}` : ''}</span>
      </div>
      <div class="cluster-spot-images">
        ${rep ? `
          <div class="cluster-spot-rep" data-sk="${rep.image_sk}" title="Center — most typical image in this cluster">
            <img src="/thumbs/${rep.source_image_id}.jpg" alt="Representative" loading="lazy">
            <span class="cluster-spot-badge">Center</span>
          </div>
        ` : ''}
        <div class="cluster-spot-diverse">
          ${diverse.map(d => `
            <div class="cluster-spot-div-img" data-sk="${d.image_sk}" title="Diverse pick — maximizes visual variety within cluster">
              <img src="/thumbs/${d.source_image_id}.jpg" alt="Diverse" loading="lazy">
            </div>
          `).join('')}
        </div>
      </div>
    `;

    card.querySelector('.cluster-spot-header').addEventListener('click', () => {
      location.hash = `#/clusters/${c.cluster_id}`;
    });

    // Image click → detail modal
    card.querySelectorAll('[data-sk]').forEach(img => {
      img.addEventListener('click', () => showImageDetail(parseInt(img.dataset.sk)));
    });

    container.appendChild(card);
  });
}

async function renderClusterDetail(el, clusterId) {
  let page = 1;

  el.innerHTML = `
    <div class="page-header">
      <h1>Cluster ${clusterId}</h1>
      <a href="#/clusters" class="btn">Back</a>
    </div>
    <div class="image-grid"></div>
    <div class="pagination">
      <button class="prev-btn">Prev</button>
      <span class="page-info"></span>
      <button class="next-btn">Next</button>
    </div>
  `;

  async function load() {
    const r = await fetch(`/api/clusters/${clusterId}?page=${page}&per_page=60`);
    const data = await r.json();
    const grid = el.querySelector('.image-grid');
    grid.innerHTML = '';

    if (!data.items || data.items.length === 0) {
      // Cluster exists but all images are suppressed — show representative
      try {
        const spotR = await fetch(`/api/clusters/${clusterId}/spotlight`);
        if (spotR.ok) {
          const spot = await spotR.json();
          grid.innerHTML = `
            <div style="grid-column:1/-1;text-align:center;padding:var(--s-6);color:var(--atlas-muted);font-family:var(--mono);font-size:var(--fs-small)">
              All ${spot.image_count || ''} images in this cluster were consolidated by deduplication.
              The representative image is shown below.
            </div>
          `;
          if (spot.representative) {
            const rep = spot.representative;
            grid.innerHTML += `
              <div style="grid-column:1/-1;display:flex;justify-content:center">
                <div style="max-width:400px;border:1px solid var(--atlas-rule-soft);border-radius:var(--r-md);overflow:hidden">
                  <img src="/thumbs/${rep.source_image_id}.jpg" alt="Representative"
                       style="width:100%;display:block">
                  <div style="padding:var(--s-3);font-family:var(--mono);font-size:var(--fs-small);color:var(--atlas-ink-2)">
                    ${rep.source_image_id} — Representative of ${spot.image_count || 'this'} consolidated images
                  </div>
                </div>
              </div>
            `;
          }
        } else {
          grid.innerHTML = `
            <div style="grid-column:1/-1;text-align:center;padding:var(--s-6);color:var(--atlas-muted);font-family:var(--mono);font-size:var(--fs-small)">
              All images in this cluster were consolidated by deduplication. No active images remain.
            </div>
          `;
        }
      } catch {
        grid.innerHTML = `
          <div style="grid-column:1/-1;text-align:center;padding:var(--s-6);color:var(--atlas-muted)">
            No active images in this cluster.
          </div>
        `;
      }
      el.querySelector('.page-info').textContent = '0 images (all deduplicated)';
      el.querySelector('.prev-btn').disabled = true;
      el.querySelector('.next-btn').disabled = true;
      return;
    }

    data.items.forEach(img => {
      grid.appendChild(createImageCard(img, () => {
        showImageDetail(img.image_sk);
      }));
    });
    el.querySelector('.page-info').textContent =
      `Page ${data.page} of ${data.pages} (${data.total} images)`;
    el.querySelector('.prev-btn').disabled = data.page <= 1;
    el.querySelector('.next-btn').disabled = data.page >= data.pages;
  }

  el.querySelector('.prev-btn').addEventListener('click', () => { page--; load(); });
  el.querySelector('.next-btn').addEventListener('click', () => { page++; load(); });

  await load();
}
