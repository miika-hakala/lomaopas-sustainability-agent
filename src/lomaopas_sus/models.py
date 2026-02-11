from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl, ConfigDict


class EnergyEfficiencyFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    solar_panels_used: Optional[bool] = None
    led_lighting_used: Optional[bool] = None
    renewable_energy_sources: Optional[List[str]] = None
    energy_reduction_targets: Optional[str] = None


class WaterConservationFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    water_saving_fixtures: Optional[bool] = None
    linen_reuse_program: Optional[bool] = None
    rainwater_harvesting: Optional[bool] = None
    water_reduction_targets: Optional[str] = None


class WasteManagementFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recycling_program: Optional[bool] = None
    plastic_reduction_initiatives: Optional[List[str]] = None
    food_waste_reduction: Optional[bool] = None
    composting_program: Optional[bool] = None


class LocalCommunityEngagementFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_sourcing_food: Optional[bool] = None
    local_employment_initiatives: Optional[bool] = None
    community_support_programs: Optional[str] = None


class CertificationsFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eco_certifications: Optional[List[str]] = None
    other_sustainability_badges: Optional[List[str]] = None


class EvidenceSnippet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: HttpUrl
    snippet: str


class ExtractedFacts(BaseModel):
    model_config = ConfigDict(extra="allow")

    energy_efficiency: EnergyEfficiencyFacts = Field(default_factory=EnergyEfficiencyFacts)
    water_conservation: WaterConservationFacts = Field(default_factory=WaterConservationFacts)
    waste_management: WasteManagementFacts = Field(default_factory=WasteManagementFacts)
    local_community_engagement: LocalCommunityEngagementFacts = Field(
        default_factory=LocalCommunityEngagementFacts
    )
    certifications: CertificationsFacts = Field(default_factory=CertificationsFacts)
    evidence_snippets: List[EvidenceSnippet] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actions: float = 0.0
    transparency: float = 0.0
    certifications: float = 0.0
    energy_efficiency: float = 0.0
    water_conservation: float = 0.0
    waste_management: float = 0.0
    local_community_engagement: float = 0.0


class SustainabilityScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score_model_version: str
    raw_facts: ExtractedFacts
    evidence: List[EvidenceSnippet]
    confidence: float = Field(..., ge=0.0, le=1.0)
    score_breakdown: ScoreBreakdown
    total_score_raw: float = Field(..., ge=0.0, le=100.0)
    total_score_final: float = Field(..., ge=0.0, le=100.0)


class Hotel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    website: HttpUrl
    hotel_id: Optional[str] = None
    location: Optional[str] = None
    booking_url: Optional[HttpUrl] = None
    fallback_urls: Optional[List[str]] = None
