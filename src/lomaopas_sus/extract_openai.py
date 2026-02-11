from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

from lomaopas_sus.models import ExtractedFacts, EvidenceSnippet


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


async def extract_facts_openai(
    text_content: str,
    schema: Dict,
    url: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.0,
    force_extract: bool = False,
) -> Tuple[Optional[ExtractedFacts], List[EvidenceSnippet], float]:
    if not OPENAI_API_KEY:
        print("OpenAI extractor not configured. Set OPENAI_API_KEY to enable.")
        return None, [], 0.0

    print(
        "OpenAI extractor stub: configured but not implemented. "
        "Provide a real extractor before production use."
    )
    return None, [], 0.0
