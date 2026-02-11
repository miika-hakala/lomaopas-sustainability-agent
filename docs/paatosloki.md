# Paatosloki (Decision Log)

## 2026-02-11: SE-P5 Threshold Calibration v1

### Konteksti

- SE-P4 (Scraping reliability + normalization + 20/20 dual-run) suoritettu
- 20/20 hotellia onnistuneesti extractoitu molemmilla (Ollama + OpenAI)
- Tarvitaan deterministinen score -> label -mapping

### Paatos: 4-tasoinen luokitusasteikko

| Label | Score-alue | Kuvaus |
|-------|-----------|--------|
| Insufficient Evidence | < 0.5 | Ei sustainability-tietoa hotellisivulla |
| Basic | 0.5 - 4.99 | Minimaalisia signaaleja (esim. local sourcing) |
| Good | 5.0 - 14.99 | Selkea sustainability-evidence useassa kategoriassa |
| Excellent | >= 15.0 | Laaja sustainability-ohjelma, sertifikaatit, tavoitteet |

### Perustelut

- Thresholdit kalibroitu 20 Costa del Sol -hotellin dual-run -datasta
- **Label agreement: 75%** (15/20 hotellia sama label molemmilla extractoreilla)
- Tavoite >= 70% saavutettu
- Luonnolliset score-klusterit: 0 (ei evidenssia), 0.5-5 (vahan), 5-15 (selkeaa), 15+ (kattavaa)
- 55-70% hotelleista "Insufficient Evidence" — heijastaa todellisuutta (useimmat hotellit eivat julkaise sustainability-tietoa etusivullaan)

### Riskit

- Pieni kalibrointiotos (n=20), thresholdit voivat vaatia saatoa suuremmalla datasetilla
- Ollama-hallusinointeja (MAC Puerto Marina: local 19.42 vs OpenAI 0.50) — threshold ei korjaa extractor-laatua
- Korkea "Insufficient Evidence" -osuus — ratkaisu: multi-page scraping (alasivut kuten /sustainability)

### Artefaktit

- Config: `configs/thresholds.v1.json`
- Kalibrointiraportti: `reports/threshold_calibration_v1.md`
- Vertailuraportti (paivitetty labeleilla): `reports/compare_local_vs_openai.md`
- Calibration script: `scripts/calibrate_thresholds.py`

---

## 2026-02-11: SE-P3 toteutettu ja dual-run ajettu

### Konteksti

- SE-P2 (Local Ollama run) suoritettu onnistuneesti
- SE-P3 (OpenAI extractor + dual-run) toteutettu ja ajettu

### Toteutus

1. **OpenAI extractor:** Toteutettu `extract_openai.py` kayttaen gpt-4o-mini + JSON mode
   - Sisaltaa token-seuranta ja kustannusarvio
   - Palauttaa (facts, evidence, confidence, meta) -tuplen
2. **Ollama extractor:** Lisatty `import re` (puuttuva riippuvuus) ja meta-seuranta (duration, tokens)
3. **CLI:** Lisatty per-hotelli raw output tallennnus `runs/{date}/`, meta JSONL-tuloksiin
4. **Compare:** Lisatty timing/cost-osio, example diffs top-3 hotelleista, max delta

### Tulokset

- 20/20 hotellia scrapattu ja ekstraktoitu molemmilla LLM:illa
- OpenAI kustannus: $0.0087 (20 hotellia)
- Keskimaarainen score-ero: 1.52, max: 18.92
- OpenAI nopeampi (~7.4s vs ~9.3s per hotelli)

### Paatos

- SE-P3 gate SATISFIED
- Dokumentaatio paivitetty
- Dual-run data ja raportti commitoitu
- Voidaan siirtya SE-P5:aan (threshold calibration)
