# Lesson 022: Heuristic Month-Fit Scoring Without Text Metadata

## The Lesson

When images lack text metadata (titles, descriptions, captions), month or season suitability can still be approximated from visual features alone — color temperature, brightness, contrast, and content flags. The signal is coarse (3-4 seasonal buckets, not 13 distinct months) but sufficient to prevent the worst mismatches and break ties in an optimizer.

## Context

A calendar optimization needed to assign 13 images to 13 months (December 2026 through December 2027). The 12,217 vote-pool images had visual features (brightness, contrast, saturation, dominant colors, content flags for Earth/Moon/crew/spacecraft) and CLIP embeddings, but zero text metadata — no titles, no descriptions, no captions. Month-fit scoring had to work entirely from visual signals.

## What Happened

1. Defined target profiles for each of 13 months: brightness level, color warmth, visual drama (contrast × saturation), and content-flag bonuses (e.g., Earth bonus for April/Earth Day, spacecraft bonus for launch month).
2. Extracted color temperature from dominant color JSON by converting RGB to HSV hue: warm hues (reds, oranges, 0-60° and 300-360°) map to warmth ≈ 1.0, cool hues (blues, cyans, 180-260°) map to warmth ≈ 0.0. Low-saturation images (common in space photos) get neutral warmth (0.5) to avoid penalizing dark space scenes.
3. Scored each image against each month as: 1 - weighted_distance(image_features, month_profile), with content-flag bonuses added. Weights: 30% brightness distance, 35% warmth distance, 35% drama distance.
4. Observed that most space images cluster in the low-brightness, low-saturation, cool-temperature region. Month-fit scores were compressed — most images scored similarly for most months (range ~0.5-0.85). The signal discriminates at the margins, not across the full range.
5. Used month-fit at 15% weight in the MMR greedy selector — enough to break ties but not enough to override strong preference signals.
6. The Hungarian algorithm for month assignment showed that even coarse month-fit signals produce meaningfully different assignments than random: Method D (month-first) achieved total month-fit of 10.5 vs. Method A's 8.5.

## Key Insights

- **Coarse signal beats no signal.** A heuristic that distinguishes "warm bright summer" from "dark dramatic winter" in 3-4 buckets is enough to prevent bad assignments (bright warm Earth shot on a November page). It doesn't need to distinguish March from April.

- **Space imagery has compressed visual feature distributions.** Most mission photos are dark, low-saturation, and cool-toned. The month-fit heuristic works best on the minority of images that have distinctive visual properties (bright Earth views, warm-toned crew shots). For the majority, month-fit is near-neutral — and that's fine.

- **Weight the signal by its reliability.** At 15% of the objective, month-fit breaks ties between otherwise-equal images but can't override a strong preference gap. This matches the signal's quality — it's a heuristic, not a measurement.

- **Content flags provide the strongest month discrimination.** An image with `has_earth_flag=true` gets a bonus for April (Earth Day). An image with `has_spacecraft_flag=true` gets a bonus for December 2026 (launch month). These categorical signals are more informative than continuous visual features for month assignment.

- **The assignment algorithm compensates for noisy scores.** The Hungarian algorithm finds the globally optimal assignment even when individual month-fit scores are noisy. Small differences in scores still produce better assignments than random allocation.

## Applicability

This lesson applies when you need to assign items to slots based on "fit" but lack rich metadata:
- Assigning stock photos to seasonal marketing campaigns using only visual features
- Ordering songs in a playlist by mood using only audio features (tempo, key, energy)
- Arranging art in a gallery by visual flow using only color/composition analysis

Does NOT apply when rich text metadata is available — in that case, NLP-based semantic matching will outperform visual heuristics.
