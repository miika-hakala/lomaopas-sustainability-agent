# Sustainability Engine - Status

Last updated: 2026-02-11

## Pipeline Status

| Phase | Description | Status |
|-------|-------------|--------|
| SE-P1 | Scoring engine (deterministic rules) | DONE |
| SE-P2 | Local Ollama run (scrape + extract + score) | DONE |
| SE-P3 | OpenAI extractor + dual-run compare | DONE |
| SE-P3.1 | Evidence gating (prevent inflated labels) | **NEXT** |
| SE-P4 | Scraping reliability + normalization + 20/20 | DONE |
| SE-P5 | Threshold calibration v1 | DONE |

## SE-P1: Scoring Engine

- Deterministic scoring from `configs/scoring_rules.yaml`
- Dry-run validated with sample facts
- Status: **DONE**

## SE-P2: Local Ollama Run

- Ollama extractor implemented (`extract_ollama.py`) using `qwen2.5:14b-instruct`
- Scraping with caching (`scrape.py`)
- Full 20-hotel local run completed
- Status: **DONE**

## SE-P3: OpenAI Extractor + Dual-Run Compare

- OpenAI extractor implemented using gpt-4o-mini with JSON mode
- Dual-run benchmark executed: 20 hotels extracted by both Ollama and OpenAI
- Comparison report generated with timing, cost, score deltas, and fact consistency
- Status: **DONE**

## SE-P4: Scraping Reliability + Normalization

- 3 rotating user-agents, 3 retries with exponential backoff
- Canonical normalization (false->null, []-null, ""-null)
- Fallback URL support, long-page keyword extraction for Ollama
- 20/20 scrapes, 20/20 local, 20/20 OpenAI
- Status: **DONE**

## SE-P5: Threshold Calibration v1

- 4-level labeling scale: Insufficient Evidence / Basic / Good / Excellent
- Calibrated on 20 Costa del Sol hotels dual-run data
- `score_to_label()` function integrated into scoring pipeline
- Compare report now shows labels and agreement
- Label agreement: 75% (15/20 hotels)
- Status: **DONE**

### Key Findings

- OpenAI (gpt-4o-mini) is ~21% faster than Ollama (qwen2.5:14b) per hotel
- OpenAI total cost for 20 hotels: $0.0087
- Mean score difference: 1.52 points (max: 18.92)
- Label agreement: 75% — meets >=70% target
- Most disagreements: Ollama misses facts (3 cases) or hallucinates (1 case)
- 55-70% of hotels labeled "Insufficient Evidence" — reflects reality (hotels don't publish sustainability on homepage)

### Known Risk: Hallucination-Inflated Labels

- MAC Puerto Marina: Ollama score 19.42 (Excellent) vs OpenAI 0.50 (Basic)
- Root cause: Ollama hallucinated sustainability claims not present on page
- Mitigation: SE-P3.1 Evidence Gating will cap labels when claim count is too low

## SE-P3.1: Evidence Gating [NEXT]

- Deterministic evidence gate to prevent inflated labels from hallucinated extractions
- Requires >= 3 distinct claims for Basic, >= 1 concrete action/certification for Good
- Label cap mechanism: score may exceed threshold but label is capped if gate fails
- Target: thresholds v1.1
