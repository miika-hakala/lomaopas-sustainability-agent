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
- Dual-run benchmark: 13 comparable hotels

### SE-P3 Gate Criteria

| Criterion | Status |
|-----------|--------|
| OpenAI extractor returns structured facts | SATISFIED |
| Dual-run (local + openai) for 20 hotels | SATISFIED (13/19 scraped) |
| Compare report with delta metrics | SATISFIED |
| Gate | **SATISFIED** |

## Future / SE-P4

- Threshold calibration based on dual-run delta analysis
- Improve Ollama extraction quality (many hotels score 0.00)
- Fix/update hotel URLs returning 403/404
- Add multi-page scraping for richer content
- Investigate evidence snippet quality from OpenAI
