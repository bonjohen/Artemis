/**
 * Reusable image card component.
 * Renders a thumbnail with score badge and cluster pill.
 */

export function createImageCard(image, onClick) {
  const card = document.createElement('div');
  card.className = 'image-card';
  card.addEventListener('click', () => onClick(image));

  const score = image.preference_score != null
    ? image.preference_score.toFixed(3)
    : '—';

  card.innerHTML = `
    <img src="/thumbs/${image.source_image_id}.jpg"
         alt="Image ${image.image_sk}"
         loading="lazy">
    <span class="score-badge">${score}</span>
    <div class="card-info">
      ${image.cluster_id != null
        ? `<span class="cluster-pill">C${image.cluster_id}</span>`
        : ''}
    </div>
  `;
  return card;
}
