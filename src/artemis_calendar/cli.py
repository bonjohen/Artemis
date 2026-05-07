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
        "run-all": cmd_run_all,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)
