/**
 * Pipeline page — stage-by-stage walkthrough of the data pipeline.
 */

import { renderContextBlock } from '../components/context-block.js';

const STAGES = [
  {
    num: 1,
    name: 'Extract',
    purpose: 'Download source pages, vote manifests, and thumbnail images from three upstream sources: ArtemisTimeline.com (metadata + votes), NASA JSC (full-resolution images), and Cloudflare R2 CDN (thumbnails).',
    inputs: 'ArtemisTimeline.com API, NASA JSC image server, R2 CDN public bucket',
    outputs: 'Raw archive files in <code>D:/artemis/raw/</code>, 12,217 thumbnails in <code>raw/images/thumbs/</code>',
    files: '<code>extract/</code> \u2014 download, manifest, image collectors',
    validation: 'Content-hash verification, zero-failure download count, immutable raw archive (never modified after capture)',
    lessons: [
      { block: 'block1', file: 'concurrent_http_downloads', title: 'Concurrent HTTP Downloads' },
      { block: 'block1', file: 'resume_safe_pipeline_design', title: 'Resume-Safe Pipeline Design' },
    ],
    appLink: null,
  },
  {
    num: 2,
    name: 'Features',
    purpose: 'Extract visual features (brightness, contrast, saturation, dominant colors) and CLIP ViT-B/32 embeddings from all 12,217 thumbnails. Run zero-shot classification across 37 content attributes with sigmoid-calibrated confidence scores.',
    inputs: 'Thumbnails (12,217 JPEG files)',
    outputs: '<code>feature_image_visual</code>, <code>feature_image_embedding</code> (512-dim CLIP), <code>feature_image_attribute</code> (~451K labels)',
    files: '<code>features/visual.py</code> (Pillow parallel), <code>features/embeddings.py</code> (CLIP), <code>vision/clip_tagger.py</code> (zero-shot)',
    validation: 'Row counts match image count, embedding dimensionality check, attribute coverage audit',
    lessons: [
      { block: 'block1', file: 'algorithm_selection_dominant_colors', title: 'Algorithm Selection: Dominant Colors' },
      { block: 'block6', file: '039_mock_tagger_for_vision_pipeline_testing', title: 'Mock Tagger for Vision Testing' },
    ],
    appLink: '#/images',
  },
  {
    num: 3,
    name: 'Cluster',
    purpose: 'Group images into 25 visual clusters using k-means on CLIP embeddings. Also runs HDBSCAN for comparison. Builds cluster summaries with representative images and preference score aggregates.',
    inputs: 'CLIP embedding vectors (12,217 \u00d7 512)',
    outputs: '<code>feature_image_cluster</code>, <code>mart_image_cluster_summary</code> (25 clusters), <code>mart_cluster_top_images</code>',
    files: '<code>cluster/clustering.py</code> (k-means, HDBSCAN), <code>cluster/marts.py</code> (summary + top images)',
    validation: 'Every image assigned to exactly one cluster, cluster sizes are non-degenerate, summary statistics populated',
    lessons: [
      { block: 'block1', file: 'choosing_k_for_clustering', title: 'Choosing k for Clustering' },
      { block: 'block1', file: 'disjoint_populations_multimodal', title: 'Disjoint Populations in Multimodal Joins' },
    ],
    appLink: '#/clusters',
  },
  {
    num: 4,
    name: 'Score',
    purpose: 'Compute preference scores using three complementary methods: Bayesian Beta-Binomial smoothing (batch votes), Elo ratings (pairwise comparisons), and Borda counts (ranked voting). Combine into a composite score with uncertainty estimates.',
    inputs: 'Synthetic vote data (100 voters, 3 modes), image features',
    outputs: '<code>mart_image_preference_score</code> (12,217 rows), <code>mart_inter_rater_reliability</code>',
    files: '<code>models/</code> \u2014 Beta-Binomial, Elo, Borda, composite scoring, inter-rater reliability',
    validation: 'Score distributions are non-degenerate, composite weights sum correctly, Krippendorff\u2019s alpha computed',
    lessons: [
      { block: 'block2', file: '012_bayesian_beta_binomial_smoothing', title: 'Bayesian Beta-Binomial Smoothing' },
      { block: 'block2', file: '013_elo_rating_for_image_comparison', title: 'Elo Rating for Image Comparison' },
      { block: 'block2', file: '016_krippendorffs_alpha_for_sparse_agreement', title: 'Krippendorff\u2019s Alpha for Sparse Agreement' },
    ],
    appLink: '#/stats',
  },
  {
    num: 5,
    name: 'Optimize',
    purpose: 'Generate 5 candidate calendar selections using different strategies: top-N popularity, cluster-limited, per-cluster top, month-first, and MMR greedy (maximum marginal relevance). Each produces a 13-image slate.',
    inputs: 'Composite scores, cluster assignments, month-fit scores',
    outputs: '<code>mart_calendar_candidate</code> (5 candidates, one per method)',
    files: '<code>optimize/</code> \u2014 selection methods, month/cover scoring, objective function',
    validation: 'Each candidate has exactly 13 unique images, no duplicate clusters in diversity-aware methods',
    lessons: [
      { block: 'block3', file: '021_calendar_as_portfolio_optimization', title: 'Calendar as Portfolio Optimization' },
      { block: 'block3', file: '023_maximum_marginal_relevance_for_selection', title: 'MMR for Diversity-Aware Selection' },
      { block: 'block3', file: '025_multiple_selection_methods_as_baselines', title: 'Multiple Methods as Baselines' },
    ],
    appLink: '#/candidates',
  },
  {
    num: 6,
    name: 'Assign',
    purpose: 'Map each selected image to its optimal calendar month using the Hungarian algorithm (linear sum assignment) on month-fit scores. Ensures a provably optimal 1-to-1 image-to-month mapping.',
    inputs: 'Candidate slates (13 images each), month-fit score matrix',
    outputs: '<code>mart_calendar_candidate_month_image</code> (65 rows: 13 months \u00d7 5 candidates)',
    files: '<code>optimize/</code> \u2014 <code>scipy.optimize.linear_sum_assignment</code>',
    validation: 'Each month assigned exactly one image, no image assigned to multiple months',
    lessons: [
      { block: 'block3', file: '024_hungarian_algorithm_for_optimal_assignment', title: 'Hungarian Algorithm for Optimal Assignment' },
      { block: 'block3', file: '022_heuristic_month_fit_without_text', title: 'Heuristic Month-Fit Without Text' },
    ],
    appLink: '#/candidates',
  },
  {
    num: 7,
    name: 'Render',
    purpose: 'Download full-resolution images for the winning calendar, compose 8.5\u00d711" monthly pages with image, month label, and NASA attribution. Generate cover page and assemble into a multi-page PDF.',
    inputs: 'Full-resolution images (NASA JSC), month assignments',
    outputs: 'PDF calendar pages, cover page, assembled multi-page PDF',
    files: '<code>render/</code> \u2014 layout constants, grid renderer, page composition, PDF assembly',
    validation: 'Page dimensions correct, image aspect ratios preserved, all 14 pages present (cover + 13 months)',
    lessons: [],
    appLink: null,
  },
  {
    num: 8,
    name: 'Validate',
    purpose: 'Test for systematic bias in the scoring pipeline (position bias, cluster bias, voter segment effects) and measure how well the optimizer recovers known ground-truth preferences from synthetic data.',
    inputs: 'Synthetic votes with known ground truth, scored images, candidate slates',
    outputs: '<code>mart_bias_detection</code>, <code>mart_calendar_validation</code>',
    files: '<code>validate/bias_detection.py</code>, <code>validate/calendar_validation.py</code>',
    validation: 'Chi-squared tests for bias, Spearman correlation between scores and ground truth, reliability delta under noise',
    lessons: [
      { block: 'block4', file: '028_chi_squared_for_bias_detection', title: 'Chi-Squared for Bias Detection' },
      { block: 'block4', file: '029_ground_truth_recovery_as_validation', title: 'Ground-Truth Recovery as Validation' },
      { block: 'block4', file: '030_reliability_delta_as_noise_measurement', title: 'Reliability Delta as Noise Measurement' },
    ],
    appLink: '#/stats',
  },
];

export async function render(el) {
  el.innerHTML = `
    ${renderContextBlock('Why this page matters', 'Trace data from raw download to validated calendar. Each stage shows inputs, outputs, key files, and related engineering lessons.')}
    <div class="page-header"><h1>Pipeline</h1></div>
    <p style="color:var(--atlas-ink-2);max-width:64ch;margin-bottom:var(--s-6);line-height:var(--lh-body)">
      Raw imagery flows through eight stages. Each stage is independently testable, resume-safe, and produces
      immutable outputs that feed the next stage.
    </p>
    <div class="pipeline-page">
      ${STAGES.map(renderStage).join('')}
    </div>
  `;

  // Toggle detail sections
  el.querySelectorAll('.stage-card-header').forEach(header => {
    header.addEventListener('click', () => {
      const card = header.closest('.stage-card');
      card.classList.toggle('expanded');
    });
  });
}

function renderStage(stage) {
  const lessonsHtml = stage.lessons.length
    ? stage.lessons.map(l =>
        `<a href="#/lessons/${l.block}/${l.file}" class="stage-lesson-link">${l.title}</a>`
      ).join('')
    : '<span style="color:var(--atlas-muted)">None yet</span>';

  const appLinkHtml = stage.appLink
    ? `<a href="${stage.appLink}" class="stage-app-link">View in app &rarr;</a>`
    : '';

  return `
    <div class="stage-card">
      <div class="stage-card-header">
        <span class="stage-num">${stage.num}</span>
        <span class="stage-name">${stage.name}</span>
        <span class="stage-toggle">+</span>
      </div>
      <div class="stage-detail">
        <p class="stage-purpose">${stage.purpose}</p>
        <div class="stage-grid">
          <div class="stage-field">
            <span class="stage-field-label">Inputs</span>
            <span class="stage-field-value">${stage.inputs}</span>
          </div>
          <div class="stage-field">
            <span class="stage-field-label">Outputs</span>
            <span class="stage-field-value">${stage.outputs}</span>
          </div>
          <div class="stage-field">
            <span class="stage-field-label">Key files</span>
            <span class="stage-field-value">${stage.files}</span>
          </div>
          <div class="stage-field">
            <span class="stage-field-label">Validation</span>
            <span class="stage-field-value">${stage.validation}</span>
          </div>
          <div class="stage-field">
            <span class="stage-field-label">Related lessons</span>
            <span class="stage-field-value stage-lessons">${lessonsHtml}</span>
          </div>
        </div>
        ${appLinkHtml}
      </div>
    </div>
  `;
}
