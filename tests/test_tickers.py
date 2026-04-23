"""Tests for CIK→ticker lookup."""
from __future__ import annotations

import json
from pathlib import Path

from sec_item_1_05_tracker.tickers import (
    fetch_tickers,
    lookup_ticker,
    lookup_title,
)


def test_lookup_ticker_padded_cik():
    """CIK lookup should zero-pad to 10 chars for lookup."""
    idx = {"0000320193": {"ticker": "AAPL", "title": "Apple Inc."}}
    assert lookup_ticker("320193", idx) == "AAPL"
    assert lookup_ticker("0000320193", idx) == "AAPL"


def test_lookup_ticker_missing_cik():
    assert lookup_ticker("9999999999", {"0000320193": {"ticker": "AAPL"}}) == ""


def test_lookup_ticker_no_index():
    assert lookup_ticker("320193", None) == ""
    assert lookup_ticker("320193", {}) == ""


def test_lookup_title():
    idx = {"0000320193": {"ticker": "AAPL", "title": "Apple Inc."}}
    assert lookup_title("320193", idx) == "Apple Inc."


def test_lookup_title_missing():
    assert lookup_title("9999", {}) == ""


def test_fetch_tickers_uses_cache_when_present(tmp_path: Path):
    cache = tmp_path / "cache.json"
    cached = {"0000000001": {"ticker": "TEST", "title": "Test Inc"}}
    cache.write_text(json.dumps(cached))
    loaded = fetch_tickers(cache_path=cache, force=False)
    assert loaded == cached


def test_fetch_tickers_cache_corrupt_falls_through(tmp_path: Path, monkeypatch):
    """If cache JSON is corrupt, we should fall through to network (which
    we mock out to avoid actual SEC call)."""
    from sec_item_1_05_tracker import tickers as tmod

    cache = tmp_path / "cache.json"
    cache.write_text("{not valid json")

    canned_response = '{"0":{"cik_str":320193,"ticker":"AAPL","title":"Apple Inc."}}'

    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return canned_response.encode()

    def fake_urlopen(req, timeout=15):
        return FakeResp()

    monkeypatch.setattr(tmod.request, "urlopen", fake_urlopen)
    loaded = fetch_tickers(cache_path=cache)
    assert "0000320193" in loaded
    assert loaded["0000320193"]["ticker"] == "AAPL"
