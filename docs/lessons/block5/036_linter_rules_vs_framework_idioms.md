# Lesson 036: Linter Rules vs. Framework Idioms

## The Lesson

When a linter rule flags code that follows a framework's official pattern, suppress the rule per-line with `noqa` rather than restructuring the code. Linter rules encode general best practices; framework idioms encode domain-specific patterns that intentionally violate those practices. Restructuring idiomatic framework code to satisfy a general lint rule produces code that is harder to read, harder to maintain, and unfamiliar to anyone who knows the framework.

## Context

A FastAPI web application used `Depends(get_db)` as a default argument in route functions — the standard FastAPI dependency injection pattern documented in FastAPI's official tutorials. Ruff's B008 rule ("Do not perform function call in argument defaults") flagged every route function. B008 exists because calling a function in a default argument is evaluated once at definition time, which causes bugs when the function returns a mutable object (e.g., `def f(items=list())`). FastAPI's `Depends()` deliberately exploits this behavior: it returns a dependency marker at definition time, which FastAPI's framework evaluates per-request at runtime.

## What Happened

1. Wrote 6 FastAPI route functions following the official `Depends()` pattern: `def list_images(..., conn = Depends(get_db)):`.
2. Ruff flagged all 6 with B008. The suggested fix was to move the `Depends()` call inside the function body. But FastAPI requires `Depends()` in the function signature — moving it to the body would break dependency injection entirely.
3. Considered three options:
   - **Suppress B008 globally** in `pyproject.toml` — too broad; B008 catches real bugs in non-FastAPI code.
   - **Restructure** to use `Annotated[Connection, Depends(get_db)]` — valid FastAPI syntax, but adds verbosity without benefit, and is still flagged by B008.
   - **Suppress per-line** with `# noqa: B008` — minimal, targeted, self-documenting.
4. Chose per-line suppression. Added `# noqa: B008` to each `Depends()` default. The comment signals to readers: "yes, this is intentional — it's a framework pattern."
5. All other B008 violations in the codebase (if any) would still be caught. The rule remains active for non-FastAPI code.

## Key Insights

- **Framework idioms are more authoritative than lint rules.** When FastAPI's documentation says `def route(db = Depends(get_db))`, that's the intended usage. The framework author designed `Depends()` to work this way. A general lint rule written without knowledge of FastAPI can't override that.

- **Per-line `noqa` is documentation, not debt.** A `# noqa: B008` comment tells the next reader: "I know this looks wrong, but it's intentional." This is better than a global suppression (which hides all B008 violations) or a code restructuring (which obscures the framework pattern).

- **Don't restructure code to satisfy a false positive.** Refactoring `Depends(get_db)` into a module-level singleton or an `Annotated` type alias adds complexity without fixing a real bug. The "fix" makes the code less readable to FastAPI developers and doesn't eliminate the `noqa` need anyway.

- **Global suppression is a last resort.** Adding `"B008"` to `[tool.ruff.lint.ignore]` would suppress B008 across the entire project. This is appropriate only if the project is entirely FastAPI and B008 has zero legitimate findings. For a mixed project (pipeline code + web code), per-line suppression preserves B008's value for non-framework code.

- **This tension recurs across linter-framework pairs.** SQLAlchemy's `Column(default=func.now())` triggers similar "function call in default" warnings. Pytest fixtures trigger "unused argument" warnings. Django's `models.py` triggers "too many arguments" for model definitions. The pattern is always the same: framework idiom > general lint rule, suppress per-line.

## Examples

```python
# FastAPI's official pattern — triggers B008
@router.get("/api/images")
def list_images(
    page: int = Query(1, ge=1),
    conn: Connection = Depends(get_db),  # noqa: B008
):
    ...

# "Fix" that breaks dependency injection — DO NOT DO THIS
@router.get("/api/images")
def list_images(page: int = Query(1, ge=1)):
    conn = Depends(get_db)  # BUG: returns a Depends marker, not a connection
    ...

# Global suppression — too broad for mixed codebases
# pyproject.toml
# [tool.ruff.lint]
# ignore = ["B008"]  # suppresses ALL B008, including real bugs elsewhere
```

## Applicability

This pattern applies whenever a linter rule conflicts with a framework's documented idiom. It does NOT apply when the flagged code is genuinely buggy — if `Depends` were a regular function returning a mutable default, B008 would be correct to flag it. The key question is: does the framework deliberately exploit the behavior the lint rule is guarding against? If yes, suppress. If no, fix.

## Related Lessons

- [Reusing Query Modules Across CLI and Web](034_reusing_query_modules_across_layers.md) — the `get_db` dependency function that `Depends()` wraps, and why it's a simple function returning a connection from `app.state`
