"""Lessons API route — serves lesson index from docs/lessons/ markdown files."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/api/lessons", tags=["lessons"])

LESSONS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "docs" / "lessons"

# Category detection from lesson content
CATEGORY_KEYWORDS = {
    "eng": [
        "engineering",
        "duckdb",
        "performance",
        "pipeline",
        "migration",
        "download",
        "concurrent",
        "batch",
        "linter",
        "packaging",
        "pyarrow",
    ],
    "data": ["data", "population", "disjoint", "surrogate", "null", "feature", "month-fit", "clustering"],
    "stats": [
        "bayesian",
        "elo",
        "borda",
        "krippendorff",
        "composite",
        "chi-squared",
        "ground-truth",
        "reliability",
        "mmr",
        "hungarian",
        "bradley-terry",
        "scoring",
        "bias",
    ],
    "arch": [
        "architecture",
        "portfolio",
        "run-id",
        "resume-safe",
        "read-only",
        "cache",
        "design system",
        "reusing query",
        "fetch shim",
    ],
    "process": [
        "synthetic data",
        "baseline",
        "formalizing",
        "multiple selection",
        "phased",
        "session continuity",
        "audit-first",
        "test-gated",
        "acceptance test",
    ],
    "ml": [
        "clip",
        "sigmoid",
        "zero-shot",
        "embedding",
        "vision",
        "tagger",
        "dedup",
        "cosine similarity",
        "connected component",
    ],
}


def _detect_category(title: str, content: str) -> str:
    text = (title + " " + content[:500]).lower()
    scores = {cat: 0 for cat in CATEGORY_KEYWORDS}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[cat] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "eng"


def _parse_lesson(path: Path, block: str) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None

    # Extract title from first # heading
    title_match = re.search(r"^#\s+(?:Lesson\s+\d+:\s*)?(.+)$", text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else path.stem

    # Extract lesson number from filename
    num_match = re.match(r"(\d+)", path.stem)
    number = num_match.group(1) if num_match else path.stem[:3]

    # Extract first paragraph after title for description
    desc = ""
    lines = text.split("\n")
    in_body = False
    for line in lines:
        if line.startswith("## "):
            if in_body:
                break
            in_body = True
            continue
        if in_body and line.strip():
            desc = line.strip()
            break

    category = _detect_category(title, text)

    return {
        "number": number,
        "title": title,
        "description": desc[:200],
        "block": block,
        "file": path.stem,
        "category": category,
    }


@router.get("")
def list_lessons():
    lessons = []
    for block_dir in sorted(LESSONS_DIR.iterdir()):
        if not block_dir.is_dir() or not block_dir.name.startswith("block"):
            continue
        block = block_dir.name
        for md_file in sorted(block_dir.glob("*.md")):
            if md_file.name in ("index.md", "PLANNED.md"):
                continue
            lesson = _parse_lesson(md_file, block)
            if lesson:
                lessons.append(lesson)
    return lessons


@router.get("/{block}/{file}")
def get_lesson(block: str, file: str):
    """Return the raw markdown content for a single lesson."""
    if not re.match(r"^block\d+$", block) or not re.match(r"^[a-zA-Z0-9_-]+$", file):
        return {"error": "Invalid lesson path"}
    path = LESSONS_DIR / block / f"{file}.md"
    if not path.exists():
        return {"error": "Lesson not found"}
    return {"block": block, "file": file, "content": path.read_text(encoding="utf-8")}
