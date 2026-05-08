"""Image attribute vocabulary: load, validate, and compute derived labels."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from artemis_calendar.config.settings import PROJECT_ROOT

DEFAULT_CONFIG = PROJECT_ROOT / "config" / "image_attributes.yaml"


@dataclass
class Thresholds:
    accepted: float = 0.80
    tentative: float = 0.50


@dataclass
class BaseAttribute:
    code: str
    label: str
    description: str
    type: str


@dataclass
class DerivedRule:
    all_of: list[str] = field(default_factory=list)
    none_of: list[str] = field(default_factory=list)


@dataclass
class DerivedAttribute:
    code: str
    label: str
    description: str
    rule: DerivedRule


@dataclass
class AttributeVocabulary:
    thresholds: Thresholds
    base_attributes: list[BaseAttribute]
    derived_attributes: list[DerivedAttribute]

    @property
    def base_codes(self) -> set[str]:
        return {a.code for a in self.base_attributes}

    @property
    def derived_codes(self) -> set[str]:
        return {a.code for a in self.derived_attributes}

    @property
    def all_codes(self) -> set[str]:
        return self.base_codes | self.derived_codes

    def get_attribute(self, code: str) -> BaseAttribute | DerivedAttribute | None:
        for a in self.base_attributes:
            if a.code == code:
                return a
        for a in self.derived_attributes:
            if a.code == code:
                return a
        return None

    def classify_confidence(self, score: float) -> str:
        """Classify a confidence score as accepted, tentative, or rejected."""
        if score >= self.thresholds.accepted:
            return "accepted"
        if score >= self.thresholds.tentative:
            return "tentative"
        return "rejected"

    def compute_derived_labels(
        self, base_confidences: dict[str, float]
    ) -> list[str]:
        """Compute derived attribute labels from base confidence scores.

        A derived label is present when all required base attributes are
        accepted (>= accepted threshold) and all excluded base attributes
        are below the tentative threshold.
        """
        labels: list[str] = []
        for da in self.derived_attributes:
            # Check all_of: every required attribute must be accepted
            all_met = all(
                base_confidences.get(code, 0.0) >= self.thresholds.accepted
                for code in da.rule.all_of
            )
            if not all_met:
                continue

            # Check none_of: every excluded attribute must be below tentative
            none_met = all(
                base_confidences.get(code, 0.0) < self.thresholds.tentative
                for code in da.rule.none_of
            )
            if not none_met:
                continue

            labels.append(da.code)
        return labels

    def compute_accepted_base_labels(
        self, base_confidences: dict[str, float]
    ) -> list[str]:
        """Return base attribute codes that meet the accepted threshold."""
        return [
            code
            for code in self.base_codes
            if base_confidences.get(code, 0.0) >= self.thresholds.accepted
        ]


def load_attribute_vocabulary(config_path: Path | None = None) -> AttributeVocabulary:
    """Load and validate the attribute vocabulary from YAML config."""
    path = config_path or DEFAULT_CONFIG
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    thresholds = Thresholds(**data.get("thresholds", {}))

    base_attrs = [
        BaseAttribute(**item) for item in data.get("base_attributes", [])
    ]

    base_codes = {a.code for a in base_attrs}

    derived_attrs = []
    for item in data.get("derived_attributes", []):
        rule_data = item.pop("rule", {})
        rule = DerivedRule(
            all_of=rule_data.get("all_of", []),
            none_of=rule_data.get("none_of", []),
        )
        # Validate rule references
        for code in rule.all_of + rule.none_of:
            if code not in base_codes:
                raise ValueError(
                    f"Derived attribute {item['code']!r} references "
                    f"unknown base attribute {code!r}"
                )
        derived_attrs.append(DerivedAttribute(**item, rule=rule))

    # Check for duplicate codes
    all_codes = [a.code for a in base_attrs] + [a.code for a in derived_attrs]
    seen = set()
    for code in all_codes:
        if code in seen:
            raise ValueError(f"Duplicate attribute code: {code!r}")
        seen.add(code)

    return AttributeVocabulary(
        thresholds=thresholds,
        base_attributes=base_attrs,
        derived_attributes=derived_attrs,
    )
