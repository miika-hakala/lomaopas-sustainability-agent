# Sustainability Engine - Status

Last updated: 2026-02-11

## Pipeline Status

| Phase | Description | Status |
|-------|-------------|--------|
| SE-P1 | Scoring engine (deterministic rules) | DONE |
| SE-P2 | Local Ollama run (scrape + extract + score) | DONE |
| SE-P3 | OpenAI extractor + dual-run compare | IN PROGRESS |

## SE-P1: Scoring Engine

- Deterministic scoring from `configs/scoring_rules.yaml`
- Dry-run validated with sample facts
- Status: **DONE**

## SE-P2: Local Ollama Run

- Ollama extractor implemented (`extract_ollama.py`) using `qwen2.5:14b-instruct`
- Scraping with caching (`scrape.py`)
- Full 20-hotel local run completed
- 14/20 hotels scraped successfully (6 blocked by 403/404/DNS)
- JSON serialization bug fixed (`model_dump(mode="json")`)
- Status: **DONE**

## SE-P3: OpenAI Extractor + Dual-Run Compare

- OpenAI extractor (`extract_openai.py`) is a **stub** — returns `None` for all hotels
- Dual-run benchmarking not executed (no OpenAI results to compare)
- Compare report not generated
- Status: **IN PROGRESS**

### Blocker

- `extract_openai.py` is not implemented. The function detects `OPENAI_API_KEY` but immediately returns `None` with a stub message. Must be implemented before dual-run can proceed.
