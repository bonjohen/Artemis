"""Synthetic vote data generator for MVP testing."""

import hashlib
import random

import duckdb

from artemis_calendar.observe.logging import get_logger
from artemis_calendar.observe.run_manifest import create_run_record, generate_run_id, update_run_status
from artemis_calendar.synthetic.ground_truth import assign_ground_truth
from artemis_calendar.synthetic.profiles import PROFILES

logger = get_logger("artemis.synthetic")

BATCH_SHOW_COUNT = 50
BATCH_SELECT_COUNT = 5
CATEGORY_RANK_COUNT = 3


def _compute_utility(
    profile_code: str,
    appeal: float,
    drama: float,
    cover: float,
    position: int,
    rng: random.Random,
    profiles_map: dict,
) -> float:
    """Compute synthetic utility for a voter-image pair."""
    p = profiles_map[profile_code]
    utility = p.general_appeal_weight * appeal + p.visual_drama_weight * drama + p.cover_value_weight * cover
    # Position bias: earlier positions get a boost
    if p.position_bias_strength > 0 and position is not None:
        utility += p.position_bias_strength * max(0, 1.0 - position / BATCH_SHOW_COUNT)
    # Random noise
    utility += p.randomness_level * rng.gauss(0, 0.3)
    return utility


def generate_synthetic_votes(
    conn: duckdb.DuckDBPyConnection,
    seed: int = 42,
    voter_count: int = 100,
    ballot_count: int = 500,
    pair_count: int = 2000,
    ranking_count: int = 250,
) -> dict[str, int]:
    """Generate synthetic vote data. Returns row counts."""
    synthetic_run_id = generate_run_id()
    rng = random.Random(seed)
    profiles_map = {p.code: p for p in PROFILES}

    run_id = generate_run_id()
    create_run_record(
        conn,
        run_id=run_id,
        pipeline_name="generate-votes",
        dataset_name="synthetic",
        source_name="synthetic",
    )

    # Clear previous synthetic data for idempotent re-runs
    for table in [
        "fact_category_ranking_image",
        "fact_category_ranking",
        "fact_pairwise_vote",
        "fact_batch_ballot_image",
        "fact_batch_ballot",
        "fact_vote_session",
        "dim_voter",
    ]:
        conn.execute(f"DELETE FROM {table} WHERE synthetic_flag = true")
    conn.execute("DELETE FROM synthetic_image_truth")

    # Step 1: Assign ground truth
    logger.info("Assigning ground truth latent scores...")
    truth_count = assign_ground_truth(conn, synthetic_run_id, seed)
    logger.info(f"Ground truth assigned to {truth_count} images")

    # Load truth into memory for fast utility computation
    truth_rows = conn.execute(
        """SELECT image_sk, latent_general_appeal, latent_visual_drama, latent_cover_value
           FROM synthetic_image_truth WHERE synthetic_run_id = ?""",
        [synthetic_run_id],
    ).fetchall()
    image_truth = {row[0]: (row[1], row[2], row[3]) for row in truth_rows}
    all_image_sks = list(image_truth.keys())

    if not all_image_sks:
        logger.warning("No images with ground truth — cannot generate votes")
        update_run_status(conn, run_id, load_status="failed", failure_message="No images")
        return {}

    # Step 2: Create voters
    logger.info(f"Creating {voter_count} synthetic voters...")
    voters = []  # (voter_sk, profile_code)
    for i in range(voter_count):
        # Assign profile based on population shares
        r = rng.random()
        cumulative = 0.0
        profile_code = PROFILES[-1].code
        for p in PROFILES:
            cumulative += p.population_share
            if r < cumulative:
                profile_code = p.code
                break

        voter_hash = hashlib.sha256(f"voter:{seed}:{i}".encode()).hexdigest()[:16]
        conn.execute(
            """INSERT INTO dim_voter (voter_public_hash, synthetic_flag, synthetic_run_id, synthetic_profile_code)
               VALUES (?, true, ?, ?)""",
            [voter_hash, synthetic_run_id, profile_code],
        )
    # Fetch the created voter_sks
    voter_rows = conn.execute(
        "SELECT voter_sk, synthetic_profile_code FROM dim_voter WHERE synthetic_run_id = ?",
        [synthetic_run_id],
    ).fetchall()
    voters = [(row[0], row[1]) for row in voter_rows]
    logger.info(f"Created {len(voters)} voters")

    counts = {"dim_voter": len(voters)}

    # Step 3: Generate batch ballots
    logger.info(f"Generating {ballot_count} batch ballots...")
    ballot_images_total = 0
    for _b in range(ballot_count):
        voter_sk, profile_code = rng.choice(voters)

        # Create vote session
        conn.execute(
            """INSERT INTO fact_vote_session (voter_sk, vote_mode, synthetic_flag, synthetic_run_id)
               VALUES (?, 'batch_pick_5_of_50', true, ?)""",
            [voter_sk, synthetic_run_id],
        )
        session_sk = conn.execute("SELECT currval('seq_vote_session_sk')").fetchone()[0]

        # Create ballot
        conn.execute(
            """INSERT INTO fact_batch_ballot
               (vote_session_sk, voter_sk, shown_count, selected_count,
                synthetic_flag, synthetic_run_id)
               VALUES (?, ?, ?, ?, true, ?)""",
            [session_sk, voter_sk, BATCH_SHOW_COUNT, BATCH_SELECT_COUNT, synthetic_run_id],
        )
        ballot_sk = conn.execute("SELECT currval('seq_batch_ballot_sk')").fetchone()[0]

        # Sample 50 images to show
        shown = rng.sample(all_image_sks, min(BATCH_SHOW_COUNT, len(all_image_sks)))

        # Score and select top 5
        scored = []
        for pos, img_sk in enumerate(shown):
            appeal, drama, cover = image_truth[img_sk]
            u = _compute_utility(profile_code, appeal, drama, cover, pos, rng, profiles_map)
            scored.append((img_sk, pos, u))

        scored.sort(key=lambda x: x[2], reverse=True)
        selected_sks = {s[0] for s in scored[:BATCH_SELECT_COUNT]}

        # Insert ballot images
        ballot_image_rows = []
        for img_sk, pos, _ in scored:
            ballot_image_rows.append((ballot_sk, voter_sk, img_sk, pos, img_sk in selected_sks, True, synthetic_run_id))
        conn.executemany(
            """INSERT INTO fact_batch_ballot_image
               (batch_ballot_sk, voter_sk, image_sk, display_position, was_selected, synthetic_flag, synthetic_run_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ballot_image_rows,
        )
        ballot_images_total += len(ballot_image_rows)

    counts["fact_batch_ballot"] = ballot_count
    counts["fact_batch_ballot_image"] = ballot_images_total
    logger.info(f"Generated {ballot_count} ballots, {ballot_images_total} ballot images")

    # Step 4: Generate pairwise votes
    logger.info(f"Generating {pair_count} pairwise votes...")
    for _p in range(pair_count):
        voter_sk, profile_code = rng.choice(voters)

        conn.execute(
            """INSERT INTO fact_vote_session (voter_sk, vote_mode, synthetic_flag, synthetic_run_id)
               VALUES (?, 'pairwise_elo', true, ?)""",
            [voter_sk, synthetic_run_id],
        )
        session_sk = conn.execute("SELECT currval('seq_vote_session_sk')").fetchone()[0]

        left_sk, right_sk = rng.sample(all_image_sks, 2)

        left_appeal, left_drama, left_cover = image_truth[left_sk]
        right_appeal, right_drama, right_cover = image_truth[right_sk]

        left_u = _compute_utility(profile_code, left_appeal, left_drama, left_cover, 0, rng, profiles_map)
        right_u = _compute_utility(profile_code, right_appeal, right_drama, right_cover, 1, rng, profiles_map)

        if left_u >= right_u:
            winner_sk, loser_sk = left_sk, right_sk
        else:
            winner_sk, loser_sk = right_sk, left_sk

        conn.execute(
            """INSERT INTO fact_pairwise_vote
               (vote_session_sk, voter_sk, winner_image_sk, loser_image_sk, left_image_sk, right_image_sk,
                synthetic_flag, synthetic_run_id)
               VALUES (?, ?, ?, ?, ?, ?, true, ?)""",
            [session_sk, voter_sk, winner_sk, loser_sk, left_sk, right_sk, synthetic_run_id],
        )

    counts["fact_pairwise_vote"] = pair_count
    logger.info(f"Generated {pair_count} pairwise votes")

    # Step 5: Generate category rankings
    logger.info(f"Generating {ranking_count} category rankings...")
    categories = conn.execute("SELECT category_key FROM dim_category").fetchall()
    category_keys = [c[0] for c in categories] if categories else ["default"]

    ranking_images_total = 0
    for _r in range(ranking_count):
        voter_sk, profile_code = rng.choice(voters)
        cat_key = rng.choice(category_keys)

        conn.execute(
            """INSERT INTO fact_vote_session (voter_sk, vote_mode, category_key, synthetic_flag, synthetic_run_id)
               VALUES (?, 'category_top_3', ?, true, ?)""",
            [voter_sk, cat_key, synthetic_run_id],
        )
        session_sk = conn.execute("SELECT currval('seq_vote_session_sk')").fetchone()[0]

        conn.execute(
            """INSERT INTO fact_category_ranking
               (vote_session_sk, voter_sk, category_key, ranked_count, synthetic_flag, synthetic_run_id)
               VALUES (?, ?, ?, ?, true, ?)""",
            [session_sk, voter_sk, cat_key, CATEGORY_RANK_COUNT, synthetic_run_id],
        )
        ranking_sk = conn.execute("SELECT currval('seq_category_ranking_sk')").fetchone()[0]

        # Sample and rank images
        candidates = rng.sample(all_image_sks, min(10, len(all_image_sks)))
        scored = []
        for img_sk in candidates:
            appeal, drama, cover = image_truth[img_sk]
            u = _compute_utility(profile_code, appeal, drama, cover, None, rng, profiles_map)
            scored.append((img_sk, u))
        scored.sort(key=lambda x: x[1], reverse=True)
        top3 = scored[:CATEGORY_RANK_COUNT]

        for rank, (img_sk, _) in enumerate(top3, 1):
            borda = CATEGORY_RANK_COUNT - rank + 1  # 3 for rank 1, 2 for rank 2, 1 for rank 3
            conn.execute(
                """INSERT INTO fact_category_ranking_image
                   (category_ranking_sk, voter_sk, category_key, image_sk, rank_position, borda_score,
                    synthetic_flag, synthetic_run_id)
                   VALUES (?, ?, ?, ?, ?, ?, true, ?)""",
                [ranking_sk, voter_sk, cat_key, img_sk, rank, float(borda), synthetic_run_id],
            )
            ranking_images_total += 1

    counts["fact_category_ranking"] = ranking_count
    counts["fact_category_ranking_image"] = ranking_images_total
    logger.info(f"Generated {ranking_count} rankings, {ranking_images_total} ranked images")

    counts["synthetic_image_truth"] = truth_count
    update_run_status(conn, run_id, load_status="success", row_count_loaded=sum(counts.values()))
    logger.info(f"Synthetic generation complete: {counts}")
    return counts
