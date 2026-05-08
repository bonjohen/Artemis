/**
 * Image detail — used as a sub-module by the images page.
 * The detail overlay is rendered inline by images.js.
 * This module is reserved for future standalone detail view if needed.
 */

export async function render(el, hash) {
  const sk = hash.split('/').pop();
  const r = await fetch(`/api/images/${sk}`);
  if (!r.ok) {
    el.innerHTML = '<p>Image not found.</p>';
    return;
  }
  const d = await r.json();

  el.innerHTML = `
    <div class="page-header">
      <h1>${d.source_image_id}</h1>
      <a href="#/images" class="btn">Back to Images</a>
    </div>
    <div class="detail-grid">
      <div>
        <img src="https://pub-1f1ce68455c0432ea65ac3155a6b2409.r2.dev/thumbs/${d.source_image_id}.jpg" alt="Image ${d.image_sk}"
             style="border-radius:var(--r-md);width:100%">
      </div>
      <div>
        <table class="score-table">
          <thead><tr><th>Metric</th><th>Value</th></tr></thead>
          <tbody>
            <tr><td>Rank</td><td>#${d.rank || '—'}</td></tr>
            <tr><td>Preference</td><td>${d.preference_score?.toFixed(4) ?? '—'}</td></tr>
            <tr><td>Elo</td><td>${d.elo_score?.toFixed(1) ?? '—'}</td></tr>
            <tr><td>Borda</td><td>${d.borda_score?.toFixed(4) ?? '—'}</td></tr>
            <tr><td>Broad Appeal</td><td>${d.broad_appeal_score?.toFixed(4) ?? '—'}</td></tr>
            <tr><td>Uncertainty</td><td>${d.uncertainty_score?.toFixed(4) ?? '—'}</td></tr>
            <tr><td>Cluster</td><td>${d.cluster_id ?? '—'}</td></tr>
            <tr><td>Brightness</td><td>${d.brightness_score?.toFixed(4) ?? '—'}</td></tr>
            <tr><td>Contrast</td><td>${d.contrast_score?.toFixed(4) ?? '—'}</td></tr>
            <tr><td>Saturation</td><td>${d.saturation_score?.toFixed(4) ?? '—'}</td></tr>
          </tbody>
        </table>
        <p style="margin-top:var(--s-3);font-size:var(--fs-small)">
          Candidates: ${d.candidates.length
            ? d.candidates.map(c => `<a href="#/candidates/${c}">${c}</a>`).join(', ')
            : 'None'}
        </p>
      </div>
    </div>
  `;
}
