# Lesson 013: Elo Rating for Image Comparison

## Problem

The Artemis pairwise voting mode shows two images side by side and asks "which is better?" This produces binary outcomes (winner / loser) for specific pairs, not absolute ratings. We need to convert these relative comparisons into a single continuous strength score per image that can be combined with other preference signals.

## Why It Matters

Pairwise comparisons are the strongest form of preference data — voters make a direct choice between two specific alternatives, eliminating the ambiguity of batch voting (where "not selected" could mean "not seen" or "seen but beaten by 5 stronger options"). However, pairwise data only covers a tiny fraction of possible image pairs, so the conversion to scores must be robust to sparsity.

## Design Choice: Standard Elo with K=32

We use the classic **Elo rating system** with K-factor 32 and starting rating 1500.

### Key terms

- **Elo rating system**: Originally designed for chess rankings by Arpad Elo. Each player (image) has a rating that goes up when they win and down when they lose. The amount of change depends on the expected outcome — beating a strong opponent gains more rating than beating a weak one.

- **Expected score formula**: E_winner = 1 / (1 + 10^((R_loser - R_winner) / 400)). This is a logistic function. If two images have equal ratings, each has a 50% expected win rate. A 400-point rating gap corresponds to a 10:1 expected win ratio.

- **K-factor**: Controls how much a single comparison moves the ratings. K=32 is moderate — each comparison can move ratings by up to 32 points. Higher K (e.g., 64) converges faster but is noisier; lower K (e.g., 16) is more stable but needs more data.

- **Logistic model**: Elo assumes the probability of winning follows a logistic function of the rating difference. This is the same assumption underlying logistic regression. The 400-point scale factor (the divisor in the exponent) is an arbitrary convention from chess — it determines the rating spread.

- **Connected vs. disconnected comparison graphs**: A comparison graph has images as nodes and comparisons as edges. If image A beats B and B beats C, we can infer A is probably better than C — this requires a path from A to C in the graph. A **connected** graph has a path between every pair of nodes. A **disconnected** graph has isolated components where no inference can cross between them. With 2,000 comparisons across 12,217 images, the Artemis graph is overwhelmingly disconnected — most images have never been compared to each other, and many appear in zero comparisons.

### Why this matters for Elo vs. BTL

Elo processes comparisons sequentially and assigns a default rating (1500) to first-seen images. This means images in disconnected components get comparable starting ratings and diverge based on local win/loss patterns — the scores are meaningful within a component but not perfectly calibrated across components.

Bradley-Terry-Luce (see lesson 014) tries to solve this by fitting all parameters simultaneously, but it mathematically requires connectivity. Elo's sequential approach is more forgiving of disconnection.

## Alternatives Considered

1. **Win rate**: Raw wins / (wins + losses). Simple but doesn't account for opponent strength.
2. **Glicko-2**: Elo variant that tracks rating uncertainty. More principled but adds complexity we don't need with synthetic data.
3. **TrueSkill**: Microsoft's Bayesian rating system. Designed for multiplayer games; overkill for pairwise comparisons.
4. **Bradley-Terry-Luce**: Maximum likelihood estimation. Deferred due to disconnected graph (see lesson 014).

## What Was Learned

Elo is the right default for pairwise comparison data — it's simple, well-understood, and degrades gracefully with sparse data. The main caveat is that Elo ratings are sensitive to the order comparisons are processed. With 2,000 comparisons processed in database insertion order (which mirrors vote submission order), this ordering effect is minimal. K=32 was chosen as a balance between responsiveness and stability — with more data, K=16 would be more appropriate to reduce noise.
