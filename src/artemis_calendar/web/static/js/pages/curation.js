/**
 * Data Curation page — dedup detection, dark frame filtering, master selection.
 */

import { renderContextBlock } from '../components/context-block.js';

const THUMB = '/thumbs/';

export async function render(el) {
  // Fetch all data in parallel
  const [summary, distribution, darkStats] = await Promise.all([
    fetch('/api/dedup/summary?top_groups=10').then(r => r.json()).catch(() => null),
    fetch('/api/dedup/distribution').then(r => r.json()).catch(() => []),
    fetch('/api/dedup/dark-stats').then(r => r.json()).catch(() => null),
  ]);

  const groups = summary?.groups || 0;
  const total = summary?.total || 12217;
  const threshold = summary?.threshold || 0.98;
  const topGroups = summary?.top_groups || [];
  const totalDuplicates = summary?.duplicates || 0;
  const darkCount = darkStats?.dark_count || 0;

  el.innerHTML = `
    ${renderContextBlock('Why this page matters', 'How near-duplicate detection and dark-frame filtering reduce 12,217 mission photos to a pool of visually distinct candidates before scoring and optimization.')}
    <div class="page-header"><h1>Data Curation</h1></div>

    <!-- Stats bar -->
    <section class="curation-stats">
      <div class="curation-stat">
        <span class="curation-stat-num">${total.toLocaleString()}</span>
        <span class="curation-stat-label">Total Images</span>
      </div>
      <div class="curation-stat">
        <span class="curation-stat-num">${groups.toLocaleString()}</span>
        <span class="curation-stat-label">Duplicate Groups</span>
      </div>
      <div class="curation-stat">
        <span class="curation-stat-num">${totalDuplicates.toLocaleString()}</span>
        <span class="curation-stat-label">Near-Duplicates</span>
      </div>
      <div class="curation-stat">
        <span class="curation-stat-num">${darkCount.toLocaleString()}</span>
        <span class="curation-stat-label">Dark Frames</span>
      </div>
    </section>

    <!-- Why Curate -->
    <section class="curation-prose">
      <h2 class="section-title">Why Curate?</h2>
      <div class="curation-prose-text">
        <p>The raw collection contains thousands of functionally identical frames: consecutive shots from the same camera angle, near-black images of empty space, and sequences that differ by only a few pixels. Without curation, identical frames inflate preference scores, bias cluster assignments, and waste the optimizer's budget.</p>
        <p>The largest duplicate group contains <strong>${topGroups[0]?.member_count?.toLocaleString() || '6,810'} images</strong> — nearly all dark-space frames that are visually indistinguishable. A calendar optimizer that treats each copy as a distinct candidate would overweight these redundant images and produce a calendar dominated by empty space.</p>
      </div>
    </section>

    <!-- How It Works -->
    <section class="curation-methods-section">
      <h2 class="section-title">How It Works</h2>
      <p class="section-desc">Three complementary filters reduce the collection to visually distinct candidates.</p>
      <div class="methods-grid">
        <div class="method-card">
          <h4>CLIP Embedding Similarity</h4>
          <p>Each image is encoded as a 512-dimensional vector by CLIP ViT-B/32. Pairs with cosine similarity &ge; ${threshold} are linked. Connected components (via scipy) group transitively similar images — if A matches B and B matches C, all three form one group, even if A and C aren't directly similar.</p>
        </div>
        <div class="method-card">
          <h4>Dark Frame Filtering</h4>
          <p>Pixel-level brightness analysis flags images where 92%+ of pixels fall below brightness 20 (on 0–255 scale). These near-black frames — <strong>${darkCount.toLocaleString()}</strong> of ${total.toLocaleString()} — are excluded from scoring and optimization via the active image filter.</p>
        </div>
        <div class="method-card">
          <h4>Master Selection</h4>
          <p>Within each duplicate group, the image with the highest composite preference score is retained as master. Ties break on brightness. The rest are suppressed via a reversible flag in the database — no images are permanently deleted.</p>
        </div>
      </div>
    </section>

    <!-- Group Size Distribution -->
    <section class="curation-dist-section">
      <h2 class="section-title">Group Size Distribution</h2>
      <p class="section-desc">${groups} duplicate groups by member count — most are small (2–5 images), but a few massive groups dominate.</p>
      <div class="curation-dist" id="curation-dist"></div>
    </section>

    <!-- Largest Duplicate Groups -->
    <section class="curation-groups-section">
      <h2 class="section-title">Largest Duplicate Groups</h2>
      <p class="section-desc">Click a group to see member images. The master (highest preference score) is highlighted.</p>
      <div class="curation-groups" id="curation-groups"></div>
    </section>
  `;

  // Render distribution chart
  renderDistribution(el.querySelector('#curation-dist'), distribution);

  // Render top groups
  renderTopGroups(el.querySelector('#curation-groups'), topGroups);
}

function renderDistribution(container, distribution) {
  if (!distribution.length) {
    container.textContent = 'No distribution data available.';
    return;
  }
  const maxCount = Math.max(...distribution.map(d => d.count));
  const bars = distribution.map(d => {
    const pct = (d.count / maxCount * 100).toFixed(0);
    return `<div class="curation-dist-row">
      <span class="curation-dist-label">${d.bucket}</span>
      <div class="curation-dist-track">
        <div class="curation-dist-fill" style="width:${pct}%"></div>
      </div>
      <span class="curation-dist-value">${d.count}</span>
    </div>`;
  }).join('');
  container.innerHTML = bars;
}

function renderTopGroups(container, groups) {
  if (!groups.length) {
    container.textContent = 'No duplicate groups found.';
    return;
  }
  for (const g of groups) {
    const card = document.createElement('div');
    card.className = 'curation-group-card';
    card.innerHTML = `
      <div class="curation-group-header">
        <img src="${THUMB}${g.source_image_id}.jpg" alt="Master: ${g.source_image_id}" class="curation-master-thumb">
        <div class="curation-group-info">
          <span class="curation-group-count">${g.member_count.toLocaleString()} images</span>
          <span class="curation-group-master">Master: ${g.source_image_id}</span>
        </div>
        <span class="curation-group-toggle">+</span>
      </div>
      <div class="curation-group-members" data-group-id="${g.group_id}" data-loaded="false"></div>
    `;

    const header = card.querySelector('.curation-group-header');
    const membersDiv = card.querySelector('.curation-group-members');
    const toggle = card.querySelector('.curation-group-toggle');

    header.addEventListener('click', async () => {
      const isOpen = card.classList.toggle('expanded');
      toggle.textContent = isOpen ? '−' : '+';
      if (isOpen && membersDiv.dataset.loaded === 'false') {
        membersDiv.innerHTML = '<div class="loading" style="padding:var(--s-3)">Loading members...</div>';
        try {
          const data = await fetch(`/api/dedup/groups/${g.group_id}/members?limit=12`).then(r => r.json());
          const remaining = g.member_count - data.members.length;
          membersDiv.innerHTML = data.members.map(m => `
            <div class="curation-member ${m.is_master ? 'curation-member-master' : ''}">
              <img src="${THUMB}${m.source_image_id}.jpg" alt="${m.source_image_id}" loading="lazy">
              <span class="curation-member-sim">${m.is_master ? 'MASTER' : m.similarity_to_master.toFixed(4)}</span>
            </div>
          `).join('') + (remaining > 0 ? `<div class="curation-member-more">${remaining.toLocaleString()} more</div>` : '');
          membersDiv.dataset.loaded = 'true';
        } catch (e) {
          membersDiv.textContent = 'Could not load members.';
        }
      }
    });

    container.appendChild(card);
  }
}
