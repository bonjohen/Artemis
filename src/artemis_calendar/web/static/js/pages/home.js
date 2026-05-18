/**
 * Home / landing page — hero with top imagery, stats, and section entry points.
 */

import { PROJECT } from '../config.js';

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
  { hash: '#/clusters',   icon: '&#11044;', title: 'Cluster Explorer',   desc: '25 visual clusters grouping images by CLIP embedding similarity — from Earth views to crew shots.' },
  { hash: '#/stats',      icon: '&#9881;',  title: 'Stats Dashboard',    desc: 'Score distributions, inter-rater reliability, bias detection, and manufactured vote counts.' },
  { hash: '#/blend',      icon: '&#9878;',  title: 'Vote Simulator',     desc: 'Simulate how voter blocs with different visual preferences shape the calendar. Adjust voter counts, run elections, inspect individual ballots.' },
  { hash: '#/selection',  icon: '&#9776;',  title: 'Selection Builder',  desc: 'Interactive 13-slot calendar builder with live composite scoring (local server only).' },
  { hash: '#/lessons',    icon: '&#9998;',  title: 'Lessons Learned',    desc: 'Standalone lessons on data engineering, statistical methods, optimization, and deployment.' },
];

export async function render(el) {
  // Fetch stats for the numbers bar
  let stats = { image_count: PROJECT.image_count };
  let lessonCount = '—';
  try {
    const [sr, lr] = await Promise.all([
      fetch('/api/stats').then(r => r.json()),
      fetch('/api/lessons').then(r => r.json()),
    ]);
    stats = sr;
    lessonCount = lr.length;
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
        <div class="stat-item">
          <span class="stat-number">${stats.image_count?.toLocaleString() || '12,217'}</span>
          <span class="stat-label">Mission Photos</span>
        </div>
        <div class="stat-item">
          <span class="stat-number">${PROJECT.cluster_count}</span>
          <span class="stat-label">Visual Clusters</span>
        </div>
        <div class="stat-item">
          <span class="stat-number">5</span>
          <span class="stat-label">Scoring Methods</span>
        </div>
        <div class="stat-item">
          <span class="stat-number">${lessonCount}</span>
          <span class="stat-label">Lessons Learned</span>
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

      <footer class="home-footer">
        <p>Artemis II Calendar Image Selection &middot; A data science case study by <a href="https://github.com/bonjohen" target="_blank">John Boen</a></p>
        <p style="margin-top:var(--s-2)">Imagery courtesy NASA Johnson Space Center &middot; <a href="https://eol.jsc.nasa.gov" target="_blank">eol.jsc.nasa.gov</a></p>
      </footer>
    </div>
  `;

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
