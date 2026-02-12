# Threshold Calibration Report v1.2

Recalibrated on 50 Costa del Sol hotels, dual-run (Ollama qwen2.5:14b + OpenAI gpt-4o-mini).

## Changes from v1

**Thresholds unchanged.** The v1 boundaries (0.5 / 5.0 / 15.0) remain optimal for the expanded 50-hotel dataset. Score distributions show the same natural clusters as the 20-hotel calibration. Evidence gating v1.1 is active.

## Labeling Scale

| Label | Score Range | Description |
|-------|------------|-------------|
| **Insufficient Evidence** | 0 – < 0.5 | No sustainability info on hotel homepage |
| **Basic** | 0.5 – < 5.0 | Minimal signals (1-2 facts) |
| **Good** | 5.0 – < 15.0 | Clear evidence across multiple categories |
| **Excellent** | 15.0 – 100 | Comprehensive program with certifications |

## Score Distributions (n=50)

| Stat | Local (Ollama) | OpenAI |
|------|---------------|--------|
| min | 0.00 | 0.00 |
| median | 0.00 | 0.00 |
| mean | 0.96 | 0.97 |
| p90 | 5.44 | 2.55 |
| max | 8.95 | 9.52 |
| non-zero count | 11 / 50 | 18 / 50 |

### Non-zero Scores

Local: 0.80, 1.60, 2.40, 2.47, 2.47, 2.47, 5.44, 6.24, 7.42, 7.92, 8.95

OpenAI: 0.50, 1.00, 1.40, 1.55, 1.55, 1.55, 1.55, 1.55, 1.55, 1.55, 2.16, 2.50, 2.50, 2.55, 4.55, 5.44, 5.59, 9.52

## Label Distribution

| Label | Local (v1.2) | OpenAI (v1.2) |
|-------|-------------|--------------|
| Insufficient Evidence | 39 (78%) | 32 (64%) |
| Basic | 6 (12%) | 15 (30%) |
| Good | 5 (10%) | 3 (6%) |
| Excellent | 0 (0%) | 0 (0%) |

### Insufficient Evidence Rate > 60%

**Local: 78%, OpenAI: 64% — both exceed the 60% target.**

**Root cause:** Single-page scraping captures only hotel homepages, which rarely mention sustainability. Hotels typically publish sustainability information on dedicated subpages (e.g., /sustainability, /environment, /csr) or in separate PDF reports.

**Evidence:**
- 30/50 hotels (60%) have zero scores from BOTH extractors — genuine absence of sustainability content
- OpenAI finds more subtle signals (18 non-zero vs 11 local) but still misses most
- This is a data quality limitation, not a threshold issue

**Mitigation:** Multi-page scraping (planned for SE-P6) would crawl subpages and significantly reduce the Insufficient Evidence rate.

## Label Agreement

- **v1.2 Agreement (score-only):** 37/50 = **74%**
- **v1.2 Agreement (with evidence gating v1.1):** 37/50 = **74%**

### Comparison with v1 (n=20)

| Metric | v1 (20 hotels) | v1.2 (50 hotels) |
|--------|----------------|-------------------|
| Agreement | 75% | 74% |
| IE rate (local) | 70% | 78% |
| IE rate (OpenAI) | 55% | 64% |
| Max delta | 18.92 | 7.40 |
| Mean delta | 1.52 | 0.94 |

Agreement stable at ~75%. Max delta dropped from 18.92 to 7.40 (MAC Puerto Marina hallucination no longer reproducible). Mean delta improved from 1.52 to 0.94.

### Threshold Adjustment Analysis

Alternative thresholds were evaluated but rejected:

| Change | Impact on Agreement | Reason for Rejection |
|--------|--------------------|--------------------|
| Basic threshold 0.5 → 0.25 | No change | No scores between 0.25 and 0.50 |
| Good threshold 5.0 → 6.0 | -1 (worse) | Would break Marinas de Nerja agreement |
| Good threshold 5.0 → 4.5 | -1 (worse) | MAC Puerto Marina OpenAI would become Good vs IE |

**Conclusion:** v1 thresholds are locally optimal for current data. Improvements require better extraction, not threshold tuning.

## Agreement Matrix (Local \ OpenAI)

| | Insufficient Evidence | Basic | Good |
|---|---|---|---|
| **Insufficient Evidence** | 30 | 9 | 0 |
| **Basic** | 1 | 5 | 0 |
| **Good** | 1 | 2 | 2 |

## Disagreements (13 hotels)

| Hotel | Local Score | Local Label | OpenAI Score | OpenAI Label | Reason |
|-------|-----------|------------|-------------|-------------|--------|
| Hotel IPV Palace & Spa | 8.95 | Good | 1.55 | Basic | Ollama hallucinated community claims |
| Hotel ILUNION Fuengirola | 0.00 | IE | 5.59 | Good | OpenAI found community/employment facts |
| Hotel Torremar Torre del Mar | 5.44 | Good | 0.00 | IE | Ollama found solar/renewable claims |
| Barcelo Malaga | 7.42 | Good | 2.55 | Basic | Ollama hallucinated broader program |
| MAC Puerto Marina | 0.00 | IE | 4.55 | Basic | OpenAI found badge fact |
| Hotel Puente Romano | 0.00 | IE | 2.50 | Basic | OpenAI found badges |
| Gran Hotel Miramar GL | 2.40 | Basic | 0.00 | IE | Ollama found local sourcing fact |
| Marbella Club Hotel | 0.00 | IE | 1.55 | Basic | OpenAI found local sourcing |
| Hotel Villa Flamenca | 0.00 | IE | 1.55 | Basic | OpenAI found local sourcing |
| Hotel Molina Lario | 0.00 | IE | 1.55 | Basic | OpenAI found local sourcing |
| Kimpton Los Monteros | 0.00 | IE | 1.55 | Basic | OpenAI found local sourcing |
| Hotel Angela | 0.00 | IE | 1.00 | Basic | OpenAI found sustainability signal |
| Fuengirola Beach | 0.00 | IE | 0.50 | Basic | OpenAI found badge |

**Pattern:** 9/13 disagreements are IE vs Basic (Ollama misses facts OpenAI finds). 3/13 are Ollama hallucinating higher scores. 1 is reversed (both miss different facts).

## City Coverage

| City | Hotels | Mean Local Score | Mean OpenAI Score |
|------|--------|-----------------|------------------|
| Benalmadena | 6 | 0.81 | 1.02 |
| Casares | 1 | 0.00 | 0.00 |
| Estepona | 2 | 0.00 | 0.00 |
| Fuengirola | 6 | 1.49 | 1.27 |
| Malaga | 10 | 0.24 | 0.26 |
| Marbella | 10 | 0.74 | 1.26 |
| Mijas | 2 | 0.00 | 0.00 |
| Nerja | 5 | 1.25 | 1.09 |
| Rincon de la Victoria | 2 | 0.00 | 0.00 |
| Torre del Mar | 1 | 5.44 | 0.00 |
| Torremolinos | 4 | 0.60 | 0.63 |
| Torrox | 1 | 0.00 | 0.00 |

## OpenAI Cost

- Total: $0.0219 for 50 hotels
- Mean per hotel: $0.000439
- Projected cost for 1000 hotels: ~$0.44

## Risks & Next Steps

### Risks

1. **High IE rate (64-78%)** exceeds 60% target — requires multi-page scraping to fix
2. **Ollama hallucination** still present (IPV Palace, Barcelo Malaga) — evidence gating helps but can't fix all cases
3. **IE/Basic boundary** is the primary disagreement zone — most extractors agree on clear sustainability vs no sustainability, but differ on borderline cases

### Confirmed from v1.2

- v1 thresholds validated on 2.5x larger dataset (50 vs 20)
- Evidence gating v1.1 remains appropriate (no false positives in this run)
- No Excellent labels in either extractor — reflects dataset reality
- MAC Puerto Marina hallucination not reproduced (Ollama output non-deterministic)

### Next Steps

- SE-P6: Multi-page scraping to reduce IE rate below 60%
- Cross-extractor consensus for higher labels
- Hallucination detection: flag |local - openai| > 5 points
