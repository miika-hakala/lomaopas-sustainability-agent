import pytest
from pathlib import Path

from lomaopas_sus.models import (
    ExtractedFacts,
    EvidenceSnippet,
    EnergyEfficiencyFacts,
    WaterConservationFacts,
    WasteManagementFacts,
    LocalCommunityEngagementFacts,
    CertificationsFacts,
)
from lomaopas_sus.scoring import load_scoring_rules, calculate_sustainability_score


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIGS_DIR = PROJECT_ROOT / "configs"
SCORING_RULES_PATH = CONFIGS_DIR / "scoring_rules.yaml"


@pytest.fixture(scope="module")
def scoring_rules():
    return load_scoring_rules(SCORING_RULES_PATH)


@pytest.fixture
def max_facts():
    return ExtractedFacts(
        energy_efficiency=EnergyEfficiencyFacts(
            solar_panels_used=True,
            led_lighting_used=True,
            renewable_energy_sources=[
                "solar",
                "wind",
                "hydro",
                "geothermal",
                "biomass",
            ],
            energy_reduction_targets="Target: 20% by 2030",
        ),
        water_conservation=WaterConservationFacts(
            water_saving_fixtures=True,
            linen_reuse_program=True,
            rainwater_harvesting=True,
            water_reduction_targets="Target: 15% by 2028",
        ),
        waste_management=WasteManagementFacts(
            recycling_program=True,
            plastic_reduction_initiatives=[
                "no single-use plastics",
                "refillable toiletries",
                "compostable packaging",
                "plastic-free events",
                "waste separation",
            ],
            food_waste_reduction=True,
            composting_program=True,
        ),
        local_community_engagement=LocalCommunityEngagementFacts(
            local_sourcing_food=True,
            local_employment_initiatives=True,
            community_support_programs="Supports local schools and charities.",
        ),
        certifications=CertificationsFacts(
            eco_certifications=[
                "Green Key",
                "Travelife",
                "EarthCheck",
                "Biosphere",
                "LEED",
            ],
            other_sustainability_badges=[
                "EcoLeader Gold",
                "Sustainable Tourism Award",
                "Green Hotel Badge",
                "Responsible Business",
                "Nature Friendly",
            ],
        ),
        evidence_snippets=[
            EvidenceSnippet(
                url="http://example.com/sustainability", snippet="solar panels and LED lights"
            ),
            EvidenceSnippet(
                url="http://example.com/waste", snippet="recycling program and no single-use plastics"
            ),
        ],
    )


def test_empty_facts_score_zero(scoring_rules):
    facts = ExtractedFacts()
    score = calculate_sustainability_score(facts, confidence=1.0, scoring_rules=scoring_rules)
    assert score.total_score_raw == 0.0
    assert score.total_score_final == 0.0
    assert score.score_breakdown.actions == 0.0
    assert score.score_breakdown.transparency == 0.0
    assert score.score_breakdown.certifications == 0.0


def test_max_facts_score_one_hundred(max_facts, scoring_rules):
    score = calculate_sustainability_score(max_facts, confidence=1.0, scoring_rules=scoring_rules)
    assert 99.9 <= score.total_score_raw <= 100.1
    assert 99.9 <= score.total_score_final <= 100.1
    assert score.score_breakdown.actions > 0
    assert score.score_breakdown.transparency > 0
    assert score.score_breakdown.certifications > 0


def test_confidence_factor(max_facts, scoring_rules):
    score_full_confidence = calculate_sustainability_score(
        max_facts, confidence=1.0, scoring_rules=scoring_rules
    )
    score_half_confidence = calculate_sustainability_score(
        max_facts, confidence=0.5, scoring_rules=scoring_rules
    )

    assert score_full_confidence.total_score_raw == score_half_confidence.total_score_raw
    assert score_half_confidence.total_score_final == pytest.approx(
        score_full_confidence.total_score_raw * 0.5
    )


def test_specific_boolean_fact_scoring(scoring_rules):
    facts = ExtractedFacts(energy_efficiency=EnergyEfficiencyFacts(solar_panels_used=True))
    score = calculate_sustainability_score(facts, confidence=1.0, scoring_rules=scoring_rules)
    assert score.total_score_raw > 0
    assert score.score_breakdown.actions > 0


def test_specific_string_fact_scoring(scoring_rules):
    facts = ExtractedFacts(
        energy_efficiency=EnergyEfficiencyFacts(energy_reduction_targets="target mentioned")
    )
    score = calculate_sustainability_score(facts, confidence=1.0, scoring_rules=scoring_rules)
    assert score.total_score_raw > 0
    assert score.score_breakdown.transparency > 0


def test_specific_list_fact_scoring(scoring_rules):
    facts = ExtractedFacts(
        energy_efficiency=EnergyEfficiencyFacts(renewable_energy_sources=["solar", "wind"])
    )
    score = calculate_sustainability_score(facts, confidence=1.0, scoring_rules=scoring_rules)
    assert score.total_score_raw > 0
    assert score.score_breakdown.actions > 0


def test_scoring_rules_loaded_correctly(scoring_rules):
    assert "score_model_version" in scoring_rules
    assert scoring_rules["score_model_version"] == "v1.0"
    assert "fact_scores" in scoring_rules
    assert "overall_score_weights" in scoring_rules
    assert "fact_max_raw_points" in scoring_rules


def test_score_breakdown_values(scoring_rules):
    facts = ExtractedFacts(
        energy_efficiency=EnergyEfficiencyFacts(solar_panels_used=True),
        certifications=CertificationsFacts(eco_certifications=["Green Key"]),
    )
    score = calculate_sustainability_score(facts, confidence=1.0, scoring_rules=scoring_rules)
    assert score.score_breakdown.actions > 0
    assert score.score_breakdown.certifications > 0
    assert score.score_breakdown.transparency == 0


def test_granular_category_scores_in_breakdown(scoring_rules):
    facts = ExtractedFacts(
        energy_efficiency=EnergyEfficiencyFacts(solar_panels_used=True),
        waste_management=WasteManagementFacts(recycling_program=True),
    )
    score = calculate_sustainability_score(facts, confidence=1.0, scoring_rules=scoring_rules)
    assert score.score_breakdown.energy_efficiency > 0
    assert score.score_breakdown.waste_management > 0
    assert score.score_breakdown.water_conservation == 0
