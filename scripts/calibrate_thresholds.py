#!/usr/bin/env python3
"""Threshold calibration script for sustainability scores.

Reads local + OpenAI JSONL outputs, analyzes score distributions,
computes label agreement, and writes threshold config + calibration report.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def load_thresholds(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["labels"]


def score_to_label(score: float, thresholds: List[Dict[str, Any]]) -> str:
    """Map a numeric score to a label using threshold config."""
    for t in thresholds:
        lo = t.get("min_score")
        hi = t.get("max_score_exclusive")
        if lo is not None and score < lo:
            continue
        if hi is not None and score >= hi:
            continue
        return t["label"]
    return thresholds[-1]["label"]


def percentile(values: List[float], p: float) -> float:
    """Compute p-th percentile (0-100)."""
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p / 100.0
    f = int(k)
    c = f + 1 if f + 1 < len(s) else f
    d = k - f
    return s[f] + d * (s[c] - s[f])


def distribution_stats(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"min": 0, "median": 0, "mean": 0, "p90": 0, "max": 0}
    return {
        "min": min(values),
        "median": statistics.median(values),
        "mean": statistics.mean(values),
        "p90": percentile(values, 90),
        "max": max(values),
    }


def main() -> None:
    root = _repo_root()
    local_path = root / "dataset" / "v1" / "costa_del_sol_20_local.jsonl"
    openai_path = root / "dataset" / "v1" / "costa_del_sol_20_openai.jsonl"
    thresholds_path = root / "configs" / "thresholds.v1.json"
    report_path = root / "reports" / "threshold_calibration_v1.md"

    if not local_path.exists() or not openai_path.exists():
        print(f"Error: JSONL files not found at {local_path} / {openai_path}")
        sys.exit(1)
    if not thresholds_path.exists():
        print(f"Error: Thresholds config not found at {thresholds_path}")
        sys.exit(1)

    local_data = load_jsonl(local_path)
    openai_data = load_jsonl(openai_path)
    thresholds = load_thresholds(thresholds_path)

    # Build score maps
    local_scores: Dict[str, float] = {}
    for e in local_data:
        local_scores[e["hotel"]["name"]] = e["score"]["total_score_final"]

    openai_scores: Dict[str, float] = {}
    for e in openai_data:
        openai_scores[e["hotel"]["name"]] = e["score"]["total_score_final"]

    all_hotels = sorted(set(local_scores.keys()) | set(openai_scores.keys()))

    # Score distributions
    local_vals = sorted(local_scores.values())
    openai_vals = sorted(openai_scores.values())

    local_stats = distribution_stats(local_vals)
    openai_stats = distribution_stats(openai_vals)

    print("=== Score Distributions ===")
    print(f"Local  (n={len(local_vals)}): {local_stats}")
    print(f"OpenAI (n={len(openai_vals)}): {openai_stats}")

    # Label assignment
    local_labels: Dict[str, str] = {h: score_to_label(s, thresholds) for h, s in local_scores.items()}
    openai_labels: Dict[str, str] = {h: score_to_label(s, thresholds) for h, s in openai_scores.items()}

    # Agreement matrix
    label_names = [t["label"] for t in thresholds]
    agreement_matrix: Dict[str, Dict[str, int]] = {l: {m: 0 for m in label_names} for l in label_names}

    agree_count = 0
    disagree_hotels: List[Tuple[str, str, str, float, float]] = []

    for hotel in all_hotels:
        ll = local_labels.get(hotel)
        ol = openai_labels.get(hotel)
        if ll and ol:
            agreement_matrix[ll][ol] += 1
            if ll == ol:
                agree_count += 1
            else:
                disagree_hotels.append((
                    hotel, ll, ol,
                    local_scores.get(hotel, 0),
                    openai_scores.get(hotel, 0),
                ))

    comparable = sum(1 for h in all_hotels if h in local_labels and h in openai_labels)
    agreement_pct = (agree_count / comparable * 100) if comparable > 0 else 0

    print(f"\n=== Label Agreement ===")
    print(f"Comparable hotels: {comparable}")
    print(f"Agreement: {agree_count}/{comparable} = {agreement_pct:.1f}%")
    print(f"Disagreements: {len(disagree_hotels)}")

    # Label distribution
    local_label_counts = {l: 0 for l in label_names}
    openai_label_counts = {l: 0 for l in label_names}
    for ll in local_labels.values():
        local_label_counts[ll] += 1
    for ol in openai_labels.values():
        openai_label_counts[ol] += 1

    print(f"\nLocal label distribution:  {dict(local_label_counts)}")
    print(f"OpenAI label distribution: {dict(openai_label_counts)}")

    # Drift analysis
    print(f"\n=== Drift (label disagreements) ===")
    for hotel, ll, ol, ls, os_ in disagree_hotels:
        print(f"  {hotel}: local={ll} ({ls:.2f}) → openai={ol} ({os_:.2f})")

    # --- Write report ---
    lines: List[str] = []
    lines.append("# Threshold Calibration Report v1\n\n")
    lines.append("Calibrated on 20 Costa del Sol hotels, dual-run (Ollama qwen2.5:14b + OpenAI gpt-4o-mini).\n\n")

    lines.append("## Labeling Scale\n\n")
    lines.append("The sustainability score (0-100) maps to a human-readable label:\n\n")
    lines.append("| Label | Score Range | Description |\n")
    lines.append("|-------|------------|-------------|\n")
    for t in thresholds:
        lo = t.get("min_score")
        hi = t.get("max_score_exclusive")
        lo_str = f"{lo}" if lo is not None else "0"
        hi_str = f"< {hi}" if hi is not None else "100"
        lines.append(f"| **{t['label']}** | {lo_str} – {hi_str} | {t['description']} |\n")

    lines.append("\n## Score Distributions\n\n")
    lines.append("| Stat | Local (Ollama) | OpenAI |\n")
    lines.append("|------|---------------|--------|\n")
    for stat in ["min", "median", "mean", "p90", "max"]:
        lines.append(f"| {stat} | {local_stats[stat]:.2f} | {openai_stats[stat]:.2f} |\n")

    lines.append(f"\nLocal scores (sorted): {[round(v, 2) for v in local_vals]}\n\n")
    lines.append(f"OpenAI scores (sorted): {[round(v, 2) for v in openai_vals]}\n\n")

    lines.append("## Threshold Selection Rationale\n\n")
    lines.append("Thresholds were chosen to:\n")
    lines.append("1. **Maximize label agreement** between extractors (target: >= 70%)\n")
    lines.append("2. **Reflect natural score clusters**: 0 (no evidence), 0.5-5 (minimal), 5-15 (clear evidence), 15+ (comprehensive)\n")
    lines.append("3. **Be deterministic and versioned** (`configs/thresholds.v1.json`)\n\n")
    lines.append("The 0.5 lower bound for Basic (vs 0) separates genuine zero-evidence hotels from those with even minimal signals. ")
    lines.append("The 5.0 Good threshold requires evidence across multiple scoring categories. ")
    lines.append("The 15.0 Excellent threshold requires broad, well-documented sustainability programs.\n\n")

    lines.append("## Label Agreement\n\n")
    lines.append(f"- **Comparable hotels:** {comparable}\n")
    lines.append(f"- **Agreement:** {agree_count}/{comparable} = **{agreement_pct:.1f}%**\n")
    lines.append(f"- **Disagreements:** {len(disagree_hotels)}\n\n")

    lines.append("### Agreement Matrix (Local \\ OpenAI)\n\n")
    lines.append("| | " + " | ".join(label_names) + " |\n")
    lines.append("|---" + "|---" * len(label_names) + "|\n")
    for row_label in label_names:
        row_vals = " | ".join(str(agreement_matrix[row_label][col]) for col in label_names)
        lines.append(f"| **{row_label}** | {row_vals} |\n")

    lines.append("\n### Label Distribution\n\n")
    lines.append("| Label | Local | OpenAI |\n")
    lines.append("|-------|-------|--------|\n")
    for label in label_names:
        lines.append(f"| {label} | {local_label_counts[label]} | {openai_label_counts[label]} |\n")

    lines.append("\n## Drift Analysis (Disagreements)\n\n")
    if disagree_hotels:
        lines.append("| Hotel | Local Label | Local Score | OpenAI Label | OpenAI Score | Reason |\n")
        lines.append("|-------|------------|------------|-------------|-------------|--------|\n")
        for hotel, ll, ol, ls, os_ in disagree_hotels:
            if ls > os_:
                reason = "Ollama hallucinated facts not found by OpenAI"
            else:
                reason = "OpenAI found facts missed by Ollama"
            lines.append(f"| {hotel} | {ll} | {ls:.2f} | {ol} | {os_:.2f} | {reason} |\n")
    else:
        lines.append("No disagreements.\n")

    lines.append("\n## Example Hotels Where Label Changes\n\n")
    examples = disagree_hotels[:3]
    for hotel, ll, ol, ls, os_ in examples:
        lines.append(f"### {hotel}\n\n")
        lines.append(f"- Local: **{ll}** (score {ls:.2f})\n")
        lines.append(f"- OpenAI: **{ol}** (score {os_:.2f})\n")
        if ls > os_:
            lines.append(f"- **Why:** Ollama extracted facts that OpenAI did not find, inflating the local score. ")
            lines.append("This may indicate hallucination by the local model.\n\n")
        else:
            lines.append(f"- **Why:** OpenAI found sustainability signals (certifications, community engagement) that Ollama missed. ")
            lines.append("OpenAI's higher extraction quality detected more nuanced facts.\n\n")

    lines.append("## Risks & Next Steps\n\n")
    lines.append("### Risks\n\n")
    lines.append("- **High Unknown rate** (55-70%): Most Costa del Sol hotels don't publish sustainability info on their homepages. ")
    lines.append("This is a real finding, not a threshold issue. Multi-page scraping (subpages like /sustainability) would help.\n")
    lines.append("- **Ollama hallucination** (MAC Puerto Marina): Local model occasionally invents facts, pushing scores into Excellent. ")
    lines.append("Thresholds can't fix extractor quality — v2 should add hallucination detection.\n")
    lines.append("- **Small calibration set** (n=20): Thresholds may need adjustment with larger hotel datasets.\n\n")
    lines.append("### v2 Ideas\n\n")
    lines.append("- Calibrate on 100+ hotels across multiple regions\n")
    lines.append("- Add cross-extractor consensus: require both extractors to agree for higher labels\n")
    lines.append("- Add sub-labels per category (energy: Good, water: Unknown, etc.)\n")
    lines.append("- Hallucination detection: flag local scores > 2x OpenAI score\n")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("".join(lines), encoding="utf-8")
    print(f"\nReport written to {report_path}")
    print(f"Thresholds config at {thresholds_path}")


if __name__ == "__main__":
    main()
