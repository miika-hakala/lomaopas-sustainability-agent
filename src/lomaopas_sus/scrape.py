from __future__ import annotations

import asyncio
import hashlib
import json
import random
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

_USER_AGENTS: List[str] = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

MAX_RETRIES = 3
INITIAL_BACKOFF_S = 2.0


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


CACHE_DIR = _repo_root() / "cache" / "scraped_content"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _headers(ua_index: int = 0) -> Dict[str, str]:
    return {
        "User-Agent": _USER_AGENTS[ua_index % len(_USER_AGENTS)],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }


async def fetch_html(
    url: str,
    timeout_s: int = 15,
) -> tuple[Optional[str], Dict[str, Any]]:
    """Fetch HTML with retry + rotating user-agent. Returns (html, debug_meta)."""
    debug: Dict[str, Any] = {
        "url": url,
        "attempts": [],
        "success": False,
        "final_status": None,
        "final_url": None,
        "content_length": None,
        "user_agent_used": None,
        "redirect_count": 0,
    }

    for attempt in range(MAX_RETRIES):
        ua_idx = attempt  # rotate UA per attempt
        hdrs = _headers(ua_idx)
        attempt_info: Dict[str, Any] = {
            "attempt": attempt + 1,
            "user_agent": hdrs["User-Agent"][:40] + "...",
            "status": None,
            "error": None,
            "duration_ms": 0,
        }
        t0 = time.monotonic()

        try:
            async with httpx.AsyncClient(
                headers=hdrs,
                follow_redirects=True,
                timeout=timeout_s,
            ) as client:
                response = await client.get(url)
                attempt_info["duration_ms"] = int((time.monotonic() - t0) * 1000)
                attempt_info["status"] = response.status_code

                if response.status_code < 400:
                    debug["success"] = True
                    debug["final_status"] = response.status_code
                    debug["final_url"] = str(response.url)
                    debug["redirect_count"] = len(response.history)
                    debug["content_length"] = len(response.content)
                    debug["user_agent_used"] = hdrs["User-Agent"]
                    debug["attempts"].append(attempt_info)
                    return response.text, debug

                # 4xx/5xx — record and maybe retry
                attempt_info["error"] = f"HTTP {response.status_code}"
                debug["final_status"] = response.status_code

        except httpx.TimeoutException:
            attempt_info["duration_ms"] = int((time.monotonic() - t0) * 1000)
            attempt_info["error"] = "timeout"
        except httpx.RequestError as exc:
            attempt_info["duration_ms"] = int((time.monotonic() - t0) * 1000)
            attempt_info["error"] = str(exc)
        except Exception as exc:
            attempt_info["duration_ms"] = int((time.monotonic() - t0) * 1000)
            attempt_info["error"] = f"unexpected: {exc}"

        debug["attempts"].append(attempt_info)

        # Don't retry on 404 (page genuinely missing)
        if attempt_info.get("status") == 404:
            break

        # Exponential backoff before next retry
        if attempt < MAX_RETRIES - 1:
            wait = INITIAL_BACKOFF_S * (2 ** attempt) + random.uniform(0, 1)
            await asyncio.sleep(wait)

    return None, debug


def clean_html_to_text(html_content: str) -> str:
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(
        ["script", "style", "header", "footer", "nav", "form", "noscript", "meta", "link", "img"]
    ):
        tag.extract()

    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return "\n".join(chunk for chunk in chunks if chunk)


def get_cache_path(url: str) -> Path:
    url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{url_hash}.txt"


def save_scrape_failure(hotel_name: str, debug: Dict[str, Any]) -> None:
    """Save failure metadata to runs/{date}/scrape_failures/."""
    fail_dir = _repo_root() / "runs" / date.today().isoformat() / "scrape_failures"
    fail_dir.mkdir(parents=True, exist_ok=True)
    safe_name = hotel_name.replace("/", "_").replace(" ", "_")[:60]
    path = fail_dir / f"{safe_name}.json"
    path.write_text(json.dumps(debug, indent=2, ensure_ascii=False), encoding="utf-8")


async def scrape_and_cache(
    url: str,
    force_scrape: bool = False,
    hotel_name: str = "",
    fallback_urls: Optional[List[str]] = None,
) -> tuple[Optional[str], str]:
    """Scrape URL with caching, retry, and fallback support.

    Returns (cleaned_text, source_type) where source_type is 'primary', 'fallback', or 'cache'.
    """
    cache_path = get_cache_path(url)

    if not force_scrape and cache_path.exists():
        return cache_path.read_text(encoding="utf-8"), "cache"

    # Try primary URL
    html, debug = await fetch_html(url)
    if html:
        cleaned = clean_html_to_text(html)
        if cleaned and len(cleaned) > 100:
            cache_path.write_text(cleaned, encoding="utf-8")
            return cleaned, "primary"

    # Log primary failure
    print(f"  Primary scrape failed for {url} (status={debug.get('final_status')})")
    save_scrape_failure(hotel_name or url, debug)

    # Try fallback URLs
    for i, fb_url in enumerate(fallback_urls or []):
        fb_cache = get_cache_path(fb_url)
        if not force_scrape and fb_cache.exists():
            return fb_cache.read_text(encoding="utf-8"), "fallback"

        fb_html, fb_debug = await fetch_html(fb_url)
        if fb_html:
            cleaned = clean_html_to_text(fb_html)
            if cleaned and len(cleaned) > 100:
                fb_cache.write_text(cleaned, encoding="utf-8")
                print(f"  Fallback #{i+1} succeeded: {fb_url}")
                return cleaned, "fallback"

        save_scrape_failure(f"{hotel_name or url}_fallback_{i+1}", fb_debug)

    return None, "failed"
