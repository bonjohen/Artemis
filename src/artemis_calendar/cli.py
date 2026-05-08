"""Command-line interface for the Artemis pipeline."""

from __future__ import annotations

import argparse
import sys

from artemis_calendar.config.database import apply_migrations, get_connection
from artemis_calendar.config.settings import DB_PATH
from artemis_calendar.observe.logging import get_logger

logger = get_logger("artemis.cli")


def cmd_migrate(args: argparse.Namespace) -> None:
    conn = get_connection()
    applied = apply_migrations(conn)
    if applied:
        logger.info(f"Applied {len(applied)} migration(s): {', '.join(applied)}")
    else:
        logger.info("No pending migrations.")
    conn.close()


def cmd_status(args: argparse.Namespace) -> None:
    conn = get_connection()
    apply_migrations(conn)

    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' AND table_name != '_migrations'"
    ).fetchall()

    print(f"\nWarehouse: {DB_PATH}")
    print(f"{'Table':<40} {'Rows':>10}")
    print("-" * 52)
    for (table_name,) in sorted(tables):
        try:
            count = conn.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
            print(f"{table_name:<40} {count:>10,}")
        except Exception as e:
            print(f"{table_name:<40} {'ERROR':>10}  {e}")
    conn.close()


def cmd_collect_metadata(args: argparse.Namespace) -> None:
    from artemis_calendar.extract.collector import collect_all_metadata

    conn = get_connection()
    apply_migrations(conn)
    run_ids = collect_all_metadata(conn, manifest_path=args.manifest)
    logger.info(f"Collected {len(run_ids)} source(s)")
    conn.close()


def cmd_load_metadata(args: argparse.Namespace) -> None:
    from artemis_calendar.load.loader import load_all_metadata

    conn = get_connection()
    apply_migrations(conn)
    counts = load_all_metadata(conn)
    logger.info(f"Load complete: {counts}")
    conn.close()


def cmd_collect_images(args: argparse.Namespace) -> None:
    from artemis_calendar.extract.images import download_full_images, download_thumbnails

    conn = get_connection()
    apply_migrations(conn)
    limit = args.limit

    if args.thumbs_only:
        count = download_thumbnails(conn, limit=limit)
        logger.info(f"Downloaded {count} thumbnails")
    elif args.full_only:
        count = download_full_images(conn, limit=limit)
        logger.info(f"Downloaded {count} full images")
    else:
        t_count = download_thumbnails(conn, limit=limit)
        f_count = download_full_images(conn, limit=limit)
        logger.info(f"Downloaded {t_count} thumbnails, {f_count} full images")
    conn.close()


def cmd_generate_votes(args: argparse.Namespace) -> None:
    from artemis_calendar.synthetic.generator import generate_synthetic_votes

    conn = get_connection()
    apply_migrations(conn)
    counts = generate_synthetic_votes(
        conn,
        seed=args.seed,
        voter_count=args.voters,
        ballot_count=args.ballots,
        pair_count=args.pairs,
        ranking_count=args.rankings,
    )
    logger.info(f"Generated synthetic votes: {counts}")
    conn.close()


def cmd_extract_visual(args: argparse.Namespace) -> None:
    from artemis_calendar.features.visual import extract_visual_features

    conn = get_connection()
    apply_migrations(conn)
    count = extract_visual_features(conn, limit=args.limit, batch_size=args.batch_size)
    logger.info(f"Extracted visual features for {count} images")
    conn.close()


def cmd_extract_embeddings(args: argparse.Namespace) -> None:
    from artemis_calendar.features.embeddings import extract_image_embeddings, extract_text_embeddings
    from artemis_calendar.features.text_features import extract_text_features

    conn = get_connection()
    apply_migrations(conn)

    if not args.text_only:
        img_count = extract_image_embeddings(conn, limit=args.limit, batch_size=args.batch_size)
        logger.info(f"Image embeddings: {img_count}")

    if not args.image_only:
        txt_emb_count = extract_text_embeddings(conn, limit=args.limit, batch_size=args.batch_size)
        logger.info(f"Text embeddings: {txt_emb_count}")

        txt_feat_count = extract_text_features(conn, limit=args.limit)
        logger.info(f"Text features: {txt_feat_count}")

    conn.close()


def cmd_run_clustering(args: argparse.Namespace) -> None:
    from artemis_calendar.cluster.clustering import run_clustering
    from artemis_calendar.cluster.marts import build_cluster_summary, build_cluster_top_images

    conn = get_connection()
    apply_migrations(conn)
    results = run_clustering(
        conn,
        algorithm=args.algorithm,
        cluster_type=args.cluster_type,
        n_clusters=args.n_clusters,
        seed=args.seed,
    )
    logger.info(f"Clustering results: {results}")

    # Build mart tables for the most recent run
    run_ids = conn.execute(
        "SELECT DISTINCT cluster_run_id FROM feature_image_cluster ORDER BY cluster_run_id DESC LIMIT 1"
    ).fetchall()
    if run_ids:
        run_id = run_ids[0][0]
        build_cluster_summary(conn, run_id)
        build_cluster_top_images(conn, run_id)

    conn.close()


def cmd_compute_scores(args: argparse.Namespace) -> None:
    from artemis_calendar.models import compute_preference_scores

    conn = get_connection()
    apply_migrations(conn)
    counts = compute_preference_scores(conn)
    logger.info(f"Scoring complete: {counts}")
    conn.close()


def cmd_optimize(args: argparse.Namespace) -> None:
    from artemis_calendar.optimize import run_calendar_optimization

    conn = get_connection()
    apply_migrations(conn)
    kwargs = {"seed": args.seed}
    if args.methods:
        kwargs["methods"] = tuple(args.methods.split(","))
    result = run_calendar_optimization(conn, **kwargs)
    logger.info(f"Optimization complete: {result}")
    conn.close()


def cmd_render_calendar(args: argparse.Namespace) -> None:
    from artemis_calendar.render.pipeline import render_calendar

    conn = get_connection()
    apply_migrations(conn)

    candidates = [args.candidate]
    if args.all:
        rows = conn.execute("SELECT DISTINCT candidate_name FROM mart_calendar_candidate").fetchall()
        candidates = [r[0] for r in rows]

    for name in candidates:
        out_dir = render_calendar(conn, name, run_id=args.run_id)
        logger.info(f"Calendar rendered to {out_dir}")

    conn.close()


def cmd_review_package(args: argparse.Namespace) -> None:
    from artemis_calendar.review.pipeline import generate_review_package

    conn = get_connection()
    apply_migrations(conn)
    out_dir = generate_review_package(
        conn,
        run_id=args.run_id,
        winner=args.winner,
        skip_render=args.skip_render,
    )
    logger.info(f"Review package at {out_dir}")
    conn.close()


def cmd_validate_bias(args: argparse.Namespace) -> None:
    from artemis_calendar.validate.bias_detection import run_bias_detection

    conn = get_connection()
    apply_migrations(conn)
    report = run_bias_detection(conn)

    print("\n=== Bias Detection Report (S3) ===")
    print(f"Run ID: {report['detection_run_id']}")
    print(
        f"\nPosition bias:  coeff={report.get('position_bias_coeff', 'N/A')}, "
        f"p={report.get('position_bias_pvalue', 'N/A')}, "
        f"detected={report.get('position_bias_detected', 'N/A')}"
    )
    print(
        f"Pairwise left:  win_rate={report.get('pairwise_left_win_rate', 'N/A')}, "
        f"p={report.get('pairwise_left_pvalue', 'N/A')}"
    )
    print(
        f"Cluster bias:   chi2={report.get('cluster_bias_chi2', 'N/A')}, p={report.get('cluster_bias_pvalue', 'N/A')}"
    )
    print(
        f"Score vs truth: spearman={report.get('score_vs_truth_spearman', 'N/A')}, "
        f"p={report.get('score_vs_truth_pvalue', 'N/A')}"
    )
    print(
        f"Reliability:    all={report.get('alpha_all_voters', 'N/A')}, "
        f"clean={report.get('alpha_excluding_biased', 'N/A')}, "
        f"delta={report.get('alpha_delta', 'N/A')}"
    )
    print(
        f"Voter segments: {report.get('voter_segment_count', 0)} profiles, "
        f"consensus_std={report.get('voter_consensus_std', 'N/A')}"
    )

    if report.get("cluster_details"):
        print("\nTop over-selected clusters:")
        for c in report["cluster_details"]:
            print(f"  Cluster {c['cluster']}: lift={c['lift']:.2f}x (obs={c['observed']}, exp={c['expected']:.0f})")

    if report.get("profile_stats"):
        print("\nVoter profile agreement:")
        for profile, s in report["profile_stats"].items():
            print(
                f"  {profile:<20} n={s['count']}, "
                f"mean_agreement={s['mean_agreement']:.4f}, "
                f"std={s['std_agreement']:.4f}"
            )

    conn.close()


def cmd_validate_calendar(args: argparse.Namespace) -> None:
    from artemis_calendar.validate.calendar_validation import run_calendar_validation

    conn = get_connection()
    apply_migrations(conn)
    report = run_calendar_validation(conn)

    print("\n=== Calendar Optimization Validation (S4) ===")
    print(f"Run ID: {report['validation_run_id']}")

    if report["methods"]:
        print(f"\n{'Method':<12} {'Recovery':>10} {'Clusters':>10} {'Max Sim':>10} {'Objective':>10}")
        print("-" * 56)
        for name, m in sorted(report["methods"].items()):
            recovery = f"{m.get('gt_recovery_rate', 0):.1%}" if m.get("gt_recovery_rate") is not None else "N/A"
            clusters = str(m.get("slate_cluster_count", "N/A"))
            max_sim = f"{m['slate_max_cosine_sim']:.3f}" if m.get("slate_max_cosine_sim") is not None else "N/A"
            objective = f"{m['objective_score']:.3f}" if m.get("objective_score") is not None else "N/A"
            print(f"{name:<12} {recovery:>10} {clusters:>10} {max_sim:>10} {objective:>10}")
    else:
        print("No candidate data found.")

    conn.close()


def cmd_vision_tag(args: argparse.Namespace) -> None:
    from artemis_calendar.vision.attributes import load_attribute_vocabulary
    from artemis_calendar.vision.loader import seed_attribute_vocabulary
    from artemis_calendar.vision.pipeline import run_vision_tagging

    conn = get_connection()
    apply_migrations(conn)

    vocab = load_attribute_vocabulary()
    seed_attribute_vocabulary(conn)

    if args.mock:
        from artemis_calendar.vision.tagger import MockTagger

        tagger = MockTagger(vocab)
    else:
        from artemis_calendar.vision.tagger import VisionTagger

        tagger = VisionTagger(
            vocab,
            model_name=args.model,
            model_version=args.model_version,
        )

    summary = run_vision_tagging(
        conn,
        tagger=tagger,
        vocab=vocab,
        limit=args.limit,
        changed_only=args.changed_only,
    )

    print("\nVision tagging complete:")
    print(f"  Images processed: {summary['images_processed']}")
    print(f"  Attributes written: {summary['attributes_written']}")
    print(f"  Flagged for review: {summary['review_flagged']}")
    print(f"  Output: {summary.get('output_path', 'N/A')}")
    conn.close()


def cmd_votes_generate_blocks(args: argparse.Namespace) -> None:
    from pathlib import Path

    from artemis_calendar.synthetic.block_generator import generate_block_votes
    from artemis_calendar.vision.voting_config import load_voting_config

    config = load_voting_config(Path(args.config))
    if args.seed is not None:
        config.seed = args.seed

    conn = get_connection()
    apply_migrations(conn)
    summary = generate_block_votes(conn, config, replace_run=args.replace_run)
    conn.close()

    print("\nBlock vote generation complete:")
    print(f"  Scenario: {summary.get('scenario_name', 'N/A')}")
    print(f"  Voters: {summary.get('total_voters', 0)}")
    print(f"  Ballots: {summary.get('total_ballots', 0)}")
    print(f"  Ballot images: {summary.get('total_ballot_images', 0)}")
    print(f"  Output: {summary.get('output_path', 'N/A')}")


def cmd_votes_validate_config(args: argparse.Namespace) -> None:
    from pathlib import Path

    from artemis_calendar.vision.voting_config import dry_run, load_voting_config, validate_voting_config

    config = load_voting_config(Path(args.config))
    errors = validate_voting_config(config)

    if errors:
        print("Validation errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    if args.dry_run:
        conn = get_connection()
        apply_migrations(conn)
        result = dry_run(config, conn)
        conn.close()

        print(f"\nScenario: {result.scenario_name}")
        print(f"Total voters: {result.total_voters}")
        print(f"Total votes: {result.total_votes}")
        for b in result.blocks:
            print(f"\nBlock: {b.label}")
            print(f"  Voters: {b.voter_count}")
            print(f"  Votes per voter: {b.votes_per_voter}")
            print(f"  Matching images: {b.matching_images}")
            for w in b.warnings:
                print(f"  Warning: {w}")
    else:
        print(f"Config valid: {config.scenario_name} ({len(config.blocks)} blocks)")


def cmd_vision_label_clusters(args: argparse.Namespace) -> None:
    from artemis_calendar.vision.cluster_labels import export_cluster_review, label_clusters

    conn = get_connection()
    apply_migrations(conn)

    count = label_clusters(conn, cluster_run_id=args.run_id, cluster_type=args.cluster_type)
    print(f"Labeled {count} clusters")

    if args.export_review:
        result = export_cluster_review(conn, cluster_run_id=args.run_id, cluster_type=args.cluster_type)
        print(f"Review exported: {result.get('json_path', 'N/A')}")

    conn.close()


def cmd_serve(args: argparse.Namespace) -> None:
    try:
        import uvicorn
    except ImportError:
        print("Web dependencies not installed. Run: pip install -e '.[web]'")
        sys.exit(1)

    from artemis_calendar.web import create_app

    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port)


def cmd_run_all(args: argparse.Namespace) -> None:
    conn = get_connection()
    applied = apply_migrations(conn)
    if applied:
        logger.info(f"Applied {len(applied)} migration(s)")
    conn.close()

    cmd_collect_metadata(args)

    # Re-open for load (collect closes the connection)
    fake_args = argparse.Namespace()
    cmd_load_metadata(fake_args)

    fake_args.seed = args.seed
    fake_args.voters = 100
    fake_args.ballots = 500
    fake_args.pairs = 2000
    fake_args.rankings = 250
    cmd_generate_votes(fake_args)

    # Feature extraction
    fake_args.limit = None
    fake_args.batch_size = 100
    cmd_extract_visual(fake_args)

    fake_args.batch_size = 32
    fake_args.image_only = False
    fake_args.text_only = False
    cmd_extract_embeddings(fake_args)

    # Clustering
    fake_args.algorithm = "kmeans"
    fake_args.cluster_type = "all"
    fake_args.n_clusters = 25
    cmd_run_clustering(fake_args)

    # Statistical modeling
    cmd_compute_scores(fake_args)

    # Optimization
    fake_args.methods = None
    cmd_optimize(fake_args)

    # Validation (S3-S4)
    cmd_validate_bias(fake_args)
    cmd_validate_calendar(fake_args)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="artemis-pipeline",
        description="Artemis II calendar image selection data pipeline",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("migrate", help="Apply pending database migrations")
    sub.add_parser("status", help="Show warehouse status and row counts")

    collect = sub.add_parser("collect-metadata", help="Download and archive all metadata sources")
    collect.add_argument("--manifest", default=None, help="Path to source manifest YAML")

    sub.add_parser("load-metadata", help="Parse raw files and load into staging + warehouse")

    images = sub.add_parser("collect-images", help="Download thumbnail and full images")
    images.add_argument("--thumbs-only", action="store_true", help="Download only thumbnails")
    images.add_argument("--full-only", action="store_true", help="Download only full images")
    images.add_argument("--limit", type=int, default=None, help="Max images to download")

    votes = sub.add_parser("generate-votes", help="Generate synthetic vote data")
    votes.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    votes.add_argument("--voters", type=int, default=100, help="Number of synthetic voters")
    votes.add_argument("--ballots", type=int, default=500, help="Number of batch ballots")
    votes.add_argument("--pairs", type=int, default=2000, help="Number of pairwise votes")
    votes.add_argument("--rankings", type=int, default=250, help="Number of category rankings")

    extract_vis = sub.add_parser("extract-visual", help="Extract visual features from thumbnails")
    extract_vis.add_argument("--limit", type=int, default=None, help="Max images to process")
    extract_vis.add_argument("--batch-size", type=int, default=100, help="Batch size for processing")

    extract_emb = sub.add_parser("extract-embeddings", help="Generate image/text embeddings and text features")
    extract_emb.add_argument("--limit", type=int, default=None, help="Max images to process")
    extract_emb.add_argument("--batch-size", type=int, default=32, help="Batch size for embedding generation")
    extract_emb.add_argument("--image-only", action="store_true", help="Only generate image embeddings")
    extract_emb.add_argument("--text-only", action="store_true", help="Only generate text embeddings and features")

    cluster = sub.add_parser("run-clustering", help="Run clustering on embeddings")
    cluster.add_argument("--algorithm", choices=["kmeans", "hdbscan"], default="kmeans", help="Clustering algorithm")
    cluster.add_argument(
        "--cluster-type", choices=["visual", "text", "multimodal", "all"], default="all", help="Type to cluster"
    )
    cluster.add_argument("--n-clusters", type=int, default=25, help="Number of clusters (k-means only)")
    cluster.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")

    sub.add_parser("compute-scores", help="Compute preference scores from vote data")

    optimize = sub.add_parser("optimize", help="Run calendar optimization to generate candidate calendars")
    optimize.add_argument("--methods", default=None, help="Comma-separated methods (method_a,method_b,...)")
    optimize.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")

    render = sub.add_parser("render-calendar", help="Render calendar pages for a candidate")
    render.add_argument("--candidate", default="method_b", help="Candidate name (default: method_b)")
    render.add_argument("--run-id", default=None, help="Optimization run ID (default: latest)")
    render.add_argument("--all", action="store_true", help="Render all candidates")

    review = sub.add_parser("review-package", help="Generate review package for candidate comparison")
    review.add_argument("--run-id", default=None, help="Optimization run ID (default: latest)")
    review.add_argument("--winner", default="method_b", help="Candidate to export (default: method_b)")
    review.add_argument("--skip-render", action="store_true", help="Skip rendering full calendars")

    vision_tag = sub.add_parser("vision-tag", help="Run vision model to tag images with structured attributes")
    vision_tag.add_argument("--limit", type=int, default=None, help="Max images to process")
    vision_tag.add_argument("--changed-only", action="store_true", help="Skip images that already have attributes")
    vision_tag.add_argument("--model", default="qwen2.5-vl-7b", help="Vision model name (default: qwen2.5-vl-7b)")
    vision_tag.add_argument(
        "--model-version", default="Qwen/Qwen2.5-VL-7B-Instruct", help="HuggingFace model ID"
    )
    vision_tag.add_argument("--mock", action="store_true", help="Use mock tagger (for testing without GPU)")

    votes_gen = sub.add_parser("votes-generate-blocks", help="Generate biased synthetic votes from block config")
    votes_gen.add_argument("--config", required=True, help="Path to voting block YAML config")
    votes_gen.add_argument("--seed", type=int, default=None, help="Override random seed")
    votes_gen.add_argument("--replace-run", action="store_true", help="Delete previous run data")

    votes_validate = sub.add_parser("votes-validate-config", help="Validate a voting block YAML config")
    votes_validate.add_argument("--config", required=True, help="Path to voting block YAML config")
    votes_validate.add_argument("--dry-run", action="store_true", help="Count matching images per block")

    vision_label = sub.add_parser(
        "vision-label-clusters", help="Generate labels for clusters from dominant attributes"
    )
    vision_label.add_argument("--run-id", default=None, help="Cluster run ID (default: latest)")
    vision_label.add_argument("--cluster-type", default="visual", help="Cluster type (default: visual)")
    vision_label.add_argument("--export-review", action="store_true", help="Export cluster review JSON and Markdown")

    sub.add_parser("validate-bias", help="Run bias detection validation on synthetic vote data (S3)")
    sub.add_parser("validate-calendar", help="Run calendar optimization validation against ground truth (S4)")

    serve = sub.add_parser("serve", help="Start the web application")
    serve.add_argument("--host", default="localhost", help="Bind host (default: localhost)")
    serve.add_argument("--port", type=int, default=8420, help="Bind port (default: 8420)")

    run_all = sub.add_parser("run-all", help="Run full pipeline: migrate → collect → load → generate")
    run_all.add_argument("--manifest", default=None, help="Path to source manifest YAML")
    run_all.add_argument("--seed", type=int, default=42, help="Random seed for synthetic votes")

    args = parser.parse_args()
    commands = {
        "migrate": cmd_migrate,
        "status": cmd_status,
        "collect-metadata": cmd_collect_metadata,
        "load-metadata": cmd_load_metadata,
        "collect-images": cmd_collect_images,
        "generate-votes": cmd_generate_votes,
        "extract-visual": cmd_extract_visual,
        "extract-embeddings": cmd_extract_embeddings,
        "run-clustering": cmd_run_clustering,
        "compute-scores": cmd_compute_scores,
        "optimize": cmd_optimize,
        "render-calendar": cmd_render_calendar,
        "review-package": cmd_review_package,
        "votes-generate-blocks": cmd_votes_generate_blocks,
        "votes-validate-config": cmd_votes_validate_config,
        "vision-tag": cmd_vision_tag,
        "vision-label-clusters": cmd_vision_label_clusters,
        "validate-bias": cmd_validate_bias,
        "validate-calendar": cmd_validate_calendar,
        "serve": cmd_serve,
        "run-all": cmd_run_all,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)
