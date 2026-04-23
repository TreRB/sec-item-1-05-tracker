"""CIK → ticker authoritative lookup via SEC's company_tickers.json.

The EDGAR search-index's display_name field usually includes the ticker
in parentheses, but not always (private-to-public transitions, CIK-only
foreign filers, non-listed regulated entities). This module caches the
SEC's canonical mapping and fills in tickers that the search response
didn't include.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional
from urllib import request


SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
DEFAULT_CACHE = Path(
    os.path.expanduser("~/.sec-item-1-05-tracker/company_tickers.json")
)
USER_AGENT = (
    "sec-item-1-05-tracker/0.2 (valtikstudios.com; tre@valtikstudios.com)"
)


def fetch_tickers(cache_path: Path = DEFAULT_CACHE,
                  force: bool = False,
                  timeout: int = 15) -> dict:
    """Fetch company_tickers.json from SEC (or use cache).

    The SEC file format is:
        {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
         "1": {...}, ...}

    We reshape to a CIK-keyed lookup:
        {"0000320193": {"ticker": "AAPL", "title": "Apple Inc."}, ...}
    """
    cache_path = Path(cache_path)
    if not force and cache_path.exists():
        try:
            return json.loads(cache_path.read_text())
        except Exception:
            pass

    req = request.Request(SEC_TICKERS_URL, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })
    with request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())

    cik_indexed = {}
    for _, row in data.items():
        cik = str(row.get("cik_str", "")).zfill(10)
        if cik:
            cik_indexed[cik] = {
                "ticker": row.get("ticker", ""),
                "title": row.get("title", ""),
            }

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cik_indexed, indent=2))
    return cik_indexed


def lookup_ticker(cik: str, tickers_index: Optional[dict] = None) -> str:
    """Return the ticker for a CIK, or '' if unknown."""
    if not tickers_index:
        return ""
    cik_norm = (cik or "").strip().zfill(10)
    entry = tickers_index.get(cik_norm)
    if not entry:
        return ""
    return entry.get("ticker", "")


def lookup_title(cik: str, tickers_index: Optional[dict] = None) -> str:
    if not tickers_index:
        return ""
    cik_norm = (cik or "").strip().zfill(10)
    entry = tickers_index.get(cik_norm)
    if not entry:
        return ""
    return entry.get("title", "")
