/**
 * Home / landing page — hero with top imagery, stats, and section entry points.
 */

import { PROJECT, FEATURED_LESSONS } from '../config.js';

const THUMB = '/thumbs/';

// Top-rated images for the hero mosaic (hand-picked for visual variety across clusters)
// Curated celestial images: moon surfaces, Earth from orbit, crescents, craters
const HERO_IMAGES = [
  'ART002-E-21001', 'ART002-E-24597', 'ART002-E-23634', 'ART002-E-23536',
  'ART002-E-23615', 'ART002-E-10366', 'ART002-E-20847', 'ART002-E-26015',
  'ART002-E-26009', 'ART002-E-21337', 'ART002-E-29446', 'ART002-E-27731',
  'ART002-E-25359', 'ART002-E-21123', 'ART002-E-24689', 'ART002-E-29123',
  'ART002-E-24724', 'ART002-E-28194', 'ART002-E-23391', 'ART002-E-26469',
];

const SECTIONS = [
  { hash: '#/images',     icon: '&#9634;',  title: 'Image Browser',     desc: 'Browse 12,217 mission photos with preference scoring, cluster filtering, and visual detail overlays.' },
  { hash: '#/candidates', icon: '&#9733;',  title: 'Calendar Candidates', desc: '5 optimized calendar selections compared by popularity, diversity, month-fit, and redundancy.' },
  { hash: '#/clusters',   icon: '&#11044;', title: 'Cluster Explorer',   desc: '20 visual clusters grouping images by CLIP embedding similarity — from Earth views to crew shots.' },
  { hash: '#/stats',      icon: '&#9881;',  title: 'Stats Dashboard',    desc: 'Score distributions, inter-rater reliability, bias detection, and manufactured vote counts.' },
  { hash: '#/blend',      icon: '&#9878;',  title: 'Vote Simulator',     desc: 'Simulate how voter blocs with different visual preferences shape the calendar. Adjust voter counts, run elections, inspect individual ballots.' },
  { hash: '#/selection',  icon: '&#9776;',  title: 'Selection Builder',  desc: 'Interactive 13-slot calendar builder with live composite scoring (local server only).' },
  { hash: '#/lessons',    icon: '&#9998;',  title: 'Lessons Learned',    desc: 'Standalone lessons on data engineering, statistical methods, optimization, and deployment.' },
];

export async function render(el) {
  // Fetch stats for the numbers bar
  let stats = { image_count: PROJECT.image_count };
  let lessonCount = '—';
  let dedupDuplicates = '—';
  let clusterCount = PROJECT.cluster_count;
  try {
    const [sr, lr, dr, cr] = await Promise.all([
      fetch('/api/stats').then(r => r.json()),
      fetch('/api/lessons').then(r => r.json()),
      fetch('/api/dedup/summary').then(r => r.json()).catch(() => null),
      fetch('/api/clusters').then(r => r.json()).catch(() => []),
    ]);
    stats = sr;
    lessonCount = lr.length;
    if (dr) dedupDuplicates = dr.duplicates.toLocaleString();
    if (cr.length) clusterCount = cr.length;
  } catch (e) { /* use defaults */ }

  el.innerHTML = `
    <div class="home">
      <!-- Hero -->
      <section class="home-hero">
        <div class="hero-mosaic" aria-hidden="true">
          ${HERO_IMAGES.map((id, i) => `<img src="${THUMB}${id}.jpg" alt="" loading="${i < 8 ? 'eager' : 'lazy'}" class="mosaic-img">`).join('')}
          <div class="mosaic-fade"></div>
        </div>
        <div class="hero-content">
          <p class="hero-eyebrow">Artemis II Mission Photography</p>
          <h1 class="hero-title">Selecting 13 images<br>from <em>twelve thousand</em></h1>
          <p class="hero-lede">A data science case study in collection optimization — how statistical modeling, visual clustering, and multi-objective scoring select the best calendar from 12,217 Artemis II mission photographs.</p>
          <div class="hero-actions">
            <a href="#/images" class="hero-btn primary">Browse Images</a>
            <a href="#/blend" class="hero-btn primary">Vote Simulator</a>
            <a href="#/lessons" class="hero-btn secondary">Read Lessons</a>
          </div>
        </div>
      </section>

      <!-- Stats bar -->
      <section class="home-stats">
        <a href="#/images" class="stat-item stat-link">
          <span class="stat-number">${stats.image_count?.toLocaleString() || '12,217'}</span>
          <span class="stat-label">Mission Photos</span>
        </a>
        <a href="#/curation" class="stat-item stat-link">
          <span class="stat-number">${dedupDuplicates}</span>
          <span class="stat-label">Near-Duplicates</span>
        </a>
        <a href="#/clusters" class="stat-item stat-link">
          <span class="stat-number">${clusterCount}</span>
          <span class="stat-label">Visual Clusters</span>
        </a>
        <a href="#/stats" class="stat-item stat-link">
          <span class="stat-number">${PROJECT.scoring_methods}</span>
          <span class="stat-label">Scoring Methods</span>
        </a>
        <a href="#/candidates" class="stat-item stat-link">
          <span class="stat-number">${PROJECT.selection_methods}</span>
          <span class="stat-label">Calendar Candidates</span>
        </a>
        <a href="#/lessons" class="stat-item stat-link">
          <span class="stat-number">${lessonCount}</span>
          <span class="stat-label">Lessons Learned</span>
        </a>
      </section>

      <!-- The Problem -->
      <section class="home-problem">
        <h2 class="section-title">The Problem</h2>
        <div class="problem-text">
          <p>Selecting 13 images for a calendar sounds simple — just pick the top-ranked photos. But top-N ranking produces visually redundant sets: similar compositions, repeated color palettes, no month variety. The real problem is <strong>collection optimization</strong>: choosing images that work <em>together</em>, balancing voter preference against visual diversity, mission coverage, and month suitability.</p>
          <p>This project treats calendar selection as a multi-objective optimization problem — not a popularity contest. Every stage of the pipeline exists to transform 12,217 raw mission photographs into a balanced, defensible 13-image collection.</p>
        </div>
      </section>

      <!-- Pipeline overview -->
      <section class="home-pipeline">
        <h2 class="section-title">The Pipeline</h2>
        <p class="section-desc">Raw imagery flows through eight stages — from download to optimized calendar.</p>
        <div class="pipeline-steps">
          <div class="pipe-step"><span class="pipe-num">1</span><span class="pipe-name">Extract</span></div>
          <div class="pipe-arrow">&rarr;</div>
          <div class="pipe-step"><span class="pipe-num">2</span><span class="pipe-name">Features</span></div>
          <div class="pipe-arrow">&rarr;</div>
          <div class="pipe-step"><span class="pipe-num">3</span><span class="pipe-name">Cluster</span></div>
          <div class="pipe-arrow">&rarr;</div>
          <div class="pipe-step"><span class="pipe-num">4</span><span class="pipe-name">Score</span></div>
          <div class="pipe-arrow">&rarr;</div>
          <div class="pipe-step"><span class="pipe-num">5</span><span class="pipe-name">Optimize</span></div>
          <div class="pipe-arrow">&rarr;</div>
          <div class="pipe-step"><span class="pipe-num">6</span><span class="pipe-name">Assign</span></div>
          <div class="pipe-arrow">&rarr;</div>
          <div class="pipe-step"><span class="pipe-num">7</span><span class="pipe-name">Render</span></div>
          <div class="pipe-arrow">&rarr;</div>
          <div class="pipe-step"><span class="pipe-num">8</span><span class="pipe-name">Validate</span></div>
        </div>
      </section>

      <!-- Top images showcase -->
      <section class="home-showcase">
        <h2 class="section-title">Highest-Rated Imagery</h2>
        <p class="section-desc">The top 10 images by composite preference score — combining Bayesian smoothing, Elo ratings, and Borda counts from manufactured voter data.</p>
        <div class="showcase-grid" id="showcase-grid"></div>
        <div style="text-align:center;margin-top:var(--s-5)">
          <a href="#/images" class="hero-btn secondary">View all ${stats.image_count?.toLocaleString() || '12,217'} images &rarr;</a>
        </div>
      </section>

      <!-- Section cards -->
      <section class="home-sections">
        <h2 class="section-title">Explore</h2>
        <div class="section-grid">
          ${SECTIONS.map(s => `
            <a href="${s.hash}" class="section-card">
              <span class="section-icon">${s.icon}</span>
              <h3 class="section-card-title">${s.title}</h3>
              <p class="section-card-desc">${s.desc}</p>
            </a>
          `).join('')}
        </div>
      </section>

      <!-- Methods callout -->
      <section class="home-methods">
        <h2 class="section-title">Statistical Methods</h2>
        <p class="section-desc">Each image is scored through multiple complementary lenses.</p>
        <div class="methods-grid">
          <div class="method-card">
            <h4>Beta-Binomial</h4>
            <p>Bayesian smoothing with Beta(2,8) prior regularizes noisy selection rates from sparse ballot data.</p>
          </div>
          <div class="method-card">
            <h4>Elo Rating</h4>
            <p>Pairwise comparison scores adapted from chess, with K-factor tuning for sparse head-to-head votes.</p>
          </div>
          <div class="method-card">
            <h4>MMR Selection</h4>
            <p>Maximum Marginal Relevance balances preference with CLIP-based visual diversity in greedy selection.</p>
          </div>
          <div class="method-card">
            <h4>Hungarian Assignment</h4>
            <p>Optimal 1-to-1 image-to-month mapping via linear sum assignment on month-fit scores.</p>
          </div>
        </div>
      </section>

      <!-- Reviewer Path -->
      <section class="home-reviewer">
        <h2 class="section-title">Review This Project in 5 Minutes</h2>
        <p class="section-desc">A guided path through the key sections — from problem statement to lessons learned.</p>
        <ol class="reviewer-path">
          <li class="path-step">
            <span class="path-num">1</span>
            <div><strong>Read the project summary</strong> <span class="path-note">— you're here. Understand why top-N fails and what collection optimization means.</span></div>
          </li>
          <li class="path-step">
            <span class="path-num">2</span>
            <div><a href="#/pipeline"><strong>Open Pipeline</strong></a> <span class="path-note">— trace data from raw download through eight stages to validated calendar.</span></div>
          </li>
          <li class="path-step">
            <span class="path-num">3</span>
            <div><a href="#/clusters"><strong>Explore Clusters</strong></a> <span class="path-note">— see how CLIP embeddings group 12,217 images into ${clusterCount} visual themes.</span></div>
          </li>
          <li class="path-step">
            <span class="path-num">4</span>
            <div><a href="#/stats"><strong>Check Stats</strong></a> <span class="path-note">— review scoring distributions, reliability metrics, and bias detection.</span></div>
          </li>
          <li class="path-step">
            <span class="path-num">5</span>
            <div><a href="#/blend"><strong>Try Vote Simulator</strong></a> <span class="path-note">— watch how shifting voter preferences change the calendar outcome.</span></div>
          </li>
          <li class="path-step">
            <span class="path-num">6</span>
            <div><a href="#/selection"><strong>Review Selection</strong></a> <span class="path-note">— see human-in-the-loop calendar assembly with live scoring.</span></div>
          </li>
          <li class="path-step">
            <span class="path-num">7</span>
            <div><a href="#/lessons"><strong>Read Lessons</strong></a> <span class="path-note">— ${lessonCount}+ engineering lessons captured as reusable knowledge artifacts.</span></div>
          </li>
        </ol>
      </section>

      <!-- Learning Thread -->
      <section class="home-learning">
        <h2 class="section-title">Learning Thread</h2>
        <p class="section-desc">Each stage of the pipeline produced reusable engineering lessons — patterns, mistakes, and design decisions worth extracting. Here are six highlights, one per category.</p>
        <div class="featured-lessons-grid" id="featured-lessons"></div>
        <div style="text-align:center;margin-top:var(--s-5)">
          <a href="#/lessons" class="hero-btn secondary" style="color:var(--atlas-ink);border-color:var(--atlas-rule-soft)">All ${lessonCount} lessons &rarr;</a>
        </div>
      </section>

      <footer class="home-footer">
        <p>Artemis II Calendar Image Selection &middot; A data science case study by <a href="https://github.com/bonjohen" target="_blank">John Boen</a></p>
        <p style="margin-top:var(--s-2)">Imagery courtesy NASA Johnson Space Center &middot; <a href="https://eol.jsc.nasa.gov" target="_blank">eol.jsc.nasa.gov</a></p>
      </footer>
    </div>
  `;

  // Populate featured lessons
  const lessonsGrid = el.querySelector('#featured-lessons');
  try {
    const allLessons = await fetch('/api/lessons').then(r => r.json());
    const lessonMap = {};
    for (const l of allLessons) lessonMap[l.file] = l;
    for (const fl of FEATURED_LESSONS) {
      const lesson = lessonMap[fl.file];
      if (!lesson) continue;
      const cat = lesson.category || 'eng';
      const card = document.createElement('a');
      card.href = `#/lessons/${fl.block}/${fl.file}`;
      card.className = 'featured-lesson-card';
      card.innerHTML = `
        <span class="featured-lesson-cat cat-${cat}">${cat}</span>
        <h4 class="featured-lesson-title">${lesson.title}</h4>
        <p class="featured-lesson-highlight">${fl.highlight}</p>
      `;
      lessonsGrid.appendChild(card);
    }
  } catch (e) {
    lessonsGrid.textContent = 'Could not load featured lessons.';
  }

  // Populate showcase grid with top 10 images
  const grid = el.querySelector('#showcase-grid');
  try {
    const r = await fetch('/api/images?page=1&per_page=10&sort=score');
    const data = await r.json();
    for (const img of data.items) {
      const card = document.createElement('a');
      card.href = `#/images`;
      card.className = 'showcase-card';
      const score = img.preference_score != null ? img.preference_score.toFixed(3) : '—';
      card.innerHTML = `
        <img src="${THUMB}${img.source_image_id}.jpg" alt="Artemis II image ${img.source_image_id}" loading="lazy">
        <div class="showcase-info">
          <span class="showcase-score">${score}</span>
          <span class="showcase-cluster">C${img.cluster_id}</span>
        </div>
      `;
      grid.appendChild(card);
    }
  } catch (e) {
    grid.textContent = 'Could not load images.';
  }
}
