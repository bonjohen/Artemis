/**
 * Shared image detail modal — reusable across all pages.
 * Call showImageDetail(image_sk) from any page to open the modal.
 */

export function showImageDetail(imageSk) {
  fetch(`/api/images/${imageSk}`)
    .then(r => r.json())
    .then(detail => {
      if (detail.detail) return; // error response

      const overlay = document.createElement('div');
      overlay.className = 'modal-overlay';
      overlay.addEventListener('click', e => {
        if (e.target === overlay) overlay.remove();
      });

      const scoreRows = [
        ['Preference', detail.preference_score],
        ['Elo', detail.elo_score],
        ['Borda', detail.borda_score],
        ['Broad Appeal', detail.broad_appeal_score],
        ['Uncertainty', detail.uncertainty_score],
        ['Brightness', detail.brightness_score],
        ['Contrast', detail.contrast_score],
        ['Saturation', detail.saturation_score],
      ].filter(([, v]) => v != null)
        .map(([k, v]) => `<tr><td>${k}</td><td>${v.toFixed(4)}</td></tr>`)
        .join('');

      const candidateList = detail.candidates?.length
        ? detail.candidates.map(c =>
            `<a href="#/candidates/${c}">${c}</a>`
          ).join(', ')
        : 'None';

      const clusterLink = detail.cluster_id != null
        ? `<a href="#/clusters/${detail.cluster_id}" class="cluster-pill">Cluster ${detail.cluster_id}</a>`
        : '';

      overlay.innerHTML = `
        <div class="modal-content">
          <button class="modal-close" aria-label="Close">&times;</button>
          <div class="detail-grid">
            <div>
              <img src="/thumbs/${detail.source_image_id}.jpg"
                   alt="Image ${detail.image_sk}">
            </div>
            <div>
              <h2 style="font-family:var(--mono);font-size:var(--fs-body);margin:0 0 var(--s-2)">
                #${detail.rank || '—'} &middot; ${detail.source_image_id}
              </h2>
              ${clusterLink}
              <table class="score-table" style="margin-top:var(--s-3)">
                <thead><tr><th>Metric</th><th>Value</th></tr></thead>
                <tbody>${scoreRows}</tbody>
              </table>
              <p style="margin-top:var(--s-3);font-size:var(--fs-small);color:var(--atlas-muted)">
                Candidates: ${candidateList}
              </p>
            </div>
          </div>
        </div>
      `;

      overlay.querySelector('.modal-close').addEventListener('click', () => overlay.remove());
      document.addEventListener('keydown', function handler(e) {
        if (e.key === 'Escape') {
          overlay.remove();
          document.removeEventListener('keydown', handler);
        }
      });

      document.body.appendChild(overlay);
    });
}
