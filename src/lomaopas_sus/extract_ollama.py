import os
import json
import re
import time
import httpx
from typing import Any, Dict, Optional, Tuple

DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"

SYSTEM_PROMPT = """You are extracting sustainability facts about a hotel from provided text.
Return ONLY valid JSON matching the expected schema. Do not include explanations.
If a field is unknown, use null/empty values, do not guess numbers."""

class OllamaExtractor:
    def __init__(self, model: Optional[str] = None, host: Optional[str] = None, timeout_s: int = 60):
        self.model = model or os.getenv("OLLAMA_MODEL") or "qwen2.5:14b-instruct"
        self.host = (host or os.getenv("OLLAMA_HOST") or DEFAULT_OLLAMA_HOST).rstrip("/")
        self.timeout_s = timeout_s

    def extract(self, hotel_name: str, text: str, schema_json: str) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        """Extract facts and return (parsed_dict, meta_dict)."""
        prompt = f"{SYSTEM_PROMPT}\n\nSchema:\n{schema_json}\n\nHotel: {hotel_name}\n\nText:\n{text}\n"
        url = f"{self.host}/api/generate"
        payload = {"model": self.model, "prompt": prompt, "stream": False}

        meta: Dict[str, Any] = {
            "extractor": "ollama",
            "model": self.model,
            "duration_ms": 0,
            "tokens_in": 0,
            "tokens_out": 0,
            "cost_estimate_usd": 0.0,
            "error": None,
        }

        t0 = time.monotonic()
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                r = client.post(url, json=payload)
                r.raise_for_status()
                data = r.json()

                meta["duration_ms"] = int((time.monotonic() - t0) * 1000)
                # Ollama returns token counts in eval_count / prompt_eval_count
                meta["tokens_in"] = data.get("prompt_eval_count", 0)
                meta["tokens_out"] = data.get("eval_count", 0)

                out = (data.get("response") or "").strip()
                if not out:
                    meta["error"] = "empty response"
                    return None, meta
                # try parse JSON (sometimes wrapped)
                if not out.startswith("{"):
                    m = re.search(r"\{.*\}", out, re.DOTALL)
                    if m:
                        out = m.group(0)
                return json.loads(out), meta
        except Exception as e:
            meta["duration_ms"] = int((time.monotonic() - t0) * 1000)
            meta["error"] = str(e)
            print(f"Ollama extraction failed for {hotel_name}: {e}")
            return None, meta
