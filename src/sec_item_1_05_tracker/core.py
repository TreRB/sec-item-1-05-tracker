"""Core: poll EDGAR FTS, filter Item 1.05, enrich, optionally fetch body."""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib import parse, request

from .body import IncidentFacts, extract_facts, fetch_body, strip_html
from .sic import sic_label, sic_sector
from .tickers import lookup_ticker, lookup_title

SEC_FTS_URL = "https://efts.sec.gov/LATEST/search-index"
USER_AGENT = (
    "sec-item-1-05-tracker/0.2 (valtikstudios.com; tre@valtikstudios.com)"
)

# SEC requires a User-Agent with identifying contact info. Without one,
# they rate-limit harder or reject.


# ─────────────────────────── HTTP helpers ───────────────────────────


def _get_json(url: str, timeout: int = 15) -> Optional[dict]:
    req = request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


# ─────────────────────────── EDGAR fetch ───────────────────────────


def fetch_filings(since: datetime, until: datetime,
                  include_amendments: bool = True,
                  max_results: int = 1000,
                  verbose: bool = False,
                  throttle: float = 0.15) -> list[dict]:
    """Pull Item 1.05 filings from EDGAR FTS between `since` and `until`.

    SEC asks for max 10 requests/sec on the public data APIs. Default
    throttle of 150ms between page fetches keeps us well under that.
    """
    forms = "8-K,8-K/A" if include_amendments else "8-K"
    params = {
        "q": '"Item 1.05"',
        "dateRange": "custom",
        "startdt": since.strftime("%Y-%m-%d"),
        "enddt": until.strftime("%Y-%m-%d"),
        "forms": forms,
    }
    hits: list[dict] = []
    from_idx = 0
    size = 100
    while from_idx < max_results:
        params["from"] = from_idx
        params["size"] = min(size, max_results - from_idx)
        url = f"{SEC_FTS_URL}?{parse.urlencode(params)}"
        data = _get_json(url)
        if not data:
            break
        h = data.get("hits", {}).get("hits", []) or []
        if not h:
            break
        if verbose:
            print(f"  EDGAR page from={from_idx} returned {len(h)} hits",
                  flush=True)
        hits.extend(h)
        total = int(data.get("hits", {}).get("total", {}).get("value", 0))
        from_idx += len(h)
        if from_idx >= total:
            break
        time.sleep(throttle)
    return hits


# ─────────────────────────── filter + enrich ───────────────────────────


def filter_item_1_05(raw_hits: Iterable[dict]) -> list[dict]:
    """Keep only filings that really have Item 1.05 in the items field."""
    out = []
    for h in raw_hits:
        src = h.get("_source", {})
        items = src.get("items", []) or []
        if not any("1.05" in str(i) for i in items):
            continue
        out.append(h)
    return out


def enrich_filing(hit: dict,
                  tickers_index: Optional[dict] = None) -> dict:
    """Map one EDGAR hit → normalized filing record."""
    src = hit.get("_source", {})
    # EDGAR _id format: "0001193125-26-149607:primary_doc.htm"
    raw_id = hit.get("_id", "") or src.get("adsh", "")
    adsh = raw_id.split(":")[0] if raw_id else ""
    ciks = src.get("ciks", []) or [""]
    cik = str(ciks[0]) if ciks else ""
    display_names = src.get("display_names", []) or [""]
    display_name = display_names[0] if display_names else ""

    # "ACME CORP  (ACME)  (CIK 0001234567)"
    ticker = ""
    m = re.search(r"\(([A-Z0-9.\-]{1,6})\)\s*\(CIK\s*(\d+)\)", display_name)
    if m:
        ticker = m.group(1)
        if not cik:
            cik = m.group(2)
    company_name = re.sub(r"\s*\(.*", "", display_name).strip()

    # Fall back to authoritative ticker lookup if we didn't get it from
    # the display name
    if tickers_index and not ticker and cik:
        ticker = lookup_ticker(cik, tickers_index)
    # Use authoritative title if the display-name parse gave us garbage
    if tickers_index and cik:
        official_title = lookup_title(cik, tickers_index)
        if official_title and not company_name:
            company_name = official_title

    sic = str(src.get("sics", [""])[0] or "")
    filed_at = src.get("file_date", "") or src.get("adsh_dt", "")
    period = src.get("period_of_report", "") or ""
    form = src.get("form", "") or ""
    file_type = src.get("file_type", "") or ""
    items = src.get("items", []) or []
    inc_states = src.get("inc_states", []) or []
    inc_state = inc_states[0] if inc_states else ""
    biz_states = src.get("biz_states", []) or []
    hq_state = biz_states[0] if biz_states else ""

    # Filing URL
    filing_url = ""
    if adsh and cik:
        adsh_nodash = adsh.replace("-", "")
        try:
            cik_int = int(cik)
            filing_url = (
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{cik_int}/{adsh_nodash}/{adsh}-index.htm"
            )
        except Exception:
            pass

    return {
        "cik": cik.zfill(10) if cik.isdigit() else cik,
        "company_name": company_name,
        "ticker": ticker,
        "sic": sic,
        "sic_label": sic_label(sic),
        "sector": sic_sector(sic),
        "filed_at": filed_at,
        "period": period,
        "accession_no": adsh,
        "form": form,
        "file_type": file_type,
        "items": items,
        "inc_state": inc_state,
        "hq_state": hq_state,
        "filing_url": filing_url,
        "first_seen": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ─────────────────────────── body enrichment ───────────────────────────


def enrich_with_body(filing: dict, timeout: int = 15,
                     verbose: bool = False) -> dict:
    """Fetch the filing body and merge extracted incident facts into
    the filing dict."""
    url = filing.get("filing_url", "")
    if not url:
        return filing
    if verbose:
        print(f"  fetching body: {filing.get('company_name','?')}", flush=True)
    body = fetch_body(url, timeout=timeout)
    if not body:
        return filing
    facts = extract_facts(body)
    # Flatten facts into the filing
    filing = dict(filing)
    filing["mentions_ransomware"] = facts.mentions_ransomware
    filing["mentions_data_access"] = facts.mentions_data_access
    filing["incident_contained"] = facts.incident_contained
    filing["still_investigating"] = facts.still_investigating
    filing["forensic_firm_engaged"] = facts.forensic_firm_engaged
    filing["law_enforcement_notified"] = facts.law_enforcement_notified
    filing["materiality_claimed_immaterial"] = facts.materiality_claimed_immaterial
    filing["materiality_still_assessing"] = facts.materiality_still_assessing
    filing["ransom_explicitly_not_paid"] = facts.ransom_explicitly_not_paid
    filing["operations_disrupted"] = facts.operations_disrupted
    filing["severity_hint"] = facts.severity_hint
    filing["body_sample"] = facts.body_sample
    return filing


# ─────────────────────────── cache ───────────────────────────


def load_cache(cache_path: Path) -> dict[str, dict]:
    if not cache_path.exists():
        return {}
    try:
        return json.loads(cache_path.read_text())
    except Exception:
        return {}


def save_cache(cache_path: Path, cache: dict[str, dict]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=2))


def merge_new_filings(cache: dict[str, dict],
                      fresh: list[dict]) -> tuple[list[dict], list[dict]]:
    """Merge `fresh` into `cache` (mutates cache). Returns
    (merged_list, newly_added_list)."""
    new: list[dict] = []
    for f in fresh:
        key = f.get("accession_no", "")
        if not key:
            continue
        if key not in cache:
            new.append(f)
        cache[key] = f
    # Merged list sorted newest first
    merged = sorted(
        cache.values(),
        key=lambda f: f.get("filed_at", ""),
        reverse=True,
    )
    return merged, new
