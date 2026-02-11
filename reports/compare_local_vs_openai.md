# LLM Extraction Comparison Report

This report compares sustainability fact extraction and scoring results
from a local LLM (Ollama) and OpenAI's LLM.

## Success Rates

- **Local (Ollama) hotels extracted:** 19
- **OpenAI hotels extracted:** 20
- **Both have data (comparable):** 19

## Timing & Cost

### Local (Ollama)

- Mean duration: 10239 ms
- Median duration: 9735 ms
- Total duration: 194.5 s
- Mean tokens out: 267
- Cost: $0.00 (local)

### OpenAI (gpt-4o-mini)

- Mean duration: 5925 ms
- Median duration: 5734 ms
- Total duration: 118.5 s
- Mean tokens in: 1726
- Mean tokens out: 296
- Total cost estimate: $0.0087
- Mean cost per hotel: $0.000437

## Overall Score Statistics

- **Mean Total Score Difference:** 1.23
- **Median Total Score Difference:** 0.70
- **Max Total Score Difference:** 5.59
- **Mean Confidence Difference:** 0.56

### Missing Data

- **Hotels with no local LLM data:** Fuerte Marbella

### Fact Consistency Breakdown

| Fact Path | Local Has | OpenAI Has | Both Have | Different Value |
|---|---|---|---|---|
| `certifications.eco_certifications` | 1 | 1 | 0 | 0 |
| `certifications.other_sustainability_badges` | 0 | 4 | 0 | 0 |
| `eco_friendliness.is_eco_friendly` | 1 | 0 | 0 | 0 |
| `energy_efficiency.led_lighting_used` | 1 | 0 | 0 | 0 |
| `energy_efficiency.renewable_energy_sources` | 1 | 0 | 0 | 1 |
| `energy_efficiency.solar_panels_used` | 1 | 0 | 1 | 0 |
| `local_community_engagement.community_support_programs` | 0 | 1 | 0 | 0 |
| `local_community_engagement.local_employment_initiatives` | 0 | 1 | 0 | 0 |
| `local_community_engagement.local_sourcing_food` | 0 | 1 | 2 | 0 |

## Score Deltas (Local vs. OpenAI)

| Hotel Name | Local Score | OpenAI Score | Delta |
|---|---|---|---|
| Hotel ILUNION Fuengirola | 0.00 | 5.59 | -5.59 |
| Hotel Torremar Torre del Mar | 5.44 | 0.00 | +5.44 |
| Hotel Puente Romano | 0.00 | 2.50 | -2.50 |
| Amàre Beach Hotel Marbella | 2.47 | 0.00 | +2.47 |
| Málaga Hills Boutique & Wellness Eco-Hotel | 7.92 | 9.52 | -1.60 |
| Hotel San Fermín Benalmádena | 0.00 | 1.55 | -1.55 |
| Gran Hotel Miramar GL | 0.00 | 1.50 | -1.50 |
| Fuengirola Beach Apartamentos Turísticos | 1.60 | 0.50 | +1.10 |
| Marbella Club Hotel | 2.47 | 1.55 | +0.93 |
| MAC Puerto Marina Benalmádena | 0.00 | 0.70 | -0.70 |
| Hard Rock Hotel Marbella | 0.00 | 0.00 | +0.00 |
| Holiday World Resort Benalmádena | 0.00 | 0.00 | +0.00 |
| Hotel Best Siroco Benalmádena | 0.00 | 0.00 | +0.00 |
| Hotel La Barracuda Torremolinos | 0.00 | 0.00 | +0.00 |
| Hotel Las Pirámides Resort Fuengirola | 0.00 | 0.00 | +0.00 |
| Kempinski Hotel Bahía Estepona | 0.00 | 0.00 | +0.00 |
| Nobu Hotel Marbella | 0.00 | 0.00 | +0.00 |
| Sunset Beach Club Benalmádena | 0.00 | 0.00 | +0.00 |
| Vincci Aleysa Boutique & Spa Benalmádena | 0.00 | 0.00 | +0.00 |

## Example Diffs (Top 3 Biggest Deltas)

### Hotel ILUNION Fuengirola (delta: -5.59)

| Fact | Local | OpenAI |
|---|---|---|
| `local_community_engagement.community_support_programs` | — | ILUNION Fuengirola is committed to diverse talent, offering real opportunities and an accessible environment that inspires growth and commitment. |
| `local_community_engagement.local_employment_initiatives` | — | True |

### Hotel Torremar Torre del Mar (delta: +5.44)

| Fact | Local | OpenAI |
|---|---|---|
| `energy_efficiency.renewable_energy_sources` | ['solar'] | — |
| `energy_efficiency.solar_panels_used` | True | — |

### Hotel Puente Romano (delta: -2.50)

| Fact | Local | OpenAI |
|---|---|---|
| `certifications.other_sustainability_badges` | — | ['1st Grand Serandipians Hotel Champion Gold', 'Wine Spectator Restaurant Award - Sea Grill', 'Best Lifestyle Hotel at the Beyond Luxury Awards', 'Hotel & Mantel Winner by Condé Nast Traveler - Chiringuito Puente Romano', "World Spa Award Europe's Best Resort Spa", "World Spa Award Spain's Best Resort Spa", 'Condé Nast Traveler Awards 2023 ‘Best Resort’', 'Wine Spectator Best of Award of Excellence'] |

