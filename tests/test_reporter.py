"""Tests for output formatters."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from sec_item_1_05_tracker.reporter import (
    CSV_FIELDS,
    detect_webhook_kind,
    discord_payload,
    html_dashboard,
    rss_document,
    slack_blocks,
    write_csv,
    write_json_feed,
    write_latest,
)


def _sample_filings() -> list[dict]:
    return [
        {
            "cik": "0000310764",
            "company_name": "Stryker Corp",
            "ticker": "SYK",
            "sic": "3841",
            "sic_label": "Surgical & Medical Instruments",
            "sector": "Manufacturing",
            "filed_at": "2026-04-09",
            "period": "2026-03-11",
            "accession_no": "0001193125-26-149607",
            "form": "8-K/A",
            "items": ["1.05", "7.01"],
            "inc_state": "MI",
            "hq_state": "MI",
            "filing_url": "https://www.sec.gov/Archives/edgar/data/310764/000119312526149607/0001193125-26-149607-index.htm",
            "first_seen": "2026-04-23T21:00:00Z",
            "mentions_ransomware": True,
            "mentions_data_access": True,
            "severity_hint": "high",
        },
        {
            "cik": "0000123456",
            "company_name": "Example Corp",
            "ticker": "EXMP",
            "sic": "7372",
            "sic_label": "Services - Prepackaged Software",
            "sector": "Services",
            "filed_at": "2026-04-15",
            "period": "2026-04-11",
            "accession_no": "0001111111-26-222222",
            "form": "8-K",
            "items": ["1.05"],
            "inc_state": "DE",
            "hq_state": "CA",
            "filing_url": "https://www.sec.gov/Archives/edgar/data/123456/x/x-index.htm",
            "first_seen": "2026-04-23T22:00:00Z",
            "severity_hint": "low",
        },
    ]


# ────────────────── JSON / latest ──────────────────


def test_write_json_feed(tmp_path: Path):
    p = tmp_path / "feed.json"
    write_json_feed(_sample_filings(), p)
    data = json.loads(p.read_text())
    assert len(data) == 2
    assert data[0]["company_name"] == "Stryker Corp"


def test_write_latest_trims(tmp_path: Path):
    p = tmp_path / "latest.json"
    write_latest(_sample_filings(), p, n=1)
    data = json.loads(p.read_text())
    assert len(data) == 1


def test_write_latest_creates_parent_dirs(tmp_path: Path):
    p = tmp_path / "nested" / "x" / "latest.json"
    write_latest(_sample_filings(), p, n=5)
    assert p.exists()


# ────────────────── RSS ──────────────────


def test_rss_document_valid_xml_and_items():
    rss = rss_document(_sample_filings())
    assert rss.startswith("<?xml")
    assert "<rss version=\"2.0\">" in rss
    assert "<title>" in rss
    assert "Stryker Corp" in rss
    assert "SYK" in rss


def test_rss_cap_max_items():
    rss = rss_document(_sample_filings(), max_items=1)
    # Count occurrences of <item> — only 1
    assert rss.count("<item>") == 1


def test_rss_includes_severity_hint():
    rss = rss_document(_sample_filings())
    assert "Severity hint: high" in rss


# ────────────────── CSV ──────────────────


def test_write_csv_header_and_rows(tmp_path: Path):
    p = tmp_path / "feed.csv"
    write_csv(_sample_filings(), p)
    rows = list(csv.DictReader(p.open()))
    assert len(rows) == 2
    assert rows[0]["company_name"] == "Stryker Corp"
    assert rows[0]["ticker"] == "SYK"
    assert rows[0]["items"] == "1.05,7.01"  # list flattened


def test_write_csv_fields_includes_body_columns():
    """Body-derived columns must be in the CSV schema so partial data
    doesn't break the header."""
    for col in ("mentions_ransomware", "severity_hint",
                "incident_contained", "forensic_firm_engaged"):
        assert col in CSV_FIELDS


def test_write_csv_handles_missing_body_fields(tmp_path: Path):
    """Filings that didn't go through body enrichment shouldn't break CSV."""
    minimal = [{"filed_at": "2026-04-01", "company_name": "X",
                "accession_no": "a"}]
    p = tmp_path / "feed.csv"
    write_csv(minimal, p)
    rows = list(csv.DictReader(p.open()))
    assert len(rows) == 1
    assert rows[0]["company_name"] == "X"
    assert rows[0]["mentions_ransomware"] == ""


# ────────────────── HTML dashboard ──────────────────


def test_html_dashboard_shape():
    html = html_dashboard(_sample_filings())
    assert "<!doctype html>" in html
    assert "<title>SEC 8-K Item 1.05" in html
    assert "Stryker Corp" in html
    assert "SYK" in html
    assert "sec-item-1-05-tracker" in html


def test_html_dashboard_severity_class():
    html = html_dashboard(_sample_filings())
    assert "sev-high" in html
    assert "sev-low" in html


def test_html_dashboard_amendment_class():
    """8-K/A forms should get a distinct CSS class."""
    html = html_dashboard(_sample_filings())
    assert "form-a" in html


def test_html_dashboard_max_items_cap():
    html = html_dashboard(_sample_filings(), max_items=1)
    # Only one <tr> row in <tbody>
    body_start = html.index("<tbody>")
    body_end = html.index("</tbody>")
    body = html[body_start:body_end]
    assert body.count("<tr>") == 1


# ────────────────── Webhooks ──────────────────


def test_slack_blocks_structure():
    payload = slack_blocks(_sample_filings())
    assert "blocks" in payload
    # Header + 2 section blocks
    assert len(payload["blocks"]) == 3
    assert payload["blocks"][0]["type"] == "header"


def test_slack_blocks_severity_emoji():
    payload = slack_blocks(_sample_filings())
    stryker_text = payload["blocks"][1]["text"]["text"]
    assert "🔴" in stryker_text  # high-severity emoji


def test_slack_blocks_filing_link():
    payload = slack_blocks(_sample_filings())
    text = payload["blocks"][1]["text"]["text"]
    assert "<https://www.sec.gov/" in text
    assert "|Filing on EDGAR>" in text


def test_slack_blocks_cap_at_10():
    many = _sample_filings() * 10  # 20 items
    payload = slack_blocks(many)
    assert len(payload["blocks"]) == 11  # header + 10


def test_discord_payload_structure():
    payload = discord_payload(_sample_filings())
    assert "embeds" in payload
    assert len(payload["embeds"]) == 2
    assert payload["embeds"][0]["title"] == "Stryker Corp"
    assert payload["embeds"][0]["url"].startswith("https://")


def test_discord_severity_color():
    """High severity = red; low = gray."""
    payload = discord_payload(_sample_filings())
    stryker = next(e for e in payload["embeds"]
                   if e["title"] == "Stryker Corp")
    example = next(e for e in payload["embeds"]
                   if e["title"] == "Example Corp")
    assert stryker["color"] == 0xef4444  # red
    assert example["color"] == 0x94a3b8  # gray


def test_detect_webhook_kind_slack():
    assert detect_webhook_kind("https://hooks.slack.com/services/T00/B00/XX") == "slack"


def test_detect_webhook_kind_discord():
    assert detect_webhook_kind("https://discord.com/api/webhooks/123/xx") == "discord"
    assert detect_webhook_kind("https://discordapp.com/api/webhooks/123/xx") == "discord"


def test_detect_webhook_kind_default_slack_for_unknown():
    assert detect_webhook_kind("https://example.com/wh") == "slack"
