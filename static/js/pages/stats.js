/**
 * Stats dashboard page.
 */

export async function render(el) {
  const r = await fetch('/api/stats');
  const data = await r.json();

  el.innerHTML = `
    <div class="page-header"><h1>Stats</h1></div>
    <div class="stats-grid"></div>
  `;

  const grid = el.querySelector('.stats-grid');

  // Image count
  addCard(grid, 'Total Images', data.image_count?.toLocaleString() || '0');

  // Reliability
  if (data.reliability && Object.keys(data.reliability).length) {
    const detail = Object.entries(data.reliability)
      .map(([mode, alpha]) => `${mode}: ${alpha?.toFixed(4) ?? '—'}`)
      .join('<br>');
    addCard(grid, 'Inter-Rater Reliability', 'Krippendorff\'s Alpha', detail);
  }

  // Vote counts
  if (data.vote_counts) {
    const detail = Object.entries(data.vote_counts)
      .map(([k, v]) => `${k.replace('_', ' ')}: ${v.toLocaleString()}`)
      .join('<br>');
    const total = Object.values(data.vote_counts).reduce((a, b) => a + b, 0);
    addCard(grid, 'Vote Data', total.toLocaleString() + ' total', detail);
  }

  // Bias
  if (data.bias && Object.keys(data.bias).length) {
    const b = data.bias;
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
  if (data.score_distribution?.length) {
    const maxCount = Math.max(...data.score_distribution.map(b => b.count));
    const bars = data.score_distribution.map(b => {
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
