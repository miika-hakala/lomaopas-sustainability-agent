from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from lomaopas_sus.models import SustainabilityScore


def load_jsonl_data(filepath: Path) -> List[Dict[str, Any]]:
    data: List[Dict[str, Any]] = []
    if not filepath.exists():
        return data
    with open(filepath, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                data.append(json.loads(line))
    return data


def compare_scores_and_facts(
    local_data: List[Dict[str, Any]],
    openai_data: List[Dict[str, Any]],
) -> str:
    report_lines: List[str] = []
    report_lines.append("# LLM Extraction Comparison Report\n\n")
    report_lines.append(
        "This report compares sustainability fact extraction and scoring results\n"
    )
    report_lines.append("from a local LLM (Ollama) and OpenAI's LLM.\n\n")

    if not local_data and not openai_data:
        return "## No data available for comparison.\n"

    local_map = {
        entry["hotel"]["name"]: SustainabilityScore.model_validate(entry["score"])
        for entry in local_data
    }
    openai_map = {
        entry["hotel"]["name"]: SustainabilityScore.model_validate(entry["score"])
        for entry in openai_data
    }

    all_hotel_names = sorted(set(local_map.keys()) | set(openai_map.keys()))

    report_lines.append("## Overall Statistics\n\n")

    total_score_diffs: List[float] = []
    confidence_diffs: List[float] = []
    missing_facts_local: List[str] = []
    missing_facts_openai: List[str] = []

    fact_diff_counts = defaultdict(
        lambda: {"local_has": 0, "openai_has": 0, "both_have": 0, "diff_value": 0}
    )

    def get_all_fact_paths(facts: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
        paths: Dict[str, Any] = {}
        for key, value in facts.items():
            if key == "evidence_snippets":
                continue
            current_path = f"{parent_key}.{key}" if parent_key else key
            if isinstance(value, dict):
                paths.update(get_all_fact_paths(value, current_path))
            else:
                paths[current_path] = value
        return paths

    for hotel_name in all_hotel_names:
        local_score = local_map.get(hotel_name)
        openai_score = openai_map.get(hotel_name)

        if local_score and openai_score:
            total_score_diffs.append(
                abs(local_score.total_score_final - openai_score.total_score_final)
            )
            confidence_diffs.append(abs(local_score.confidence - openai_score.confidence))

            local_facts = local_score.raw_facts.model_dump(exclude_none=True)
            openai_facts = openai_score.raw_facts.model_dump(exclude_none=True)

            local_fact_paths = get_all_fact_paths(local_facts)
            openai_fact_paths = get_all_fact_paths(openai_facts)

            all_fact_keys = sorted(set(local_fact_paths.keys()) | set(openai_fact_paths.keys()))
            for key in all_fact_keys:
                local_val = local_fact_paths.get(key)
                openai_val = openai_fact_paths.get(key)

                if local_val is not None and openai_val is not None:
                    if local_val == openai_val:
                        fact_diff_counts[key]["both_have"] += 1
                    else:
                        fact_diff_counts[key]["diff_value"] += 1
                elif local_val is not None:
                    fact_diff_counts[key]["local_has"] += 1
                elif openai_val is not None:
                    fact_diff_counts[key]["openai_has"] += 1

        elif local_score:
            missing_facts_openai.append(hotel_name)
        elif openai_score:
            missing_facts_local.append(hotel_name)

    if total_score_diffs:
        report_lines.append(
            f"- **Mean Total Score Difference:** {sum(total_score_diffs) / len(total_score_diffs):.2f}\n"
        )
        total_score_diffs.sort()
        report_lines.append(
            f"- **Median Total Score Difference:** {total_score_diffs[len(total_score_diffs) // 2]:.2f}\n"
        )
    if confidence_diffs:
        report_lines.append(
            f"- **Mean Confidence Difference:** {sum(confidence_diffs) / len(confidence_diffs):.2f}\n"
        )
        confidence_diffs.sort()
        report_lines.append(
            f"- **Median Confidence Difference:** {confidence_diffs[len(confidence_diffs) // 2]:.2f}\n"
        )

    report_lines.append("\n### Missing Data\n\n")
    if missing_facts_local:
        report_lines.append(
            f"- **Hotels with no local LLM data:** {', '.join(missing_facts_local)}\n"
        )
    if missing_facts_openai:
        report_lines.append(
            f"- **Hotels with no OpenAI LLM data:** {', '.join(missing_facts_openai)}\n"
        )

    report_lines.append("\n### Fact Consistency Breakdown\n\n")
    report_lines.append("| Fact Path | Local Has | OpenAI Has | Both Have | Different Value |\n")
    report_lines.append("|---|---|---|---|---|\n")
    for fact_path, counts in fact_diff_counts.items():
        report_lines.append(
            f"| `{fact_path}` | {counts['local_has']} | {counts['openai_has']} "
            f"| {counts['both_have']} | {counts['diff_value']} |\n"
        )

    report_lines.append("\n## Biggest Score Deltas (Local vs. OpenAI)\n\n")
    score_deltas = []
    for hotel_name in all_hotel_names:
        local_score = local_map.get(hotel_name)
        openai_score = openai_map.get(hotel_name)
        if local_score and openai_score:
            delta = local_score.total_score_final - openai_score.total_score_final
            score_deltas.append((abs(delta), hotel_name, delta))

    score_deltas.sort(key=lambda x: x[0], reverse=True)

    if score_deltas:
        report_lines.append("| Hotel Name | Local Score | OpenAI Score | Difference |\n")
        report_lines.append("|---|---|---|---|\n")
        for _, hotel_name, delta in score_deltas[:10]:
            local_s = local_map[hotel_name].total_score_final
            openai_s = openai_map[hotel_name].total_score_final
            report_lines.append(
                f"| {hotel_name} | {local_s:.2f} | {openai_s:.2f} | {delta:.2f} |\n"
            )
    else:
        report_lines.append("No hotels with comparable scores to calculate deltas.\n")

    return "".join(report_lines)
