# LLM Extraction Comparison Report

This report compares sustainability fact extraction and scoring results
from a local LLM (Ollama) and OpenAI's LLM.

## Success Rates

- **Local (Ollama) hotels extracted:** 13
- **OpenAI hotels extracted:** 13
- **Both have data (comparable):** 13

## Timing & Cost

### Local (Ollama)

- Mean duration: 10542 ms
- Median duration: 9357 ms
- Total duration: 137.0 s
- Mean tokens out: 275
- Cost: $0.00 (local)

### OpenAI (gpt-4o-mini)

- Mean duration: 6498 ms
- Median duration: 6693 ms
- Total duration: 84.5 s
- Mean tokens in: 1589
- Mean tokens out: 276
- Total cost estimate: $0.0052
- Mean cost per hotel: $0.000404

## Overall Score Statistics

- **Mean Total Score Difference:** 0.94
- **Median Total Score Difference:** 0.00
- **Max Total Score Difference:** 5.59
- **Mean Confidence Difference:** 0.62

### Missing Data

- All hotels have data from both extractors.

### Fact Consistency Breakdown

| Fact Path | Local Has | OpenAI Has | Both Have | Different Value |
|---|---|---|---|---|
| `certifications.eco_certifications` | 0 | 1 | 11 | 1 |
| `certifications.other_sustainability_badges` | 0 | 1 | 11 | 1 |
| `energy_efficiency.energy_reduction_targets` | 1 | 0 | 0 | 0 |
| `energy_efficiency.led_lighting_used` | 4 | 0 | 0 | 0 |
| `energy_efficiency.renewable_energy_sources` | 0 | 0 | 12 | 1 |
| `energy_efficiency.solar_panels_used` | 6 | 0 | 1 | 0 |
| `local_community_engagement.community_support_programs` | 1 | 1 | 0 | 0 |
| `local_community_engagement.local_employment_initiatives` | 6 | 1 | 0 | 0 |
| `local_community_engagement.local_sourcing_food` | 5 | 1 | 1 | 0 |
| `waste_management.composting_program` | 6 | 0 | 0 | 0 |
| `waste_management.food_waste_reduction` | 6 | 0 | 0 | 0 |
| `waste_management.plastic_reduction_initiatives` | 0 | 0 | 13 | 0 |
| `waste_management.recycling_program` | 6 | 0 | 0 | 0 |
| `water_conservation.linen_reuse_program` | 5 | 0 | 0 | 0 |
| `water_conservation.rainwater_harvesting` | 6 | 0 | 0 | 0 |
| `water_conservation.water_reduction_targets` | 1 | 0 | 0 | 0 |
| `water_conservation.water_saving_fixtures` | 5 | 0 | 0 | 0 |

## Score Deltas (Local vs. OpenAI)

| Hotel Name | Local Score | OpenAI Score | Delta |
|---|---|---|---|
| Hotel ILUNION Fuengirola | 0.00 | 5.59 | -5.59 |
| Gran Hotel Miramar GL | 2.40 | 0.00 | +2.40 |
| Málaga Hills Boutique & Wellness Eco-Hotel | 7.92 | 9.52 | -1.60 |
| Marbella Club Hotel | 0.00 | 1.55 | -1.55 |
| Fuengirola Beach Apartamentos Turísticos | 1.60 | 0.50 | +1.10 |
| Amàre Beach Hotel Marbella | 0.00 | 0.00 | +0.00 |
| Hard Rock Hotel Marbella | 0.00 | 0.00 | +0.00 |
| Holiday World Resort Benalmádena | 0.00 | 0.00 | +0.00 |
| Hotel Best Siroco Benalmádena | 0.00 | 0.00 | +0.00 |
| Hotel Las Pirámides Resort Fuengirola | 0.00 | 0.00 | +0.00 |
| Hotel Puente Romano | 0.00 | 0.00 | +0.00 |
| Nobu Hotel Marbella | 0.00 | 0.00 | +0.00 |
| Sunset Beach Club Benalmádena | 0.00 | 0.00 | +0.00 |

## Example Diffs (Top 3 Biggest Deltas)

### Hotel ILUNION Fuengirola (delta: -5.59)

| Fact | Local | OpenAI |
|---|---|---|
| `energy_efficiency.solar_panels_used` | False | — |
| `local_community_engagement.community_support_programs` | — | ILUNION Fuengirola is committed to diverse talent, offering real opportunities and an accessible environment that inspires growth and commitment. |
| `local_community_engagement.local_employment_initiatives` | — | True |
| `local_community_engagement.local_sourcing_food` | False | — |
| `waste_management.composting_program` | False | — |
| `waste_management.food_waste_reduction` | False | — |
| `waste_management.recycling_program` | False | — |

### Gran Hotel Miramar GL (delta: +2.40)

| Fact | Local | OpenAI |
|---|---|---|
| `energy_efficiency.solar_panels_used` | False | — |
| `local_community_engagement.local_employment_initiatives` | False | — |
| `water_conservation.rainwater_harvesting` | False | — |

### Málaga Hills Boutique & Wellness Eco-Hotel (delta: -1.60)

| Fact | Local | OpenAI |
|---|---|---|
| `certifications.eco_certifications` | — | ['sustainability certificates'] |
| `certifications.other_sustainability_badges` | — | [] |
| `energy_efficiency.renewable_energy_sources` | ['solar'] | ['solar energy'] |
| `local_community_engagement.local_employment_initiatives` | False | — |
| `waste_management.composting_program` | False | — |
| `waste_management.food_waste_reduction` | False | — |
| `waste_management.recycling_program` | False | — |
| `water_conservation.linen_reuse_program` | False | — |
| `water_conservation.rainwater_harvesting` | False | — |
| `water_conservation.water_saving_fixtures` | False | — |

