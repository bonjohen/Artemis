/**
 * Centralized project metadata — single source of truth for counts and constants.
 * Import from here rather than hardcoding values in page modules.
 */

export const PROJECT = {
  name: 'Artemis II Calendar Image Selection',
  summary:
    'A data science case study in collection optimization — selecting 13 balanced calendar images from 12,217 Artemis II mission photographs using statistical modeling, visual clustering, and multi-objective scoring.',
  image_count: 12217,
  cluster_count: 25,
  scoring_methods: 5,
  selection_methods: 5,
  pipeline_stages: 8,
  github_url: 'https://github.com/bonjohen/Artemis',
  site_url: 'https://artemis.johnboen.com',
};

/**
 * Featured lessons for the homepage Learning Thread section.
 * One per category to demonstrate breadth. {block, file, highlight}
 */
export const FEATURED_LESSONS = [
  { block: 'block1', file: 'batch_db_operations', highlight: 'Bulk insert via PyArrow instead of hanging executemany' },
  { block: 'block2', file: '012_bayesian_beta_binomial_smoothing', highlight: 'Beta-Binomial priors regularize noisy selection rates' },
  { block: 'block3', file: '021_calendar_as_portfolio_optimization', highlight: 'Calendar selection is portfolio optimization, not top-N' },
  { block: 'block5', file: '033_vanilla_js_spa_no_build_step', highlight: 'Hash-based SPA routing for zero-config static hosting' },
  { block: 'block6', file: '039_mock_tagger_for_vision_pipeline_testing', highlight: 'Mock tagger pattern for vision pipeline testing' },
  { block: 'block4', file: '028_chi_squared_for_bias_detection', highlight: 'Chi-squared tests expose position and cluster bias' },
];
