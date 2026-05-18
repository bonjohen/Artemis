/**
 * Stats dashboard page — image analysis, content attributes, dedup, scoring.
 */

import { renderContextBlock } from '../components/context-block.js';

export async function render(el) {
  el.innerHTML = `
    ${renderContextBlock('Why this page matters', 'Score distributions, inter-rater reliability, and bias detection across synthetic voter cohorts. Demonstrates statistical validation and manufactured-data transparency.')}
    <div class="page-header"><h1>Stats</h1></div>
    <div class="stats-grid" id="stats-grid"></div>
  `;

  const grid = el.querySelector('#stats-grid');

  // Load all data in parallel
  const [stats, attrDist, derivedDist, dedupSummary] = await Promise.all([
    fetch('/api/stats').then(r => r.json()).catch(() => ({})),
    fetch('/api/attributes/distribution').then(r => r.json()).catch(() => []),
    fetch('/api/attributes/derived').then(r => r.json()).catch(() => []),
    fetch('/api/dedup/summary').then(r => r.json()).catch(() => null),
  ]);

  // === SECTION: Image Analysis ===
  addSectionHeader(grid, 'Image Analysis');

  // Dedup summary
  if (dedupSummary && dedupSummary.suppressed > 0) {
    const pct = ((dedupSummary.suppressed / dedupSummary.total) * 100).toFixed(0);
    addCard(grid, 'Deduplication', `${dedupSummary.active.toLocaleString()} unique`, [
      `${dedupSummary.suppressed.toLocaleString()} duplicates removed (${pct}%)`,
      `${dedupSummary.total.toLocaleString()} total in collection`,
      `${dedupSummary.groups.toLocaleString()} duplicate groups`,
      `Threshold: ${dedupSummary.threshold} cosine similarity`,
    ].join('<br>'));
  }

  // Attribute coverage
  if (attrDist.length) {
    const totalTagged = attrDist.reduce((s, a) => s + a.total, 0);
    const totalAccepted = attrDist.reduce((s, a) => s + a.accepted, 0);
    const uniqueImages = dedupSummary?.active || stats.image_count || 0;
    addCard(grid, 'Content Attributes', `${attrDist.length} attributes`, [
      `${totalAccepted.toLocaleString()} accepted labels across ${uniqueImages.toLocaleString()} images`,
      `${totalTagged.toLocaleString()} total confidence scores`,
      'Model: CLIP ViT-B/32 zero-shot',
      'Method: sigmoid-calibrated cosine similarity',
    ].join('<br>'));
  }

  // Derived attributes
  if (derivedDist.length) {
    const detail = derivedDist.map(d =>
      `${d.code.replace(/_/g, ' ')}: ${d.count.toLocaleString()}`
    ).join('<br>');
    addCard(grid, 'Derived Labels', `${derivedDist.length} composite attributes`, detail);
  }

  // === SECTION: Attribute Distribution (full-width chart) ===
  if (attrDist.length) {
    const chartCard = document.createElement('div');
    chartCard.className = 'stat-card';
    chartCard.style.gridColumn = 'span 2';

    const maxAccepted = Math.max(...attrDist.map(a => a.accepted));
    const bars = attrDist.map(a => {
      const accPct = (a.accepted / Math.max(maxAccepted, 1) * 100).toFixed(0);
      const tentPct = (a.tentative / Math.max(maxAccepted, 1) * 100).toFixed(0);
      const label = a.code.replace(/_/g, ' ');
      return `<div class="attr-bar-row">
        <span class="attr-bar-label">${label}</span>
        <div class="attr-bar-track">
          <div class="attr-bar-fill attr-accepted" style="width:${accPct}%"></div>
          <div class="attr-bar-fill attr-tentative" style="width:${tentPct}%"></div>
        </div>
        <span class="attr-bar-value">${a.accepted.toLocaleString()}</span>
      </div>`;
    }).join('');

    chartCard.innerHTML = `
      <h3>Attribute Distribution <span style="font-weight:400;color:var(--atlas-muted);font-size:var(--fs-meta);margin-left:var(--s-2)">
        <span style="display:inline-block;width:10px;height:10px;background:var(--atlas-accent);border-radius:2px;vertical-align:middle"></span> accepted
        <span style="display:inline-block;width:10px;height:10px;background:var(--atlas-accent);opacity:0.3;border-radius:2px;vertical-align:middle;margin-left:var(--s-2)"></span> tentative
      </span></h3>
      <div style="display:flex;flex-direction:column;gap:3px;margin-top:var(--s-3)">${bars}</div>
    `;
    grid.appendChild(chartCard);
  }

  // === SECTION: Scoring Methods ===
  addSectionHeader(grid, 'Scoring Methods');

  // Image count
  addCard(grid, 'Total Images', stats.image_count?.toLocaleString() || '0');

  // Reliability
  if (stats.reliability && Object.keys(stats.reliability).length) {
    const detail = Object.entries(stats.reliability)
      .map(([mode, alpha]) => `${mode}: ${alpha?.toFixed(4) ?? '—'}`)
      .join('<br>');
    addCard(grid, 'Inter-Rater Reliability', 'Krippendorff\'s Alpha', detail);
  }

  // Vote counts
  if (stats.vote_counts) {
    const detail = Object.entries(stats.vote_counts)
      .map(([k, v]) => `${k.replace('_', ' ')}: ${v.toLocaleString()}`)
      .join('<br>');
    const total = Object.values(stats.vote_counts).reduce((a, b) => a + b, 0);
    addCard(grid, 'Vote Data', total.toLocaleString() + ' total', detail);
  }

  // Bias
  if (stats.bias && Object.keys(stats.bias).length) {
    const b = stats.bias;
    const detail = [
      b.position_bias_coeff != null
        ? `Position: coeff=${b.position_bias_coeff.toFixed(4)}, p=${b.position_bias_pvalue?.toFixed(4)}`
        : null,
      b.cluster_bias_chi2 != null
        ? `Cluster: chi2=${b.cluster_bias_chi2.toFixed(2)}, p=${b.cluster_bias_pvalue?.toFixed(4)}`
        : null,
      b.score_vs_truth_spearman != null
        ? `Score-Truth: rho=${b.score_vs_truth_spearman.toFixed(4)}, p=${b.score_vs_truth_pvalue?.toFixed(4)}`
        : null,
      b.voter_segment_count != null
        ? `Voter segments: ${b.voter_segment_count}`
        : null,
    ].filter(Boolean).join('<br>');
    addCard(grid, 'Bias Detection', 'Results', detail);
  }

  // Score distribution
  if (stats.score_distribution?.length) {
    const maxCount = Math.max(...stats.score_distribution.map(b => b.count));
    const bars = stats.score_distribution.map(b => {
      const pct = (b.count / maxCount * 100).toFixed(0);
      return `<div style="display:flex;align-items:center;gap:var(--s-2);font-size:var(--fs-meta);font-family:var(--mono)">
        <span style="min-width:36px;text-align:right">${b.bucket.toFixed(2)}</span>
        <div style="height:12px;width:${pct}%;background:var(--atlas-accent);border-radius:2px;min-width:2px"></div>
        <span style="color:var(--atlas-muted)">${b.count}</span>
      </div>`;
    }).join('');
    const card = document.createElement('div');
    card.className = 'stat-card';
    card.style.gridColumn = 'span 2';
    card.innerHTML = `
      <h3>Score Distribution</h3>
      <div style="display:flex;flex-direction:column;gap:2px">${bars}</div>
    `;
    grid.appendChild(card);
  }
}

function addSectionHeader(grid, title) {
  const header = document.createElement('div');
  header.style.gridColumn = 'span 2';
  header.style.marginTop = 'var(--s-5)';
  header.innerHTML = `<h2 style="font-family:var(--serif);font-size:var(--fs-h3);font-weight:500;margin:0;padding-bottom:var(--s-2);border-bottom:1px solid var(--atlas-rule-soft)">${title}</h2>`;
  grid.appendChild(header);
}

function addCard(grid, title, value, detail) {
  const card = document.createElement('div');
  card.className = 'stat-card';
  card.innerHTML = `
    <h3>${title}</h3>
    <div class="stat-value">${value}</div>
    ${detail ? `<div class="stat-detail">${detail}</div>` : ''}
  `;
  grid.appendChild(card);
}
