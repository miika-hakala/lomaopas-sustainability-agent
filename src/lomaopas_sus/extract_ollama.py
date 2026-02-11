import os
import json
import httpx
from typing import Any, Dict, Optional

DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"

SYSTEM_PROMPT = """You are extracting sustainability facts about a hotel from provided text.
Return ONLY valid JSON matching the expected schema. Do not include explanations.
If a field is unknown, use null/empty values, do not guess numbers."""

class OllamaExtractor:
    def __init__(self, model: Optional[str] = None, host: Optional[str] = None, timeout_s: int = 60):
        self.model = model or os.getenv("OLLAMA_MODEL") or "qwen2.5:14b-instruct"
        self.host = (host or os.getenv("OLLAMA_HOST") or DEFAULT_OLLAMA_HOST).rstrip("/")
        self.timeout_s = timeout_s

    def extract(self, hotel_name: str, text: str, schema_json: str) -> Optional[Dict[str, Any]]:
        prompt = f"{SYSTEM_PROMPT}\n\nSchema:\n{schema_json}\n\nHotel: {hotel_name}\n\nText:\n{text}\n"
        url = f"{self.host}/api/generate"
        payload = {"model": self.model, "prompt": prompt, "stream": False}

        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                r = client.post(url, json=payload)
                r.raise_for_status()
                data = r.json()
                out = (data.get("response") or "").strip()
                if not out:
                    return None
                # try parse JSON (sometimes wrapped)
                # find first '{' ... last '}'
                if not out.startswith("{"):
                    m = re.search(r"\{.*\}", out, re.DOTALL)
                    if m:
                        out = m.group(0)
                return json.loads(out)
        except Exception as e:
            print(f"Ollama extraction failed for {hotel_name}: {e}")
            return None
