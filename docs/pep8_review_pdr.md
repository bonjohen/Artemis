# PEP 8 Compliance Review

**Project:** Artemis Calendar Image Selection Platform
**Date:** 2026-05-09
**Scope:** `src/artemis_calendar/` (77 files) + `tests/` (25 files) = 94 Python files, ~17,600 lines
**Tools:** `ruff check` (lint), `ruff format --check` (formatting), Python 3.11+

## 1. Executive Summary

The Artemis codebase is in strong PEP 8 compliance. Ruff reports **8 lint violations** across 3 files and **25 files with formatting drift** (whitespace/wrapping only). There are zero naming convention violations, zero unused imports, and zero undefined names. Tests have zero lint violations.

| Metric | Value |
|---|---|
| Python files | 94 |
| Total lines | ~17,600 |
| Lint violations | 8 (3 files) |
| Formatting drift | 25 files (17 src, 8 tests) |
| Naming violations (N rules) | 0 |
| Unused imports (F401) | 0 |
| Undefined names (F821) | 0 |
| `# noqa` suppressions | 0 |

**Overall grade: A.** The violations are minor and mechanically fixable. No architectural or naming debt.

## 2. Ruff Configuration

From `pyproject.toml`:

```toml
[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "SIM"]
```

### Rule coverage

| Rule set | What it catches |
|---|---|
| **E** | PEP 8 style (indentation, whitespace, line length) |
| **F** | Pyflakes (unused imports, undefined names, redefined names) |
| **W** | PEP 8 warnings (deprecated syntax, trailing whitespace) |
| **I** | isort-compatible import ordering |
| **N** | PEP 8 naming conventions (snake_case, PascalCase, ALL_CAPS) |
| **UP** | pyupgrade (modern Python syntax for 3.11+) |
| **B** | flake8-bugbear (common bug patterns, mutable defaults) |
| **SIM** | flake8-simplify (unnecessary complexity) |

### Line length: 120

The project uses 120 characters, wider than PEP 8's strict 79 but a common pragmatic choice for data engineering code where SQL strings, PyArrow schema definitions, and DataFrame operations run long. This is consistent with the Black-compatible range (88-120). The 120-char limit is explicitly configured and intentional.

## 3. Lint Violations

### 3.1 B905: `zip()` without explicit `strict=` (5 violations)

**Severity:** Low. These are correctness guardrails, not bugs. All 5 call sites zip arrays that are guaranteed to be the same length by construction.

| File | Line | Context |
|---|---|---|
| `src/artemis_calendar/features/dedup.py` | 172 | `zip(member_indices, member_sks_list)` |
| `src/artemis_calendar/vision/clip_tagger.py` | 173 | `zip(codes, probs)` — dict comprehension |
| `src/artemis_calendar/vision/clip_tagger.py` | 175 | `zip(codes, probs)` — loop |
| `src/artemis_calendar/vision/clip_tagger.py` | 386 | `zip(codes, probs)` — dict comprehension |
| `src/artemis_calendar/vision/clip_tagger.py` | 388 | `zip(codes, probs)` — loop |

**Recommended fix:** Add `strict=True` to all 5 call sites. This makes the length-match assumption explicit and will raise `ValueError` if a future code change introduces a length mismatch.

```python
# Before
for code, prob in zip(codes, probs):

# After
for code, prob in zip(codes, probs, strict=True):
```

### 3.2 I001: Unsorted imports (1 violation)

**Severity:** Trivial. Auto-fixable.

| File | Line | Context |
|---|---|---|
| `src/artemis_calendar/web/app.py` | 3 | Local import block not alphabetized |

The local imports are:

```python
from artemis_calendar.web.routes.candidates import router as candidates_router
from artemis_calendar.web.routes.dedup import router as dedup_router      # <-- out of order
from artemis_calendar.web.routes.clusters import router as clusters_router # <-- should be before dedup
```

**Recommended fix:** `ruff check --fix src/artemis_calendar/web/app.py` (auto-sorts the import block).

### 3.3 B008: Function call in default argument (2 violations)

**Severity:** False positive. This is idiomatic FastAPI.

| File | Line | Context |
|---|---|---|
| `src/artemis_calendar/web/routes/blend.py` | 293 | `conn: DuckDBPyConnection = Depends(get_db)` |
| `src/artemis_calendar/web/routes/blend.py` | 308 | `conn: DuckDBPyConnection = Depends(get_db)` |

B008 warns against mutable default arguments (`def f(x=[])`), but FastAPI's `Depends()` is a dependency injection marker, not a mutable default. FastAPI evaluates it per-request, not at function definition time. This is the standard FastAPI pattern used across the web framework ecosystem.

**Recommended fix:** Suppress B008 for FastAPI route files. Two options:

Option A — per-file suppression (preferred, minimal scope):
```python
# At top of blend.py
# ruff: noqa: B008
```

Option B — per-line suppression:
```python
def get_presets(conn: duckdb.DuckDBPyConnection = Depends(get_db)):  # noqa: B008
```

Option C — project-wide in `pyproject.toml` (broader, but `Depends()` is only used in `web/routes/`):
```toml
[tool.ruff.lint.per-file-ignores]
"src/artemis_calendar/web/routes/*.py" = ["B008"]
```

## 4. Formatting Drift

25 files would be reformatted by `ruff format`. All changes are whitespace and line-wrapping adjustments — no semantic changes.

### 4.1 Source files (17 files)

| File | Diff lines | Primary drift type |
|---|---|---|
| `models/block_stats.py` | 202 | Tuple packing, dict literals, long expressions |
| `vision/clip_tagger.py` | 114 | `pa.schema()` definitions, tuple appends |
| `web/routes/lessons.py` | 73 | Dict/list literal wrapping |
| `static/exporter.py` | 72 | Dict/list literal wrapping |
| `features/dedup.py` | 67 | SQL string wrapping, tuple packing |
| `synthetic/block_generator.py` | 66 | Dict/list literal wrapping |
| `vision/cluster_labels.py` | 57 | SQL strings, dict literals |
| `vision/voting_config.py` | 47 | Dict/list literal wrapping |
| `vision/attributes.py` | 35 | Schema definitions |
| `vision/pipeline.py` | 34 | Function call wrapping |
| `web/routes/blend.py` | 28 | Function signatures, dict literals |
| `web/routes/images.py` | 22 | Dict/list literal wrapping |
| `vision/tagger.py` | 20 | Prompt string wrapping |
| `web/routes/dedup.py` | 14 | Dict literal wrapping |
| `cli.py` | 10 | argparse call wrapping |
| `web/routes/clusters.py` | 7 | Dict literal wrapping |
| `vision/loader.py` | 5 | Minor whitespace |

### 4.2 Test files (8 files)

| File | Diff lines | Primary drift type |
|---|---|---|
| `tests/test_acceptance_blocks.py` | 53 | Dict/list fixture wrapping |
| `tests/test_vision_tagger.py` | 34 | Mock data structure wrapping |
| `tests/test_static_export.py` | 28 | Expected output wrapping |
| `tests/test_vision_attributes.py` | 20 | Fixture wrapping |
| `tests/test_voting_config.py` | 20 | Config dict wrapping |
| `tests/test_block_stats.py` | 12 | Minor wrapping |
| `tests/test_vision_clusters.py` | 10 | Minor wrapping |
| `tests/test_block_generator.py` | 6 | Minor wrapping |

### 4.3 Common drift patterns

The formatting drift falls into three categories:

1. **Tuple/list/dict packing.** Multi-element tuples appended to buffers are packed onto fewer lines than `ruff format` prefers. The formatter expands them to one-element-per-line when the packed form exceeds the line length. This is the dominant pattern in `vision/` and `models/`.

2. **PyArrow schema definitions.** `pa.schema([...])` calls with many fields are packed tightly. The formatter breaks them into one-field-per-line.

3. **Argparse and function call wrapping.** Long `add_argument()` and `add_parser()` calls are wrapped differently than the formatter prefers. The formatter collapses some wrapped calls to single lines when they fit within 120 characters.

## 5. What's Already Right

These are areas where the codebase is fully PEP 8 compliant with no issues:

- **Naming conventions.** All functions use `snake_case`, all classes use `PascalCase`, all constants use `ALL_CAPS`. Zero N-rule violations across 94 files.
- **Import hygiene.** Zero unused imports (F401). Every import is used. Import ordering is correct in 93 of 94 files.
- **No `# noqa` abuse.** Zero `# noqa` comments in the codebase. Every ruff warning is either addressed or genuinely present.
- **Test naming.** All test functions follow `test_<behavior>()` convention.
- **Module structure.** `__init__.py` files are minimal. No star imports. No circular imports.
- **Type annotations.** Function signatures in the web layer use type hints consistently. Pipeline functions use them where they add clarity.
- **Docstrings.** Public functions and classes have docstrings. Module-level docstrings describe purpose.

## 6. Recommendations

Prioritized by effort and impact:

### Priority 1: Run `ruff format` (5 minutes, mechanical)

```bash
ruff format src/ tests/
```

This fixes all 25 files of formatting drift in one command. Zero risk — formatting changes are semantically identical. Run tests afterward to confirm.

### Priority 2: Add `strict=True` to `zip()` calls (5 minutes, 5 edits)

Add `strict=True` to the 5 `zip()` calls in `features/dedup.py` and `vision/clip_tagger.py`. This converts implicit assumptions about array length into explicit runtime checks.

### Priority 3: Auto-fix import ordering (1 minute, 1 edit)

```bash
ruff check --fix src/artemis_calendar/web/app.py
```

Sorts the import block in `app.py` alphabetically within each section.

### Priority 4: Suppress B008 for FastAPI routes (2 minutes, config change)

Add to `pyproject.toml`:

```toml
[tool.ruff.lint.per-file-ignores]
"src/artemis_calendar/web/routes/*.py" = ["B008"]
```

This acknowledges that `Depends()` in default arguments is idiomatic FastAPI, not a bug.

### After all fixes: expected state

```
ruff check src/ tests/    → 0 violations
ruff format --check src/ tests/  → 0 files would be reformatted
```
