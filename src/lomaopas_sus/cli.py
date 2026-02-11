from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from lomaopas_sus.models import Hotel, ExtractedFacts
from lomaopas_sus.scrape import scrape_and_cache
from lomaopas_sus.extract_openai import extract_facts_openai
from lomaopas_sus.extract_ollama import OllamaExtractor
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


async def run_command(args: argparse.Namespace) -> None:
    print(f"Running pipeline with mode={args.mode}, limit={args.limit}")

    hotels_config_path = CONFIGS_DIR / "costa_del_sol_hotels.json"
    extract_schema_path = CONFIGS_DIR / "extract_schema.json"
    scoring_rules_path = CONFIGS_DIR / "scoring_rules.yaml"

    if not hotels_config_path.exists():
        print(f"Error: Hotels config file not found at {hotels_config_path}")
        return
    if not extract_schema_path.exists():
        print(f"Error: Extraction schema file not found at {extract_schema_path}")
        return
    if not scoring_rules_path.exists():
        print(f"Error: Scoring rules file not found at {scoring_rules_path}")
        return

    hotels_data = json.loads(hotels_config_path.read_text(encoding="utf-8"))
    hotels = [Hotel.model_validate(h) for h in hotels_data]

    extraction_schema = json.loads(extract_schema_path.read_text(encoding="utf-8"))
    scoring_rules = load_scoring_rules(scoring_rules_path)

    local_jsonl_path = DATASET_DIR / "costa_del_sol_20_local.jsonl"
    openai_jsonl_path = DATASET_DIR / "costa_del_sol_20_openai.jsonl"

    local_results = []
    openai_results = []

    for i, hotel in enumerate(hotels):
        if args.limit and i >= args.limit:
            break

        print(f"Processing hotel: {hotel.name} ({hotel.website})")

        cleaned_text = await scrape_and_cache(str(hotel.website), force_scrape=args.force_scrape)
        if not cleaned_text:
            print(f"Skipping {hotel.name} due to scraping failure.")
            continue

        if args.mode in ["local", "all"]:
            print(f"  Extracting with Ollama for {hotel.name}...")
            ollama_response = ollama_extractor.extract(
                hotel_name=hotel.name,
                text=f"{cleaned_text}\n{hotel.website}",
                schema_json=json.dumps(extraction_schema),
            )
            ollama_facts = ExtractedFacts.model_validate(ollama_response) if ollama_response else None
            ollama_evidence = {} # Ollama extractor does not provide evidence
            ollama_confidence = 0.8 # Default confidence for Ollama

            if ollama_facts:
                ollama_score = calculate_sustainability_score(
                    ollama_facts, ollama_confidence, scoring_rules
                )
                local_results.append(
                    {"hotel": hotel.model_dump(mode="json"), "score": ollama_score.model_dump()}
                )
                print(f"  Ollama Score: {ollama_score.total_score_final:.2f}")
            else:
                print(f"  Ollama extraction unavailable for {hotel.name}")

        if args.mode in ["openai", "all"]:
            print(f"  Extracting with OpenAI for {hotel.name}...")
            openai_facts, openai_evidence, openai_confidence = await extract_facts_openai(
                cleaned_text,
                extraction_schema,
                str(hotel.website),
                force_extract=args.force_extract,
            )
            if openai_facts:
                openai_score = calculate_sustainability_score(
                    openai_facts, openai_confidence, scoring_rules
                )
                openai_results.append(
                    {"hotel": hotel.model_dump(mode="json"), "score": openai_score.model_dump()}
                )
                print(f"  OpenAI Score: {openai_score.total_score_final:.2f}")
            else:
                print(f"  OpenAI extraction unavailable for {hotel.name}")

    if local_results:
        with open(local_jsonl_path, "w", encoding="utf-8") as handle:
            for entry in local_results:
                handle.write(json.dumps(entry) + "\n")
        print(f"Local LLM results saved to {local_jsonl_path}")

    if openai_results:
        with open(openai_jsonl_path, "w", encoding="utf-8") as handle:
            for entry in openai_results:
                handle.write(json.dumps(entry) + "\n")
        print(f"OpenAI LLM results saved to {openai_jsonl_path}")


def compare_command(_: argparse.Namespace) -> None:
    print("Generating comparison report...")
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
    run_parser.set_defaults(func=run_command)

    compare_parser = subparsers.add_parser(
        "compare", help="Compare local vs. OpenAI extraction results"
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