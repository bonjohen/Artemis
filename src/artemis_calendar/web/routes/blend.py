"""Voter blend simulator — in-memory synthetic voting with attribute-biased blocks."""

from __future__ import annotations

import hashlib
import random
from collections import defaultdict

import duckdb
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from artemis_calendar.synthetic.block_generator import (
    BATCH_SELECT_COUNT,
    BATCH_SHOW_COUNT,
    compute_attribute_match,
    compute_block_utility,
)
from artemis_calendar.vision.voting_config import PreferenceRule, VotingBlockConfig
from artemis_calendar.web.db import get_db

router = APIRouter(prefix="/api/blend", tags=["blend"])

SAMPLES_PER_BLOCK = 3  # Number of example ballots to capture per block
DEFAULT_MIN_CONFIDENCE = 0.90  # Higher than the global 0.80 acceptance threshold
DEFAULT_MAX_DARK_RATIO = 0.92  # Exclude images that are >= 92% dark pixels


def _load_simulation_images(
    conn: duckdb.DuckDBPyConnection,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    max_dark_ratio: float = DEFAULT_MAX_DARK_RATIO,
) -> tuple[dict[int, set[str]], dict[int, str]]:
    """Load images eligible for simulation with quality-filtered attributes.

    Filters:
    - Vote-pool images only
    - Excludes non-master dedup members (near-duplicates)
    - Excludes images that are >= max_dark_ratio dark pixels
    - Only includes attributes with confidence >= min_confidence

    Returns (image_attrs, sid_map) where:
    - image_attrs: {image_sk: {attribute_codes}}
    - sid_map: {image_sk: source_image_id}
    """
    # Get eligible image SKs: vote-pool, not suppressed duplicate, not too dark
    eligible_rows = conn.execute(
        """
        SELECT di.image_sk, di.source_image_id
        FROM dim_image di
        LEFT JOIN feature_image_visual v ON v.image_sk = di.image_sk
        WHERE di.vote_pool_flag = true
          AND di.image_sk NOT IN (
              SELECT image_sk FROM dedup_image_member WHERE is_master = false
          )
          AND COALESCE(v.dark_pixel_ratio, 0) < ?
        """,
        [max_dark_ratio],
    ).fetchall()

    eligible_sks = {int(r[0]) for r in eligible_rows}
    sid_map = {int(r[0]): r[1] for r in eligible_rows}

    # Load attributes only for eligible images at higher confidence
    attr_rows = conn.execute(
        """
        SELECT fa.image_sk, fa.attribute_code
        FROM feature_image_attribute fa
        WHERE fa.image_sk IN (SELECT UNNEST(?::BIGINT[]))
          AND fa.confidence_score >= ?
        """,
        [list(eligible_sks), min_confidence],
    ).fetchall()

    image_attrs: dict[int, set[str]] = {sk: set() for sk in eligible_sks}
    for image_sk, code in attr_rows:
        image_attrs[int(image_sk)].add(code)

    return image_attrs, sid_map

# ---------------------------------------------------------------------------
# Preset block definitions
# ---------------------------------------------------------------------------

PRESET_BLOCKS = [
    {
        "block_id": "earth_moon",
        "label": "Earth+Moon Fans",
        "description": "Prefer images showing both Earth and Moon together",
        "voter_count": 10,
        "votes_per_voter": 10,
        "preference_weight": 3.0,
        "randomness_weight": 0.5,
        "preference_rules": {"all_of": ["earth", "moon"], "any_of": [], "none_of": []},
    },
    {
        "block_id": "earth_only",
        "label": "Earth Only",
        "description": "Prefer Earth views without Moon or Sun",
        "voter_count": 10,
        "votes_per_voter": 10,
        "preference_weight": 3.0,
        "randomness_weight": 0.5,
        "preference_rules": {
            "all_of": ["earth"],
            "any_of": [],
            "none_of": ["moon", "sun"],
        },
    },
    {
        "block_id": "moon_only",
        "label": "Moon Only",
        "description": "Prefer Moon views without Earth or Sun",
        "voter_count": 10,
        "votes_per_voter": 10,
        "preference_weight": 3.0,
        "randomness_weight": 0.5,
        "preference_rules": {
            "all_of": ["moon"],
            "any_of": [],
            "none_of": ["earth", "sun"],
        },
    },
    {
        "block_id": "sun_only",
        "label": "Sun Only",
        "description": "Prefer images featuring the Sun without Earth or Moon",
        "voter_count": 10,
        "votes_per_voter": 10,
        "preference_weight": 3.0,
        "randomness_weight": 0.5,
        "preference_rules": {
            "all_of": ["sun"],
            "any_of": [],
            "none_of": ["earth", "moon"],
        },
    },
    {
        "block_id": "crescent",
        "label": "Crescent Fans",
        "description": "Prefer crescent shapes — crescent Moon or crescent Earth",
        "voter_count": 10,
        "votes_per_voter": 10,
        "preference_weight": 3.0,
        "randomness_weight": 0.5,
        "preference_rules": {
            "all_of": [],
            "any_of": ["crescent_moon", "crescent_earth"],
            "none_of": [],
        },
    },
    {
        "block_id": "eclipse",
        "label": "Eclipse / Sun+Moon",
        "description": "Prefer images with Sun and Moon together, or Sun with lens flare",
        "voter_count": 10,
        "votes_per_voter": 10,
        "preference_weight": 3.0,
        "randomness_weight": 0.5,
        "preference_rules": {
            "all_of": [],
            "any_of": ["sun", "lens_flare"],
            "none_of": [],
        },
    },
    {
        "block_id": "crew",
        "label": "Crew / People",
        "description": "Prefer images showing astronauts, crew, hands, or selfies",
        "voter_count": 10,
        "votes_per_voter": 10,
        "preference_weight": 3.0,
        "randomness_weight": 0.5,
        "preference_rules": {
            "all_of": [],
            "any_of": ["astronaut", "crew", "hand", "selfie"],
            "none_of": [],
        },
    },
    {
        "block_id": "equipment",
        "label": "Equipment / Hardware",
        "description": "Prefer images of spacecraft, vehicles, habitat, or interior views",
        "voter_count": 10,
        "votes_per_voter": 10,
        "preference_weight": 3.0,
        "randomness_weight": 0.5,
        "preference_rules": {
            "all_of": [],
            "any_of": ["spacecraft", "vehicle", "habitat", "interior", "porthole"],
            "none_of": [],
        },
    },
    {
        "block_id": "moon_sun",
        "label": "Moon+Sun Fans",
        "description": "Prefer images showing Moon and Sun together",
        "voter_count": 10,
        "votes_per_voter": 10,
        "preference_weight": 3.0,
        "randomness_weight": 0.5,
        "preference_rules": {"all_of": ["moon", "sun"], "any_of": [], "none_of": []},
    },
    {
        "block_id": "neutral",
        "label": "Neutral",
        "description": "No attribute preference — votes by general appeal + noise",
        "voter_count": 10,
        "votes_per_voter": 10,
        "preference_weight": 0.0,
        "randomness_weight": 1.0,
        "preference_rules": {"all_of": [], "any_of": [], "none_of": []},
    },
]


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class BlockInput(BaseModel):
    block_id: str
    label: str = ""
    voter_count: int = Field(ge=0, le=200)
    votes_per_voter: int = Field(default=10, ge=1, le=50)
    preference_weight: float = Field(default=3.0, ge=0.0, le=10.0)
    randomness_weight: float = Field(default=0.5, ge=0.0, le=5.0)
    preference_rules: dict = Field(
        default_factory=lambda: {"all_of": [], "any_of": [], "none_of": []}
    )


class BlendRequest(BaseModel):
    blocks: list[BlockInput]
    seed: int = 42
    min_confidence: float = Field(default=DEFAULT_MIN_CONFIDENCE, ge=0.5, le=1.0)
    max_dark_ratio: float = Field(default=DEFAULT_MAX_DARK_RATIO, ge=0.5, le=1.0)


class ImageResult(BaseModel):
    image_sk: int
    nasa_id: str
    selection_rate: float
    selection_count: int
    shown_count: int


class BallotImage(BaseModel):
    image_sk: int
    nasa_id: str
    utility: float
    attribute_match: float
    base_appeal: float
    was_selected: bool
    matched_attrs: list[str]


class SampleBallot(BaseModel):
    voter_number: int
    ballot_number: int
    block_id: str
    images: list[BallotImage]


class BlockResult(BaseModel):
    block_id: str
    label: str
    voter_count: int
    ballot_count: int
    top_13: list[ImageResult]
    sample_ballots: list[SampleBallot]


class BlendResponse(BaseModel):
    seed: int
    total_voters: int
    total_ballots: int
    eligible_images: int
    min_confidence: float
    max_dark_ratio: float
    blocks: list[BlockResult]
    blended: list[ImageResult]
    overlap: dict[str, list[int]]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/presets")
def get_presets(conn: duckdb.DuckDBPyConnection = Depends(get_db)):
    """Return preset block configs and available attribute codes."""
    try:
        rows = conn.execute(
            "SELECT DISTINCT attribute_code FROM feature_image_attribute "
            "WHERE is_accepted = true ORDER BY attribute_code"
        ).fetchall()
        attributes = [r[0] for r in rows]
    except Exception:
        attributes = []

    return {"blocks": PRESET_BLOCKS, "attributes": attributes}


@router.post("/simulate", response_model=BlendResponse)
def simulate(req: BlendRequest, conn: duckdb.DuckDBPyConnection = Depends(get_db)):
    """Run in-memory voting simulation and return per-block + blended top-13."""
    if not req.blocks:
        raise HTTPException(400, "At least one block required")

    active_blocks = [b for b in req.blocks if b.voter_count > 0]
    if not active_blocks:
        raise HTTPException(400, "At least one block must have voter_count > 0")

    # Load filtered images: no duplicates, no near-black, higher confidence
    image_attrs, sid_map = _load_simulation_images(
        conn,
        min_confidence=req.min_confidence,
        max_dark_ratio=req.max_dark_ratio,
    )
    all_image_sks = list(image_attrs.keys())

    if not all_image_sks:
        raise HTTPException(500, "No eligible images found after filtering")

    # Generate deterministic base appeal per image (same as block_generator)
    base_appeals = {}
    for sk in all_image_sks:
        h = hashlib.sha256(f"appeal:{sk}:{req.seed}".encode()).hexdigest()
        base_appeals[sk] = int(h[:8], 16) / 0xFFFFFFFF

    # Simulate voting per block
    total_voters = 0
    total_ballots = 0
    blended_selected: dict[int, int] = defaultdict(int)
    blended_shown: dict[int, int] = defaultdict(int)
    block_results: list[BlockResult] = []

    for block_input in active_blocks:
        block_config = VotingBlockConfig(
            block_id=block_input.block_id,
            label=block_input.label or block_input.block_id,
            voter_count=block_input.voter_count,
            votes_per_voter=block_input.votes_per_voter,
            preference_rules=PreferenceRule(
                all_of=block_input.preference_rules.get("all_of", []),
                any_of=block_input.preference_rules.get("any_of", []),
                none_of=block_input.preference_rules.get("none_of", []),
            ),
            preference_weight=block_input.preference_weight,
            randomness_weight=block_input.randomness_weight,
        )

        rng = random.Random(req.seed + hash(block_input.block_id))
        selected_counts: dict[int, int] = defaultdict(int)
        shown_counts: dict[int, int] = defaultdict(int)
        ballot_count = 0
        sample_ballots: list[SampleBallot] = []

        # Decide which ballots to capture as samples.
        # Capture the 1st ballot of the 1st, middle, and last voter.
        sample_voter_indices = set()
        if block_input.voter_count >= 3:
            sample_voter_indices = {0, block_input.voter_count // 2, block_input.voter_count - 1}
        elif block_input.voter_count > 0:
            sample_voter_indices = {0}

        for voter_i in range(block_input.voter_count):
            for vote_i in range(block_input.votes_per_voter):
                shown = rng.sample(
                    all_image_sks, min(BATCH_SHOW_COUNT, len(all_image_sks))
                )
                scored = []
                for img_sk in shown:
                    attrs = image_attrs.get(img_sk, set())
                    u = compute_block_utility(
                        attrs, block_config, base_appeals[img_sk], rng
                    )
                    scored.append((img_sk, u))

                scored.sort(key=lambda x: x[1], reverse=True)
                winners = {s[0] for s in scored[:BATCH_SELECT_COUNT]}

                # Capture sample ballot (1st ballot of selected voters)
                if voter_i in sample_voter_indices and vote_i == 0:
                    # Build the preference rules' attribute set for matching display
                    rule_attrs = set(
                        block_input.preference_rules.get("all_of", [])
                        + block_input.preference_rules.get("any_of", [])
                    )

                    ballot_images = []
                    for img_sk, utility in scored:
                        attrs = image_attrs.get(img_sk, set())
                        match_score = compute_attribute_match(attrs, block_config)
                        matched = sorted(attrs & rule_attrs) if rule_attrs else []
                        ballot_images.append(
                            BallotImage(
                                image_sk=img_sk,
                                nasa_id=sid_map.get(img_sk, ""),
                                utility=round(utility, 4),
                                attribute_match=round(match_score, 4),
                                base_appeal=round(base_appeals[img_sk], 4),
                                was_selected=img_sk in winners,
                                matched_attrs=matched,
                            )
                        )

                    sample_ballots.append(
                        SampleBallot(
                            voter_number=voter_i + 1,
                            ballot_number=vote_i + 1,
                            block_id=block_input.block_id,
                            images=ballot_images,
                        )
                    )

                for img_sk, _ in scored:
                    shown_counts[img_sk] += 1
                    blended_shown[img_sk] += 1
                    if img_sk in winners:
                        selected_counts[img_sk] += 1
                        blended_selected[img_sk] += 1

                ballot_count += 1

        total_voters += block_input.voter_count
        total_ballots += ballot_count

        # Compute selection rates and pick top-13
        rates = {
            sk: selected_counts[sk] / max(shown_counts[sk], 1)
            for sk in all_image_sks
            if shown_counts[sk] > 0
        }
        top_sks = sorted(rates, key=rates.get, reverse=True)[:13]

        block_results.append(
            BlockResult(
                block_id=block_input.block_id,
                label=block_input.label or block_input.block_id,
                voter_count=block_input.voter_count,
                ballot_count=ballot_count,
                top_13=[
                    ImageResult(
                        image_sk=sk,
                        nasa_id=sid_map.get(sk, ""),
                        selection_rate=rates.get(sk, 0.0),
                        selection_count=selected_counts[sk],
                        shown_count=shown_counts[sk],
                    )
                    for sk in top_sks
                ],
                sample_ballots=sample_ballots,
            )
        )

    # Blended top-13
    blended_rates = {
        sk: blended_selected[sk] / max(blended_shown[sk], 1)
        for sk in all_image_sks
        if blended_shown[sk] > 0
    }
    blended_top_sks = sorted(blended_rates, key=blended_rates.get, reverse=True)[:13]
    blended_top_set = set(blended_top_sks)

    blended_results = [
        ImageResult(
            image_sk=sk,
            nasa_id=sid_map.get(sk, ""),
            selection_rate=blended_rates.get(sk, 0.0),
            selection_count=blended_selected[sk],
            shown_count=blended_shown[sk],
        )
        for sk in blended_top_sks
    ]

    # Compute overlap: which block top-13 images also appear in blended top-13
    overlap: dict[str, list[int]] = {}
    for br in block_results:
        block_top_set = {img.image_sk for img in br.top_13}
        shared = sorted(block_top_set & blended_top_set)
        overlap[br.block_id] = shared

    return BlendResponse(
        seed=req.seed,
        total_voters=total_voters,
        total_ballots=total_ballots,
        eligible_images=len(all_image_sks),
        min_confidence=req.min_confidence,
        max_dark_ratio=req.max_dark_ratio,
        blocks=block_results,
        blended=blended_results,
        overlap=overlap,
    )
