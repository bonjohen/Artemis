"""Generate synthetic votes from voting block configurations with attribute-based bias."""

from __future__ import annotations

import hashlib
import json
import random

import duckdb

from artemis_calendar.config.settings import OUTPUT_ROOT
from artemis_calendar.observe.logging import get_logger
from artemis_calendar.observe.run_manifest import create_run_record, generate_run_id, update_run_status
from artemis_calendar.vision.voting_config import (
    VotingBlockConfig,
    VotingScenarioConfig,
    save_scenario_to_db,
)

logger = get_logger("artemis.synthetic.blocks")

BATCH_SHOW_COUNT = 50
BATCH_SELECT_COUNT = 5
VOTING_OUTPUT_DIR = OUTPUT_ROOT / "voting_blocks"


def load_image_attributes(
    conn: duckdb.DuckDBPyConnection,
) -> dict[int, set[str]]:
    """Load accepted attributes for all vote-pool images. Returns {image_sk: {attr_codes}}."""
    rows = conn.execute(
        """
        SELECT fa.image_sk, fa.attribute_code
        FROM feature_image_attribute fa
        JOIN dim_image di ON fa.image_sk = di.image_sk
        WHERE di.vote_pool_flag = true AND fa.is_accepted = true
        """
    ).fetchall()

    image_attrs: dict[int, set[str]] = {}
    for image_sk, code in rows:
        image_sk = int(image_sk)
        if image_sk not in image_attrs:
            image_attrs[image_sk] = set()
        image_attrs[image_sk].add(code)
    return image_attrs


def compute_attribute_match(
    image_attrs: set[str],
    block: VotingBlockConfig,
) -> float:
    """Compute how well an image matches a block's preference rules.

    Returns a score in [0, 1] where 1 = perfect match.
    """
    if not block.preference_rules.all_of and not block.preference_rules.any_of:
        return 0.0  # Neutral block — no attribute preference

    score = 0.0
    max_score = 0.0

    # all_of: each required attribute present = +1
    if block.preference_rules.all_of:
        max_score += len(block.preference_rules.all_of)
        for code in block.preference_rules.all_of:
            if code in image_attrs:
                score += 1.0

    # any_of: at least one present = +1
    if block.preference_rules.any_of:
        max_score += 1.0
        if any(code in image_attrs for code in block.preference_rules.any_of):
            score += 1.0

    # none_of: each excluded attribute absent = +0.5 (penalty, not reward)
    if block.preference_rules.none_of:
        for code in block.preference_rules.none_of:
            if code in image_attrs:
                score -= 0.5  # Penalty for having excluded attribute

    return score / max(max_score, 1.0)


def compute_block_utility(
    image_attrs: set[str],
    block: VotingBlockConfig,
    base_appeal: float,
    rng: random.Random,
) -> float:
    """Compute synthetic utility for a voter-image pair in a voting block.

    utility = base_appeal
            + preference_weight * attribute_match_score
            + randomness_weight * noise
    """
    match_score = compute_attribute_match(image_attrs, block)
    noise = rng.gauss(0, 0.3)

    return (
        base_appeal
        + block.preference_weight * match_score
        + block.randomness_weight * noise
    )


def generate_block_votes(
    conn: duckdb.DuckDBPyConnection,
    config: VotingScenarioConfig,
    *,
    replace_run: bool = False,
) -> dict:
    """Generate synthetic votes from a voting block configuration.

    Returns summary dict with counts.
    """
    synthetic_run_id = generate_run_id()
    rng = random.Random(config.seed)

    run_id = generate_run_id()
    create_run_record(
        conn,
        run_id=run_id,
        pipeline_name="generate-block-votes",
        dataset_name="synthetic_block_votes",
        source_name=config.scenario_id,
    )

    # Save scenario to DB
    save_scenario_to_db(conn, config)

    # Clean previous block vote data for this scenario if replacing
    if replace_run:
        conn.execute(
            "DELETE FROM synthetic_voter_block_assignment WHERE scenario_id = ?",
            [config.scenario_id],
        )
        # Clean votes from this scenario's voters
        conn.execute(
            """DELETE FROM fact_batch_ballot_image WHERE synthetic_run_id IN (
                SELECT synthetic_run_id FROM synthetic_voter_block_assignment
                WHERE scenario_id = ?)""",
            [config.scenario_id],
        )

    # Load image data
    image_attrs = load_image_attributes(conn)
    all_image_sks = list(image_attrs.keys())

    if not all_image_sks:
        # Fallback: use all vote-pool images without attributes
        all_image_sks = [
            int(r[0])
            for r in conn.execute(
                "SELECT image_sk FROM dim_image WHERE vote_pool_flag = true"
            ).fetchall()
        ]
        image_attrs = {sk: set() for sk in all_image_sks}

    if not all_image_sks:
        logger.warning("No vote-pool images found")
        update_run_status(conn, run_id, load_status="failed", failure_message="No images")
        return {"error": "No vote-pool images"}

    # Generate base appeal scores (deterministic from image SK + seed)
    base_appeals = {}
    for sk in all_image_sks:
        h = hashlib.sha256(f"appeal:{sk}:{config.seed}".encode()).hexdigest()
        base_appeals[sk] = int(h[:8], 16) / 0xFFFFFFFF

    logger.info(
        f"Generating votes for scenario {config.scenario_id!r}: "
        f"{config.total_voters} voters, {config.total_votes} votes, "
        f"{len(all_image_sks)} images"
    )

    total_voters = 0
    total_ballots = 0
    total_ballot_images = 0
    block_summaries = []

    for block in config.blocks:
        block_voters = []

        # Create voters for this block
        for i in range(block.voter_count):
            voter_hash = hashlib.sha256(
                f"block:{config.scenario_id}:{block.block_id}:{config.seed}:{i}".encode()
            ).hexdigest()[:16]

            conn.execute(
                """INSERT INTO dim_voter
                   (voter_public_hash, synthetic_flag, synthetic_run_id, synthetic_profile_code)
                   VALUES (?, true, ?, ?)""",
                [voter_hash, synthetic_run_id, f"block_{block.block_id}"],
            )
            voter_sk = conn.execute(
                "SELECT currval('seq_voter_sk')"
            ).fetchone()[0]

            # Record block assignment
            conn.execute(
                """INSERT INTO synthetic_voter_block_assignment
                   (voter_sk, synthetic_run_id, scenario_id, block_id, synthetic_profile_code)
                   VALUES (?, ?, ?, ?, ?)""",
                [voter_sk, synthetic_run_id, config.scenario_id,
                 block.block_id, f"block_{block.block_id}"],
            )

            block_voters.append(voter_sk)

        total_voters += len(block_voters)

        # Generate batch ballots for each voter
        block_ballot_count = 0
        block_ballot_images = 0
        selected_image_counts: dict[int, int] = {}

        for voter_sk in block_voters:
            for _ in range(block.votes_per_voter):
                # Create vote session
                conn.execute(
                    """INSERT INTO fact_vote_session
                       (voter_sk, vote_mode, synthetic_flag, synthetic_run_id)
                       VALUES (?, 'batch_pick_5_of_50', true, ?)""",
                    [voter_sk, synthetic_run_id],
                )
                session_sk = conn.execute(
                    "SELECT currval('seq_vote_session_sk')"
                ).fetchone()[0]

                # Create ballot
                conn.execute(
                    """INSERT INTO fact_batch_ballot
                       (vote_session_sk, voter_sk, shown_count, selected_count,
                        synthetic_flag, synthetic_run_id)
                       VALUES (?, ?, ?, ?, true, ?)""",
                    [session_sk, voter_sk, BATCH_SHOW_COUNT,
                     BATCH_SELECT_COUNT, synthetic_run_id],
                )
                ballot_sk = conn.execute(
                    "SELECT currval('seq_batch_ballot_sk')"
                ).fetchone()[0]

                # Sample images to show
                shown = rng.sample(
                    all_image_sks,
                    min(BATCH_SHOW_COUNT, len(all_image_sks)),
                )

                # Score and select
                scored = []
                for pos, img_sk in enumerate(shown):
                    attrs = image_attrs.get(img_sk, set())
                    u = compute_block_utility(
                        attrs, block, base_appeals[img_sk], rng
                    )
                    scored.append((img_sk, pos, u))

                scored.sort(key=lambda x: x[2], reverse=True)
                selected_sks = {s[0] for s in scored[:BATCH_SELECT_COUNT]}

                # Track selections
                for sk in selected_sks:
                    selected_image_counts[sk] = selected_image_counts.get(sk, 0) + 1

                # Insert ballot images
                for img_sk, pos, _ in scored:
                    conn.execute(
                        """INSERT INTO fact_batch_ballot_image
                           (batch_ballot_sk, voter_sk, image_sk,
                            display_position, was_selected,
                            synthetic_flag, synthetic_run_id)
                           VALUES (?, ?, ?, ?, ?, true, ?)""",
                        [ballot_sk, voter_sk, img_sk, pos,
                         img_sk in selected_sks, synthetic_run_id],
                    )
                    block_ballot_images += 1

                block_ballot_count += 1

        total_ballots += block_ballot_count
        total_ballot_images += block_ballot_images

        # Build block summary
        top_selected = sorted(
            selected_image_counts.items(), key=lambda x: -x[1]
        )[:10]

        block_summaries.append({
            "block_id": block.block_id,
            "label": block.label,
            "voter_count": len(block_voters),
            "ballot_count": block_ballot_count,
            "ballot_image_count": block_ballot_images,
            "top_selected_images": [
                {"image_sk": sk, "selection_count": c}
                for sk, c in top_selected
            ],
        })

        logger.info(
            f"Block {block.block_id!r}: {len(block_voters)} voters, "
            f"{block_ballot_count} ballots, {block_ballot_images} ballot images"
        )

    # Write output summary
    output_dir = VOTING_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "generated_vote_summary.json"
    summary = {
        "scenario_id": config.scenario_id,
        "scenario_name": config.scenario_name,
        "synthetic_run_id": synthetic_run_id,
        "seed": config.seed,
        "total_voters": total_voters,
        "total_ballots": total_ballots,
        "total_ballot_images": total_ballot_images,
        "blocks": block_summaries,
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    update_run_status(
        conn, run_id,
        row_count_raw=total_ballots,
        row_count_loaded=total_ballot_images,
        load_status="complete",
    )

    logger.info(
        f"Block vote generation complete: {total_voters} voters, "
        f"{total_ballots} ballots, {total_ballot_images} ballot images"
    )
    summary["output_path"] = str(summary_path)
    return summary
