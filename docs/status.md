# Sustainability Engine - Status

Last updated: 2026-02-11

## Pipeline Status

| Phase | Description | Status |
|-------|-------------|--------|
| SE-P1 | Scoring engine (deterministic rules) | DONE |
| SE-P2 | Local Ollama run (scrape + extract + score) | DONE |
| SE-P3 | OpenAI extractor + dual-run compare | DONE |

## SE-P1: Scoring Engine

- Deterministic scoring from `configs/scoring_rules.yaml`
- Dry-run validated with sample facts
- Status: **DONE**

## SE-P2: Local Ollama Run

- Ollama extractor implemented (`extract_ollama.py`) using `qwen2.5:14b-instruct`
- Scraping with caching (`scrape.py`)
- Full 20-hotel local run completed (13/19 scraped successfully)
- Status: **DONE**

## SE-P3: OpenAI Extractor + Dual-Run Compare

- OpenAI extractor implemented using gpt-4o-mini with JSON mode
- Dual-run benchmark executed: 13 hotels extracted by both Ollama and OpenAI
- Comparison report generated with timing, cost, score deltas, and fact consistency
- Status: **DONE**

### Key Findings

- OpenAI (gpt-4o-mini) is ~38% faster than Ollama (qwen2.5:14b) per hotel
- OpenAI total cost for 13 hotels: $0.0052
- Mean score difference: 0.94 points (max: 5.59)
- OpenAI extracts more structured facts (especially certifications, community engagement)
- Ollama tends to output `false` for unmentioned facts; OpenAI uses `null`
