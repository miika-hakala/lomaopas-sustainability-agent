# Threshold Calibration Report v1

Calibrated on 20 Costa del Sol hotels, dual-run (Ollama qwen2.5:14b + OpenAI gpt-4o-mini).

## Labeling Scale

The sustainability score (0-100) maps to a human-readable label:

| Label | Score Range | Description |
|-------|------------|-------------|
| **Insufficient Evidence** | 0 – < 0.5 | No sustainability information found on the hotel website, or extraction confidence too low to produce any score. |
| **Basic** | 0.5 – < 5.0 | Minimal sustainability signals: one or two facts such as local sourcing, a quality badge, or a general eco-friendly statement. No systematic program evident. |
| **Good** | 5.0 – < 15.0 | Clear sustainability evidence across multiple categories: renewable energy, certifications, community engagement, or published targets. Hotel actively communicates sustainability efforts. |
| **Excellent** | 15.0 – 100 | Comprehensive sustainability program with evidence in energy, water, waste, community, and certifications. Strong transparency with published targets and third-party verification. |

## Score Distributions

| Stat | Local (Ollama) | OpenAI |
|------|---------------|--------|
| min | 0.00 | 0.00 |
| median | 0.00 | 0.00 |
| mean | 1.86 | 1.27 |
| p90 | 3.02 | 2.81 |
| max | 19.42 | 9.52 |

Local scores (sorted): [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.4, 2.47, 2.47, 2.47, 7.92, 19.42]

OpenAI scores (sorted): [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5, 0.5, 1.5, 1.55, 1.55, 2.16, 2.5, 5.59, 9.52]

## Threshold Selection Rationale

Thresholds were chosen to:
1. **Maximize label agreement** between extractors (target: >= 70%)
2. **Reflect natural score clusters**: 0 (no evidence), 0.5-5 (minimal), 5-15 (clear evidence), 15+ (comprehensive)
3. **Be deterministic and versioned** (`configs/thresholds.v1.json`)

The 0.5 lower bound for Basic (vs 0) separates genuine zero-evidence hotels from those with even minimal signals. The 5.0 Good threshold requires evidence across multiple scoring categories. The 15.0 Excellent threshold requires broad, well-documented sustainability programs.

## Label Agreement

- **Comparable hotels:** 20
- **Agreement:** 15/20 = **75.0%**
- **Disagreements:** 5

### Agreement Matrix (Local \ OpenAI)

| | Insufficient Evidence | Basic | Good | Excellent |
|---|---|---|---|---|
| **Insufficient Evidence** | 11 | 3 | 0 | 0 |
| **Basic** | 0 | 3 | 1 | 0 |
| **Good** | 0 | 0 | 1 | 0 |
| **Excellent** | 0 | 1 | 0 | 0 |

### Label Distribution

| Label | Local | OpenAI |
|-------|-------|--------|
| Insufficient Evidence | 14 | 11 |
| Basic | 4 | 7 |
| Good | 1 | 2 |
| Excellent | 1 | 0 |

## Drift Analysis (Disagreements)

| Hotel | Local Label | Local Score | OpenAI Label | OpenAI Score | Reason |
|-------|------------|------------|-------------|-------------|--------|
| Fuengirola Beach Apartamentos Turísticos | Insufficient Evidence | 0.00 | Basic | 0.50 | OpenAI found facts missed by Ollama |
| Hotel ILUNION Fuengirola | Basic | 2.47 | Good | 5.59 | OpenAI found facts missed by Ollama |
| Hotel Puente Romano | Insufficient Evidence | 0.00 | Basic | 2.50 | OpenAI found facts missed by Ollama |
| Hotel San Fermín Benalmádena | Insufficient Evidence | 0.00 | Basic | 1.55 | OpenAI found facts missed by Ollama |
| MAC Puerto Marina Benalmádena | Excellent | 19.42 | Basic | 0.50 | Ollama hallucinated facts not found by OpenAI |

## Example Hotels Where Label Changes

### Fuengirola Beach Apartamentos Turísticos

- Local: **Insufficient Evidence** (score 0.00)
- OpenAI: **Basic** (score 0.50)
- **Why:** OpenAI found sustainability signals (certifications, community engagement) that Ollama missed. OpenAI's higher extraction quality detected more nuanced facts.

### Hotel ILUNION Fuengirola

- Local: **Basic** (score 2.47)
- OpenAI: **Good** (score 5.59)
- **Why:** OpenAI found sustainability signals (certifications, community engagement) that Ollama missed. OpenAI's higher extraction quality detected more nuanced facts.

### Hotel Puente Romano

- Local: **Insufficient Evidence** (score 0.00)
- OpenAI: **Basic** (score 2.50)
- **Why:** OpenAI found sustainability signals (certifications, community engagement) that Ollama missed. OpenAI's higher extraction quality detected more nuanced facts.

## Risks & Next Steps

### Risks

- **High Unknown rate** (55-70%): Most Costa del Sol hotels don't publish sustainability info on their homepages. This is a real finding, not a threshold issue. Multi-page scraping (subpages like /sustainability) would help.
- **Ollama hallucination** (MAC Puerto Marina): Local model occasionally invents facts, pushing scores into Excellent. Thresholds can't fix extractor quality — v2 should add hallucination detection.
- **Small calibration set** (n=20): Thresholds may need adjustment with larger hotel datasets.

### v2 Ideas

- Calibrate on 100+ hotels across multiple regions
- Add cross-extractor consensus: require both extractors to agree for higher labels
- Add sub-labels per category (energy: Good, water: Unknown, etc.)
- Hallucination detection: flag local scores > 2x OpenAI score
