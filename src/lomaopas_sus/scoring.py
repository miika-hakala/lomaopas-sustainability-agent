from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, Optional

import yaml

from lomaopas_sus.models import ExtractedFacts, SustainabilityScore, ScoreBreakdown


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_scoring_rules(config_path: Optional[Path] = None) -> Dict:
    if config_path is None:
        config_path = _repo_root() / "configs" / "scoring_rules.yaml"
    with open(config_path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _resolve_config_key(
    fact_name: str,
    fact_value,
    fact_scores: Dict[str, Dict[str, float]],
    fact_max: Dict[str, Dict[str, float]],
    category: str,
) -> Optional[str]:
    if fact_value is None:
        list_candidate = f"{fact_name}_per_item"
        string_candidate = f"{fact_name}_non_empty"
        if list_candidate in fact_scores.get(category, {}) and list_candidate in fact_max.get(category, {}):
            candidate = list_candidate
        elif string_candidate in fact_scores.get(category, {}) and string_candidate in fact_max.get(category, {}):
            candidate = string_candidate
        else:
            candidate = fact_name
    elif isinstance(fact_value, list):
        candidate = f"{fact_name}_per_item"
    elif isinstance(fact_value, str):
        candidate = f"{fact_name}_non_empty"
    else:
        candidate = fact_name

    if candidate in fact_scores.get(category, {}) and candidate in fact_max.get(category, {}):
        return candidate
    if fact_name in fact_scores.get(category, {}) and fact_name in fact_max.get(category, {}):
        return fact_name
    return None


def calculate_sustainability_score(
    extracted_facts: ExtractedFacts,
    confidence: float,
    scoring_rules: Dict,
) -> SustainabilityScore:
    score_model_version = scoring_rules["score_model_version"]
    fact_scores_config = scoring_rules["fact_scores"]
    overall_score_weights = scoring_rules["overall_score_weights"]
    fact_max_raw_points_config = scoring_rules["fact_max_raw_points"]

    raw_scores_by_category = defaultdict(float)
    max_possible_raw_scores_by_category = defaultdict(float)
    granular_scores = defaultdict(float)

    def get_list_points(items: Optional[list], points_per_item: float, max_points: float) -> float:
        if not items:
            return 0.0
        return min(max_points, len(items) * points_per_item)

    facts_dict = extracted_facts.model_dump()

    for fact_category_name, fact_category_data in facts_dict.items():
        if fact_category_name == "evidence_snippets" or fact_category_data is None:
            continue

        for fact_name, fact_value in fact_category_data.items():
            config_key = _resolve_config_key(
                fact_name,
                fact_value,
                fact_scores_config,
                fact_max_raw_points_config,
                fact_category_name,
            )
            if config_key is None:
                continue

            fact_score_config = fact_scores_config[fact_category_name][config_key]
            fact_max_raw_points = fact_max_raw_points_config[fact_category_name][config_key]

            current_fact_raw_score = 0.0
            if fact_value is None:
                current_fact_raw_score = 0.0
            elif isinstance(fact_value, bool):
                if fact_value:
                    current_fact_raw_score = float(fact_score_config)
            elif isinstance(fact_value, str):
                if fact_value.strip():
                    current_fact_raw_score = float(fact_score_config)
            elif isinstance(fact_value, list):
                current_fact_raw_score = get_list_points(
                    fact_value, float(fact_score_config), float(fact_max_raw_points)
                )

            granular_scores[f"{fact_category_name}.{fact_name}"] = current_fact_raw_score

            if fact_category_name in [
                "energy_efficiency",
                "water_conservation",
                "waste_management",
                "local_community_engagement",
            ]:
                raw_scores_by_category["actions"] += current_fact_raw_score
                max_possible_raw_scores_by_category["actions"] += float(fact_max_raw_points)

            if fact_category_name in [
                "energy_efficiency",
                "water_conservation",
                "local_community_engagement",
            ] and config_key.endswith("_non_empty"):
                raw_scores_by_category["transparency"] += current_fact_raw_score
                max_possible_raw_scores_by_category["transparency"] += float(fact_max_raw_points)

            if fact_category_name == "certifications":
                raw_scores_by_category["certifications"] += current_fact_raw_score
                max_possible_raw_scores_by_category["certifications"] += float(fact_max_raw_points)

            if fact_category_name in [
                "energy_efficiency",
                "water_conservation",
                "waste_management",
                "local_community_engagement",
            ]:
                granular_scores[fact_category_name] += current_fact_raw_score

    final_score_raw = 0.0
    score_breakdown_dict = defaultdict(float)

    for category, weight in overall_score_weights.items():
        current_raw = raw_scores_by_category[category]
        max_raw = max_possible_raw_scores_by_category[category]

        if max_raw > 0:
            normalized_score = (current_raw / max_raw) * float(weight) * 100.0
        else:
            normalized_score = 0.0

        final_score_raw += normalized_score
        score_breakdown_dict[category] = normalized_score

    final_score_raw = min(100.0, max(0.0, final_score_raw))
    total_score_final = min(100.0, max(0.0, final_score_raw * confidence))

    score_breakdown = ScoreBreakdown(
        actions=score_breakdown_dict.get("actions", 0.0),
        transparency=score_breakdown_dict.get("transparency", 0.0),
        certifications=score_breakdown_dict.get("certifications", 0.0),
        energy_efficiency=granular_scores.get("energy_efficiency", 0.0),
        water_conservation=granular_scores.get("water_conservation", 0.0),
        waste_management=granular_scores.get("waste_management", 0.0),
        local_community_engagement=granular_scores.get("local_community_engagement", 0.0),
    )

    return SustainabilityScore(
        score_model_version=score_model_version,
        raw_facts=extracted_facts,
        evidence=extracted_facts.evidence_snippets,
        confidence=confidence,
        score_breakdown=score_breakdown,
        total_score_raw=final_score_raw,
        total_score_final=total_score_final,
    )
