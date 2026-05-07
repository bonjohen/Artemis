# Lesson: Algorithm Selection — sklearn KMeans vs Pillow Quantize for Dominant Colors

## Problem

The visual feature extraction pipeline ran sklearn's `KMeans` on every thumbnail to find 5 dominant colors. Each call took ~147ms per image. For 12,217 images, that's ~30 minutes of CPU time on dominant color extraction alone — a feature that contributes a single JSON column to the feature table.

## Why It Matters

This is a case of reaching for a general-purpose tool (sklearn KMeans) when a domain-specific tool (color quantization) solves the exact same problem orders of magnitude faster. The dominant color problem is literally what image quantization algorithms were designed for — they've been optimized for decades in image processing libraries.

## What Happened

<!-- reconstructed from git history (72a73ef, 9ad5892) and lesson context -->

1. Initial visual feature extraction used sklearn's `KMeans(n_clusters=5)` to find dominant colors in each thumbnail. The code reshaped pixel arrays into an N×3 matrix, ran k-means with 3 random restarts, and extracted centroids as colors. This was mathematically correct and produced good results on test images.
2. At full scale (12,217 images), dominant color extraction alone consumed ~30 minutes of CPU time. Profiling showed ~147ms per image for `KMeans.fit()` — a single JSON column was the most expensive operation in the entire visual feature pipeline.
3. Recognized that dominant color extraction is literally the problem that image quantization algorithms were designed for. Color quantization has been optimized in libraries like Pillow for decades, exploiting the constrained 3D RGB space that general-purpose k-means ignores.
4. Replaced `KMeans` with Pillow's `quantize(colors=5, method=Image.Quantize.MEDIANCUT)`. Benchmarked at 0.2ms per image — a 735x speedup.
5. Verified output quality: solid-color images produce the expected dominant color, real space photos show black as dominant with >90% proportion. For downstream use (clustering diversity), the perceptual grouping from MEDIANCUT is more than adequate.
6. Combined with two other fixes in the same commit (single LAB conversion, batch DB inserts), total visual feature extraction went from "killed after running too long" to ~2 minutes for all 12,217 images.

## The Benchmark

```python
from PIL import Image
from sklearn.cluster import KMeans
import time, numpy as np

img = Image.open("thumbnail.jpg")

# sklearn KMeans: 147ms per image
small = img.copy()
small.thumbnail((100, 100))
pixels = np.array(small.convert("RGB")).reshape(-1, 3).astype(np.float64)
km = KMeans(n_clusters=5, random_state=42, n_init=3)
km.fit(pixels)

# Pillow quantize: 0.2ms per image
small = img.copy()
small.thumbnail((100, 100))
q = small.convert("RGB").quantize(colors=5, method=Image.Quantize.MEDIANCUT)
```

**Result: 0.2ms vs 147ms — a 735x speedup.**

## Why KMeans Is Overkill Here

KMeans solves a general clustering problem: given N points in d-dimensional space, find k centroids that minimize within-cluster variance. It's iterative (runs until convergence), initializes randomly (needs `n_init` restarts), and operates on arbitrary feature spaces.

Color quantization is a constrained version of this problem:
- The space is always 3D (RGB)
- Values are bounded [0, 255]
- The goal is perceptual grouping, not mathematical optimality
- The "data" is pixel colors, which have spatial coherence

Pillow's `MEDIANCUT` algorithm exploits these constraints. It recursively splits the color space along the axis with the greatest range, producing perceptually distinct groups in O(n log k) time. No iteration, no random restarts, no convergence checking.

## The Fix

```python
# Before: sklearn KMeans (147ms/image)
def _compute_dominant_colors(img, k=5):
    from sklearn.cluster import KMeans
    small = img.copy()
    small.thumbnail((100, 100))
    pixels = np.array(small.convert("RGB")).reshape(-1, 3).astype(np.float64)
    kmeans = KMeans(n_clusters=min(k, len(pixels)), random_state=42, n_init=3)
    kmeans.fit(pixels)
    # ... extract centroids and counts ...

# After: Pillow quantize (0.2ms/image)
def _compute_dominant_colors(img, k=5):
    small = img.copy()
    small.thumbnail((100, 100))
    q = small.convert("RGB").quantize(colors=k, method=Image.Quantize.MEDIANCUT)
    palette = q.getpalette()
    hist = q.histogram()
    # ... extract colors from palette and histogram ...
```

## Results

| Metric | sklearn KMeans | Pillow quantize |
|---|---|---|
| Time per image | 147ms | 0.2ms |
| Time for 12,217 images | ~30 min | ~2.4 sec |
| Dependencies | sklearn (heavy) | Pillow (already required) |
| Quality | Mathematically optimal | Perceptually equivalent |

## Verifying Quality

The concern with switching algorithms is whether the output quality degrades. Two checks:

1. **Uniform color test:** A solid-red image should produce a dominant color near (255, 0, 0). Both algorithms pass.
2. **Real-world test:** Space photos (mostly black) should show black as dominant with >90% proportion. Both algorithms produce this.

For the downstream use case (clustering diversity, calendar selection), perceptual grouping is what matters — not whether the centroid is at (12, 14, 15) vs (13, 13, 14). The quantize output is more than adequate.

## Broader Lesson

Before using a general ML algorithm, ask: **is there a domain-specific algorithm for this exact problem?**

Common instances of this pattern:
- **Color quantization:** Use image library quantize, not KMeans
- **Nearest neighbor search:** Use FAISS/Annoy, not brute-force distance computation
- **String matching:** Use suffix arrays or specialized libraries, not cosine similarity on character n-grams
- **Time series anomaly detection:** Use statistical process control, not autoencoders

The general tool works, but the specialized tool is often 10-1000x faster because it exploits problem structure that the general tool ignores.

## Additional Optimization Applied

Beyond the algorithm swap, the visual extraction also benefited from:

1. **Single LAB conversion** for both brightness and contrast (was converting twice)
2. **`ThreadPoolExecutor`** for parallel feature extraction across images
3. **`executemany` batch inserts** instead of per-image INSERT statements

Combined effect: visual feature extraction for 12,217 images went from "killed after running too long" to ~2 minutes total.
