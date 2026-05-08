/**
 * Cluster explorer page — cluster cards and member grid.
 */

import { createImageCard } from '../components/image-card.js';

export async function render(el, hash) {
  const parts = hash.split('/');
  if (parts.length >= 3 && parts[2]) {
    await renderClusterDetail(el, parseInt(parts[2]));
  } else {
    await renderClusterList(el);
  }
}

async function renderClusterList(el) {
  const r = await fetch('/api/clusters');
  const clusters = await r.json();

  el.innerHTML = `
    <div class="page-header"><h1>Clusters</h1></div>
    <div class="cluster-cards"></div>
  `;

  const grid = el.querySelector('.cluster-cards');
  clusters.forEach(c => {
    const card = document.createElement('div');
    card.className = 'cluster-card';
    card.addEventListener('click', () => {
      location.hash = `#/clusters/${c.cluster_id}`;
    });
    const thumbSrc = c.top_image_guid
      ? `/thumbs/${c.top_image_guid}.jpg`
      : '';
    card.innerHTML = `
      ${thumbSrc ? `<img src="${thumbSrc}" alt="Cluster ${c.cluster_id}" loading="lazy">` : ''}
      <div class="cluster-info">
        <div class="cluster-label">Cluster ${c.cluster_id}</div>
        <div class="cluster-meta">
          ${c.image_count} images
          ${c.mean_preference_score != null
            ? ` | Score: ${c.mean_preference_score.toFixed(3)}`
            : ''}
        </div>
      </div>
    `;
    grid.appendChild(card);
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
    data.items.forEach(img => {
      grid.appendChild(createImageCard(img, () => {
        location.hash = `#/images/${img.image_sk}`;
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
