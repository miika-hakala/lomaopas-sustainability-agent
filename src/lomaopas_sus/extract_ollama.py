from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

from lomaopas_sus.models import ExtractedFacts, EvidenceSnippet


OLLAMA_HOST = os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434"


async def extract_facts_ollama(
    text_content: str,
    schema: Dict,
    url: str,
    model: str = "llama3",
    temperature: float = 0.0,
    force_extract: bool = False,
) -> Tuple[Optional[ExtractedFacts], List[EvidenceSnippet], float]:
    if not OLLAMA_HOST:
        print("Ollama extractor not configured. Set OLLAMA_HOST to enable.")
        return None, [], 0.0

    print(
        "Ollama extractor stub: configured but not implemented. "
        "Provide a real extractor before production use."
    )
    return None, [], 0.0
