# Sustainability Engine - Active Tasks

## SE-P3: OpenAI Extractor + Dual-Run Compare

### SE-P3A: Implement OpenAI extractor

- **Status:** DONE
- **File:** `src/lomaopas_sus/extract_openai.py`
- **Description:** Real implementation using OpenAI gpt-4o-mini with JSON mode. Returns `(ExtractedFacts, List[EvidenceSnippet], confidence, meta)`. Includes token tracking and cost estimation.

### SE-P3B: Execute dual-run (20 hotels)

- **Status:** DONE
- **Description:** Full pipeline executed for 20 Costa del Sol hotels in both modes.
  - 20/20 hotels successfully scraped and extracted
  - Output: `dataset/v1/costa_del_sol_20_local.jsonl` and `dataset/v1/costa_del_sol_20_openai.jsonl`
  - Raw per-hotel outputs: `runs/2026-02-11/local/` and `runs/2026-02-11/openai/`

### SE-P3C: Generate compare report + delta metrics

- **Status:** DONE
- **Description:** Comparison report generated at `reports/compare_local_vs_openai.md`
  - Includes: success rates, timing/cost, score deltas, fact consistency, example diffs, label agreement
  - Mean score difference: 1.52
  - OpenAI total cost: $0.0087 for 20 hotels

## SE-P4: Scraping Reliability + Normalization

- **Status:** DONE
- **Description:** Retry policy (3 attempts, rotating UA, exponential backoff), canonical normalization (false->null, []-null), fallback URLs, long-page handling for local extractor.
  - 20/20 scrapes, 20/20 local, 20/20 OpenAI extractions

## SE-P5: Threshold Calibration v1

### SE-P5A: Define labeling scale

- **Status:** DONE
- **Description:** 4-level scale: Insufficient Evidence / Basic / Good / Excellent
  - Config: `configs/thresholds.v1.json`

### SE-P5B: Calibration analysis

- **Status:** DONE
- **Description:** Calibration script (`scripts/calibrate_thresholds.py`) analyzes score distributions, agreement matrix, drift between extractors.
  - Report: `reports/threshold_calibration_v1.md`

### SE-P5C: Integrate threshold mapping into pipeline

- **Status:** DONE
- **Description:** `score_to_label()` function in `scoring.py`, compare report now shows labels and agreement.
  - Label agreement: 15/20 = 75%

## NEXT: MVP2 DB schema

- **Status:** DONE
- **Description:** Implemented the database schema for MVP2, including entities, ingest jobs, facts snapshots, current, proposed, and review actions. This laid the groundwork for persistent storage and a review workflow for sustainability facts.

## NEXT: MVP2 Worker

- **Status:** DONE
- **Description:** Implemented the Supabase worker, which consumes ingest_jobs, produces facts_snapshots, calculates diffs, auto-accepts small diffs, proposes large diffs for review, and includes a scheduler for refresh jobs.
