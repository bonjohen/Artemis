/**
 * Candidates page — comparison view and detail.
 * Full implementation in Phase 5.
 */

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
    <div class="page-header"><h1>Candidates</h1></div>
    <div class="candidate-cards"></div>
  `;

  const grid = el.querySelector('.candidate-cards');
  candidates.forEach(c => {
    const card = document.createElement('div');
    card.className = 'candidate-card';
    card.addEventListener('click', () => {
      location.hash = `#/candidates/${c.candidate_name}`;
    });
    card.innerHTML = `
      <h3>${c.candidate_name}</h3>
      <div class="metric"><span>Objective</span><span>${c.objective_score.toFixed(3)}</span></div>
      <div class="metric"><span>Popularity</span><span>${c.popularity_score.toFixed(3)}</span></div>
      <div class="metric"><span>Diversity</span><span>${c.diversity_score.toFixed(3)}</span></div>
      <div class="metric"><span>Month Fit</span><span>${c.month_fit_score.toFixed(3)}</span></div>
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

  el.innerHTML = `
    <div class="page-header">
      <h1>${c.candidate_name}</h1>
      <div class="controls">
        <a href="#/candidates" class="btn">Back</a>
        <button class="btn btn-primary use-starting-point">Use as Starting Point</button>
      </div>
    </div>
    <table class="score-table" style="max-width:500px;margin-bottom:var(--s-4)">
      <tbody>
        <tr><td>Objective</td><td>${c.objective_score.toFixed(3)}</td></tr>
        <tr><td>Popularity</td><td>${c.popularity_score.toFixed(3)}</td></tr>
        <tr><td>Diversity</td><td>${c.diversity_score.toFixed(3)}</td></tr>
        <tr><td>Month Fit</td><td>${c.month_fit_score.toFixed(3)}</td></tr>
        <tr><td>Cover Fit</td><td>${c.cover_fit_score.toFixed(3)}</td></tr>
        <tr><td>Redundancy</td><td>-${c.redundancy_penalty.toFixed(3)}</td></tr>
        <tr><td>Uncertainty</td><td>-${c.uncertainty_penalty.toFixed(3)}</td></tr>
      </tbody>
    </table>
    <h2 style="font-family:var(--serif);font-size:var(--fs-h3)">Month Assignments</h2>
    <div class="month-grid"></div>
  `;

  const monthGrid = el.querySelector('.month-grid');
  data.images.forEach(img => {
    const card = document.createElement('div');
    card.className = 'month-card';
    card.innerHTML = `
      <img src="https://pub-1f1ce68455c0432ea65ac3155a6b2409.r2.dev/thumbs/${img.source_image_id}.jpg"
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
