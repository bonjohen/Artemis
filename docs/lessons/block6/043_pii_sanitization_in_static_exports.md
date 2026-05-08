# Lesson 043: PII Sanitization in Static JSON Exports

## Problem

The static site serves pre-built JSON files from a public URL. The warehouse database contains voter surrogate keys (`voter_sk`), hashed voter IDs (`voter_public_hash`), random seeds, config hashes, and local file paths. None of these should appear in public-facing JSON. The sanitization must be reliable, testable, and not depend on developers remembering to exclude fields manually in each export function.

## Why It Matters

PII leaks in static exports are particularly insidious because they persist indefinitely (cached by CDNs, indexed by search engines) and are hard to retract. Even non-PII like local file paths (`C:\Projects\Artemis\...`) or config hashes reveal internal system details. A per-field approach ("remember to exclude voter_sk in this query") is fragile — it only takes one new export function to forget a field. Defense in depth requires both query-level exclusion and post-export verification.

## What Happened

1. Each export function (`export_vision_summary`, `export_voting_block_summary`, etc.) is written to query only the fields needed for the public view. This is the primary defense: never SELECT fields you don't need.
2. Added `_sanitize_no_pii(data)` — a recursive function that walks nested dicts and lists, deleting any key found in a hardcoded forbidden set: `{voter_sk, voter_public_hash, random_seed, seed, config_hash}`. Applied to the voting block summary before writing.
3. Added a post-export sweep in `export_all_static_json`: after all files are written, reads each file back and checks for forbidden field names as string matches. Logs a warning if found. This catches cases where a field slipped through both the query and the sanitizer.
4. The acceptance test `test_no_admin_controls` goes further: it checks that the exported JSON contains none of `voter_sk`, `voter_public_hash`, `random_seed`, `model_prompt`, or `C:\`. The `C:\` check catches local paths that might leak through error messages or metadata.
5. The sanitizer uses string key matching rather than value inspection. This means a field named `voter_sk` is removed regardless of its value, but a field with a different name containing a voter SK value would not be caught. The acceptance test's string-in-content check provides the second layer for this case.

## Design Choice: Defense in Depth Over Single-Point Filtering

### Why three layers, not one

- **Query-level exclusion** prevents sensitive data from ever entering the export function's scope. But it relies on each developer writing correct SELECT statements.
- **Recursive field sanitizer** catches forgotten fields in nested structures. But it only knows about its hardcoded forbidden set.
- **Post-export content scan** catches everything the first two layers missed. But it's a string match, so it could have false positives (an attribute code that happens to contain "seed").

No single layer is complete. Together, they cover: intentional exclusion (layer 1), accidental inclusion of known-bad fields (layer 2), and unknown-bad content (layer 3).

### Why a forbidden set rather than an allowed set

An allowlist would be safer in theory (only explicitly approved fields pass through), but the export functions produce different schemas — vision summary has different fields than voting block summary. Maintaining a per-export allowlist would be as error-prone as remembering to exclude fields. The forbidden set is small, stable, and shared across all exports.

## Key Insights

- **Defense in depth is the only reliable PII strategy for static exports.** Any single layer can be bypassed by a new field, a nested structure, or a serialization edge case. Multiple independent layers reduce the probability of leakage multiplicatively.
- **Test for absence, not just for correctness.** The acceptance test doesn't just check that the JSON has the right structure — it checks that specific strings are *not present* in the output. This is an unusual testing pattern (most tests assert presence) but essential for security properties.
- **String-match content scanning catches what schema-level sanitization misses.** A `voter_sk` value embedded in an error message, a comment, or a JSON string field wouldn't be caught by the recursive dict walker. The content scan's string match catches it regardless of structure.
- **Local paths are PII-adjacent.** `C:\Users\boen3\...` in a public JSON file reveals the developer's username and directory structure. The `C:\` check in the acceptance test is specifically for this — it's not about confidentiality so much as professionalism and attack surface reduction.
- **Sanitization is cheaper than remediation.** Removing a leaked field from a static JSON file is easy. Removing it from CDN caches, web archives, search engine indexes, and downstream consumers who fetched the data is hard. The cost of three sanitization layers is negligible; the cost of a missed leak is unbounded.

## Applicability

This pattern applies to any system that exports data from a rich internal store to a public-facing format:
- API responses that must exclude internal IDs or audit trails
- Data exports for partner integrations with field-level access control
- Public dashboards backed by internal analytics databases

Does NOT apply when:
- All consumers are internal (no public exposure)
- The export format has a formal schema with code generation (the schema itself enforces field inclusion/exclusion)
- The data is already anonymized at the source

## Related Lessons

- [Lesson 037: Static Site via Fetch Shim](../block5/037_static_site_via_fetch_shim.md) — the static site consumes these JSON files; the shim replaces API calls with file reads, so the JSON must be self-contained and safe
- [Lesson 038: CI Path Portability](../block5/038_ci_path_portability_and_release_artifacts.md) — hardcoded paths are a related problem; CI path portability prevents paths from entering the system, while PII sanitization removes them on exit
