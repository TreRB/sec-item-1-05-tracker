"""Unit tests that don't hit the network."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from sec_item_1_05_tracker.core import (
    enrich_filing,
    filter_item_1_05,
    load_cache,
    merge_new_filings,
    save_cache,
    sic_label,
    write_feeds,
)


def test_sic_label_known():
    assert sic_label("7372") == "Services-Prepackaged Software"
    assert sic_label("8060") == "Services-Hospitals"


def test_sic_label_unknown_returns_empty():
    assert sic_label("") == ""
    assert sic_label("9999") == ""


def test_filter_item_1_05_keeps_items_with_1_05():
    hits = [
        {"_source": {"items": ["1.05", "7.01"]}},
        {"_source": {"items": ["2.02"]}},
        {"_source": {"items": ["Item 1.05"]}},
    ]
    out = filter_item_1_05(hits)
    assert len(out) == 2


def test_filter_item_1_05_drops_when_no_items():
    hits = [{"_source": {}}]
    assert filter_item_1_05(hits) == []


def test_enrich_filing_parses_display_name():
    hit = {
        "_id": "0001193125-26-123456",
        "_source": {
            "display_names": ["EXAMPLE CORP  (EXMP)  (CIK 0001234567)"],
            "ciks": ["0001234567"],
            "sics": ["7372"],
            "file_date": "2026-04-15",
            "period_of_report": "2026-04-11",
            "form": "8-K",
            "file_type": "8-K",
            "items": ["1.05"],
            "inc_states": ["DE"],
            "biz_states": ["CA"],
        },
    }
    f = enrich_filing(hit)
    assert f["company_name"] == "EXAMPLE CORP"
    assert f["ticker"] == "EXMP"
    assert f["cik"] == "0001234567"
    assert f["sic"] == "7372"
    assert f["sic_label"] == "Services-Prepackaged Software"
    assert f["filed_at"] == "2026-04-15"
    assert f["inc_state"] == "DE"
    assert f["hq_state"] == "CA"
    assert "edgar/data/1234567" in f["filing_url"]


def test_enrich_filing_handles_missing_fields():
    hit = {"_id": "", "_source": {}}
    f = enrich_filing(hit)
    assert f["company_name"] == ""
    assert f["sic_label"] == ""
    assert f["filing_url"] == ""


def test_merge_new_filings_deduplicates():
    cache = {"a": {"accession_no": "a", "x": 1}}
    fresh = [
        {"accession_no": "a", "x": 2},  # update existing
        {"accession_no": "b", "x": 3},  # new
    ]
    merged, new = merge_new_filings(cache, fresh)
    assert new == 1
    assert cache["a"]["x"] == 2  # updated
    assert cache["b"]["x"] == 3


def test_merge_new_filings_skips_missing_accession():
    cache = {}
    fresh = [{"accession_no": "", "x": 1}]
    merged, new = merge_new_filings(cache, fresh)
    assert new == 0
    assert cache == {}


def test_cache_roundtrip(tmp_path: Path):
    p = tmp_path / "cache.json"
    c = {"a": {"accession_no": "a", "filed_at": "2026-04-15"}}
    save_cache(p, c)
    loaded = load_cache(p)
    assert loaded == c


def test_load_cache_missing_returns_empty(tmp_path: Path):
    assert load_cache(tmp_path / "nope.json") == {}


def test_write_feeds_writes_json_and_rss(tmp_path: Path):
    filings = [
        {
            "accession_no": "0001193125-26-123456",
            "company_name": "EXAMPLE CORP",
            "ticker": "EXMP",
            "sic": "7372",
            "sic_label": "Services-Prepackaged Software",
            "filed_at": "2026-04-15",
            "period": "2026-04-11",
            "form": "8-K",
            "items": ["1.05"],
            "inc_state": "DE",
            "hq_state": "CA",
            "filing_url": "https://www.sec.gov/Archives/edgar/data/123/x.htm",
            "first_seen": "2026-04-15T14:22:01Z",
        }
    ]
    write_feeds(filings, tmp_path)
    assert (tmp_path / "feed.json").exists()
    assert (tmp_path / "latest.json").exists()
    assert (tmp_path / "feed.rss").exists()
    feed = json.loads((tmp_path / "feed.json").read_text())
    assert feed[0]["company_name"] == "EXAMPLE CORP"
    rss = (tmp_path / "feed.rss").read_text()
    assert "EXAMPLE CORP" in rss
    assert "Item 1.05" in rss


def test_write_feeds_sort_newest_first(tmp_path: Path):
    filings = [
        {"accession_no": "a", "filed_at": "2026-01-01", "company_name": "A"},
        {"accession_no": "b", "filed_at": "2026-04-15", "company_name": "B"},
        {"accession_no": "c", "filed_at": "2026-02-20", "company_name": "C"},
    ]
    write_feeds(filings, tmp_path)
    feed = json.loads((tmp_path / "feed.json").read_text())
    assert [f["company_name"] for f in feed] == ["B", "C", "A"]


def test_write_feeds_json_only_skips_rss(tmp_path: Path):
    filings = [
        {"accession_no": "a", "filed_at": "2026-04-15", "company_name": "A"},
    ]
    write_feeds(filings, tmp_path, json_only=True)
    assert (tmp_path / "feed.json").exists()
    assert not (tmp_path / "feed.rss").exists()


def test_write_feeds_rss_only_skips_json(tmp_path: Path):
    filings = [
        {"accession_no": "a", "filed_at": "2026-04-15", "company_name": "A"},
    ]
    write_feeds(filings, tmp_path, rss_only=True)
    assert not (tmp_path / "feed.json").exists()
    assert (tmp_path / "feed.rss").exists()
