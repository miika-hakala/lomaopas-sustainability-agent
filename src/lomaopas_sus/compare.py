from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from lomaopas_sus.models import SustainabilityScore
from lomaopas_sus.scoring import score_to_label, load_thresholds


def load_jsonl_data(filepath: Path) -> List[Dict[str, Any]]:
    data: List[Dict[str, Any]] = []
    if not filepath.exists():
        return data
    with open(filepath, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                data.append(json.loads(line))
    return data


def _median(values: List[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    if n % 2 == 0:
        return (s[n // 2 - 1] + s[n // 2]) / 2
    return s[n // 2]


def _get_meta(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return entry.get("meta")


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

    local_map: Dict[str, SustainabilityScore] = {}
    local_meta_map: Dict[str, Dict[str, Any]] = {}
    for entry in local_data:
        name = entry["hotel"]["name"]
        local_map[name] = SustainabilityScore.model_validate(entry["score"])
        if _get_meta(entry):
            local_meta_map[name] = entry["meta"]

    openai_map: Dict[str, SustainabilityScore] = {}
    openai_meta_map: Dict[str, Dict[str, Any]] = {}
    for entry in openai_data:
        name = entry["hotel"]["name"]
        openai_map[name] = SustainabilityScore.model_validate(entry["score"])
        if _get_meta(entry):
            openai_meta_map[name] = entry["meta"]

    all_hotel_names = sorted(set(local_map.keys()) | set(openai_map.keys()))

    # --- Success rates ---
    report_lines.append("## Success Rates\n\n")
    report_lines.append(f"- **Local (Ollama) hotels extracted:** {len(local_map)}\n")
    report_lines.append(f"- **OpenAI hotels extracted:** {len(openai_map)}\n")
    comparable = sorted(set(local_map.keys()) & set(openai_map.keys()))
    report_lines.append(f"- **Both have data (comparable):** {len(comparable)}\n\n")

    # --- Timing & Cost ---
    report_lines.append("## Timing & Cost\n\n")

    local_durations = [m["duration_ms"] for m in local_meta_map.values() if m.get("duration_ms")]
    openai_durations = [m["duration_ms"] for m in openai_meta_map.values() if m.get("duration_ms")]
    openai_costs = [m.get("cost_estimate_usd", 0) for m in openai_meta_map.values()]
    openai_tokens_in = [m.get("tokens_in", 0) for m in openai_meta_map.values()]
    openai_tokens_out = [m.get("tokens_out", 0) for m in openai_meta_map.values()]
    local_tokens_out = [m.get("tokens_out", 0) for m in local_meta_map.values()]

    if local_durations:
        report_lines.append(f"### Local (Ollama)\n\n")
        report_lines.append(f"- Mean duration: {sum(local_durations)/len(local_durations):.0f} ms\n")
        report_lines.append(f"- Median duration: {_median(local_durations):.0f} ms\n")
        report_lines.append(f"- Total duration: {sum(local_durations)/1000:.1f} s\n")
        if local_tokens_out:
            report_lines.append(f"- Mean tokens out: {sum(local_tokens_out)/len(local_tokens_out):.0f}\n")
        report_lines.append(f"- Cost: $0.00 (local)\n\n")

    if openai_durations:
        report_lines.append(f"### OpenAI (gpt-4o-mini)\n\n")
        report_lines.append(f"- Mean duration: {sum(openai_durations)/len(openai_durations):.0f} ms\n")
        report_lines.append(f"- Median duration: {_median(openai_durations):.0f} ms\n")
        report_lines.append(f"- Total duration: {sum(openai_durations)/1000:.1f} s\n")
        if openai_tokens_in:
            report_lines.append(f"- Mean tokens in: {sum(openai_tokens_in)/len(openai_tokens_in):.0f}\n")
        if openai_tokens_out:
            report_lines.append(f"- Mean tokens out: {sum(openai_tokens_out)/len(openai_tokens_out):.0f}\n")
        if openai_costs:
            total_cost = sum(openai_costs)
            report_lines.append(f"- Total cost estimate: ${total_cost:.4f}\n")
            report_lines.append(f"- Mean cost per hotel: ${total_cost/len(openai_costs):.6f}\n\n")

    # --- Score Statistics ---
    report_lines.append("## Overall Score Statistics\n\n")

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
        report_lines.append(
            f"- **Median Total Score Difference:** {_median(total_score_diffs):.2f}\n"
        )
        report_lines.append(
            f"- **Max Total Score Difference:** {max(total_score_diffs):.2f}\n"
        )
    if confidence_diffs:
        report_lines.append(
            f"- **Mean Confidence Difference:** {sum(confidence_diffs) / len(confidence_diffs):.2f}\n"
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
    if not missing_facts_local and not missing_facts_openai:
        report_lines.append("- All hotels have data from both extractors.\n")

    # --- Fact Consistency ---
    report_lines.append("\n### Fact Consistency Breakdown\n\n")
    report_lines.append("| Fact Path | Local Has | OpenAI Has | Both Have | Different Value |\n")
    report_lines.append("|---|---|---|---|---|\n")
    for fact_path in sorted(fact_diff_counts.keys()):
        counts = fact_diff_counts[fact_path]
        report_lines.append(
            f"| `{fact_path}` | {counts['local_has']} | {counts['openai_has']} "
            f"| {counts['both_have']} | {counts['diff_value']} |\n"
        )

    # --- Score Deltas with Labels ---
    try:
        thresholds = load_thresholds()
    except Exception:
        thresholds = None

    report_lines.append("\n## Score Deltas (Local vs. OpenAI)\n\n")
    score_deltas = []
    for hotel_name in all_hotel_names:
        local_score = local_map.get(hotel_name)
        openai_score = openai_map.get(hotel_name)
        if local_score and openai_score:
            delta = local_score.total_score_final - openai_score.total_score_final
            score_deltas.append((abs(delta), hotel_name, delta))

    score_deltas.sort(key=lambda x: x[0], reverse=True)

    if score_deltas:
        if thresholds:
            report_lines.append("| Hotel Name | Local Score | Local Label | OpenAI Score | OpenAI Label | Delta |\n")
            report_lines.append("|---|---|---|---|---|---|\n")
        else:
            report_lines.append("| Hotel Name | Local Score | OpenAI Score | Delta |\n")
            report_lines.append("|---|---|---|---|\n")
        for _, hotel_name, delta in score_deltas:
            local_s = local_map[hotel_name].total_score_final
            openai_s = openai_map[hotel_name].total_score_final
            if thresholds:
                ll = score_to_label(local_s, thresholds)
                ol = score_to_label(openai_s, thresholds)
                report_lines.append(
                    f"| {hotel_name} | {local_s:.2f} | {ll} | {openai_s:.2f} | {ol} | {delta:+.2f} |\n"
                )
            else:
                report_lines.append(
                    f"| {hotel_name} | {local_s:.2f} | {openai_s:.2f} | {delta:+.2f} |\n"
                )
    else:
        report_lines.append("No hotels with comparable scores to calculate deltas.\n")

    # --- Label Agreement ---
    if thresholds:
        report_lines.append("\n## Label Agreement\n\n")
        agree = 0
        total_cmp = 0
        for hotel_name in comparable:
            ls = local_map[hotel_name].total_score_final
            os_ = openai_map[hotel_name].total_score_final
            ll = score_to_label(ls, thresholds)
            ol = score_to_label(os_, thresholds)
            total_cmp += 1
            if ll == ol:
                agree += 1
        pct = (agree / total_cmp * 100) if total_cmp > 0 else 0
        report_lines.append(f"- **Agreement:** {agree}/{total_cmp} = **{pct:.0f}%**\n")
        report_lines.append(f"- Thresholds: `configs/thresholds.v1.json`\n\n")

    # --- Example Diffs (top 3 biggest deltas) ---
    report_lines.append("\n## Example Diffs (Top 3 Biggest Deltas)\n\n")
    examples = score_deltas[:3] if score_deltas else []

    for _, hotel_name, delta in examples:
        report_lines.append(f"### {hotel_name} (delta: {delta:+.2f})\n\n")
        local_score = local_map[hotel_name]
        openai_score = openai_map[hotel_name]

        local_facts = local_score.raw_facts.model_dump(exclude_none=True)
        openai_facts = openai_score.raw_facts.model_dump(exclude_none=True)

        local_paths = get_all_fact_paths(local_facts)
        openai_paths = get_all_fact_paths(openai_facts)

        all_keys = sorted(set(local_paths.keys()) | set(openai_paths.keys()))
        report_lines.append("| Fact | Local | OpenAI |\n")
        report_lines.append("|---|---|---|\n")
        for key in all_keys:
            lv = local_paths.get(key, "—")
            ov = openai_paths.get(key, "—")
            if lv != ov:
                report_lines.append(f"| `{key}` | {lv} | {ov} |\n")
        report_lines.append("\n")

    return "".join(report_lines)
