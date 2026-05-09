/**
 * Vote Simulator — configure attribute-biased voting blocks,
 * run in-memory simulation, compare per-block top-13 vs blended result,
 * and inspect individual sample ballots to see how bias shapes selections.
 */

import { showImageDetail } from '../components/image-detail.js';

const SCENARIO_PRESETS = {
  balanced:       { label: 'Balanced (all 10)',  values: { earth_moon: 10, earth_only: 10, moon_only: 10, sun_only: 10, crescent: 10, eclipse: 10, crew: 10, equipment: 10, moon_sun: 10, neutral: 10 } },
  celestial:      { label: 'Celestial Focus',    values: { earth_moon: 20, earth_only: 15, moon_only: 20, sun_only: 10, crescent: 20, eclipse: 10, crew: 0, equipment: 0, moon_sun: 5, neutral: 10 } },
  human:          { label: 'Human Interest',     values: { earth_moon: 0, earth_only: 5, moon_only: 0, sun_only: 0, crescent: 0, eclipse: 0, crew: 40, equipment: 40, moon_sun: 0, neutral: 15 } },
  dramatic:       { label: 'Dramatic Shots',     values: { earth_moon: 15, earth_only: 0, moon_only: 0, sun_only: 10, crescent: 30, eclipse: 25, crew: 0, equipment: 0, moon_sun: 10, neutral: 10 } },
  neutral_only:   { label: 'Neutral Only',       values: { earth_moon: 0, earth_only: 0, moon_only: 0, sun_only: 0, crescent: 0, eclipse: 0, crew: 0, equipment: 0, moon_sun: 0, neutral: 100 } },
};

// Embedded presets — renders without API so GitHub Pages shows the UI
const DEFAULT_BLOCKS = [
  { block_id: 'earth_moon', label: 'Earth+Moon Fans', description: 'Prefer images showing both Earth and Moon together', voter_count: 10, votes_per_voter: 10, preference_weight: 3.0, randomness_weight: 0.5, preference_rules: { all_of: ['earth', 'moon'], any_of: [], none_of: [] } },
  { block_id: 'earth_only', label: 'Earth Only', description: 'Prefer Earth views without Moon or Sun', voter_count: 10, votes_per_voter: 10, preference_weight: 3.0, randomness_weight: 0.5, preference_rules: { all_of: ['earth'], any_of: [], none_of: ['moon', 'sun'] } },
  { block_id: 'moon_only', label: 'Moon Only', description: 'Prefer Moon views without Earth or Sun', voter_count: 10, votes_per_voter: 10, preference_weight: 3.0, randomness_weight: 0.5, preference_rules: { all_of: ['moon'], any_of: [], none_of: ['earth', 'sun'] } },
  { block_id: 'sun_only', label: 'Sun Only', description: 'Prefer images featuring the Sun without Earth or Moon', voter_count: 10, votes_per_voter: 10, preference_weight: 3.0, randomness_weight: 0.5, preference_rules: { all_of: ['sun'], any_of: [], none_of: ['earth', 'moon'] } },
  { block_id: 'crescent', label: 'Crescent Fans', description: 'Prefer crescent shapes — crescent Moon or crescent Earth', voter_count: 10, votes_per_voter: 10, preference_weight: 3.0, randomness_weight: 0.5, preference_rules: { all_of: [], any_of: ['crescent_moon', 'crescent_earth'], none_of: [] } },
  { block_id: 'eclipse', label: 'Eclipse / Sun+Moon', description: 'Prefer images with Sun and Moon together, or Sun with lens flare', voter_count: 10, votes_per_voter: 10, preference_weight: 3.0, randomness_weight: 0.5, preference_rules: { all_of: [], any_of: ['sun', 'lens_flare'], none_of: [] } },
  { block_id: 'crew', label: 'Crew / People', description: 'Prefer images showing astronauts, crew, hands, or selfies', voter_count: 10, votes_per_voter: 10, preference_weight: 3.0, randomness_weight: 0.5, preference_rules: { all_of: [], any_of: ['astronaut', 'crew', 'hand', 'selfie'], none_of: [] } },
  { block_id: 'equipment', label: 'Equipment / Hardware', description: 'Prefer images of spacecraft, vehicles, habitat, or interior views', voter_count: 10, votes_per_voter: 10, preference_weight: 3.0, randomness_weight: 0.5, preference_rules: { all_of: [], any_of: ['spacecraft', 'vehicle', 'habitat', 'interior', 'porthole'], none_of: [] } },
  { block_id: 'moon_sun', label: 'Moon+Sun Fans', description: 'Prefer images showing Moon and Sun together', voter_count: 10, votes_per_voter: 10, preference_weight: 3.0, randomness_weight: 0.5, preference_rules: { all_of: ['moon', 'sun'], any_of: [], none_of: [] } },
  { block_id: 'neutral', label: 'Neutral', description: 'No attribute preference — votes by general appeal + noise', voter_count: 10, votes_per_voter: 10, preference_weight: 0.0, randomness_weight: 1.0, preference_rules: { all_of: [], any_of: [], none_of: [] } },
];

let presets = null;
let lastResult = null;

export async function render(el) {
  // Try API first, fall back to embedded defaults
  presets = await fetch('/api/blend/presets').then(r => {
    if (!r.ok) throw new Error(r.status);
    return r.json();
  }).catch(() => ({ blocks: DEFAULT_BLOCKS, attributes: [] }));

  el.innerHTML = `
    <div class="page-header">
      <h1>Vote Simulator</h1>
      <div class="controls">
        <label>Scenario
          <select class="scenario-select">
            <option value="">Custom</option>
            ${Object.entries(SCENARIO_PRESETS).map(([k, v]) =>
              `<option value="${k}">${v.label}</option>`
            ).join('')}
          </select>
        </label>
        <label>Seed
          <input type="number" class="seed-input" value="42" min="1" max="99999" style="width:70px">
        </label>
        <button class="btn run-btn">Run Simulation</button>
      </div>
    </div>

    <details class="blend-explainer" open>
      <summary>How this works</summary>
      <p>Each <strong>voter block</strong> represents a group of voters who prefer certain image attributes.
      When you run a simulation, each voter is shown 50 random images and picks their top 5.
      Biased voters score images higher when they match the block's attribute rules —
      so "Earth+Moon Fans" will disproportionately select images tagged with both <code>earth</code> and <code>moon</code>.</p>
      <p>The <strong>blended result</strong> combines all voters' picks. Adjust the voter counts to see how
      different electorate compositions change which images rise to the top.</p>
      <p>Expand <strong>Sample Ballots</strong> below the results to see exactly what individual voters saw and chose.</p>
    </details>

    <div class="blend-config" id="blend-config"></div>
    <div class="blend-summary" id="blend-summary"></div>
    <div class="blend-results" id="blend-results"></div>
    <div class="blend-ballots" id="blend-ballots"></div>
  `;

  renderBlockCards(el);
  bindEvents(el);
}

function renderBlockCards(el) {
  const container = el.querySelector('#blend-config');
  container.innerHTML = presets.blocks.map(b => `
    <div class="blend-block-card" data-block="${b.block_id}">
      <div class="blend-block-header">
        <strong>${b.label}</strong>
        <span class="blend-block-desc">${b.description}</span>
      </div>
      <div class="blend-block-rules">
        ${formatRules(b.preference_rules)}
      </div>
      <div class="blend-slider-row">
        <label>Voters: <span class="voter-val">${b.voter_count}</span></label>
        <input type="range" class="voter-slider" data-block="${b.block_id}"
               min="0" max="100" value="${b.voter_count}" step="5">
      </div>
      <div class="blend-weights">
        <span>Pref weight: ${b.preference_weight}</span>
        <span>Noise: ${b.randomness_weight}</span>
      </div>
    </div>
  `).join('');
}

function formatRules(rules) {
  const parts = [];
  if (rules.all_of?.length) parts.push(`<span class="rule-tag rule-all">ALL: ${rules.all_of.join(', ')}</span>`);
  if (rules.any_of?.length) parts.push(`<span class="rule-tag rule-any">ANY: ${rules.any_of.join(', ')}</span>`);
  if (rules.none_of?.length) parts.push(`<span class="rule-tag rule-none">NONE: ${rules.none_of.join(', ')}</span>`);
  return parts.length ? parts.join(' ') : '<span class="rule-tag rule-neutral">No attribute bias</span>';
}

function bindEvents(el) {
  el.querySelectorAll('.voter-slider').forEach(slider => {
    slider.addEventListener('input', () => {
      slider.closest('.blend-block-card').querySelector('.voter-val').textContent = slider.value;
      el.querySelector('.scenario-select').value = '';
    });
  });

  el.querySelector('.scenario-select').addEventListener('change', (e) => {
    const key = e.target.value;
    if (!key) return;
    const preset = SCENARIO_PRESETS[key];
    Object.entries(preset.values).forEach(([blockId, count]) => {
      const slider = el.querySelector(`.voter-slider[data-block="${blockId}"]`);
      if (slider) {
        slider.value = count;
        slider.closest('.blend-block-card').querySelector('.voter-val').textContent = count;
      }
    });
  });

  el.querySelector('.run-btn').addEventListener('click', () => runSimulation(el));
}

async function runSimulation(el) {
  const btn = el.querySelector('.run-btn');
  const resultsEl = el.querySelector('#blend-results');
  const summaryEl = el.querySelector('#blend-summary');
  const ballotsEl = el.querySelector('#blend-ballots');

  const blocks = presets.blocks.map(b => {
    const slider = el.querySelector(`.voter-slider[data-block="${b.block_id}"]`);
    return {
      block_id: b.block_id,
      label: b.label,
      voter_count: parseInt(slider?.value || '0'),
      votes_per_voter: b.votes_per_voter,
      preference_weight: b.preference_weight,
      randomness_weight: b.randomness_weight,
      preference_rules: b.preference_rules,
    };
  });

  const seed = parseInt(el.querySelector('.seed-input').value) || 42;

  btn.disabled = true;
  btn.textContent = 'Simulating...';
  resultsEl.innerHTML = '<div class="loading">Running simulation...</div>';
  summaryEl.innerHTML = '';
  ballotsEl.innerHTML = '';

  try {
    const resp = await fetch('/api/blend/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ blocks, seed }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || resp.statusText);
    }

    lastResult = await resp.json();
    renderSummary(summaryEl, lastResult);
    renderResults(resultsEl, lastResult);
    renderSampleBallots(ballotsEl, lastResult);
  } catch (err) {
    const isOffline = err.message.includes('Failed to fetch') || err.message.includes('404') || err.message.includes('Internal Server Error');
    resultsEl.innerHTML = isOffline
      ? `<div class="blend-offline-msg">
           <strong>Simulation requires the local server</strong>
           <p>The vote simulator runs in-memory on the backend and is only available when the Artemis server is running locally on port 8070.</p>
           <p>The block configuration UI above shows the available voter types and their attribute bias rules.</p>
         </div>`
      : `<p class="error">Simulation failed: ${err.message}</p>`;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Run Simulation';
  }
}

function renderSummary(el, data) {
  const activeBlocks = data.blocks.filter(b => b.voter_count > 0);
  el.innerHTML = `
    <div class="blend-summary-bar">
      <span><strong>${data.total_voters}</strong> voters</span>
      <span><strong>${data.total_ballots}</strong> ballots</span>
      <span><strong>${data.eligible_images?.toLocaleString() || '?'}</strong> eligible images</span>
      <span><strong>${activeBlocks.length}</strong> active blocks</span>
      <span>Seed: <strong>${data.seed}</strong></span>
      <span title="Min CLIP confidence for attribute labels">Conf &ge; ${(data.min_confidence || 0.9).toFixed(2)}</span>
      <span title="Exclude images with this % or more dark pixels">Dark &lt; ${((data.max_dark_ratio || 0.92) * 100).toFixed(0)}%</span>
    </div>
  `;
}

function renderResults(el, data) {
  const blendedSet = new Set(data.blended.map(img => img.image_sk));

  const imageCounts = {};
  const allColumns = [...data.blocks, { block_id: '_blended', top_13: data.blended }];
  for (const col of allColumns) {
    for (const img of col.top_13) {
      imageCounts[img.image_sk] = (imageCounts[img.image_sk] || 0) + 1;
    }
  }

  const columns = data.blocks.map(b =>
    renderColumn(b.label, `${b.voter_count} voters, ${b.ballot_count} ballots`, b.top_13, blendedSet, imageCounts)
  );
  columns.push(
    renderColumn('Blended Result', `${data.total_voters} voters combined`, data.blended, blendedSet, imageCounts, true)
  );

  el.innerHTML = `
    <h2 class="blend-section-title">Top 13 Per Block vs Blended</h2>
    <div class="blend-columns">${columns.join('')}</div>
  `;

  el.querySelectorAll('.blend-thumb').forEach(thumb => {
    thumb.addEventListener('click', () => showImageDetail(parseInt(thumb.dataset.sk)));
  });
}

function renderColumn(title, subtitle, images, blendedSet, imageCounts, isBlended = false) {
  const items = images.map((img, i) => {
    const inBlended = blendedSet.has(img.image_sk);
    const count = imageCounts[img.image_sk] || 1;
    const overlapClass = count > 1 ? `blend-overlap-${Math.min(count, 4)}` : '';
    const blendedMark = !isBlended && inBlended ? ' blend-in-blended' : '';
    const rate = (img.selection_rate * 100).toFixed(1);

    return `
      <div class="blend-thumb ${overlapClass}${blendedMark}" data-sk="${img.image_sk}" title="SK ${img.image_sk} — selected ${img.selection_count}/${img.shown_count} times shown">
        <span class="blend-rank">${i + 1}</span>
        <img src="/thumbs/${img.nasa_id}.jpg" alt="${img.nasa_id}" loading="lazy">
        <div class="blend-rate-bar">
          <div class="blend-rate-fill" style="width:${Math.min(rate, 100)}%"></div>
        </div>
        <span class="blend-rate-label">${rate}%</span>
      </div>
    `;
  }).join('');

  return `
    <div class="blend-column ${isBlended ? 'blend-column-blended' : ''}">
      <div class="blend-column-header">
        <strong>${title}</strong>
        <span>${subtitle}</span>
      </div>
      ${items}
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Sample Ballots — show representative voter records
// ---------------------------------------------------------------------------

function renderSampleBallots(el, data) {
  const allBallots = data.blocks.flatMap(b => b.sample_ballots || []);
  if (!allBallots.length) {
    el.innerHTML = '';
    return;
  }

  const blockLabels = {};
  for (const b of data.blocks) blockLabels[b.block_id] = b.label;

  const accordions = allBallots.map(ballot => {
    const selected = ballot.images.filter(img => img.was_selected);
    const notSelected = ballot.images.filter(img => !img.was_selected);

    return `
      <details class="ballot-detail">
        <summary class="ballot-summary">
          <strong>${blockLabels[ballot.block_id] || ballot.block_id}</strong>
          — Voter #${ballot.voter_number}, Ballot #${ballot.ballot_number}
          <span class="ballot-meta">Shown ${ballot.images.length} images, selected ${selected.length}</span>
        </summary>
        <div class="ballot-body">
          <div class="ballot-section">
            <h4 class="ballot-section-title">Selected (top ${selected.length} by utility score)</h4>
            <p class="ballot-section-desc">These images scored highest for this voter. The utility combines base appeal, attribute match, and random noise.</p>
            <div class="ballot-grid ballot-grid-selected">
              ${selected.map(img => renderBallotImage(img, true)).join('')}
            </div>
          </div>
          <div class="ballot-section">
            <h4 class="ballot-section-title">Not Selected (${notSelected.length} remaining)</h4>
            <p class="ballot-section-desc">These images were shown but scored lower. Notice the attribute match scores — biased voters systematically rank non-matching images lower.</p>
            <div class="ballot-grid ballot-grid-rejected">
              ${notSelected.map(img => renderBallotImage(img, false)).join('')}
            </div>
          </div>
        </div>
      </details>
    `;
  }).join('');

  el.innerHTML = `
    <h2 class="blend-section-title">Sample Ballots</h2>
    <p class="blend-section-desc">Each ballot below is one voter's actual decision: 50 random images shown, 5 selected. Expand to see <em>why</em> each image was or wasn't chosen.</p>
    ${accordions}
  `;

  el.querySelectorAll('.ballot-img').forEach(img => {
    img.addEventListener('click', () => showImageDetail(parseInt(img.dataset.sk)));
  });
}

function renderBallotImage(img, isSelected) {
  const matchBadges = img.matched_attrs.length
    ? img.matched_attrs.map(a => `<span class="ballot-attr-tag">${a}</span>`).join('')
    : '<span class="ballot-attr-none">no match</span>';

  return `
    <div class="ballot-img ${isSelected ? 'ballot-img-selected' : ''}" data-sk="${img.image_sk}">
      <img src="/thumbs/${img.nasa_id}.jpg" alt="${img.nasa_id}" loading="lazy">
      <div class="ballot-img-scores">
        <div class="ballot-score-row">
          <span class="ballot-score-label">Utility</span>
          <span class="ballot-score-val">${img.utility.toFixed(3)}</span>
        </div>
        <div class="ballot-score-row">
          <span class="ballot-score-label">Attr match</span>
          <span class="ballot-score-val">${img.attribute_match.toFixed(2)}</span>
        </div>
        <div class="ballot-score-row">
          <span class="ballot-score-label">Base appeal</span>
          <span class="ballot-score-val">${img.base_appeal.toFixed(3)}</span>
        </div>
        <div class="ballot-attrs">${matchBadges}</div>
      </div>
    </div>
  `;
}
