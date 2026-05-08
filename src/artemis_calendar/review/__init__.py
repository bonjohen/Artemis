"""Review package generation for calendar candidate comparison and selection."""

from __future__ import annotations


def generate_review_package(*args, **kwargs):
    """Lazy import to avoid PIL dependency at import time."""
    from artemis_calendar.review.pipeline import generate_review_package as _impl

    return _impl(*args, **kwargs)


__all__ = ["generate_review_package"]
