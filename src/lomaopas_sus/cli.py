from __future__ import annotations

import argparse
import asyncio
import json
import re
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
from uuid import UUID
import os

from lomaopas_sus.models import Hotel, ExtractedFacts, SustainabilityScore, ScoreBreakdown
from lomaopas_sus.scrape import scrape_and_cache
from lomaopas_sus.extract_openai import extract_facts_openai
from lomaopas_sus.extract_ollama import OllamaExtractor
from lomaopas_sus.normalize import normalize_facts_dict, normalize_extracted_facts
from lomaopas_sus.scoring import load_scoring_rules, calculate_sustainability_score
from lomaopas_sus.compare import load_jsonl_data, compare_scores_and_facts
from lomaopas_sus.supabase_client import SupabaseClient
from lomaopas_sus.diff import compute_facts_diff, should_auto_accept_diff

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
            ollama_response, ollama_meta = await ollama_extractor.extract(
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


async def worker_run_command(args: argparse.Namespace) -> None:
    supabase_client = SupabaseClient()
    print(f"Worker {supabase_client.worker_id} started. Dry-run: {args.dry_run}")

    extraction_schema_path = CONFIGS_DIR / "extract_schema.json"
    scoring_rules_path = CONFIGS_DIR / "scoring_rules.yaml"

    if not extraction_schema_path.exists():
        print(f"Error: Extraction schema file not found at {extraction_schema_path}")
        return
    if not scoring_rules_path.exists():
        print(f"Error: Scoring rules file not found at {scoring_rules_path}")
        return

    extraction_schema = json.loads(extraction_schema_path.read_text(encoding="utf-8"))
    scoring_rules = load_scoring_rules(scoring_rules_path)

    try:
        while True:
            job = await supabase_client.fetch_next_job()
            if not job:
                if args.once:
                    print("No queued jobs found. Exiting (once mode).")
                    break
                print("No queued jobs found. Waiting...")
                await asyncio.sleep(10) # Wait before checking for new jobs
                continue

            job_id = UUID(job["id"])
            entity_id = UUID(job["entity_id"])
            reason = job["reason"]

            print(f"\nProcessing job {job_id} for entity {entity_id} (Reason: {reason})")
            
            # Lock job
            locked_job = await supabase_client.lock_job(job_id)
            if not locked_job:
                print(f"Failed to lock job {job_id}. Skipping.")
                continue
            print(f"Job {job_id} locked by {supabase_client.worker_id}.")

            entity = None
            try:
                entity = await supabase_client.get_entity(entity_id)
                if not entity:
                    raise ValueError(f"Entity {entity_id} not found.")
                
                entity_name = entity.get("name", "Unknown")
                entity_website_url = None
                entity_sources = await supabase_client.get_entity_sources(entity_id)
                
                primary_source = next((s for s in entity_sources if s["source_type"] == "primary" and s["allowed"]), None)
                if primary_source:
                    entity_website_url = primary_source["url"]
                else:
                    raise ValueError(f"No primary source found or allowed for entity {entity_id}")

                print(f"  Fetching data for {entity_name} ({entity_website_url})...")
                cleaned_text, source_type = await scrape_and_cache(
                    entity_website_url,
                    force_scrape=False, # Worker should rely on cache and refresh cadence
                    hotel_name=entity_name,
                    # Fallback URLs are not directly available in entity_sources for scrape_and_cache
                    # Would need to implement logic to pass all entity_sources here or refactor scrape.
                    # For MVP, assume primary_source is sufficient.
                )
                if not cleaned_text:
                    raise ValueError(f"Scraping failed for {entity_name} ({entity_website_url}).")

                # Prepare text for local extractor (if used)
                local_text = _prepare_text_for_local(cleaned_text)
                openai_text = cleaned_text[:15_000] if len(cleaned_text) > 15_000 else cleaned_text

                # Determine extractor mode
                extractor_mode = os.getenv("DEFAULT_EXTRACTOR_MODE", "all") # Default to all for now
                # Or could be defined per-entity in the future

                extracted_facts = None
                extractor_meta = {}
                score_obj = None

                if extractor_mode in ["local", "all"]:
                    print(f"  Extracting with Ollama for {entity_name}...")
                    ollama_response, ollama_meta = ollama_extractor.extract(
                        hotel_name=entity_name,
                        text=f"{local_text}\n{entity_website_url}",
                        schema_json=json.dumps(extraction_schema),
                    )
                    # Preprocess: Ollama sometimes returns [] instead of {} for sub-models
                    if ollama_response and isinstance(ollama_response, dict):
                        for key in ["energy_efficiency", "water_conservation", "waste_management", "local_community_engagement", "certifications"]:
                            if key in ollama_response and ollama_response[key] == []:
                                ollama_response[key] = {}
                        ollama_response = normalize_facts_dict(ollama_response)

                    if ollama_response:
                        extracted_facts = ExtractedFacts.model_validate(ollama_response)
                        score_obj = calculate_sustainability_score(extracted_facts, 0.8, scoring_rules) # Default confidence
                        extractor_meta = {**ollama_meta, "extractor": "local", "model": ollama_extractor.model}
                    else:
                        print(f"  Ollama extraction failed for {entity_name}")
                        extractor_meta = {**ollama_meta, "extractor": "local", "model": ollama_extractor.model, "error": "Extraction failed"}

                # If "all" mode, could also run OpenAI and pick best or average.
                # For MVP, let's stick to local if "all" is specified and local has facts.
                # If local failed, maybe try OpenAI? For now, simple.

                if not extracted_facts and extractor_mode in ["openai", "all"]:
                    print(f"  Extracting with OpenAI for {entity_name}...")
                    openai_facts, openai_evidence, openai_confidence, openai_meta = await extract_facts_openai(
                        openai_text,
                        extraction_schema,
                        entity_website_url,
                        force_extract=False,
                    )
                    if openai_facts:
                        extracted_facts = normalize_extracted_facts(openai_facts)
                        score_obj = calculate_sustainability_score(extracted_facts, openai_confidence, scoring_rules)
                        extractor_meta = {**openai_meta, "extractor": "openai", "model": "gpt-4o-mini"}
                    else:
                        print(f"  OpenAI extraction failed for {entity_name}")
                        extractor_meta = {**openai_meta, "extractor": "openai", "model": "gpt-4o-mini", "error": "Extraction failed"}
                
                if not extracted_facts or not score_obj:
                    raise ValueError(f"No facts extracted for {entity_name} using mode {extractor_mode}.")

                # Insert facts_snapshot
                snapshot_data = {
                    "entity_id": str(entity_id),
                    "extractor": extractor_meta.get("extractor", "unknown"),
                    "model": extractor_meta.get("model"),
                    "facts": extracted_facts.model_dump(mode="json"),
                    "evidence": extracted_facts.evidence_snippets, # Assuming evidence_snippets is directly in ExtractedFacts
                    "meta": {
                        "job_id": str(job_id),
                        "run_id": supabase_client.worker_id,
                        "durations": extractor_meta.get("duration_ms"),
                        "tokens_in": extractor_meta.get("tokens_in"),
                        "tokens_out": extractor_meta.get("tokens_out"),
                        "cost_estimate_usd": extractor_meta.get("cost_estimate_usd"),
                        **extractor_meta
                    },
                    "score": score_obj.total_score_final,
                    # "label": score_obj.label # Removed: label is derived, not stored directly in snapshot
                }
                if args.dry_run:
                    print(f"  DRY-RUN: Would insert snapshot: {json.dumps(snapshot_data, indent=2)}")
                    snapshot_id = "dry-run-snapshot-id" # Placeholder
                else:
                    inserted_snapshot = await supabase_client.insert_snapshot(snapshot_data)
                    if not inserted_snapshot:
                        raise ValueError("Failed to insert facts_snapshot.")
                    snapshot_id = UUID(inserted_snapshot["id"])
                    print(f"  Facts snapshot {snapshot_id} inserted.")

                # Diff vs current and decide auto-accept/pending_review
                current_snapshot_data = await supabase_client.get_current_snapshot(entity_id)
                current_facts = None
                current_score = None
                is_first_snapshot = True

                if current_snapshot_data:
                    is_first_snapshot = False
                    current_facts = ExtractedFacts.model_validate(current_snapshot_data["facts"])
                    # Reconstruct current_score for diffing
                    current_score = SustainabilityScore(
                        score_model_version="v1.0", # Assume v1.0 for existing
                        raw_facts=current_facts,
                        evidence=current_facts.evidence_snippets,
                        confidence=0.8, # Default confidence
                        score_breakdown=ScoreBreakdown(), # Placeholder
                        total_score_raw=current_snapshot_data.get("score", 0.0), # Use stored score
                        total_score_final=current_snapshot_data.get("score", 0.0),
                    )
                
                diff_json = compute_facts_diff(current_facts, extracted_facts, current_score, score_obj)
                auto_accept = should_auto_accept_diff(diff_json, is_first_snapshot)
                
                if args.dry_run:
                    print(f"  DRY-RUN: Diff: {json.dumps(diff_json, indent=2)}")
                    print(f"  DRY-RUN: Auto-accept: {auto_accept}")
                else:
                    if auto_accept:
                        await supabase_client.upsert_current(entity_id, snapshot_id)
                        print(f"  Diff auto-accepted. Current facts updated to snapshot {snapshot_id}.")
                    else:
                        await supabase_client.insert_proposed(entity_id, snapshot_id, diff_json)
                        print(f"  Large diff detected. Facts proposed from snapshot {snapshot_id} for review.")

                # Mark job success
                if not args.dry_run:
                    await supabase_client.mark_job_success(job_id)
                    await supabase_client.update_entity_last_attempt_success(entity_id, is_success=True)
                print(f"Job {job_id} completed successfully.")

            except Exception as e:
                error_msg = f"Worker failed for job {job_id}: {e}"
                print(error_msg)
                if not args.dry_run:
                    await supabase_client.mark_job_failed(job_id, error_msg)
                    await supabase_client.update_entity_last_attempt_success(entity_id, is_success=False)
                print(f"Job {job_id} marked as failed.")
            
            if args.once:
                break

    except Exception as e:
        print(f"Worker main loop error: {e}")

async def worker_schedule_command(args: argparse.Namespace) -> None:
    supabase_client = SupabaseClient()
    print("Running scheduler...")

    try:
        # Select entities where status='active' AND (next_refresh_at <= now OR next_refresh_at is null)
        # Using a direct query string to ensure correct date comparison in Supabase/PostgREST
        now_utc = datetime.now(timezone.utc).isoformat()
        url = (
            f"{supabase_client.base_url}/entities?select=id,refresh_cadence_days,next_refresh_at,status&"
            f"status=eq.active&"
            f"or=(next_refresh_at.lte.{now_utc},next_refresh_at.is.null)"
        )
        
        entities_to_schedule = await supabase_client._make_request("GET", url)
        
        if not entities_to_schedule:
            print("No active entities found requiring refresh.")
            return

        print(f"Found {len(entities_to_schedule)} entities to schedule.")

        for entity_data in entities_to_schedule:
            entity_id = UUID(entity_data["id"])
            refresh_cadence_days = entity_data["refresh_cadence_days"]

            print(f"  Scheduling refresh job for entity {entity_id} (cadence: {refresh_cadence_days} days).")
            
            if not args.dry_run:
                # Insert ingest_job(reason='refresh', scheduled_for=now)
                job_payload = {
                    "entity_id": str(entity_id),
                    "reason": "refresh",
                    "status": "queued",
                    "scheduled_for": now_utc,
                }
                inserted_job = await supabase_client._make_request("POST", f"{supabase_client.base_url}/ingest_jobs", json_data=job_payload)
                if not inserted_job:
                    print(f"    Failed to insert ingest job for entity {entity_id}.")
                    continue
                print(f"    Inserted job {inserted_job[0]['id']}.")

                # Update entities.next_refresh_at
                next_refresh_at = datetime.now(timezone.utc) + timedelta(days=refresh_cadence_days)
                await supabase_client.update_entity_next_refresh(entity_id, next_refresh_at)
                print(f"    Updated entity {entity_id} next_refresh_at to {next_refresh_at.isoformat()}.")
            else:
                print(f"  DRY-RUN: Would schedule refresh job for entity {entity_id} and update next_refresh_at.")

    except Exception as e:
        print(f"Scheduler main loop error: {e}")


def dry_run_command(_: argparse.Namespace) -> None:
    print("Performing dry-run of the scoring pipeline...")

    scoring_rules_path = CONFIGS_DIR / "extract_schema.json"
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

    worker_parser = subparsers.add_parser(
        "worker", help="Supabase job worker and scheduler commands"
    )
    worker_subparsers = worker_parser.add_subparsers(
        dest="worker_command", help="Worker commands"
    )

    worker_run_parser = worker_subparsers.add_parser(
        "run", help="Run the sustainability fact extraction worker"
    )
    worker_run_parser.add_argument(
        "--once", action="store_true", help="Run one job and exit"
    )
    worker_run_parser.add_argument(
        "--dry-run", action="store_true", help="Do not write to DB, just log actions"
    )
    worker_run_parser.set_defaults(func=worker_run_command)

    worker_schedule_parser = worker_subparsers.add_parser(
        "schedule", help="Schedule new ingest jobs based on entity refresh cadences"
    )
    worker_schedule_parser.set_defaults(func=worker_schedule_command)


    args = parser.parse_args()

    if hasattr(args, "func"):
        if args.command == "run" or (args.command == "worker" and args.worker_command in ["run", "schedule"]):
            asyncio.run(args.func(args))
        else:
            args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()