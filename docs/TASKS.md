# Sustainability Engine - Active Tasks

## SE-P3: OpenAI Extractor + Dual-Run Compare

### SE-P3A: Implement OpenAI extractor

- **Status:** TODO
- **File:** `src/lomaopas_sus/extract_openai.py`
- **Description:** Replace the stub in `extract_facts_openai()` with a real implementation that calls the OpenAI API (gpt-4o-mini) to extract structured sustainability facts matching `ExtractedFacts` schema. Must return `(ExtractedFacts, List[EvidenceSnippet], confidence)`.
- **Requires:** `OPENAI_API_KEY` environment variable

### SE-P3B: Execute dual-run (20 hotels)

- **Status:** BLOCKED (by SE-P3A)
- **Description:** Run the full pipeline for 20 Costa del Sol hotels in both modes:
  ```bash
  python -m lomaopas_sus.cli run --mode local
  python -m lomaopas_sus.cli run --mode openai
  ```
- **Expected output:** `dataset/v1/costa_del_sol_20_local.jsonl` and `dataset/v1/costa_del_sol_20_openai.jsonl`

### SE-P3C: Generate compare report + delta metrics

- **Status:** BLOCKED (by SE-P3B)
- **Description:** Run the comparison command and verify delta metrics:
  ```bash
  python -m lomaopas_sus.cli compare
  ```
- **Expected output:** `reports/compare_local_vs_openai.md` with per-hotel score deltas, average absolute delta, and max delta.
