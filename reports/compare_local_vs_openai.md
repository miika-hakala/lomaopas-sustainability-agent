# LLM Extraction Comparison Report

This report compares sustainability fact extraction and scoring results
from a local LLM (Ollama) and OpenAI's LLM.

## Success Rates

- **Local (Ollama) hotels extracted:** 20
- **OpenAI hotels extracted:** 20
- **Both have data (comparable):** 20

## Timing & Cost

### Local (Ollama)

- Mean duration: 9297 ms
- Median duration: 9183 ms
- Total duration: 185.9 s
- Mean tokens out: 264
- Cost: $0.00 (local)

### OpenAI (gpt-4o-mini)

- Mean duration: 7387 ms
- Median duration: 6668 ms
- Total duration: 147.7 s
- Mean tokens in: 1726
- Mean tokens out: 293
- Total cost estimate: $0.0087
- Mean cost per hotel: $0.000435

## Overall Score Statistics

- **Mean Total Score Difference:** 1.52
- **Median Total Score Difference:** 0.00
- **Max Total Score Difference:** 18.92
- **Mean Confidence Difference:** 0.55

### Missing Data

- All hotels have data from both extractors.

### Fact Consistency Breakdown

| Fact Path | Local Has | OpenAI Has | Both Have | Different Value |
|---|---|---|---|---|
| `certifications.eco_certifications` | 0 | 1 | 0 | 0 |
| `certifications.other_sustainability_badges` | 0 | 3 | 1 | 0 |
| `energy_efficiency.energy_reduction_targets` | 1 | 0 | 0 | 0 |
| `energy_efficiency.renewable_energy_sources` | 0 | 0 | 0 | 1 |
| `energy_efficiency.solar_panels_used` | 0 | 0 | 1 | 0 |
| `local_community_engagement.community_support_programs` | 1 | 1 | 0 | 0 |
| `local_community_engagement.local_employment_initiatives` | 0 | 0 | 1 | 0 |
| `local_community_engagement.local_sourcing_food` | 0 | 1 | 3 | 0 |

## Score Deltas (Local vs. OpenAI)

| Hotel Name | Local Score | Local Label (v1) | Local Gated (v1.1) | OpenAI Score | OpenAI Label (v1) | OpenAI Gated (v1.1) | Delta |
|---|---|---|---|---|---|---|---|
| MAC Puerto Marina Benalmádena | 19.42 | Excellent | Good | 0.50 | Basic | Basic | +18.92 |
| Hotel ILUNION Fuengirola | 2.47 | Basic | Basic | 5.59 | Good | Good | -3.12 |
| Hotel Puente Romano | 0.00 | Insufficient Evidence | Insufficient Evidence | 2.50 | Basic | Basic | -2.50 |
| Málaga Hills Boutique & Wellness Eco-Hotel | 7.92 | Good | Good | 9.52 | Good | Good | -1.60 |
| Hotel San Fermín Benalmádena | 0.00 | Insufficient Evidence | Insufficient Evidence | 1.55 | Basic | Basic | -1.55 |
| Marbella Club Hotel | 2.47 | Basic | Basic | 1.55 | Basic | Basic | +0.93 |
| Gran Hotel Miramar GL | 2.40 | Basic | Basic | 1.50 | Basic | Basic | +0.90 |
| Fuengirola Beach Apartamentos Turísticos | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.50 | Basic | Basic | -0.50 |
| Fuerte Marbella | 2.47 | Basic | Basic | 2.16 | Basic | Basic | +0.31 |
| Amàre Beach Hotel Marbella | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Hard Rock Hotel Marbella | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Holiday World Resort Benalmádena | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Hotel Best Siroco Benalmádena | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Hotel La Barracuda Torremolinos | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Hotel Las Pirámides Resort Fuengirola | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Hotel Torremar Torre del Mar | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Kempinski Hotel Bahía Estepona | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Nobu Hotel Marbella | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Sunset Beach Club Benalmádena | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Vincci Aleysa Boutique & Spa Benalmádena | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |

## Label Agreement

- **v1 Agreement (score-only):** 15/20 = **75%**
- **v1.1 Agreement (with evidence gating):** 15/20 = **75%**
- Thresholds: `configs/thresholds.v1.json` + evidence gate v1.1

### Evidence Gate Changes

  - MAC Puerto Marina Benalmádena: local Excellent -> Good (claims=2), openai Basic -> Basic (claims=1)

## Example Diffs (Top 3 Biggest Deltas)

### MAC Puerto Marina Benalmádena (delta: +18.92)

| Fact | Local | OpenAI |
|---|---|---|
| `certifications.other_sustainability_badges` | — | ['Travelifes Responsible Guest Guide'] |
| `energy_efficiency.energy_reduction_targets` | Commitment to reduce greenhouse gas emissions | — |
| `local_community_engagement.community_support_programs` | Community participation | — |

### Hotel ILUNION Fuengirola (delta: -3.12)

| Fact | Local | OpenAI |
|---|---|---|
| `local_community_engagement.community_support_programs` | — | ILUNION Fuengirola is committed to diverse talent, offering real opportunities and an accessible environment that inspires growth and commitment. |

### Hotel Puente Romano (delta: -2.50)

| Fact | Local | OpenAI |
|---|---|---|
| `certifications.other_sustainability_badges` | — | ['1st Grand Serandipians Hotel Champion Gold', 'Wine Spectator Restaurant Award - Sea Grill', 'Best Lifestyle Hotel at the Beyond Luxury Awards', 'Hotel & Mantel Winner by Condé Nast Traveler - Chiringuito Puente Romano', "World Spa Award Europe's Best Resort Spa", "World Spa Award Spain's Best Resort Spa", 'Condé Nast Traveler Awards 2023 ‘Best Resort’', 'Wine Spectator Best of Award of Excellence'] |

