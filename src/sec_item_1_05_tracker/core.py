"""Core logic: poll EDGAR FTS, filter Item 1.05, enrich, write feeds."""
from __future__ import annotations

import json
import os
import re
import time
import xml.sax.saxutils as xsu
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib import parse, request

SEC_FTS_URL = "https://efts.sec.gov/LATEST/search-index"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
USER_AGENT = (
    "sec-item-1-05-tracker/0.1 (valtikstudios.com; tre@valtikstudios.com)"
)

# SEC requires a User-Agent that identifies the requester. Tools that
# skip this can get rate-limited or blocked.


# ─────────────────────────── SIC labels ────────────────────────────
# Partial SIC-to-label map covering the industries that show up most in
# Item 1.05 filings. Not exhaustive — if you need the full list, pull
# from the SEC Division of Corporation Finance SIC page.

SIC_LABELS: dict[str, str] = {
    "1311": "Crude Petroleum & Natural Gas",
    "2834": "Pharmaceutical Preparations",
    "3559": "Special Industry Machinery",
    "3674": "Semiconductors & Related Devices",
    "3711": "Motor Vehicles",
    "3721": "Aircraft",
    "3724": "Aircraft Engines & Engine Parts",
    "3728": "Aircraft Parts & Auxiliary Equipment",
    "3812": "Search, Detection, Navigation, Guidance",
    "3841": "Surgical & Medical Instruments",
    "4911": "Electric Services",
    "4931": "Electric & Other Services Combined",
    "4953": "Refuse Systems",
    "5200": "Retail Stores, Home Furniture & Equipment",
    "5411": "Grocery Stores",
    "5734": "Computer & Computer Software Stores",
    "5812": "Eating Places",
    "5912": "Drug Stores & Proprietary Stores",
    "5961": "Catalog, Mail-Order Houses",
    "6020": "State Commercial Banks",
    "6022": "State Commercial Banks",
    "6199": "Finance Services",
    "6211": "Security Brokers, Dealers & Flotation Companies",
    "6311": "Life Insurance",
    "6321": "Accident & Health Insurance",
    "6331": "Fire, Marine & Casualty Insurance",
    "6770": "Blank Checks",
    "7370": "Services-Computer Services",
    "7371": "Services-Computer Programming",
    "7372": "Services-Prepackaged Software",
    "7389": "Services-Business Services, NEC",
    "7990": "Services-Amusement & Recreation Services",
    "8000": "Services-Health Services",
    "8011": "Services-Offices of Doctors of Medicine",
    "8060": "Services-Hospitals",
    "8071": "Services-Medical Laboratories",
    "8090": "Services-Health Services, NEC",
    "8711": "Services-Engineering Services",
}


def sic_label(sic: str) -> str:
    return SIC_LABELS.get(sic or "", "")


# ─────────────────────────── HTTP ────────────────────────────


def _get_json(url: str, timeout: int = 15) -> Optional[dict]:
    req = request.Request(url, headers={"User-Agent": USER_AGENT,
                                        "Accept": "application/json"})
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


# ─────────────────────────── EDGAR fetch ────────────────────────────


def fetch_filings(since: datetime, until: datetime,
                  include_amendments: bool = True,
                  max_results: int = 1000,
                  verbose: bool = False) -> list[dict]:
    """Pull all Item 1.05 filings from EDGAR FTS between since and until."""
    date_from = since.strftime("%Y-%m-%d")
    date_to = until.strftime("%Y-%m-%d")
    forms = "8-K,8-K/A" if include_amendments else "8-K"
    params = {
        "q": '"Item 1.05"',
        "dateRange": "custom",
        "startdt": date_from,
        "enddt": date_to,
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
        time.sleep(0.15)  # SEC rate courtesy
    return hits


# ─────────────────────────── filter + normalize ────────────────────────────


def filter_item_1_05(raw_hits: Iterable[dict]) -> list[dict]:
    """Keep only filings that really have Item 1.05 in the items field."""
    out = []
    for h in raw_hits:
        src = h.get("_source", {})
        items = src.get("items", []) or []
        # EDGAR stores items as list of strings. Check both exact and
        # prefix matches because some filings write "1.05"/"Item 1.05".
        if not any("1.05" in str(i) for i in items):
            continue
        out.append(h)
    return out


def enrich_filing(hit: dict) -> dict:
    """Map one EDGAR hit → normalized filing record."""
    src = hit.get("_source", {})
    # EDGAR _id format: "0001193125-26-149607:primary_doc.htm" — keep only
    # the accession number (before the colon).
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
    # Clean company name
    company_name = re.sub(r"\s*\(.*", "", display_name).strip()

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

    # Filing URL: Archives/edgar/data/<cik>/<accession-no-dashes>/<adsh>-index.htm
    if adsh and cik:
        adsh_nodash = adsh.replace("-", "")
        filing_url = (
            f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
            f"&CIK={cik}&type=8-K&dateb=&owner=include&count=40"
        )
        # Prefer the direct archive index
        filing_url = (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{int(cik)}/{adsh_nodash}/{adsh}-index.htm"
        )
    else:
        filing_url = ""

    return {
        "cik": cik.zfill(10) if cik.isdigit() else cik,
        "company_name": company_name,
        "ticker": ticker,
        "sic": sic,
        "sic_label": sic_label(sic),
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


# ─────────────────────────── feed output ────────────────────────────


def _rss_item(f: dict) -> str:
    title = xsu.escape(f"{f.get('company_name','?')} — 8-K Item 1.05")
    link = xsu.escape(f.get("filing_url", ""))
    desc_parts = []
    if f.get("ticker"):
        desc_parts.append(f"Ticker: {f['ticker']}")
    if f.get("sic_label"):
        desc_parts.append(f"Industry: {f['sic_label']}")
    if f.get("hq_state"):
        desc_parts.append(f"HQ: {f['hq_state']}")
    if f.get("form"):
        desc_parts.append(f"Form: {f['form']}")
    desc_parts.append(f"Filed: {f.get('filed_at','')}")
    desc = xsu.escape(". ".join(desc_parts) + ".")
    guid = xsu.escape(f.get("accession_no", ""))
    pub_date = f.get("filed_at", "")
    # RFC 822 date
    try:
        dt = datetime.strptime(pub_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        pub_date_rfc = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
    except Exception:
        pub_date_rfc = ""
    return (
        f"<item>\n"
        f"  <title>{title}</title>\n"
        f"  <link>{link}</link>\n"
        f"  <description>{desc}</description>\n"
        f"  <guid isPermaLink=\"false\">{guid}</guid>\n"
        f"  <pubDate>{pub_date_rfc}</pubDate>\n"
        f"</item>"
    )


def _rss_document(filings: list[dict], max_items: int = 100) -> str:
    items_xml = "\n".join(_rss_item(f) for f in filings[:max_items])
    now_rfc = datetime.now(timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S +0000"
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>SEC Form 8-K Item 1.05 Filings Tracker</title>
  <link>https://github.com/TreRB/sec-item-1-05-tracker</link>
  <description>Every SEC Form 8-K Item 1.05 (Material Cybersecurity Incident) filing, as it lands on EDGAR. Maintained by Valtik Studios.</description>
  <language>en-us</language>
  <lastBuildDate>{now_rfc}</lastBuildDate>
  <generator>sec-item-1-05-tracker/0.1</generator>
{items_xml}
</channel>
</rss>
"""


def write_feeds(filings: list[dict], output_dir: Path,
                json_only: bool = False, rss_only: bool = False,
                latest_n: int = 20) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    # Sort newest first
    sorted_filings = sorted(
        filings, key=lambda f: f.get("filed_at", ""), reverse=True
    )

    if not rss_only:
        (output_dir / "feed.json").write_text(
            json.dumps(sorted_filings, indent=2)
        )
        (output_dir / "latest.json").write_text(
            json.dumps(sorted_filings[:latest_n], indent=2)
        )

    if not json_only:
        (output_dir / "feed.rss").write_text(_rss_document(sorted_filings))


# ─────────────────────────── cache ────────────────────────────


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
                      fresh: list[dict]) -> tuple[list[dict], int]:
    """Merge fresh filings into cache. Returns (merged list, new count)."""
    new = 0
    for f in fresh:
        key = f.get("accession_no", "")
        if not key:
            continue
        if key not in cache:
            new += 1
        cache[key] = f
    merged = list(cache.values())
    return merged, new
