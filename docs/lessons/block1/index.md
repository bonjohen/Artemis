  
  ┌─────────────────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────────┐
  │               Lesson                │                                        Core Teaching                                         │ ├─────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
  │ concurrent_http_downloads           │ Shared client + thread pool + batch DB = 5x throughput                                       │
  ├─────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
  │ algorithm_selection_dominant_colors │ Domain-specific tool (Pillow quantize) 735x faster than general ML (sklearn KMeans)          │
  ├─────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
  │ disjoint_populations_multimodal     │ Anti-correlated selection criteria produce empty joins — design for union, not intersection  │
  ├─────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
  │ duckdb_single_writer_constraint     │ Embedded DB = exclusive file lock — separate I/O from DB writes                              │
  ├─────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
  │ choosing_k_for_clustering           │ For constrained selection, k is driven by the output (13 calendar images) not just the input │
  ├─────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
  │ surrogate_key_range_debugging       │ Min/max on surrogate keys instantly reveals disjoint populations                             │
  ├─────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
  │ per_record_overhead_at_scale        │ 1ms overhead × 12,000 records = 12 seconds of invisible waste                                │
  ├─────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
  │ batch_db_operations                 │ executemany, unnest, aggregate records — patterns for DuckDB at scale                        │
  ├─────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
  │ resume_safe_pipeline_design         │ Three layers: disk dedup, DB flag filtering, graceful flush on interrupt                     │
  ├─────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
  │ synthetic_data_before_real_data     │ Build and test the full pipeline with known ground truth before real data arrives            │
  ├─────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 11-pep-8-compliance                │ Consistent style makes a 15-module codebase searchable, lintable, and AI-friendly           │
  └─────────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────┘