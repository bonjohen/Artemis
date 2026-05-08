/**
 * Selection builder page — method loader, drag-and-drop image pool,
 * 13-slot calendar grid with cover checkbox, live scoring.
 */

const MONTH_LABELS = [
  'December 2026', 'January 2027', 'February 2027', 'March 2027',
  'April 2027', 'May 2027', 'June 2027', 'July 2027',
  'August 2027', 'September 2027', 'October 2027', 'November 2027',
  'December 2027',
];

let assignments = new Array(13).fill(null); // index 0-12 → seq 1-13
let coverSeq = null; // sequence_number of cover image (1-13), or null
let scores = null;
let poolPage = 1;
let poolSort = 'score';
let poolCluster = null;

export async function render(el) {
  // Try loading from sessionStorage or saved selection
  const startingPoint = sessionStorage.getItem('selection_starting_point');
  if (startingPoint) {
    const loaded = JSON.parse(startingPoint);
    sessionStorage.removeItem('selection_starting_point');
    _applyAssignments(loaded);
  } else if (assignments.every(a => a === null)) {
    const r = await fetch('/api/selection?name=current');
    const data = await r.json();
    if (data.assignments?.length) _applyAssignments(data.assignments);
  }

  el.innerHTML = `
    <div class="page-header">
      <h1>Selection Builder</h1>
      <div class="controls">
        <label>Method
          <select class="method-select">
            <option value="">-- load method --</option>
          </select>
        </label>
        <label>Name
          <input type="text" class="name-input" placeholder="Selection name" value="current"
                 style="width:120px">
        </label>
        <button class="btn save-btn">Save</button>
        <button class="btn load-btn">Load</button>
        <button class="btn clear-btn">Clear All</button>
      </div>
    </div>
    <div class="sb-layout">
      <div class="sb-calendar-col">
        <h3 class="sb-section-title">Calendar Slots</h3>
        <div class="sb-slots"></div>
        <div class="sb-scores-inline">
          <h3 class="sb-section-title">Scores</h3>
          <div class="score-display">
            <p style="color:var(--atlas-muted);font-size:var(--fs-small)">
              Add images to see scores
            </p>
          </div>
        </div>
      </div>
      <div class="sb-pool-col">
        <h3 class="sb-section-title">Image Pool</h3>
        <div class="sb-pool-controls">
          <select class="pool-sort">
            <option value="score">By Score</option>
            <option value="brightness">By Brightness</option>
            <option value="cluster">By Cluster</option>
          </select>
          <select class="pool-cluster">
            <option value="">All Clusters</option>
          </select>
        </div>
        <div class="sb-pool-grid"></div>
        <div class="sb-pool-pagination"></div>
      </div>
    </div>
  `;

  // Populate method dropdown
  await _loadMethods(el);

  // Populate cluster dropdown
  await _loadClusters(el);

  // Render initial state
  _renderSlots(el);
  await _loadPool(el);

  if (assignments.some(a => a !== null)) await _updateScores(el);

  // --- Event handlers ---

  // Method select
  el.querySelector('.method-select').addEventListener('change', async (e) => {
    if (!e.target.value) return;
    const r = await fetch(`/api/candidates/${e.target.value}`);
    const data = await r.json();
    if (data.images?.length) {
      assignments = new Array(13).fill(null);
      coverSeq = null;
      for (const img of data.images) {
        assignments[img.sequence_number - 1] = {
          image_sk: img.image_sk,
          source_image_id: img.source_image_id,
          preference_score: img.preference_score,
          cluster_id: img.cluster_id,
        };
      }
      // Cover is sequence 1 by convention for loaded methods
      if (data.candidate?.cover_image_sk) {
        const idx = assignments.findIndex(a => a && a.image_sk === data.candidate.cover_image_sk);
        if (idx >= 0) coverSeq = idx + 1;
      }
      _renderSlots(el);
      await _updateScores(el);
    }
    e.target.value = '';
  });

  // Sort
  el.querySelector('.pool-sort').addEventListener('change', async (e) => {
    poolSort = e.target.value;
    poolPage = 1;
    await _loadPool(el);
  });

  // Cluster filter
  el.querySelector('.pool-cluster').addEventListener('change', async (e) => {
    poolCluster = e.target.value || null;
    poolPage = 1;
    await _loadPool(el);
  });

  // Save
  el.querySelector('.save-btn').addEventListener('click', async () => {
    const name = el.querySelector('.name-input').value || 'current';
    const body = {
      name,
      assignments: _serializeAssignments(),
      notes: coverSeq ? `cover_seq:${coverSeq}` : '',
    };
    await fetch('/api/selection', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const btn = el.querySelector('.save-btn');
    btn.textContent = 'Saved!';
    setTimeout(() => { btn.textContent = 'Save'; }, 1500);
  });

  // Load
  el.querySelector('.load-btn').addEventListener('click', async () => {
    const name = el.querySelector('.name-input').value || 'current';
    const r = await fetch(`/api/selection?name=${name}`);
    const data = await r.json();
    if (data.assignments?.length) {
      _applyAssignments(data.assignments);
      // Restore cover from notes
      if (data.notes && data.notes.startsWith('cover_seq:')) {
        coverSeq = parseInt(data.notes.split(':')[1], 10) || null;
      }
      _renderSlots(el);
      await _updateScores(el);
    }
  });

  // Clear
  el.querySelector('.clear-btn').addEventListener('click', () => {
    assignments = new Array(13).fill(null);
    coverSeq = null;
    scores = null;
    _renderSlots(el);
    el.querySelector('.score-display').innerHTML = `
      <p style="color:var(--atlas-muted);font-size:var(--fs-small)">
        Add images to see scores
      </p>`;
  });
}


// --- Data helpers ---

function _applyAssignments(list) {
  assignments = new Array(13).fill(null);
  for (const a of list) {
    const idx = a.sequence_number - 1;
    if (idx >= 0 && idx < 13) {
      assignments[idx] = {
        image_sk: a.image_sk,
        source_image_id: a.source_image_id || a.guid || null,
        preference_score: a.preference_score ?? null,
        cluster_id: a.cluster_id ?? null,
      };
    }
  }
}

function _serializeAssignments() {
  const result = [];
  for (let i = 0; i < 13; i++) {
    if (assignments[i]) {
      result.push({ image_sk: assignments[i].image_sk, sequence_number: i + 1 });
    }
  }
  return result;
}


// --- Methods dropdown ---

async function _loadMethods(el) {
  const select = el.querySelector('.method-select');
  try {
    const r = await fetch('/api/candidates');
    const candidates = await r.json();
    const labels = {
      method_a: 'A: Top Popularity',
      method_b: 'B: Cluster-Limited',
      method_c: 'C: Per Cluster',
      method_d: 'D: Month First',
      method_e: 'E: MMR Greedy',
    };
    for (const c of candidates) {
      const opt = document.createElement('option');
      opt.value = c.candidate_name;
      opt.textContent = labels[c.candidate_name] || c.candidate_name;
      select.appendChild(opt);
    }
  } catch { /* candidates not available */ }
}


// --- Clusters dropdown ---

async function _loadClusters(el) {
  const select = el.querySelector('.pool-cluster');
  try {
    const r = await fetch('/api/clusters');
    const clusters = await r.json();
    for (const c of clusters) {
      const opt = document.createElement('option');
      opt.value = c.cluster_id;
      opt.textContent = `Cluster ${c.cluster_id} (${c.image_count})`;
      select.appendChild(opt);
    }
  } catch { /* clusters not available */ }
}


// --- Slots rendering ---

function _renderSlots(el) {
  const container = el.querySelector('.sb-slots');
  container.innerHTML = '';

  for (let seq = 1; seq <= 13; seq++) {
    const a = assignments[seq - 1];
    const slot = document.createElement('div');
    slot.className = `sb-slot ${a ? 'filled' : ''}`;
    slot.dataset.seq = seq;

    // Drop target
    slot.addEventListener('dragover', (e) => { e.preventDefault(); slot.classList.add('drag-over'); });
    slot.addEventListener('dragleave', () => { slot.classList.remove('drag-over'); });
    slot.addEventListener('drop', async (e) => {
      e.preventDefault();
      slot.classList.remove('drag-over');
      try {
        const data = JSON.parse(e.dataTransfer.getData('text/plain'));
        // Remove this image from any other slot
        for (let i = 0; i < 13; i++) {
          if (assignments[i] && assignments[i].image_sk === data.image_sk) {
            assignments[i] = null;
            if (coverSeq === i + 1) coverSeq = null;
          }
        }
        assignments[seq - 1] = data;
        _renderSlots(el);
        await _updateScores(el);
      } catch { /* bad data */ }
    });

    if (a) {
      const guid = a.source_image_id || '';
      const isCover = coverSeq === seq;
      slot.innerHTML = `
        <div class="sb-slot-img-wrap">
          ${guid ? `<img src="/thumbs/${guid}.jpg" alt="${MONTH_LABELS[seq-1]}" loading="lazy"
                         draggable="true" data-sk="${a.image_sk}">` : ''}
          <button class="sb-slot-remove" title="Remove">&times;</button>
        </div>
        <div class="sb-slot-footer">
          <span class="sb-slot-label">${MONTH_LABELS[seq - 1]}</span>
          <label class="sb-cover-check">
            <input type="checkbox" name="cover" ${isCover ? 'checked' : ''}>
            <span class="sb-cover-text">${isCover ? 'Cover' : 'Cover'}</span>
          </label>
        </div>
      `;

      // Allow re-dragging from slot
      const img = slot.querySelector('img');
      if (img) {
        img.addEventListener('dragstart', (e) => {
          e.dataTransfer.setData('text/plain', JSON.stringify(a));
          e.dataTransfer.effectAllowed = 'move';
        });
      }

      // Remove button
      slot.querySelector('.sb-slot-remove').addEventListener('click', async () => {
        assignments[seq - 1] = null;
        if (coverSeq === seq) coverSeq = null;
        _renderSlots(el);
        await _updateScores(el);
      });

      // Cover checkbox — radio-like behavior (at most one)
      slot.querySelector('input[name="cover"]').addEventListener('change', (e) => {
        if (e.target.checked) {
          coverSeq = seq;
        } else {
          coverSeq = null;
        }
        // Re-render to uncheck others
        _renderSlots(el);
      });
    } else {
      slot.innerHTML = `
        <div class="sb-slot-empty">Drop image here</div>
        <div class="sb-slot-footer">
          <span class="sb-slot-label">${MONTH_LABELS[seq - 1]}</span>
        </div>
      `;
    }

    container.appendChild(slot);
  }
}


// --- Image pool ---

async function _loadPool(el) {
  const grid = el.querySelector('.sb-pool-grid');
  const pag = el.querySelector('.sb-pool-pagination');
  grid.innerHTML = '<div class="loading">Loading...</div>';

  let url = `/api/images?page=${poolPage}&per_page=48&sort=${poolSort}`;
  if (poolCluster) url += `&cluster_id=${poolCluster}`;

  const r = await fetch(url);
  const data = await r.json();

  grid.innerHTML = '';

  // Track assigned image_sks for dimming
  const assignedSks = new Set(assignments.filter(Boolean).map(a => a.image_sk));

  for (const img of data.items) {
    const card = document.createElement('div');
    card.className = `sb-pool-card ${assignedSks.has(img.image_sk) ? 'assigned' : ''}`;
    card.draggable = true;
    card.innerHTML = `
      <img src="/thumbs/${img.source_image_id}.jpg" alt="Image ${img.image_sk}" loading="lazy">
      <div class="sb-pool-info">
        <span class="sb-pool-score">${img.preference_score?.toFixed(2) ?? '—'}</span>
        ${img.cluster_id != null ? `<span class="sb-pool-cluster">C${img.cluster_id}</span>` : ''}
      </div>
    `;

    const dragData = {
      image_sk: img.image_sk,
      source_image_id: img.source_image_id,
      preference_score: img.preference_score,
      cluster_id: img.cluster_id,
    };

    card.addEventListener('dragstart', (e) => {
      e.dataTransfer.setData('text/plain', JSON.stringify(dragData));
      e.dataTransfer.effectAllowed = 'copy';
      card.classList.add('dragging');
    });
    card.addEventListener('dragend', () => { card.classList.remove('dragging'); });

    grid.appendChild(card);
  }

  // Pagination
  pag.innerHTML = '';
  if (data.pages > 1) {
    const prev = document.createElement('button');
    prev.className = 'btn';
    prev.textContent = 'Prev';
    prev.disabled = poolPage <= 1;
    prev.addEventListener('click', async () => { poolPage--; await _loadPool(el); });

    const info = document.createElement('span');
    info.className = 'sb-pool-page-info';
    info.textContent = `${poolPage} / ${data.pages}`;

    const next = document.createElement('button');
    next.className = 'btn';
    next.textContent = 'Next';
    next.disabled = poolPage >= data.pages;
    next.addEventListener('click', async () => { poolPage++; await _loadPool(el); });

    pag.append(prev, info, next);
  }
}


// --- Scoring ---

async function _updateScores(el) {
  const filled = _serializeAssignments();
  const display = el.querySelector('.score-display');

  if (!filled.length) {
    display.innerHTML = `
      <p style="color:var(--atlas-muted);font-size:var(--fs-small)">
        Add images to see scores
      </p>`;
    return;
  }

  display.innerHTML = `<p style="color:var(--atlas-muted);font-size:var(--fs-small)">Scoring...</p>`;

  try {
    const r = await fetch('/api/selection/score', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ assignments: filled }),
    });
    scores = await r.json();

    display.innerHTML = `
      <table class="score-table">
        <tbody>
          <tr><td>Objective</td><td><strong>${scores.objective_score?.toFixed(3) ?? '—'}</strong></td></tr>
          <tr><td>Popularity</td><td>${scores.popularity_score?.toFixed(3) ?? '—'}</td></tr>
          <tr><td>Diversity</td><td>${scores.diversity_score?.toFixed(3) ?? '—'}</td></tr>
          <tr><td>Month Fit</td><td>${scores.month_fit_score?.toFixed(3) ?? '—'}</td></tr>
          <tr><td>Cover Fit</td><td>${scores.cover_fit_score?.toFixed(3) ?? '—'}</td></tr>
          <tr><td>Redundancy</td><td>-${scores.redundancy_penalty?.toFixed(3) ?? '—'}</td></tr>
          <tr><td>Uncertainty</td><td>-${scores.uncertainty_penalty?.toFixed(3) ?? '—'}</td></tr>
          <tr><td>Filled</td><td>${filled.length} / 13</td></tr>
        </tbody>
      </table>
    `;
  } catch (err) {
    display.innerHTML = `<p style="color:var(--atlas-muted);font-size:var(--fs-small)">Scoring error: ${err.message}</p>`;
  }

  // Refresh pool to update assigned state
  await _loadPool(el);
}
