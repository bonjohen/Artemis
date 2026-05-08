/**
 * Candidates page — comparison view with method explanations and detail.
 */

const METHOD_INFO = {
  method_a: {
    label: 'Method A — Top Popularity',
    short: 'Pure popularity ranking',
    desc: 'Selects the 13 highest-scoring images by composite preference score (Beta-Binomial posterior mean). No diversity constraint — if the top 13 are all Earth views, so be it. This is the naive baseline that proves diversity-aware methods add value.',
    strengths: 'Maximizes aggregate voter preference. Simple and transparent.',
    weaknesses: 'No diversity guarantee — images may cluster in a few visual themes. No month-fit consideration.',
  },
  method_b: {
    label: 'Method B — Cluster-Limited',
    short: 'Top popularity with cluster caps',
    desc: 'Selects by preference score but limits each visual cluster to at most 2 images. Iterates through images in score order, skipping any whose cluster already has 2 representatives. Guarantees visual spread across at least 7 of the 25 clusters.',
    strengths: 'Simple diversity guarantee. Still preference-driven within the constraint.',
    weaknesses: 'Hard cap is blunt — a cluster with 1,400 images gets the same limit as one with 77. No month-fit.',
  },
  method_c: {
    label: 'Method C — Per-Cluster Top',
    short: 'Best image from each cluster',
    desc: 'Selects the single highest-scoring image from each of the top 13 clusters (ranked by mean preference score). Guarantees every selected image comes from a different cluster, maximizing visual diversity by construction.',
    strengths: 'Maximum cluster diversity — 13 unique clusters. No visual redundancy possible.',
    weaknesses: 'Ignores within-cluster score variation. Some clusters may have weak top images. No month-fit.',
  },
  method_d: {
    label: 'Method D — Month-First',
    short: 'Best image for each month',
    desc: 'For each of the 13 calendar months, selects the image with the highest combined preference + month-fit score from an under-represented cluster. Month-fit scores are computed from visual features: brightness and warm tones for summer, cool tones for winter, etc.',
    strengths: 'Every image is chosen for its month. Seasonal variety built in.',
    weaknesses: 'Month-fit heuristics are coarse (no text metadata for most images). May sacrifice top-preference images for better month matches.',
  },
  method_e: {
    label: 'Method E — MMR Greedy',
    short: 'Maximum Marginal Relevance',
    desc: 'Iteratively selects images using Maximum Marginal Relevance — at each step, picks the image that maximizes a weighted combination of preference score, broad appeal, month-fit, and novelty (CLIP cosine distance from already-selected images), minus an uncertainty penalty. The diversity term uses 512-dimensional CLIP embeddings to measure visual similarity.',
    strengths: 'Balances all objectives simultaneously. Produces the most well-rounded calendar. Diversity is continuous (cosine distance) not discrete (cluster caps).',
    weaknesses: 'Most complex method — harder to explain why a specific image was chosen. Sensitive to weight tuning.',
  },
};

export async function render(el, hash) {
  const parts = hash.split('/');
  if (parts.length >= 3 && parts[2]) {
    await renderDetail(el, parts[2]);
  } else {
    await renderList(el);
  }
}

async function renderList(el) {
  const r = await fetch('/api/candidates');
  const candidates = await r.json();

  el.innerHTML = `
    <div class="page-header"><h1>Calendar Candidates</h1></div>
    <p style="color:var(--atlas-ink-2);max-width:64ch;margin-bottom:var(--s-6);line-height:var(--lh-body)">
      Five selection methods each produce a 13-image calendar. Each method makes different tradeoffs between
      voter preference, visual diversity, month suitability, and redundancy control. The objective score is a
      weighted composite: <span style="font-family:var(--mono);font-size:12px">2.0&times;popularity + 1.5&times;diversity + 0.8&times;month&#8209;fit + 0.5&times;cover&#8209;fit &minus; 1.0&times;redundancy &minus; 0.3&times;uncertainty</span>.
    </p>
    <div class="candidate-cards"></div>
  `;

  const grid = el.querySelector('.candidate-cards');
  candidates.forEach(c => {
    const info = METHOD_INFO[c.candidate_name] || { label: c.candidate_name, short: '', desc: '' };
    const card = document.createElement('div');
    card.className = 'candidate-card';
    card.addEventListener('click', () => {
      location.hash = `#/candidates/${c.candidate_name}`;
    });
    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:var(--s-3)">
        <h3 style="margin:0;font-family:var(--serif);font-size:18px">${info.label}</h3>
        <span style="font-family:var(--mono);font-size:20px;font-weight:600;color:var(--atlas-accent)">${c.objective_score.toFixed(3)}</span>
      </div>
      <p style="font-size:13px;color:var(--atlas-ink-2);margin:0 0 var(--s-4);line-height:1.5">${info.short}</p>
      <div class="metric"><span>Popularity</span><span>${c.popularity_score.toFixed(3)}</span></div>
      <div class="metric"><span>Diversity</span><span>${c.diversity_score.toFixed(3)}</span></div>
      <div class="metric"><span>Month Fit</span><span>${c.month_fit_score.toFixed(3)}</span></div>
      <div class="metric"><span>Redundancy</span><span style="color:var(--atlas-bad)">-${c.redundancy_penalty.toFixed(3)}</span></div>
    `;
    grid.appendChild(card);
  });
}

async function renderDetail(el, name) {
  const r = await fetch(`/api/candidates/${name}`);
  if (!r.ok) {
    el.innerHTML = '<p>Candidate not found.</p>';
    return;
  }
  const data = await r.json();
  const c = data.candidate;
  const info = METHOD_INFO[c.candidate_name] || { label: c.candidate_name, desc: '', strengths: '', weaknesses: '' };

  el.innerHTML = `
    <div class="page-header">
      <h1>${info.label}</h1>
      <div class="controls">
        <a href="#/candidates" class="btn">&larr; All Candidates</a>
        <button class="btn btn-primary use-starting-point">Use as Starting Point</button>
      </div>
    </div>

    <!-- Method explanation -->
    <div style="background:var(--atlas-paper-2);border:1px solid var(--atlas-rule-soft);border-radius:var(--r-md);padding:var(--s-5);margin-bottom:var(--s-6);max-width:72ch">
      <h3 style="font-family:var(--serif);font-size:var(--fs-h3);margin:0 0 var(--s-3)">How this method works</h3>
      <p style="line-height:var(--lh-body);margin:0 0 var(--s-4)">${info.desc}</p>
      <div class="methods-grid">
        <div>
          <h4 style="font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--atlas-good);margin:0 0 var(--s-2)">Strengths</h4>
          <p style="font-size:var(--fs-small);color:var(--atlas-ink-2);line-height:1.5;margin:0">${info.strengths || ''}</p>
        </div>
        <div>
          <h4 style="font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--atlas-bad);margin:0 0 var(--s-2)">Weaknesses</h4>
          <p style="font-size:var(--fs-small);color:var(--atlas-ink-2);line-height:1.5;margin:0">${info.weaknesses || ''}</p>
        </div>
      </div>
    </div>

    <!-- Scores -->
    <table class="score-table" style="max-width:500px;margin-bottom:var(--s-6)">
      <tbody>
        <tr><td>Objective Score</td><td style="font-weight:600">${c.objective_score.toFixed(3)}</td></tr>
        <tr><td>Popularity (2.0&times;)</td><td>${c.popularity_score.toFixed(3)}</td></tr>
        <tr><td>Diversity (1.5&times;)</td><td>${c.diversity_score.toFixed(3)}</td></tr>
        <tr><td>Month Fit (0.8&times;)</td><td>${c.month_fit_score.toFixed(3)}</td></tr>
        <tr><td>Cover Fit (0.5&times;)</td><td>${c.cover_fit_score.toFixed(3)}</td></tr>
        <tr><td>Redundancy (1.0&times;)</td><td style="color:var(--atlas-bad)">-${c.redundancy_penalty.toFixed(3)}</td></tr>
        <tr><td>Uncertainty (0.3&times;)</td><td style="color:var(--atlas-bad)">-${c.uncertainty_penalty.toFixed(3)}</td></tr>
      </tbody>
    </table>

    <h2 style="font-family:var(--serif);font-size:var(--fs-h3);margin-bottom:var(--s-4)">Month Assignments</h2>
    <div class="month-grid"></div>
  `;

  const monthGrid = el.querySelector('.month-grid');
  data.images.forEach(img => {
    const card = document.createElement('div');
    card.className = 'month-card';
    card.innerHTML = `
      <img src="/thumbs/${img.source_image_id}.jpg"
           alt="${img.month_label}" loading="lazy">
      <div class="month-info">
        <div class="month-label">${img.month_label}</div>
        <div class="month-score">
          Score: ${img.preference_score.toFixed(3)}
          | Fit: ${img.month_fit_score.toFixed(3)}
        </div>
      </div>
    `;
    monthGrid.appendChild(card);
  });

  // "Use as starting point" button
  el.querySelector('.use-starting-point').addEventListener('click', () => {
    const assignments = data.images.map(img => ({
      image_sk: img.image_sk,
      sequence_number: img.sequence_number,
      source_image_id: img.source_image_id,
      month_label: img.month_label,
    }));
    sessionStorage.setItem('selection_starting_point', JSON.stringify(assignments));
    location.hash = '#/selection';
  });
}
