# Lesson: PEP 8 Compliance in Data Engineering Pipelines

## Problem

Python scripts in the Artemis project span multiple roles: XML/JSON migration, schema validation, metadata enrichment, test harnesses, and lesson harvesting. Without a consistent style standard, each script drifts toward the author's (or AI assistant's) habits — camelCase here, inconsistent indentation there, star imports everywhere. The cost is not cosmetic: style inconsistency makes grep-based refactoring unreliable, code review slower, and onboarding harder.

## Why It Matters

PEP 8 is Python's canonical style guide. Compliance matters for three practical reasons in a project like Artemis:

1. **Tooling reliability.** Linters (`ruff`), formatters (`ruff format`), and type checkers (`mypy`) assume PEP 8 conventions. Violating them triggers false positives that train developers to ignore warnings — including warnings that catch real bugs.
2. **Cross-module consistency.** Artemis has 15+ modules (`extract/`, `parse/`, `load/`, `validate/`, `features/`, `cluster/`, `models/`, `optimize/`, `render/`, `review/`, `web/`, `vision/`, `synthetic/`, `config/`, `observe/`). A developer reading `features/embeddings.py` after `models/scoring.py` should not have to context-switch between naming conventions.
3. **AI-assisted development.** When an AI assistant generates code, PEP 8 compliance ensures the generated code is stylistically indistinguishable from hand-written code. Without a shared standard, every AI-generated function needs manual reformatting.

## What Happened

<!-- reconstructed from project patterns -->

1. Early pipeline scripts used a mix of naming conventions. Some functions used `camelCase` (inherited from JavaScript habits), some used `snake_case` (PEP 8), and constants were inconsistently `ALL_CAPS` or `Title_Case`.
2. When `ruff` was added as the project linter, it surfaced dozens of style violations that were not bugs but created noise in the output. Developers began adding `# noqa` comments to suppress warnings rather than fixing the underlying style.
3. A round of standardization converted all public APIs to PEP 8 `snake_case`, constants to `ALL_CAPS`, and classes to `PascalCase`. This eliminated the `# noqa` noise and made `ruff check` output actionable — every remaining warning was a genuine issue worth investigating.
4. The lesson was reinforced during migration and validation script work: scripts that followed PEP 8 from the start required zero rework when integrated into the main pipeline. Scripts that didn't required a formatting pass before they could be imported without linter warnings.

## PEP 8 Rules That Matter Most for Data Pipelines

### Naming conventions

| Element | Convention | Example |
|---|---|---|
| Functions, methods, variables | `snake_case` | `extract_visual_features()` |
| Classes | `PascalCase` | `BetaBinomialModel` |
| Constants | `ALL_CAPS` | `RATE_LIMIT_NASA = 1.0` |
| Module-private names | `_leading_underscore` | `_parse_manifest_row()` |
| Throwaway variables | `_` | `for _ in range(10)` |

### Import ordering

```python
# 1. Standard library
import json
from pathlib import Path

# 2. Third-party
import duckdb
import numpy as np
from PIL import Image

# 3. Local project
from artemis_calendar.config.settings import WAREHOUSE_PATH
from artemis_calendar.features.visual import extract_brightness
```

`ruff` enforces this ordering via its `isort`-compatible rules. No manual sorting needed — `ruff check --fix` handles it.

### Line length

The project uses ruff's default of 88 characters (Black-compatible). This is wider than PEP 8's strict 79 but narrower than the 120 that some teams use. The 88-character limit works well for data pipeline code where SQL strings and DataFrame operations tend to run long.

### Specific patterns for Artemis scripts

- **Migration scripts** (`load/`, schema DDL): SQL strings use triple-quoted `"""` blocks, indented to match the Python scope. Column names in SQL follow the warehouse convention (`snake_case`), not Python.
- **Validation scripts** (`validate/`): Assert messages include the metric name and threshold so failures are self-documenting: `assert alpha > 0.6, f"Krippendorff alpha {alpha:.3f} below 0.6 threshold"`.
- **Metadata enrichment** (`features/`, `vision/`): Functions that compute a single feature return a single value, not a dict. Functions that compute multiple features return a `NamedTuple` or `dataclass`, not a raw tuple.
- **Test files** (`tests/`): Test function names start with `test_` and describe the behavior, not the implementation: `test_composite_score_excludes_null_elo()`, not `test_scoring_function_3()`.
- **Lesson harvesting** (`docs/lessons/`): Markdown files follow the section structure (Problem, Why It Matters, What Happened, Broader Lesson) so automated tooling can parse them consistently.

## Enforcement

PEP 8 compliance is enforced at two levels:

1. **`ruff check`** — runs on every commit (CI and local). Catches import ordering, naming violations, unused imports, and structural issues. Zero-tolerance: no `# noqa` without a comment explaining why.
2. **`ruff format --check`** — verifies formatting matches the canonical output. If `ruff format` would change a file, the check fails. This eliminates all whitespace and formatting debates.

Both commands run in under 2 seconds for the entire Artemis codebase, so there is no cost to running them on every save.

## When to Deviate

PEP 8 itself says: "A foolish consistency is the hobgoblin of little minds." Acceptable deviations in Artemis:

- **Single-letter variables in mathematical code** (`k` for cluster count, `n` for sample size, `p` for probability) — these match the literature and are clearer than verbose alternatives.
- **DataFrame column access** (`df['image_sk']`) — column names follow the warehouse convention, not Python variable naming.
- **External API compatibility** — when wrapping a third-party API that uses `camelCase` (e.g., some JavaScript interop in the web layer), match the external convention at the boundary.

## Broader Lesson

Style guides are not about aesthetics. They are about making a codebase searchable, predictable, and machine-parseable. In a project with 15+ modules and AI-assisted development, PEP 8 compliance is the cheapest form of quality insurance: it costs nothing to maintain (automated formatters do the work) and pays back on every code review, every refactor, and every new contributor's first day.
