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

## SE-P3: OpenAI Extractor + Dual-Run Compare [IN PROGRESS]

### SE-P3 Open Items

- OpenAI extractor implementation pending
- Dual-run benchmarking not executed
- Compare report + delta metrics not generated

### SE-P3 Gate Criteria

| Criterion | Status |
|-----------|--------|
| OpenAI extractor returns structured facts | NOT SATISFIED |
| Dual-run (local + openai) for 20 hotels | NOT SATISFIED |
| Compare report with delta metrics | NOT SATISFIED |
| Gate | **NOT SATISFIED** |

## Future

- Improve Ollama extraction quality (most hotels score 0.00)
- Fix/update hotel URLs returning 403/404
- Add evidence snippet extraction for Ollama mode
- Investigate multi-page scraping for richer content
