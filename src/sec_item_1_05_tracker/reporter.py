"""Output formats: JSON, RSS, CSV, HTML dashboard, Slack/Discord webhooks."""
from __future__ import annotations

import csv
import datetime
import html as ihtml
import io
import json
import xml.sax.saxutils as xsu
from pathlib import Path
from typing import Optional
from urllib import request


# ────────────────────────── JSON + Latest ──────────────────────────


def write_json_feed(filings: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(filings, indent=2))


def write_latest(filings: list[dict], output_path: Path, n: int = 20) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(filings[:n], indent=2))


# ────────────────────────── CSV ──────────────────────────


CSV_FIELDS = [
    "filed_at", "period", "company_name", "ticker", "cik",
    "form", "sic", "sic_label", "sector",
    "hq_state", "inc_state", "accession_no", "filing_url",
    "items",
    # Body-derived fields (populated only when --fetch-bodies was used)
    "mentions_ransomware", "mentions_data_access", "incident_contained",
    "forensic_firm_engaged", "law_enforcement_notified",
    "materiality_claimed_immaterial", "materiality_still_assessing",
    "operations_disrupted", "severity_hint",
]


def write_csv(filings: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in filings:
            r = dict(row)
            # Flatten list → comma-separated string
            if isinstance(r.get("items"), list):
                r["items"] = ",".join(r["items"])
            writer.writerow(r)


# ────────────────────────── RSS 2.0 ──────────────────────────


def rss_document(filings: list[dict], max_items: int = 100) -> str:
    items_xml = "\n".join(_rss_item(f) for f in filings[:max_items])
    now_rfc = datetime.datetime.now(datetime.timezone.utc).strftime(
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
  <generator>sec-item-1-05-tracker/0.2</generator>
{items_xml}
</channel>
</rss>
"""


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
    if f.get("severity_hint"):
        desc_parts.append(f"Severity hint: {f['severity_hint']}")
    desc_parts.append(f"Filed: {f.get('filed_at','')}")
    desc = xsu.escape(". ".join(desc_parts) + ".")
    guid = xsu.escape(f.get("accession_no", ""))
    pub_date = f.get("filed_at", "")
    try:
        dt = datetime.datetime.strptime(pub_date, "%Y-%m-%d").replace(
            tzinfo=datetime.timezone.utc
        )
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


# ────────────────────────── HTML dashboard ──────────────────────────


def html_dashboard(filings: list[dict], max_items: int = 200) -> str:
    """Single-file HTML dashboard. No JS, filter-on-page-load only.
    Drop this at /feed.html and it's a read-only incident tracker."""
    rows_html = "\n".join(_html_row(f) for f in filings[:max_items])
    n = min(len(filings), max_items)
    generated = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )
    css = """
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           margin: 2em; background: #0a0a0a; color: #e5e5e5; }
    h1 { color: #f59e0b; }
    table { width: 100%; border-collapse: collapse; margin-top: 1em;
            font-size: 14px; }
    th, td { padding: 8px 12px; text-align: left;
             border-bottom: 1px solid #222; }
    th { background: #141414; color: #f59e0b; }
    tr:hover { background: #141414; }
    a { color: #60a5fa; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .sev-high { color: #ef4444; font-weight: 600; }
    .sev-medium { color: #f59e0b; }
    .sev-low { color: #94a3b8; }
    .filed { color: #94a3b8; font-size: 13px; white-space: nowrap; }
    .ticker { color: #10b981; font-weight: 600; }
    .form-a { color: #a855f7; }
    footer { color: #666; margin-top: 2em; font-size: 12px; }
    """.strip()
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>SEC 8-K Item 1.05 — Incident Feed</title>
<style>{css}</style>
</head>
<body>
<h1>SEC Form 8-K Item 1.05 — Material Cybersecurity Incidents</h1>
<p>Last {n} filings, newest first. Generated {generated} by
<a href="https://github.com/TreRB/sec-item-1-05-tracker">sec-item-1-05-tracker</a>.</p>
<table>
<thead><tr>
  <th>Filed</th><th>Company</th><th>Ticker</th><th>Form</th>
  <th>Industry</th><th>HQ</th><th>Severity hint</th>
</tr></thead>
<tbody>
{rows_html}
</tbody>
</table>
<footer>
Pulled from <a href="https://efts.sec.gov/LATEST/search-index?q=%22Item+1.05%22&forms=8-K">EDGAR full-text search</a>.
Data is public. Built by <a href="https://valtikstudios.com">Valtik Studios</a>.
</footer>
</body>
</html>
"""


def _html_row(f: dict) -> str:
    sev = f.get("severity_hint") or ""
    sev_class = f"sev-{sev}" if sev else ""
    form = (f.get("form") or "").strip()
    form_class = "form-a" if form.endswith("/A") else ""
    company = ihtml.escape(f.get("company_name", "?"))
    ticker = ihtml.escape(f.get("ticker", ""))
    sic_label = ihtml.escape(f.get("sic_label", ""))
    hq_state = ihtml.escape(f.get("hq_state", ""))
    filed = ihtml.escape(f.get("filed_at", ""))
    link = ihtml.escape(f.get("filing_url", ""))
    return f"""<tr>
  <td class="filed">{filed}</td>
  <td><a href="{link}" target="_blank" rel="noopener">{company}</a></td>
  <td class="ticker">{ticker}</td>
  <td class="{form_class}">{form}</td>
  <td>{sic_label}</td>
  <td>{hq_state}</td>
  <td class="{sev_class}">{sev}</td>
</tr>"""


# ────────────────────────── Webhook (Slack / Discord) ──────────────────────────


def slack_blocks(filings: list[dict]) -> dict:
    """Format up to 10 new filings as Slack Block Kit payload."""
    items = filings[:10]
    blocks = [{
        "type": "header",
        "text": {"type": "plain_text",
                 "text": f"{len(items)} new SEC 8-K Item 1.05 filing(s)"}
    }]
    for f in items:
        sev = f.get("severity_hint", "")
        sev_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(sev, "⚪")
        title = f"{sev_emoji} *{f.get('company_name','?')}*"
        if f.get("ticker"):
            title += f" (`{f['ticker']}`)"
        body_lines = [title]
        if f.get("filed_at"):
            body_lines.append(f"Filed {f['filed_at']} · {f.get('form','8-K')}")
        if f.get("sic_label"):
            body_lines.append(f"{f['sic_label']}")
        url = f.get("filing_url", "")
        if url:
            body_lines.append(f"<{url}|Filing on EDGAR>")
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(body_lines)},
        })
    return {"blocks": blocks}


def discord_payload(filings: list[dict]) -> dict:
    """Discord webhook payload for up to 10 filings."""
    items = filings[:10]
    embeds = []
    for f in items:
        sev = f.get("severity_hint", "low")
        color = {"high": 0xef4444, "medium": 0xf59e0b, "low": 0x94a3b8}.get(sev, 0x6b7280)
        fields = []
        if f.get("ticker"):
            fields.append({"name": "Ticker", "value": f["ticker"], "inline": True})
        if f.get("filed_at"):
            fields.append({"name": "Filed", "value": f["filed_at"], "inline": True})
        if f.get("sic_label"):
            fields.append({"name": "Industry", "value": f["sic_label"], "inline": False})
        embeds.append({
            "title": f.get("company_name", "?"),
            "url": f.get("filing_url", ""),
            "color": color,
            "fields": fields,
            "footer": {"text": f.get("form", "8-K")},
        })
    return {
        "username": "SEC 8-K Tracker",
        "content": f"{len(items)} new Item 1.05 filing(s)",
        "embeds": embeds,
    }


def post_webhook(url: str, payload: dict, timeout: int = 10) -> int:
    """POST a webhook payload to Slack or Discord. Returns HTTP status."""
    body = json.dumps(payload).encode()
    req = request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "User-Agent": "sec-item-1-05-tracker/0.2",
    })
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except Exception:
        return 0


def detect_webhook_kind(url: str) -> str:
    """Infer 'slack' or 'discord' from a webhook URL."""
    u = (url or "").lower()
    if "hooks.slack.com" in u:
        return "slack"
    if "discord" in u:
        return "discord"
    return "slack"  # default
