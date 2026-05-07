# Lesson 026: Formalizing De Facto Dependencies

## The Lesson

A dependency that's imported in production code but missing from the package manifest is a time bomb. It works on the developer's machine (where the package was installed for something else) and fails on fresh installs, CI, or new team members. Audit imports against declared dependencies whenever adding a new module that uses an existing library.

## Context

A Python data science project declared its ML dependencies in `pyproject.toml` under `[project.optional-dependencies] ml`. The list included scikit-learn, torch, transformers, Pillow, NLTK, and HDBSCAN. Two production modules (`models/batch_scores.py` and `models/composite.py`) imported `scipy.stats.beta` — but scipy was not in the dependency list. It worked because scipy is a transitive dependency of scikit-learn, but this relationship is not guaranteed across versions.

## What Happened

1. Phase 3 (statistical modeling) added two modules that imported `from scipy.stats import beta as beta_dist` for Beta-Binomial posterior computation. Both imports were lazy (inside functions) so they didn't fail at import time.
2. Phase 4 (calendar optimization) needed `scipy.optimize.linear_sum_assignment` for the Hungarian algorithm. When checking whether to add scipy as a dependency, discovered it was already imported in two existing files.
3. scipy was present on the development machine because scikit-learn pulls it in as a transitive dependency. But relying on transitive dependencies is fragile — sklearn could drop scipy in a future version, or a user could install the project without the `ml` extras.
4. Added `scipy>=1.12` to `pyproject.toml` under the `ml` optional dependencies, formalizing the de facto dependency.
5. The fix was one line in the manifest. The risk of not fixing it: a cryptic `ModuleNotFoundError: No module named 'scipy'` on a fresh install, with no obvious connection to the scoring or optimization code.

## Key Insights

- **Transitive dependencies are not your dependencies.** Just because package A pulls in package B doesn't mean you can import B. The relationship can change between versions, and tools like `pip check` won't flag it because it's technically satisfied.

- **Lazy imports hide missing dependencies.** `from scipy.stats import beta` inside a function won't fail until that function is called. The module imports cleanly, tests that don't exercise that path pass, and the failure appears only in production.

- **Audit imports when adding new modules.** Before adding a new module that imports a library, grep the codebase for existing imports of that library. If it's already used but not declared, fix the manifest at the same time.

- **One line of prevention beats hours of debugging.** A `ModuleNotFoundError` in production, CI, or a new developer's environment wastes far more time than adding a line to pyproject.toml.

## Applicability

This applies to any project with a package manifest (pyproject.toml, setup.py, package.json, Cargo.toml, go.mod). The pattern is the same: code imports a library, the library happens to be installed, but the manifest doesn't declare it.

Especially common in data science projects where the ML ecosystem has deep transitive dependency trees (numpy → scipy → sklearn → many others).
