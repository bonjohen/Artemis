/**
 * Context block component — "Why this page matters" explanation.
 * Returns an HTML string for interpolation into page templates.
 */

export function renderContextBlock(title, text) {
  return `
    <div class="context-block">
      <p class="context-block-title">${title}</p>
      <p class="context-block-text">${text}</p>
    </div>
  `;
}
