# Paatosloki (Decision Log)

## 2026-02-11: SE-P3 dokumentaation paivitys

### Konteksti

- SE-P2 (Local Ollama run) suoritettu onnistuneesti
- SE-P3 (OpenAI extractor + dual-run) aloitettu mutta keskenerainen
- Dual-run yritettiin ajaa mutta OpenAI extractor on stub

### Havainnot

1. **Local run (Ollama):** 14/20 hotellia scrapattu, Ollama-ekstraktio toimii mutta useimmat hotellit saavat scoren 0.00
2. **OpenAI extractor:** `extract_openai.py` on stub — palauttaa `None` kaikille hotelleille
3. **Dual-run:** Ei voitu ajaa koska OpenAI-tuloksia ei synny
4. **JSON-serialisointibug:** Korjattu `model_dump(mode="json")` — Pydantic `Url`-tyyppi ei serialisoitunut

### Paatos

- Keskustelu paatetty
- Dokumentaatio paivitetty vastaamaan nykytilaa (status, roadmap, tasks, paatosloki)
- Dual-run ei viela ajettu — odottaa OpenAI extractorin toteutusta
- Jatketaan uudessa ketjussa SE-P3:sta (SE-P3A -> SE-P3B -> SE-P3C)

### Seuraavat askeleet

1. Toteuta OpenAI extractor (`SE-P3A`)
2. Aja dual-run 20 hotellille (`SE-P3B`)
3. Generoi vertailuraportti + delta-metriikat (`SE-P3C`)
