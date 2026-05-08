"""Voting block configuration: schema validation, loading, and dry-run analysis."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import duckdb
import yaml

from artemis_calendar.config.settings import PROJECT_ROOT
from artemis_calendar.observe.logging import get_logger
from artemis_calendar.vision.attributes import AttributeVocabulary, load_attribute_vocabulary

logger = get_logger("artemis.vision.voting_config")

DEFAULT_CONFIG_DIR = PROJECT_ROOT / "config" / "voting_blocks"


@dataclass
class PreferenceRule:
    all_of: list[str] = field(default_factory=list)
    any_of: list[str] = field(default_factory=list)
    none_of: list[str] = field(default_factory=list)


@dataclass
class VotingBlockConfig:
    block_id: str
    label: str
    voter_count: int
    votes_per_voter: int
    preference_rules: PreferenceRule
    preference_weight: float = 0.0
    randomness_weight: float = 1.0
    description: str = ""


@dataclass
class VotingScenarioConfig:
    scenario_id: str
    scenario_name: str
    description: str
    seed: int
    blocks: list[VotingBlockConfig]

    @property
    def total_voters(self) -> int:
        return sum(b.voter_count for b in self.blocks)

    @property
    def total_votes(self) -> int:
        return sum(b.voter_count * b.votes_per_voter for b in self.blocks)

    @property
    def config_hash(self) -> str:
        """Deterministic hash of the scenario config for change detection."""
        data = {
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "blocks": [
                {
                    "block_id": b.block_id,
                    "voter_count": b.voter_count,
                    "votes_per_voter": b.votes_per_voter,
                    "preference_weight": b.preference_weight,
                    "randomness_weight": b.randomness_weight,
                    "rules": {
                        "all_of": sorted(b.preference_rules.all_of),
                        "any_of": sorted(b.preference_rules.any_of),
                        "none_of": sorted(b.preference_rules.none_of),
                    },
                }
                for b in self.blocks
            ],
        }
        return hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()[:16]


def load_voting_config(config_path: Path) -> VotingScenarioConfig:
    """Load and parse a voting block YAML config file."""
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    blocks = []
    for block_data in data.get("blocks", []):
        rules_data = block_data.get("preference_rules", {})
        rule = PreferenceRule(
            all_of=rules_data.get("all_of", []),
            any_of=rules_data.get("any_of", []),
            none_of=rules_data.get("none_of", []),
        )
        blocks.append(
            VotingBlockConfig(
                block_id=block_data["block_id"],
                label=block_data.get("label", block_data["block_id"]),
                voter_count=block_data["voter_count"],
                votes_per_voter=block_data["votes_per_voter"],
                preference_rules=rule,
                preference_weight=block_data.get("preference_weight", 0.0),
                randomness_weight=block_data.get("randomness_weight", 1.0),
                description=block_data.get("description", ""),
            )
        )

    return VotingScenarioConfig(
        scenario_id=data["scenario_id"],
        scenario_name=data.get("scenario_name", data["scenario_id"]),
        description=data.get("description", ""),
        seed=data.get("seed", 42),
        blocks=blocks,
    )


def validate_voting_config(
    config: VotingScenarioConfig,
    vocab: AttributeVocabulary | None = None,
) -> list[str]:
    """Validate a voting scenario config. Returns list of error messages (empty = valid)."""
    if vocab is None:
        vocab = load_attribute_vocabulary()

    errors = []

    if not config.scenario_id:
        errors.append("scenario_id is required")

    if not config.blocks:
        errors.append("At least one voting block is required")

    # Check for duplicate block IDs
    block_ids = [b.block_id for b in config.blocks]
    seen = set()
    for bid in block_ids:
        if bid in seen:
            errors.append(f"Duplicate block_id: {bid!r}")
        seen.add(bid)

    # Validate each block
    all_codes = vocab.all_codes
    for block in config.blocks:
        if block.voter_count <= 0:
            errors.append(f"Block {block.block_id!r}: voter_count must be > 0")
        if block.votes_per_voter <= 0:
            errors.append(f"Block {block.block_id!r}: votes_per_voter must be > 0")

        # Validate attribute references in rules
        for code in block.preference_rules.all_of:
            if code not in all_codes:
                errors.append(
                    f"Block {block.block_id!r}: unknown attribute {code!r} in all_of"
                )
        for code in block.preference_rules.any_of:
            if code not in all_codes:
                errors.append(
                    f"Block {block.block_id!r}: unknown attribute {code!r} in any_of"
                )
        for code in block.preference_rules.none_of:
            if code not in all_codes:
                errors.append(
                    f"Block {block.block_id!r}: unknown attribute {code!r} in none_of"
                )

        # Check for contradictions (same code in all_of and none_of)
        overlap = set(block.preference_rules.all_of) & set(block.preference_rules.none_of)
        if overlap:
            errors.append(
                f"Block {block.block_id!r}: attributes {overlap} in both all_of and none_of"
            )

    return errors


@dataclass
class BlockDryRunResult:
    block_id: str
    label: str
    voter_count: int
    votes_per_voter: int
    matching_images: int
    warnings: list[str]


@dataclass
class DryRunResult:
    scenario_id: str
    scenario_name: str
    total_voters: int
    total_votes: int
    blocks: list[BlockDryRunResult]
    errors: list[str]


def dry_run(
    config: VotingScenarioConfig,
    conn: duckdb.DuckDBPyConnection,
    vocab: AttributeVocabulary | None = None,
) -> DryRunResult:
    """Validate config and count matching images per block without generating votes.

    An image matches a block's rules if:
    - all_of: image has accepted attributes for ALL listed codes
    - any_of: image has accepted attributes for ANY listed code (if non-empty)
    - none_of: image does NOT have accepted attributes for ANY listed code
    """
    if vocab is None:
        vocab = load_attribute_vocabulary()

    errors = validate_voting_config(config, vocab)
    block_results = []

    for block in config.blocks:
        warnings = []

        # Build SQL conditions for matching images
        conditions = []
        params = []

        if block.preference_rules.all_of:
            for code in block.preference_rules.all_of:
                conditions.append(
                    """EXISTS (
                        SELECT 1 FROM feature_image_attribute fa
                        WHERE fa.image_sk = di.image_sk
                          AND fa.attribute_code = ? AND fa.is_accepted = true
                    )"""
                )
                params.append(code)

        if block.preference_rules.none_of:
            for code in block.preference_rules.none_of:
                conditions.append(
                    """NOT EXISTS (
                        SELECT 1 FROM feature_image_attribute fa
                        WHERE fa.image_sk = di.image_sk
                          AND fa.attribute_code = ? AND fa.is_accepted = true
                    )"""
                )
                params.append(code)

        if block.preference_rules.any_of:
            placeholders = ", ".join("?" * len(block.preference_rules.any_of))
            conditions.append(
                f"""EXISTS (
                    SELECT 1 FROM feature_image_attribute fa
                    WHERE fa.image_sk = di.image_sk
                      AND fa.attribute_code IN ({placeholders})
                      AND fa.is_accepted = true
                )"""
            )
            params.extend(block.preference_rules.any_of)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT count(DISTINCT di.image_sk)
            FROM dim_image di
            WHERE di.vote_pool_flag = true AND {where_clause}
        """

        try:
            matching = conn.execute(query, params).fetchone()[0]
        except Exception:
            matching = 0
            warnings.append("Failed to count matching images (attributes may not be loaded)")

        if matching < block.votes_per_voter:
            warnings.append(
                f"Low image count ({matching}); consider lowering preference strength or adding fallback"
            )

        block_results.append(
            BlockDryRunResult(
                block_id=block.block_id,
                label=block.label,
                voter_count=block.voter_count,
                votes_per_voter=block.votes_per_voter,
                matching_images=matching,
                warnings=warnings,
            )
        )

    return DryRunResult(
        scenario_id=config.scenario_id,
        scenario_name=config.scenario_name,
        total_voters=config.total_voters,
        total_votes=config.total_votes,
        blocks=block_results,
        errors=errors,
    )


def save_scenario_to_db(
    conn: duckdb.DuckDBPyConnection,
    config: VotingScenarioConfig,
) -> None:
    """Persist scenario and block definitions to warehouse tables."""
    # Upsert scenario
    conn.execute(
        """
        INSERT INTO dim_voting_scenario (scenario_id, scenario_name, description, seed, config_hash)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (scenario_id) DO UPDATE SET
            scenario_name = EXCLUDED.scenario_name,
            description = EXCLUDED.description,
            seed = EXCLUDED.seed,
            config_hash = EXCLUDED.config_hash
        """,
        [config.scenario_id, config.scenario_name, config.description,
         config.seed, config.config_hash],
    )

    # Delete existing blocks and rules for this scenario
    conn.execute("DELETE FROM voting_block_rule WHERE scenario_id = ?", [config.scenario_id])
    conn.execute("DELETE FROM dim_voting_block WHERE scenario_id = ?", [config.scenario_id])

    for block in config.blocks:
        conn.execute(
            """
            INSERT INTO dim_voting_block
                (block_id, scenario_id, block_label, voter_count, votes_per_voter,
                 preference_weight, randomness_weight, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [block.block_id, config.scenario_id, block.label,
             block.voter_count, block.votes_per_voter,
             block.preference_weight, block.randomness_weight,
             block.description],
        )

        # Insert rules
        for rule_type, codes in [
            ("all_of", block.preference_rules.all_of),
            ("any_of", block.preference_rules.any_of),
            ("none_of", block.preference_rules.none_of),
        ]:
            for code in codes:
                conn.execute(
                    """
                    INSERT INTO voting_block_rule
                        (block_id, scenario_id, rule_type, attribute_code)
                    VALUES (?, ?, ?, ?)
                    """,
                    [block.block_id, config.scenario_id, rule_type, code],
                )

    logger.info(
        f"Saved scenario {config.scenario_id!r} with {len(config.blocks)} blocks"
    )
