# Lesson 034: Reusing Query Modules Across CLI and Web

## The Lesson

When a CLI pipeline and a web API need the same data, import the query functions directly rather than duplicating SQL. Add the serialization layer (Pydantic models, JSON responses) at the API boundary, not in the query module. The query module returns plain Python objects (dataclasses, dicts, tuples); the web route converts them. This keeps the query logic in one place and testable without a web framework.

## Context

A calendar image selection platform had a CLI-driven review package (`review/queries.py`) with functions like `fetch_all_candidates()`, `fetch_candidate_images()`, and `fetch_cluster_alternatives()`. These returned dataclasses (`CandidateScore`, `MonthImage`, `ClusterAlternative`). A new web API needed the exact same data for its `/api/candidates` and `/api/candidates/{name}` endpoints. The question was whether to duplicate the queries in the web layer (risking drift) or import them directly (risking tight coupling).

## What Happened

1. Started by reading the existing `review/queries.py`. It contained 5 functions and 3 dataclasses, all taking a `duckdb.DuckDBPyConnection` as the first argument. No framework-specific code — pure SQL + dataclass construction.
2. Created `web/models.py` with Pydantic schemas (`CandidateResponse`, `MonthImageResponse`, etc.) that mirrored the review dataclasses but with Pydantic's serialization, validation, and OpenAPI integration.
3. The web route `routes/candidates.py` imported the query functions directly: `from artemis_calendar.review.queries import fetch_all_candidates, fetch_candidate_images`. The route calls the function, iterates the returned dataclasses, and converts each to a Pydantic model.
4. New queries that only the web app needed (paginated image browse, image detail with rank) went into a separate `web/queries.py` that returns plain dicts — no dataclasses, since the web is their only consumer.
5. The review module's `resolve_run_id()` function was also reused to default both CLI and web to the latest optimization run.

## Key Insights

- **Query functions should take a connection, not know their caller.** The `fetch_all_candidates(conn, run_id)` signature works equally well from a CLI command handler and a FastAPI route. The function doesn't know whether `conn` was opened read-write (CLI) or read-only (web). This is the right abstraction boundary.

- **Dataclasses and Pydantic models serve different purposes.** Dataclasses are internal data containers — lightweight, no validation overhead. Pydantic models are API contracts — they handle serialization, OpenAPI schema generation, and input validation. Converting at the route level (not in the query function) keeps each tool where it belongs.

- **Duplication is worse than coupling for SQL.** SQL queries are hard to keep in sync when duplicated. A join condition, a subquery filter, or a column rename in one copy but not the other produces subtle data discrepancies. Direct import creates a dependency, but the alternative (copy-paste SQL that drifts) is strictly worse.

- **New-consumer-only queries belong to the new consumer.** The web app needed paginated, sorted, filtered image browsing — a query the CLI never uses. This went into `web/queries.py`, not `review/queries.py`. The rule is: shared queries live in the module that first created them; single-consumer queries live with their consumer.

- **The conversion boilerplate is worth it.** Converting a `CandidateScore` dataclass to a `CandidateResponse` Pydantic model is 8 lines of field assignment. This feels redundant, but it buys you: API-layer validation, OpenAPI documentation, and freedom to evolve the API schema independently of the internal representation.

## Examples

```python
# review/queries.py — framework-agnostic, returns dataclasses
@dataclass
class CandidateScore:
    candidate_name: str
    objective_score: float
    # ...

def fetch_all_candidates(conn, run_id) -> list[CandidateScore]:
    rows = conn.execute("SELECT ... WHERE candidate_run_id = ?", [run_id]).fetchall()
    return [CandidateScore(...) for r in rows]

# web/models.py — Pydantic, API-facing
class CandidateResponse(BaseModel):
    candidate_name: str
    objective_score: float = 0.0

# web/routes/candidates.py — conversion at the boundary
from artemis_calendar.review.queries import fetch_all_candidates

@router.get("/api/candidates")
def list_candidates(conn=Depends(get_db)):
    candidates = fetch_all_candidates(conn, run_id)
    return [CandidateResponse(candidate_name=c.candidate_name, ...) for c in candidates]
```

## Applicability

This pattern applies when: multiple consumers (CLI, web, notebooks) need the same data from the same database, and the query logic is non-trivial (joins, subqueries, aggregation). It does NOT apply when: the web API needs fundamentally different data shapes (GraphQL), when queries need async/await (DuckDB is synchronous), or when the query module has side effects (writes) that the web layer shouldn't trigger.

## Related Lessons

- [Read-Only DB for Web Layers](031_read_only_db_for_web_layers.md) — the web app's connection is read-only, so reusing write-capable query functions is safe because they never reach a write path
- [Run-ID Partitioned Scoring](../block2/018_run_id_partitioned_scoring.md) — `resolve_run_id()` is the shared function that both CLI and web use to default to the latest run
