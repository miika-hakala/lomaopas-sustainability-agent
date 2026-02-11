# Sustainability Engine - Active Tasks

## SE-P3: OpenAI Extractor + Dual-Run Compare

### SE-P3A: Implement OpenAI extractor

- **Status:** DONE
- **File:** `src/lomaopas_sus/extract_openai.py`
- **Description:** Real implementation using OpenAI gpt-4o-mini with JSON mode. Returns `(ExtractedFacts, List[EvidenceSnippet], confidence, meta)`. Includes token tracking and cost estimation.

### SE-P3B: Execute dual-run (20 hotels)

- **Status:** DONE
- **Description:** Full pipeline executed for 19 Costa del Sol hotels (1 removed from config) in both modes.
  - 13/19 hotels successfully scraped and extracted (6 blocked by 403/404/DNS)
  - Output: `dataset/v1/costa_del_sol_20_local.jsonl` and `dataset/v1/costa_del_sol_20_openai.jsonl`
  - Raw per-hotel outputs: `runs/2026-02-11/local/` and `runs/2026-02-11/openai/`

### SE-P3C: Generate compare report + delta metrics

- **Status:** DONE
- **Description:** Comparison report generated at `reports/compare_local_vs_openai.md`
  - Includes: success rates, timing/cost, score deltas, fact consistency, example diffs
  - Mean score difference: 0.94
  - OpenAI total cost: $0.0052 for 13 hotels
