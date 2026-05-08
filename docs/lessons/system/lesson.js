import { marked } from 'https://esm.sh/marked@15.0.4';
import DOMPurify from 'https://esm.sh/dompurify';

const THEME_KEY = 'artemis:theme';
const savedTheme = localStorage.getItem(THEME_KEY);
if (savedTheme) document.documentElement.setAttribute('data-theme', savedTheme);
document.getElementById('theme-toggle').addEventListener('click', () => {
  const cur = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  const next = cur === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem(THEME_KEY, next);
});

const params = new URLSearchParams(window.location.search);
const lesson = params.get('lesson');
const container = document.getElementById('lesson-content');

if (!lesson) {
  container.innerHTML = '<p class="lesson-error">No lesson specified. <a href="lessons.html">Browse all lessons</a>.</p>';
} else {
  const path = `${lesson}.md`;
  try {
    const resp = await fetch(path);
    if (!resp.ok) throw new Error(`${resp.status}`);
    let md = await resp.text();

    // Rewrite relative .md links to lesson viewer links
    md = md.replace(/\[([^\]]+)\]\((\d{2,3}[^)]+)\.md\)/g,
      (_, text, file) => {
        // Determine the block from the current lesson path
        const block = lesson.split('/')[0];
        return `[${text}](lesson.html?lesson=${block}/${file})`;
      });

    container.innerHTML = DOMPurify.sanitize(marked.parse(md));
    const h1 = container.querySelector('h1');
    if (h1) document.title = h1.textContent + ' — Artemis';
  } catch (e) {
    container.textContent = '';
    const p = document.createElement('p');
    p.className = 'lesson-error';
    p.textContent = 'Could not load lesson "' + lesson + '". ';
    const a = document.createElement('a');
    a.href = 'lessons.html';
    a.textContent = 'Browse all lessons';
    p.appendChild(a);
    p.appendChild(document.createTextNode('.'));
    container.appendChild(p);
  }
}
