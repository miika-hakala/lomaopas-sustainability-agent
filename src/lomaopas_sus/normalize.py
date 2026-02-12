"""Canonical normalization layer for extracted facts.

Ensures consistent representation regardless of extractor (Ollama vs OpenAI):
- All "unknown / not mentioned" → null
- false → null (without per-fact negation evidence, false = "not mentioned")
- Empty lists → null
- Empty strings → null
- Remove extractor-specific extra fields
- Add meta.normalized = true
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from lomaopas_sus.models import ExtractedFacts

# Categories that contain fact sub-models
_FACT_CATEGORIES = [
    "energy_efficiency",
    "water_conservation",
    "waste_management",
    "local_community_engagement",
    "certifications",
]

# Known extractor-specific extra fields to strip (Ollama sometimes adds these)
_EXTRA_FIELD_PREFIXES = [
    "economy_",
    "faq_",
    "sustainable_pool_",
    "additional_",
    "general_",
]


def _is_extra_field(key: str) -> bool:
    return any(key.startswith(p) for p in _EXTRA_FIELD_PREFIXES)


def _normalize_value(value: Any) -> Any:
    """Normalize a single fact value to canonical form."""
    if value is None:
        return None

    # false without evidence → null (we can't distinguish "explicitly denied" from "not mentioned")
    if value is False:
        return None

    # true stays true
    if value is True:
        return True

    # Empty string → null
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None

    # Empty list → null; non-empty list → keep but normalize items
    if isinstance(value, list):
        cleaned = [item for item in value if item]  # drop empty strings/None
        return cleaned if cleaned else None

    return value


def normalize_facts_dict(raw_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a raw extraction dict (before Pydantic validation).

    Applies canonical normalization rules:
    - false → null for all boolean fact fields
    - [] → null for list fields
    - "" → null for string fields
    - Strips extractor-specific extra fields
    """
    result: Dict[str, Any] = {}

    for key, value in raw_dict.items():
        # Skip extractor-specific extra fields
        if _is_extra_field(key):
            continue

        # evidence_snippets: normalize entries (fix common LLM field name variants)
        if key == "evidence_snippets":
            if not isinstance(value, list):
                result[key] = []
                continue
            fixed: List[Any] = []
            for item in value:
                if isinstance(item, dict):
                    # Ollama sometimes uses "text" instead of "snippet"
                    if "text" in item and "snippet" not in item:
                        item["snippet"] = item.pop("text")
                    if "url" in item and "snippet" in item:
                        fixed.append({"url": item["url"], "snippet": item["snippet"]})
            result[key] = fixed
            continue

        # Known fact categories: normalize each sub-field
        if key in _FACT_CATEGORIES and isinstance(value, dict):
            normalized_sub: Dict[str, Any] = {}
            for sub_key, sub_val in value.items():
                normalized_sub[sub_key] = _normalize_value(sub_val)
            result[key] = normalized_sub
            continue

        # Pass through other known fields
        result[key] = value

    return result


def normalize_extracted_facts(facts: ExtractedFacts) -> ExtractedFacts:
    """Normalize an already-validated ExtractedFacts model.

    Returns a new ExtractedFacts with canonical form.
    """
    raw = facts.model_dump()
    normalized = normalize_facts_dict(raw)
    return ExtractedFacts.model_validate(normalized)
