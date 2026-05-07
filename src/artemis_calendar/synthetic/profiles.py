"""Synthetic voter profile definitions for MVP testing."""

from dataclasses import dataclass


@dataclass
class VoterProfile:
    code: str
    description: str
    general_appeal_weight: float
    visual_drama_weight: float
    cover_value_weight: float
    position_bias_strength: float
    randomness_level: float
    population_share: float


# MVP profiles — 4 voter types matching the plan
PROFILES = [
    VoterProfile(
        code="neutral",
        description="Reasonable general audience — prefers high-appeal images with some randomness",
        general_appeal_weight=0.7,
        visual_drama_weight=0.2,
        cover_value_weight=0.1,
        position_bias_strength=0.0,
        randomness_level=0.15,
        population_share=0.60,
    ),
    VoterProfile(
        code="visual_drama",
        description="Strongly prefers dramatic Earth/Moon/space images",
        general_appeal_weight=0.3,
        visual_drama_weight=0.6,
        cover_value_weight=0.1,
        position_bias_strength=0.0,
        randomness_level=0.10,
        population_share=0.20,
    ),
    VoterProfile(
        code="position_biased",
        description="Biased by display position — prefers images shown earlier in batch",
        general_appeal_weight=0.5,
        visual_drama_weight=0.1,
        cover_value_weight=0.0,
        position_bias_strength=0.4,
        randomness_level=0.20,
        population_share=0.10,
    ),
    VoterProfile(
        code="random",
        description="Random voter — no stable preference pattern",
        general_appeal_weight=0.1,
        visual_drama_weight=0.1,
        cover_value_weight=0.0,
        position_bias_strength=0.0,
        randomness_level=0.80,
        population_share=0.10,
    ),
]


def get_profile_by_code(code: str) -> VoterProfile:
    for p in PROFILES:
        if p.code == code:
            return p
    raise ValueError(f"Unknown profile code: {code}")
