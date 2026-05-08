/**
 * Lessons page — card grid listing + detail view with markdown rendering.
 */

const BLOCKS = [
  { id: 'block1', title: 'Block 1 — Infrastructure & Scaling' },
  { id: 'block2', title: 'Block 2 — Statistical Methods' },
  { id: 'block3', title: 'Block 3 — Calendar Optimization' },
  { id: 'block4', title: 'Block 4 — Synthetic Validation' },
  { id: 'block5', title: 'Block 5 — Web App & Interactive Tooling' },
];

const CATEGORIES = {
  eng: 'Engineering',
  data: 'Data',
  stats: 'Statistics',
  arch: 'Architecture',
  process: 'Process',
};

export async function render(el, hash) {
  const parts = hash.replace(/\?.*/, '').split('/');
  // #/lessons/block1/some_file → parts = ['', 'lessons', 'block1', 'some_file']
  if (parts.length >= 4 && parts[2] && parts[3]) {
    await renderDetail(el, parts[2], parts[3]);
  } else {
    await renderList(el);
  }
}

async function renderList(el) {
  const resp = await fetch('/api/lessons');
  const lessons = await resp.json();

  let activeFilter = 'all';

  function renderCards() {
    const filtered = activeFilter === 'all'
      ? lessons
      : lessons.filter(l => l.category === activeFilter);

    let html = `
      <header style="margin-bottom:var(--s-6)">
        <h1 class="h2">Lessons Learned</h1>
        <p style="color:var(--atlas-ink-2);max-width:56ch;margin-top:var(--s-2)">
          Patterns, mistakes, and decisions from building the Artemis II calendar image selection pipeline.
        </p>
      </header>
      <div style="display:flex;gap:var(--s-2);flex-wrap:wrap;margin-bottom:var(--s-5)">
        <button class="filter-btn ${activeFilter === 'all' ? 'active' : ''}" data-cat="all">All (${lessons.length})</button>
    `;
    for (const [key, label] of Object.entries(CATEGORIES)) {
      const count = lessons.filter(l => l.category === key).length;
      if (count > 0) {
        html += `<button class="filter-btn ${activeFilter === key ? 'active' : ''}" data-cat="${key}">${label} (${count})</button>`;
      }
    }
    html += '</div>';

    for (const block of BLOCKS) {
      const blockLessons = filtered.filter(l => l.block === block.id);
      if (blockLessons.length === 0) continue;

      html += `
        <h2 class="h3" style="margin:var(--s-6) 0 var(--s-4)">${block.title}</h2>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:var(--s-4)">
      `;
      for (const lesson of blockLessons) {
        const catLabel = CATEGORIES[lesson.category] || lesson.category;
        html += `
          <a href="#/lessons/${lesson.block}/${lesson.file}" class="card" style="display:flex;flex-direction:column;padding:var(--s-5);border:1px solid var(--atlas-rule-soft);border-radius:var(--r-md);text-decoration:none;color:inherit;min-height:160px;transition:background var(--t-fast),border-color var(--t-fast)">
            <div style="display:flex;justify-content:space-between;margin-bottom:var(--s-3)">
              <span style="font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--atlas-accent);font-weight:600">Lesson ${lesson.number}</span>
              <span style="font-family:var(--mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--atlas-muted);padding:2px 8px;border:1px solid var(--atlas-rule-soft);border-radius:var(--r-pill)">${catLabel}</span>
            </div>
            <div style="font-family:var(--serif);font-size:18px;font-weight:500;line-height:1.3;margin-bottom:6px">${lesson.title}</div>
            <div style="font-size:12px;line-height:1.5;color:var(--atlas-ink-2);flex:1">${lesson.description}</div>
          </a>
        `;
      }
      html += '</div>';
    }

    el.innerHTML = html;

    el.querySelectorAll('.filter-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        activeFilter = btn.dataset.cat;
        renderCards();
      });
    });
  }

  renderCards();
}

async function renderDetail(el, block, file) {
  el.innerHTML = '<div class="loading">Loading lesson...</div>';

  try {
    const resp = await fetch(`/api/lessons/${block}/${file}`);
    const data = await resp.json();

    if (data.error) {
      el.innerHTML = `<p>${data.error}. <a href="#/lessons">Back to lessons</a></p>`;
      return;
    }

    // Dynamically import marked for markdown rendering
    const { marked } = await import('https://esm.sh/marked@15.0.4');

    // Rewrite relative .md links to SPA lesson links
    let md = data.content;
    md = md.replace(
      /\[([^\]]+)\]\((\d{2,3}[^)]+)\.md\)/g,
      (_, text, linkedFile) => `[${text}](#/lessons/${block}/${linkedFile})`
    );

    const rendered = marked.parse(md);

    el.innerHTML = `
      <div class="lesson-detail">
        <div style="margin-bottom:var(--s-5)">
          <a href="#/lessons" style="font-family:var(--mono);font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--atlas-muted);text-decoration:none">&larr; All Lessons</a>
        </div>
        <article class="lesson-body">${rendered}</article>
      </div>
    `;

    // Update page title
    const h1 = el.querySelector('.lesson-body h1');
    if (h1) document.title = h1.textContent + ' — Artemis';
  } catch (e) {
    el.textContent = `Error loading lesson: ${e.message}`;
  }
}
