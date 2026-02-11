from __future__ import annotations

import argparse
import asyncio
import json
import re
from datetime import date
from pathlib import Path

from lomaopas_sus.models import Hotel, ExtractedFacts
from lomaopas_sus.scrape import scrape_and_cache
from lomaopas_sus.extract_openai import extract_facts_openai
from lomaopas_sus.extract_ollama import OllamaExtractor
from lomaopas_sus.normalize import normalize_facts_dict, normalize_extracted_facts
from lomaopas_sus.scoring import load_scoring_rules, calculate_sustainability_score
from lomaopas_sus.compare import load_jsonl_data, compare_scores_and_facts

ollama_extractor = OllamaExtractor()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


CONFIGS_DIR = _repo_root() / "configs"
DATASET_DIR = _repo_root() / "dataset" / "v1"
REPORTS_DIR = _repo_root() / "reports"
SAMPLE_FACTS_PATH = CONFIGS_DIR / "sample_facts.json"

DATASET_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _save_raw_output(runs_dir: Path, extractor: str, hotel_name: str, data: dict) -> None:
    """Save per-hotel raw extraction output to runs/{date}/{extractor}/."""
    safe_name = hotel_name.replace("/", "_").replace(" ", "_")[:60]
    out_dir = runs_dir / extractor
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{safe_name}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


_SUSTAINABILITY_ANCHORS = re.compile(
    r"sustainab|solar\b|recycle|recycling|eco[\-\s]?friend|green\senergy|"
    r"\benergy\seffic|renewable|water[\s\-]?sav|waste\sreduc|compost\b|"
    r"\borganic\b|environment|carbon\sfootprint|emission|linen\s?reuse|"
    r"\bled[\s\-]?light|heat[\s\-]?pump|locally[\s\-]?sourc|local\sproduce|"
    r"community\ssupport|bio[\s\-]?divers|rainwater|eco[\s\-]?cert|"
    r"plastic[\s\-]?free|zero[\s\-]?waste|clean\senergy",
    re.IGNORECASE,
)

_LOCAL_MAX_CHARS = 8_000
_ANCHOR_CONTEXT = 300  # chars before and after each anchor match


def _prepare_text_for_local(text: str) -> str:
    """Prepare text for local (Ollama) extractor.

    If text <= _LOCAL_MAX_CHARS, return as-is.
    Otherwise, extract sustainability-relevant snippets around keyword anchors.
    Falls back to simple truncation if no anchors found.
    """
    if len(text) <= _LOCAL_MAX_CHARS:
        return text

    # Always keep the page header for hotel context
    header = text[:500]

    # Find all anchor matches and collect surrounding context
    seen_ranges: list[tuple[int, int]] = []
    for match in _SUSTAINABILITY_ANCHORS.finditer(text):
        start = max(0, match.start() - _ANCHOR_CONTEXT)
        end = min(len(text), match.end() + _ANCHOR_CONTEXT)
        seen_ranges.append((start, end))

    if not seen_ranges:
        # No sustainability keywords found — simple truncation
        return text[:_LOCAL_MAX_CHARS]

    # Merge overlapping ranges
    seen_ranges.sort()
    merged: list[tuple[int, int]] = [seen_ranges[0]]
    for start, end in seen_ranges[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    # Build output: header + merged snippets, capped
    parts = [header, "\n...\n"]
    budget = _LOCAL_MAX_CHARS - len(header) - 10
    for start, end in merged:
        snippet = text[start:end]
        if len(snippet) > budget:
            snippet = snippet[:budget]
        parts.append(snippet)
        parts.append("\n...\n")
        budget -= len(snippet) + 5
        if budget <= 0:
            break

    return "".join(parts)


def _load_hotels(dataset_path: Path) -> list[Hotel]:
    """Load hotels from JSON array or JSONL file."""
    text = dataset_path.read_text(encoding="utf-8").strip()
    if text.startswith("["):
        # JSON array format (legacy)
        return [Hotel.model_validate(h) for h in json.loads(text)]
    # JSONL format
    hotels = []
    for line in text.splitlines():
        if line.strip():
            data = json.loads(line)
            # Map primary_url -> website if needed
            if "primary_url" in data and "website" not in data:
                data["website"] = data.pop("primary_url")
            hotels.append(Hotel.model_validate(data))
    return hotels


async def run_command(args: argparse.Namespace) -> None:
    print(f"Running pipeline with mode={args.mode}, limit={args.limit}")

    # Determine dataset path
    if args.dataset:
        dataset_path = Path(args.dataset)
        if not dataset_path.is_absolute():
            dataset_path = _repo_root() / dataset_path
    else:
        dataset_path = CONFIGS_DIR / "costa_del_sol_hotels.json"

    extract_schema_path = CONFIGS_DIR / "extract_schema.json"
    scoring_rules_path = CONFIGS_DIR / "scoring_rules.yaml"

    if not dataset_path.exists():
        print(f"Error: Dataset file not found at {dataset_path}")
        return
    if not extract_schema_path.exists():
        print(f"Error: Extraction schema file not found at {extract_schema_path}")
        return
    if not scoring_rules_path.exists():
        print(f"Error: Scoring rules file not found at {scoring_rules_path}")
        return

    hotels = _load_hotels(dataset_path)
    print(f"Loaded {len(hotels)} hotels from {dataset_path}")

    extraction_schema = json.loads(extract_schema_path.read_text(encoding="utf-8"))
    scoring_rules = load_scoring_rules(scoring_rules_path)

    total = min(args.limit, len(hotels)) if args.limit else len(hotels)

    # Determine output directory from dataset location
    output_dir = dataset_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = dataset_path.stem  # e.g. "costa_del_sol_50"
    local_jsonl_path = output_dir / f"{stem}_local.jsonl"
    openai_jsonl_path = output_dir / f"{stem}_openai.jsonl"

    # Per-run raw output directory
    runs_dir = _repo_root() / "runs" / date.today().isoformat()

    local_results = []
    openai_results = []
    scrape_ok = 0
    scrape_fail = 0

    for i, hotel in enumerate(hotels):
        if args.limit and i >= args.limit:
            break

        print(f"\n[{i+1}/{total}] Processing hotel: {hotel.name} ({hotel.website})")

        cleaned_text, source_type = await scrape_and_cache(
            str(hotel.website),
            force_scrape=args.force_scrape,
            hotel_name=hotel.name,
            fallback_urls=hotel.fallback_urls,
        )
        if not cleaned_text:
            print(f"  SKIP: scraping failure for {hotel.name}")
            scrape_fail += 1
            continue

        scrape_ok += 1
        if source_type != "cache":
            print(f"  Scraped ({source_type}), {len(cleaned_text)} chars")

        # Prepare text: local extractor gets keyword-focused extract; OpenAI gets more
        local_text = _prepare_text_for_local(cleaned_text)
        openai_text = cleaned_text[:15_000] if len(cleaned_text) > 15_000 else cleaned_text

        if args.mode in ["local", "all"]:
            print(f"  Extracting with Ollama for {hotel.name}... ({len(local_text)} chars)")
            ollama_response, ollama_meta = ollama_extractor.extract(
                hotel_name=hotel.name,
                text=f"{local_text}\n{hotel.website}",
                schema_json=json.dumps(extraction_schema),
            )
            # Preprocess: Ollama sometimes returns [] instead of {} for sub-models
            if ollama_response and isinstance(ollama_response, dict):
                for key in ["energy_efficiency", "water_conservation", "waste_management", "local_community_engagement", "certifications"]:
                    if key in ollama_response and ollama_response[key] == []:
                        ollama_response[key] = {}

                # Normalize before validation
                ollama_response = normalize_facts_dict(ollama_response)

            ollama_facts = ExtractedFacts.model_validate(ollama_response) if ollama_response else None
            ollama_confidence = 0.8

            # Save raw output
            _save_raw_output(runs_dir, "local", hotel.name, {
                "hotel": hotel.model_dump(mode="json"),
                "raw_response": ollama_response,
                "meta": {**ollama_meta, "normalized": True, "source_type": source_type},
            })

            if ollama_facts:
                ollama_score = calculate_sustainability_score(
                    ollama_facts, ollama_confidence, scoring_rules
                )
                local_results.append({
                    "hotel": hotel.model_dump(mode="json"),
                    "score": ollama_score.model_dump(mode="json"),
                    "meta": {**ollama_meta, "normalized": True, "source_type": source_type},
                })
                print(f"  Ollama Score: {ollama_score.total_score_final:.2f}  ({ollama_meta['duration_ms']}ms, {ollama_meta['tokens_out']} tok out)")
            else:
                print(f"  Ollama extraction unavailable for {hotel.name} (error: {ollama_meta.get('error')})")

        if args.mode in ["openai", "all"]:
            print(f"  Extracting with OpenAI for {hotel.name}...")
            openai_facts, openai_evidence, openai_confidence, openai_meta = await extract_facts_openai(
                openai_text,
                extraction_schema,
                str(hotel.website),
                force_extract=args.force_extract,
            )

            # Normalize after extraction
            if openai_facts:
                openai_facts = normalize_extracted_facts(openai_facts)

            # Save raw output
            _save_raw_output(runs_dir, "openai", hotel.name, {
                "hotel": hotel.model_dump(mode="json"),
                "raw_facts": openai_facts.model_dump(mode="json") if openai_facts else None,
                "meta": {**openai_meta, "normalized": True, "source_type": source_type},
            })

            if openai_facts:
                openai_score = calculate_sustainability_score(
                    openai_facts, openai_confidence, scoring_rules
                )
                openai_results.append({
                    "hotel": hotel.model_dump(mode="json"),
                    "score": openai_score.model_dump(mode="json"),
                    "meta": {**openai_meta, "normalized": True, "source_type": source_type},
                })
                print(f"  OpenAI Score: {openai_score.total_score_final:.2f}  ({openai_meta['duration_ms']}ms, ${openai_meta['cost_estimate_usd']:.6f})")
            else:
                print(f"  OpenAI extraction unavailable for {hotel.name} (error: {openai_meta.get('error')})")

    print(f"\n--- Scrape summary: {scrape_ok} OK, {scrape_fail} failed ---")

    if local_results:
        with open(local_jsonl_path, "w", encoding="utf-8") as handle:
            for entry in local_results:
                handle.write(json.dumps(entry) + "\n")
        print(f"Local LLM results saved to {local_jsonl_path} ({len(local_results)} hotels)")

    if openai_results:
        with open(openai_jsonl_path, "w", encoding="utf-8") as handle:
            for entry in openai_results:
                handle.write(json.dumps(entry) + "\n")
        print(f"OpenAI LLM results saved to {openai_jsonl_path} ({len(openai_results)} hotels)")

    print(f"Raw outputs saved to {runs_dir}/")


def compare_command(args: argparse.Namespace) -> None:
    print("Generating comparison report...")

    if args.dataset:
        dataset_path = Path(args.dataset)
        if not dataset_path.is_absolute():
            dataset_path = _repo_root() / dataset_path
        output_dir = dataset_path.parent
        stem = dataset_path.stem
        local_jsonl_path = output_dir / f"{stem}_local.jsonl"
        openai_jsonl_path = output_dir / f"{stem}_openai.jsonl"
        report_path = REPORTS_DIR / f"compare_local_vs_openai_{stem}.md"
    else:
        local_jsonl_path = DATASET_DIR / "costa_del_sol_20_local.jsonl"
        openai_jsonl_path = DATASET_DIR / "costa_del_sol_20_openai.jsonl"
        report_path = REPORTS_DIR / "compare_local_vs_openai.md"

    local_data = load_jsonl_data(local_jsonl_path)
    openai_data = load_jsonl_data(openai_jsonl_path)

    report_content = compare_scores_and_facts(local_data, openai_data)
    report_path.write_text(report_content, encoding="utf-8")

    print(f"Comparison report generated at {report_path}")


def dry_run_command(_: argparse.Namespace) -> None:
    print("Performing dry-run of the scoring pipeline...")

    scoring_rules_path = CONFIGS_DIR / "scoring_rules.yaml"
    if not scoring_rules_path.exists():
        print(f"Error: Scoring rules file not found at {scoring_rules_path}")
        return
    scoring_rules = load_scoring_rules(scoring_rules_path)

    if not SAMPLE_FACTS_PATH.exists():
        print(f"Error: Sample facts file not found at {SAMPLE_FACTS_PATH}")
        return

    sample_facts_data = json.loads(SAMPLE_FACTS_PATH.read_text(encoding="utf-8"))
    sample_facts = ExtractedFacts.model_validate(sample_facts_data)
    sample_confidence = 0.9

    score = calculate_sustainability_score(sample_facts, sample_confidence, scoring_rules)

    print("--- Dry Run Result ---")
    print(score.model_dump_json(indent=2))
    print(
        "Dry run completed. "
        f"Total Raw Score: {score.total_score_raw:.2f}, "
        f"Total Final Score: {score.total_score_final:.2f}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Lomaopas Sustainability Agent CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    run_parser = subparsers.add_parser(
        "run", help="Run scraping, extraction, and scoring pipeline"
    )
    run_parser.add_argument(
        "--mode",
        choices=["local", "openai", "all"],
        default="all",
        help="Which LLM extractor to use: local (Ollama), openai, or all",
    )
    run_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of hotels to process",
    )
    run_parser.add_argument(
        "--force-scrape",
        action="store_true",
        help="Force re-scraping of websites, bypassing cache",
    )
    run_parser.add_argument(
        "--force-extract",
        action="store_true",
        help="Force re-extraction by LLMs, bypassing cache",
    )
    run_parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Path to hotel dataset file (JSON array or JSONL)",
    )
    run_parser.set_defaults(func=run_command)

    compare_parser = subparsers.add_parser(
        "compare", help="Compare local vs. OpenAI extraction results"
    )
    compare_parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Path to hotel dataset file (to find matching output files)",
    )
    compare_parser.set_defaults(func=compare_command)

    dry_run_parser = subparsers.add_parser(
        "dry-run", help="Perform a dry run of the scoring pipeline with sample data"
    )
    dry_run_parser.set_defaults(func=dry_run_command)

    args = parser.parse_args()

    if hasattr(args, "func"):
        if args.command == "run":
            asyncio.run(args.func(args))
        else:
            args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
