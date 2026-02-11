# Sustainability Engine - Roadmap

## SE-P1: Scoring Engine [DONE]

- Deterministic scoring rules in YAML
- Score breakdown by category (energy, water, waste, community, certifications)
- Confidence-weighted final score
- Dry-run CLI command

## SE-P2: Local Ollama Run [DONE]

- Web scraping with caching
- Ollama-based fact extraction (qwen2.5:14b-instruct)
- Full pipeline: scrape -> extract -> score -> JSONL output
- CLI `run --mode local`

## SE-P3: OpenAI Extractor + Dual-Run Compare [DONE]

- OpenAI extractor with gpt-4o-mini and JSON mode
- Token tracking and cost estimation
- Per-hotel raw output saving to `runs/{date}/`
- Enhanced comparison report with timing, cost, fact consistency, example diffs
- Dual-run benchmark: 20 comparable hotels

### SE-P3 Gate Criteria

| Criterion | Status |
|-----------|--------|
| OpenAI extractor returns structured facts | SATISFIED |
| Dual-run (local + openai) for 20 hotels | SATISFIED (20/20) |
| Compare report with delta metrics | SATISFIED |
| Gate | **SATISFIED** |

## SE-P4: Scraping Reliability + Normalization [DONE]

- 3 rotating user-agents, 3 retries with exponential backoff
- Canonical normalization layer (false->null, []-null, ""-null)
- Fallback URL support, long-page keyword extraction
- 20/20 scrapes, 20/20 extractions both extractors

## SE-P5: Threshold Calibration v1 [DONE]

- 4-level labeling scale: Insufficient Evidence / Basic / Good / Excellent
- Calibration script analyzing score distributions and agreement
- `score_to_label()` integrated into scoring and compare pipelines
- Label agreement: 75% (15/20 hotels) — exceeds 70% target

### SE-P5 Gate Criteria

| Criterion | Status |
|-----------|--------|
| Thresholds deterministic and versioned (v1) | SATISFIED |
| Label agreement >= 70% | SATISFIED (75%) |
| Calibration report with rationale | SATISFIED |
| Compare report shows labels | SATISFIED |
| Gate | **SATISFIED** |

## Stabilization

### SE-P3.1: Evidence Gating [NEXT]

- Deterministic evidence gate: minimum claim count + concrete evidence requirement
- >= 3 distinct claims for Basic, >= 1 concrete action/certification for Good
- Label cap: even if score exceeds threshold, label capped if gate fails
- Re-calibrate on 20-hotel dataset, target agreement >= 75%
- Thresholds version: v1.1

**Gate:** Label agreement >= 75% with evidence gating active; MAC Puerto Marina hallucination case correctly capped.

## Future / SE-P6

- Calibrate on 100+ hotels across multiple regions
- Multi-page scraping (subpages like /sustainability)
- Cross-extractor consensus: require both to agree for higher labels
- Hallucination detection: flag local scores > 2x OpenAI score
- Sub-labels per category (energy: Good, water: Unknown, etc.)
