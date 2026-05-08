/**
 * Selection builder page — 13-slot calendar grid with live scoring.
 */

const MONTH_LABELS = [
  'Cover / Dec 2026', 'January 2027', 'February 2027', 'March 2027',
  'April 2027', 'May 2027', 'June 2027', 'July 2027',
  'August 2027', 'September 2027', 'October 2027', 'November 2027',
  'December 2027',
];

let assignments = [];
let scores = null;

export async function render(el) {
  // Check for starting point from candidates page
  const startingPoint = sessionStorage.getItem('selection_starting_point');
  if (startingPoint) {
    assignments = JSON.parse(startingPoint);
    sessionStorage.removeItem('selection_starting_point');
  } else if (assignments.length === 0) {
    // Try loading current selection
    const r = await fetch('/api/selection?name=current');
    const data = await r.json();
    if (data.assignments?.length) {
      assignments = data.assignments;
    }
  }

  el.innerHTML = `
    <div class="page-header">
      <h1>Selection Builder</h1>
      <div class="controls">
        <input type="text" class="name-input" placeholder="Selection name" value="current"
               style="width:140px">
        <button class="btn save-btn">Save</button>
        <button class="btn load-btn">Load</button>
      </div>
    </div>
    <div class="selection-layout">
      <div>
        <div class="calendar-slots"></div>
      </div>
      <div class="selection-sidebar">
        <h3>Scores</h3>
        <div class="score-display">
          <p style="color:var(--atlas-muted);font-size:var(--fs-small)">
            ${assignments.length ? 'Scoring...' : 'Add images to see scores'}
          </p>
        </div>
      </div>
    </div>
  `;

  renderSlots(el);

  if (assignments.length) {
    await updateScores(el);
  }

  // Save button
  el.querySelector('.save-btn').addEventListener('click', async () => {
    const name = el.querySelector('.name-input').value || 'current';
    const body = {
      name,
      assignments: assignments.map(a => ({
        image_sk: a.image_sk,
        sequence_number: a.sequence_number,
      })),
      notes: '',
    };
    await fetch('/api/selection', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    el.querySelector('.save-btn').textContent = 'Saved!';
    setTimeout(() => {
      el.querySelector('.save-btn').textContent = 'Save';
    }, 1500);
  });

  // Load button
  el.querySelector('.load-btn').addEventListener('click', async () => {
    const name = el.querySelector('.name-input').value || 'current';
    const r = await fetch(`/api/selection?name=${name}`);
    const data = await r.json();
    if (data.assignments?.length) {
      assignments = data.assignments;
      renderSlots(el);
      await updateScores(el);
    }
  });
}

function renderSlots(el) {
  const container = el.querySelector('.calendar-slots');
  container.innerHTML = '';

  for (let seq = 1; seq <= 13; seq++) {
    const assignment = assignments.find(a => a.sequence_number === seq);
    const slot = document.createElement('div');
    slot.className = `slot ${assignment ? 'filled' : ''}`;

    if (assignment) {
      const guid = assignment.source_image_id || '';
      slot.innerHTML = `
        ${guid ? `<img src="/thumbs/${guid}.jpg" alt="${MONTH_LABELS[seq-1]}" loading="lazy">` : ''}
        <div class="slot-label">${MONTH_LABELS[seq - 1]}</div>
      `;
    } else {
      slot.innerHTML = `
        <div class="slot-label">${MONTH_LABELS[seq - 1]}</div>
        <div style="font-size:var(--fs-meta);color:var(--atlas-muted)">Empty</div>
      `;
    }

    container.appendChild(slot);
  }
}

async function updateScores(el) {
  if (!assignments.length) return;

  const body = {
    assignments: assignments.map(a => ({
      image_sk: a.image_sk,
      sequence_number: a.sequence_number,
    })),
  };

  try {
    const r = await fetch('/api/selection/score', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    scores = await r.json();

    const display = el.querySelector('.score-display');
    display.innerHTML = `
      <table class="score-table">
        <tbody>
          <tr><td>Objective</td><td>${scores.objective_score?.toFixed(3) ?? '—'}</td></tr>
          <tr><td>Popularity</td><td>${scores.popularity_score?.toFixed(3) ?? '—'}</td></tr>
          <tr><td>Diversity</td><td>${scores.diversity_score?.toFixed(3) ?? '—'}</td></tr>
          <tr><td>Month Fit</td><td>${scores.month_fit_score?.toFixed(3) ?? '—'}</td></tr>
          <tr><td>Cover Fit</td><td>${scores.cover_fit_score?.toFixed(3) ?? '—'}</td></tr>
          <tr><td>Redundancy</td><td>-${scores.redundancy_penalty?.toFixed(3) ?? '—'}</td></tr>
          <tr><td>Uncertainty</td><td>-${scores.uncertainty_penalty?.toFixed(3) ?? '—'}</td></tr>
        </tbody>
      </table>
    `;
  } catch (err) {
    const display = el.querySelector('.score-display');
    display.textContent = `Scoring error: ${err.message}`;
  }
}
