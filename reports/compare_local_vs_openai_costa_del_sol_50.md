# LLM Extraction Comparison Report

This report compares sustainability fact extraction and scoring results
from a local LLM (Ollama) and OpenAI's LLM.

## Success Rates

- **Local (Ollama) hotels extracted:** 50
- **OpenAI hotels extracted:** 50
- **Both have data (comparable):** 50

## Timing & Cost

### Local (Ollama)

- Mean duration: 9466 ms
- Median duration: 9160 ms
- Total duration: 473.3 s
- Mean tokens out: 264
- Cost: $0.00 (local)

### OpenAI (gpt-4o-mini)

- Mean duration: 6346 ms
- Median duration: 6190 ms
- Total duration: 317.3 s
- Mean tokens in: 1815
- Mean tokens out: 278
- Total cost estimate: $0.0219
- Mean cost per hotel: $0.000439

## Overall Score Statistics

- **Mean Total Score Difference:** 0.94
- **Median Total Score Difference:** 0.00
- **Max Total Score Difference:** 7.40
- **Mean Confidence Difference:** 0.59

### Missing Data

- All hotels have data from both extractors.

### Fact Consistency Breakdown

| Fact Path | Local Has | OpenAI Has | Both Have | Different Value |
|---|---|---|---|---|
| `certifications.eco_certifications` | 0 | 3 | 1 | 0 |
| `certifications.other_sustainability_badges` | 1 | 4 | 1 | 1 |
| `energy_efficiency.renewable_energy_sources` | 1 | 0 | 0 | 2 |
| `energy_efficiency.solar_panels_used` | 2 | 0 | 2 | 0 |
| `local_community_engagement.community_support_programs` | 1 | 2 | 0 | 0 |
| `local_community_engagement.local_employment_initiatives` | 0 | 1 | 0 | 0 |
| `local_community_engagement.local_sourcing_food` | 0 | 4 | 6 | 0 |

## Score Deltas (Local vs. OpenAI)

| Hotel Name | Local Score | Local Label (v1) | Local Gated (v1.1) | OpenAI Score | OpenAI Label (v1) | OpenAI Gated (v1.1) | Delta |
|---|---|---|---|---|---|---|---|
| Hotel IPV Palace & Spa | 8.95 | Good | Good | 1.55 | Basic | Basic | +7.40 |
| Hotel ILUNION Fuengirola | 0.00 | Insufficient Evidence | Insufficient Evidence | 5.59 | Good | Good | -5.59 |
| Hotel Torremar Torre del Mar | 5.44 | Good | Good | 0.00 | Insufficient Evidence | Insufficient Evidence | +5.44 |
| Barcelo Malaga | 7.42 | Good | Good | 2.55 | Basic | Basic | +4.88 |
| MAC Puerto Marina Benalmádena | 0.00 | Insufficient Evidence | Insufficient Evidence | 4.55 | Basic | Basic | -4.55 |
| Hotel Puente Romano | 0.00 | Insufficient Evidence | Insufficient Evidence | 2.50 | Basic | Basic | -2.50 |
| Gran Hotel Miramar GL | 2.40 | Basic | Basic | 0.00 | Insufficient Evidence | Insufficient Evidence | +2.40 |
| Hotel Puente Real | 0.80 | Basic | Basic | 2.50 | Basic | Basic | -1.70 |
| Málaga Hills Boutique & Wellness Eco-Hotel | 7.92 | Good | Good | 9.52 | Good | Good | -1.60 |
| Hotel Molina Lario | 0.00 | Insufficient Evidence | Insufficient Evidence | 1.55 | Basic | Basic | -1.55 |
| Hotel Villa Flamenca | 0.00 | Insufficient Evidence | Insufficient Evidence | 1.55 | Basic | Basic | -1.55 |
| Kimpton Los Monteros Marbella | 0.00 | Insufficient Evidence | Insufficient Evidence | 1.55 | Basic | Basic | -1.55 |
| Marbella Club Hotel | 0.00 | Insufficient Evidence | Insufficient Evidence | 1.55 | Basic | Basic | -1.55 |
| Hotel Angela | 0.00 | Insufficient Evidence | Insufficient Evidence | 1.00 | Basic | Basic | -1.00 |
| Don Carlos Marbella | 2.47 | Basic | Basic | 1.55 | Basic | Basic | +0.93 |
| Hotel San Fermín Benalmádena | 2.47 | Basic | Basic | 1.55 | Basic | Basic | +0.93 |
| Hotel Marinas de Nerja | 6.24 | Good | Good | 5.44 | Good | Good | +0.80 |
| Fuengirola Beach Apartamentos Turísticos | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.50 | Basic | Basic | -0.50 |
| Fuerte Marbella | 2.47 | Basic | Basic | 2.16 | Basic | Basic | +0.31 |
| MS Amaragua Hotel | 1.60 | Basic | Basic | 1.40 | Basic | Basic | +0.20 |
| Alanda Marbella Hotel | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Amàre Beach Hotel Marbella | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Elba Estepona Gran Hotel & Thalasso Spa | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Finca Cortesin | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Hard Rock Hotel Marbella | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Holiday World Resort Benalmádena | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Hotel Balcon de Europa | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Hotel Best Siroco Benalmádena | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Hotel El Puerto | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Hotel Elimar | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Hotel La Barracuda Torremolinos | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Hotel Las Pirámides Resort Fuengirola | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Hotel Natali | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Hotel Nerja Club & Spa | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Hotel Palacete de Alamos | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Hotel Petit Palace Plaza Malaga | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Hotel Rincon Sol | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Hotel Riu Monica | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Hotel Room Mate Valeria | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Hotel Urban Beach Torrox | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Kempinski Hotel Bahía Estepona | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| La Zambra | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Nobu Hotel Marbella | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Only YOU Hotel Malaga | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Senator Marbella Spa Hotel | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Soho Boutique Equitativa | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Sunset Beach Club Benalmádena | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Vincci Aleysa Boutique & Spa Benalmádena | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Vincci Posada del Patio | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |
| Wyndham Grand Costa del Sol | 0.00 | Insufficient Evidence | Insufficient Evidence | 0.00 | Insufficient Evidence | Insufficient Evidence | +0.00 |

## Label Agreement

- **v1 Agreement (score-only):** 37/50 = **74%**
- **v1.1 Agreement (with evidence gating):** 37/50 = **74%**
- Thresholds: `configs/thresholds.v1.json` + evidence gate v1.1


## Example Diffs (Top 3 Biggest Deltas)

### Hotel IPV Palace & Spa (delta: +7.40)

| Fact | Local | OpenAI |
|---|---|---|
| `local_community_engagement.community_support_programs` | We are ambassadors of the typical gastronomy of the Costa del Sol and of the Manchego-Andalusian culinary tradition. | — |

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

