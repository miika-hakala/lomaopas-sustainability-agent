import pytest

from lomaopas_sus.models import (
    ExtractedFacts,
    EnergyEfficiencyFacts,
    WaterConservationFacts,
    WasteManagementFacts,
    LocalCommunityEngagementFacts,
    CertificationsFacts,
    EvidenceSnippet,
)
from lomaopas_sus.evidence_gate import (
    apply_evidence_gate,
    count_claims,
    has_certification,
    has_concrete_action,
)


def test_excellent_without_enough_evidence_downgraded():
    """Excellent label with only 2 claims should be capped to Good."""
    facts = ExtractedFacts(
        energy_efficiency=EnergyEfficiencyFacts(solar_panels_used=True),
        local_community_engagement=LocalCommunityEngagementFacts(local_sourcing_food=True),
    )
    assert count_claims(facts) == 2

    gated, meta = apply_evidence_gate(19.42, "Excellent", facts)
    assert gated == "Good"
    assert meta["evidence_gate_applied"] is True
    assert meta["original_label"] == "Excellent"
    assert meta["claim_count"] == 2


def test_excellent_without_cert_or_action_downgraded():
    """Excellent with 3 claims but no certification or concrete action → Good."""
    facts = ExtractedFacts(
        local_community_engagement=LocalCommunityEngagementFacts(
            local_sourcing_food=True,
            local_employment_initiatives=True,
            community_support_programs="Supports local schools",
        ),
    )
    assert count_claims(facts) == 3
    assert has_certification(facts) is False
    # community_support_programs is not in _CONCRETE_ACTION_FIELDS
    # local_sourcing_food and local_employment_initiatives are not either
    assert has_concrete_action(facts) is False

    gated, meta = apply_evidence_gate(20.0, "Excellent", facts)
    assert gated == "Good"
    assert meta["evidence_gate_applied"] is True


def test_excellent_with_enough_evidence_stays():
    """Excellent with ≥3 claims and a certification stays Excellent."""
    facts = ExtractedFacts(
        energy_efficiency=EnergyEfficiencyFacts(
            solar_panels_used=True,
            led_lighting_used=True,
            renewable_energy_sources=["solar", "wind"],
        ),
        certifications=CertificationsFacts(
            eco_certifications=["Green Key"],
        ),
    )
    assert count_claims(facts) == 4  # 3 energy + 1 cert
    assert has_certification(facts) is True

    gated, meta = apply_evidence_gate(20.0, "Excellent", facts)
    assert gated == "Excellent"
    assert meta["evidence_gate_applied"] is False


def test_excellent_with_concrete_action_stays():
    """Excellent with ≥3 claims and a concrete action (no cert) stays Excellent."""
    facts = ExtractedFacts(
        energy_efficiency=EnergyEfficiencyFacts(
            solar_panels_used=True,
            renewable_energy_sources=["solar"],
            energy_reduction_targets="20% by 2030",
        ),
    )
    assert count_claims(facts) == 3
    assert has_certification(facts) is False
    assert has_concrete_action(facts) is True

    gated, meta = apply_evidence_gate(18.0, "Excellent", facts)
    assert gated == "Excellent"
    assert meta["evidence_gate_applied"] is False


def test_low_evidence_capped_basic():
    """Only 1 claim → label capped to Basic max."""
    facts = ExtractedFacts(
        energy_efficiency=EnergyEfficiencyFacts(solar_panels_used=True),
    )
    assert count_claims(facts) == 1

    # Even if score says Good
    gated, meta = apply_evidence_gate(8.0, "Good", facts)
    assert gated == "Basic"
    assert meta["evidence_gate_applied"] is True
    assert meta["claim_count"] == 1


def test_zero_evidence_stays_insufficient():
    """Zero claims with Insufficient Evidence stays unchanged."""
    facts = ExtractedFacts()
    assert count_claims(facts) == 0

    gated, meta = apply_evidence_gate(0.0, "Insufficient Evidence", facts)
    assert gated == "Insufficient Evidence"
    assert meta["evidence_gate_applied"] is False


def test_basic_label_not_downgraded_with_two_claims():
    """Basic label with 2 claims stays Basic (gate only caps, doesn't upgrade)."""
    facts = ExtractedFacts(
        energy_efficiency=EnergyEfficiencyFacts(solar_panels_used=True),
        water_conservation=WaterConservationFacts(linen_reuse_program=True),
    )
    gated, meta = apply_evidence_gate(2.0, "Basic", facts)
    assert gated == "Basic"
    assert meta["evidence_gate_applied"] is False


def test_good_label_with_enough_evidence_stays():
    """Good label with ≥2 claims is not affected by gating."""
    facts = ExtractedFacts(
        energy_efficiency=EnergyEfficiencyFacts(solar_panels_used=True),
        water_conservation=WaterConservationFacts(linen_reuse_program=True),
        waste_management=WasteManagementFacts(recycling_program=True),
    )
    gated, meta = apply_evidence_gate(8.0, "Good", facts)
    assert gated == "Good"
    assert meta["evidence_gate_applied"] is False


def test_count_claims_empty():
    """Empty facts should have 0 claims."""
    facts = ExtractedFacts()
    assert count_claims(facts) == 0


def test_count_claims_all_fields():
    """Facts with all fields populated should count all claims."""
    facts = ExtractedFacts(
        energy_efficiency=EnergyEfficiencyFacts(
            solar_panels_used=True,
            led_lighting_used=True,
            renewable_energy_sources=["solar"],
            energy_reduction_targets="20% by 2030",
        ),
        water_conservation=WaterConservationFacts(
            water_saving_fixtures=True,
            linen_reuse_program=True,
            rainwater_harvesting=True,
            water_reduction_targets="15% by 2028",
        ),
        waste_management=WasteManagementFacts(
            recycling_program=True,
            plastic_reduction_initiatives=["no single-use plastics"],
            food_waste_reduction=True,
            composting_program=True,
        ),
        local_community_engagement=LocalCommunityEngagementFacts(
            local_sourcing_food=True,
            local_employment_initiatives=True,
            community_support_programs="Supports local schools",
        ),
        certifications=CertificationsFacts(
            eco_certifications=["Green Key"],
            other_sustainability_badges=["EcoLeader Gold"],
        ),
    )
    # 4 + 4 + 4 + 3 + 2 = 17
    assert count_claims(facts) == 17


def test_score_not_modified_by_gate():
    """Evidence gate never modifies the score, only the label."""
    facts = ExtractedFacts(
        energy_efficiency=EnergyEfficiencyFacts(solar_panels_used=True),
    )
    score = 19.42
    gated, meta = apply_evidence_gate(score, "Excellent", facts)
    # Score is passed through — gate only returns label
    assert meta["original_label"] == "Excellent"
    assert gated != "Excellent"  # downgraded
