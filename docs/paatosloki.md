# Paatosloki (Decision Log)

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

- 13/19 hotellia scrapattu ja ekstraktoitu molemmilla LLM:illa
- 6 hotellia skipattu (403 Forbidden: 4, 404 Not Found: 1, DNS failure: 1)
- OpenAI kustannus: $0.0052 (13 hotellia)
- Keskimaarainen score-ero: 0.94, max: 5.59
- OpenAI nopeampi (~6.5s vs ~10.5s per hotelli)

### Paatos

- SE-P3 gate SATISFIED
- Dokumentaatio paivitetty
- Dual-run data ja raportti commitoitu
- Voidaan siirtya SE-P4:aan (threshold calibration)
