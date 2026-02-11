# Lomaopas Sustainability Agent

This repository contains a standalone sustainability agent for extracting structured sustainability facts from hotel websites and deterministically scoring them.

## Purpose
- Extract sustainability facts from hotel websites (LLM-backed extractors are stubbed by default).
- Score hotels deterministically using rules in `configs/scoring_rules.yaml`.
- Compare local vs OpenAI extraction outputs once real extractors are implemented.

## Repo Layout
- `configs/` scoring rules, extraction schema, hotel list, and sample facts.
- `src/lomaopas_sus/` implementation.
- `dataset/v1/` (empty placeholder for future JSONL outputs).
- `reports/compare_local_vs_openai.md` placeholder comparison report.

## Setup
```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` if you plan to enable extractors.

## CLI
Dry-run scoring using bundled sample facts:
```bash
python -m lomaopas_sus.cli dry-run
```

Full pipeline (requires real extractor implementations + env vars):
```bash
python -m lomaopas_sus.cli run --mode [local|openai|all] --limit 5
```

Compare outputs (expects JSONL files in `dataset/v1/`):
```bash
python -m lomaopas_sus.cli compare
```

## Notes
- Extractors are stubs unless `OLLAMA_HOST` or `OPENAI_API_KEY` are set.
- Dry-run is deterministic and does not require network access.
