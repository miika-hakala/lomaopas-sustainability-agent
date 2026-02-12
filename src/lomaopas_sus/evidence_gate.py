"""Evidence gating layer (v1.1).

Deterministic rules that cap the sustainability label when the extracted
facts do not contain enough distinct claims or concrete evidence.
No LLM calls — pure field counting on ExtractedFacts.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from lomaopas_sus.models import ExtractedFacts

# Labels ordered from lowest to highest
_LABEL_ORDER = ["Insufficient Evidence", "Basic", "Good", "Excellent"]

# Fact fields that count as concrete measurable actions
_CONCRETE_ACTION_FIELDS = {
    "energy_efficiency.solar_panels_used",
    "energy_efficiency.renewable_energy_sources",
    "energy_efficiency.energy_reduction_targets",
    "energy_efficiency.led_lighting_used",
    "water_conservation.water_saving_fixtures",
    "water_conservation.rainwater_harvesting",
    "water_conservation.linen_reuse_program",
    "water_conservation.water_reduction_targets",
    "waste_management.recycling_program",
    "waste_management.plastic_reduction_initiatives",
    "waste_management.food_waste_reduction",
    "waste_management.composting_program",
}


def _is_truthy(value: Any) -> bool:
    """Return True if the value represents a present sustainability claim."""
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    return bool(value)


def count_claims(facts: ExtractedFacts) -> int:
    """Count the number of distinct non-null sustainability claims."""
    facts_dict = facts.model_dump()
    count = 0
    for category_name, category_data in facts_dict.items():
        if category_name == "evidence_snippets" or not isinstance(category_data, dict):
            continue
        for _field_name, value in category_data.items():
            if _is_truthy(value):
                count += 1
    return count


def has_certification(facts: ExtractedFacts) -> bool:
    """Return True if the facts contain at least one eco-certification."""
    certs = facts.certifications
    if certs.eco_certifications and len(certs.eco_certifications) > 0:
        return True
    return False


def has_concrete_action(facts: ExtractedFacts) -> bool:
    """Return True if the facts contain at least one concrete measurable action."""
    facts_dict = facts.model_dump()
    for category_name, category_data in facts_dict.items():
        if category_name == "evidence_snippets" or not isinstance(category_data, dict):
            continue
        for field_name, value in category_data.items():
            path = f"{category_name}.{field_name}"
            if path in _CONCRETE_ACTION_FIELDS and _is_truthy(value):
                return True
    return False


def _cap_label(label: str, max_label: str) -> str:
    """Cap a label at the given maximum level."""
    label_idx = _LABEL_ORDER.index(label)
    max_idx = _LABEL_ORDER.index(max_label)
    if label_idx > max_idx:
        return max_label
    return label


def apply_evidence_gate(
    score: float,
    label: str,
    facts: ExtractedFacts,
    thresholds: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Apply evidence gating rules to cap an inflated label.

    Returns (gated_label, gate_meta) where gate_meta contains:
      - evidence_gate_applied: bool
      - original_label: str (before gating)
      - claim_count: int
      - has_certification: bool
      - has_concrete_action: bool
    """
    claim_count = count_claims(facts)
    cert = has_certification(facts)
    action = has_concrete_action(facts)

    gate_meta: Dict[str, Any] = {
        "evidence_gate_applied": False,
        "original_label": label,
        "claim_count": claim_count,
        "has_certification": cert,
        "has_concrete_action": action,
    }

    gated = label

    # Rule C: evidence_count < 2 → cap to Basic
    if claim_count < 2:
        gated = _cap_label(gated, "Basic")

    # Rule A+B: Excellent requires ≥3 claims AND (certification OR concrete action)
    if gated == "Excellent":
        if claim_count < 3 or (not cert and not action):
            gated = _cap_label(gated, "Good")

    if gated != label:
        gate_meta["evidence_gate_applied"] = True

    return gated, gate_meta
