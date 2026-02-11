from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


CACHE_DIR = _repo_root() / "cache" / "scraped_content"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


async def fetch_html(url: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True, timeout=10)
            response.raise_for_status()
            return response.text
    except httpx.RequestError as exc:
        print(f"Error fetching {url}: {exc}")
        return None
    except Exception as exc:
        print(f"Unexpected error fetching {url}: {exc}")
        return None


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


async def scrape_and_cache(url: str, force_scrape: bool = False) -> Optional[str]:
    cache_path = get_cache_path(url)

    if not force_scrape and cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    html_content = await fetch_html(url)
    if html_content:
        cleaned_text = clean_html_to_text(html_content)
        cache_path.write_text(cleaned_text, encoding="utf-8")
        return cleaned_text
    return None
