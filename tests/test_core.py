"""Unit tests for core EDGAR-processing logic."""
from __future__ import annotations

import json
from pathlib import Path

from sec_item_1_05_tracker.core import (
    enrich_filing,
    filter_item_1_05,
    load_cache,
    merge_new_filings,
    save_cache,
)


def test_filter_keeps_items_with_1_05():
    hits = [
        {"_source": {"items": ["1.05", "7.01"]}},
        {"_source": {"items": ["2.02"]}},
        {"_source": {"items": ["Item 1.05"]}},
    ]
    assert len(filter_item_1_05(hits)) == 2


def test_filter_drops_empty():
    assert filter_item_1_05([{"_source": {}}]) == []


def test_enrich_parses_display_name():
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
    assert f["sic_label"] == "Services - Prepackaged Software"
    assert f["sector"] == "Services"
    assert "edgar/data/1234567" in f["filing_url"]


def test_enrich_uses_tickers_index_fallback():
    """When display_name doesn't include a ticker, fall back to the
    SEC company_tickers.json lookup."""
    tickers = {"0001234567": {"ticker": "EXMP", "title": "Example Corp"}}
    hit = {
        "_id": "0001193125-26-999999",
        "_source": {
            "display_names": ["EXAMPLE CORP  (CIK 0001234567)"],  # no ticker
            "ciks": ["0001234567"],
            "sics": ["7372"],
            "file_date": "2026-04-15",
            "form": "8-K",
            "items": ["1.05"],
        },
    }
    f = enrich_filing(hit, tickers_index=tickers)
    assert f["ticker"] == "EXMP"


def test_enrich_strips_colon_suffix_from_accession():
    """EDGAR _id is sometimes '0001193125-26-123456:primary_doc.htm';
    we want just the accession part."""
    hit = {
        "_id": "0001193125-26-149607:d112875d8ka.htm",
        "_source": {
            "display_names": ["STRYKER CORP  (SYK)  (CIK 0000310764)"],
            "ciks": ["0000310764"],
            "sics": ["3841"],
            "file_date": "2026-04-09",
            "form": "8-K/A",
            "items": ["1.05"],
        },
    }
    f = enrich_filing(hit)
    assert f["accession_no"] == "0001193125-26-149607"
    # Only valid colon in URL should be after "https"
    assert f["filing_url"].count(":") == 1
    assert "/" + "0001193125-26-149607-index.htm" in f["filing_url"]


def test_enrich_missing_fields_graceful():
    f = enrich_filing({"_id": "", "_source": {}})
    assert f["company_name"] == ""
    assert f["filing_url"] == ""


def test_enrich_includes_sector():
    hit = {
        "_id": "x",
        "_source": {
            "display_names": ["ACME (CIK 0000000001)"],
            "ciks": ["0000000001"],
            "sics": ["8060"],
            "file_date": "2026-04-01",
            "form": "8-K",
            "items": ["1.05"],
        },
    }
    f = enrich_filing(hit)
    assert f["sic_label"] == "Services - Hospitals"
    assert f["sector"] == "Services"


def test_merge_new_filings_counts_new():
    cache = {"a": {"accession_no": "a", "filed_at": "2026-01-01"}}
    fresh = [
        {"accession_no": "a", "filed_at": "2026-01-01"},  # existing
        {"accession_no": "b", "filed_at": "2026-04-10"},  # new
        {"accession_no": "c", "filed_at": "2026-03-15"},  # new
    ]
    merged, new = merge_new_filings(cache, fresh)
    assert len(new) == 2
    assert {n["accession_no"] for n in new} == {"b", "c"}


def test_merge_new_filings_sorts_newest_first():
    cache = {}
    fresh = [
        {"accession_no": "a", "filed_at": "2026-01-15"},
        {"accession_no": "b", "filed_at": "2026-04-15"},
        {"accession_no": "c", "filed_at": "2026-02-20"},
    ]
    merged, _ = merge_new_filings(cache, fresh)
    assert [m["accession_no"] for m in merged] == ["b", "c", "a"]


def test_merge_skips_missing_accession():
    cache = {}
    _, new = merge_new_filings(cache, [{"accession_no": "", "filed_at": "2026-04-01"}])
    assert new == []
    assert cache == {}


def test_cache_roundtrip(tmp_path: Path):
    p = tmp_path / "cache.json"
    c = {"a": {"accession_no": "a", "filed_at": "2026-04-01"}}
    save_cache(p, c)
    assert load_cache(p) == c


def test_load_cache_missing_returns_empty(tmp_path: Path):
    assert load_cache(tmp_path / "no.json") == {}
