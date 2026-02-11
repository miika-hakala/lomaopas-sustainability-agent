from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from openai import AsyncOpenAI

from lomaopas_sus.models import ExtractedFacts, EvidenceSnippet

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

SYSTEM_PROMPT = """You are extracting sustainability facts about a hotel from provided website text.
Return ONLY valid JSON matching the schema below. Do not include explanations outside the JSON.
If a field is unknown or not mentioned on the website, use null for optional fields, empty arrays for lists.
Only mark boolean fields as true if there is clear evidence in the text.
Include evidence_snippets with short direct quotes from the text that support your extracted facts.

Required JSON schema:
{
  "energy_efficiency": {
    "solar_panels_used": bool or null,
    "led_lighting_used": bool or null,
    "renewable_energy_sources": ["string"] or [],
    "energy_reduction_targets": "string" or null
  },
  "water_conservation": {
    "water_saving_fixtures": bool or null,
    "linen_reuse_program": bool or null,
    "rainwater_harvesting": bool or null,
    "water_reduction_targets": "string" or null
  },
  "waste_management": {
    "recycling_program": bool or null,
    "plastic_reduction_initiatives": ["string"] or [],
    "food_waste_reduction": bool or null,
    "composting_program": bool or null
  },
  "local_community_engagement": {
    "local_sourcing_food": bool or null,
    "local_employment_initiatives": bool or null,
    "community_support_programs": "string" or null
  },
  "certifications": {
    "eco_certifications": ["string"] or [],
    "other_sustainability_badges": ["string"] or []
  },
  "evidence_snippets": [{"url": "source_url", "snippet": "direct quote"}],
  "confidence": 0.0-1.0
}"""


# Pricing per 1M tokens for cost estimation (gpt-4o-mini, 2024 pricing)
_COST_PER_1M_INPUT = {"gpt-4o-mini": 0.15, "gpt-4o": 2.50}
_COST_PER_1M_OUTPUT = {"gpt-4o-mini": 0.60, "gpt-4o": 10.00}


async def extract_facts_openai(
    text_content: str,
    schema: Dict,
    url: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.0,
    force_extract: bool = False,
) -> Tuple[Optional[ExtractedFacts], List[EvidenceSnippet], float, Dict[str, Any]]:
    """Extract sustainability facts using OpenAI API.

    Returns:
        Tuple of (facts, evidence_snippets, confidence, meta_dict).
        meta_dict contains: extractor, model, duration_ms, tokens_in, tokens_out, cost_estimate_usd.
    """
    meta: Dict[str, Any] = {
        "extractor": "openai",
        "model": model,
        "duration_ms": 0,
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_estimate_usd": 0.0,
        "error": None,
    }

    api_key = OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OpenAI extractor not configured. Set OPENAI_API_KEY to enable.")
        meta["error"] = "OPENAI_API_KEY not set"
        return None, [], 0.0, meta

    # Truncate text to avoid excessive token usage (gpt-4o-mini context is 128k)
    max_chars = 60_000
    if len(text_content) > max_chars:
        text_content = text_content[:max_chars] + "\n[... truncated ...]"

    user_prompt = (
        f"Extract sustainability facts for this hotel from the following website text.\n"
        f"Source URL: {url}\n\n"
        f"Website text:\n{text_content}"
    )

    client = AsyncOpenAI(api_key=api_key)
    t0 = time.monotonic()

    try:
        response = await client.chat.completions.create(
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        duration_ms = int((time.monotonic() - t0) * 1000)
        meta["duration_ms"] = duration_ms

        usage = response.usage
        if usage:
            meta["tokens_in"] = usage.prompt_tokens
            meta["tokens_out"] = usage.completion_tokens
            cost_in = usage.prompt_tokens * _COST_PER_1M_INPUT.get(model, 0.15) / 1_000_000
            cost_out = usage.completion_tokens * _COST_PER_1M_OUTPUT.get(model, 0.60) / 1_000_000
            meta["cost_estimate_usd"] = round(cost_in + cost_out, 6)

        raw_text = response.choices[0].message.content or ""
        if not raw_text.strip():
            meta["error"] = "empty response"
            return None, [], 0.0, meta

        parsed = json.loads(raw_text)

        # Extract confidence from LLM response if provided, else default
        confidence = 0.9
        if "confidence" in parsed and isinstance(parsed["confidence"], (int, float)):
            confidence = min(1.0, max(0.0, float(parsed["confidence"])))
            del parsed["confidence"]

        facts = ExtractedFacts.model_validate(parsed)
        evidence = facts.evidence_snippets

        return facts, evidence, confidence, meta

    except Exception as exc:
        duration_ms = int((time.monotonic() - t0) * 1000)
        meta["duration_ms"] = duration_ms
        meta["error"] = str(exc)
        print(f"OpenAI extraction failed: {exc}")
        return None, [], 0.0, meta
