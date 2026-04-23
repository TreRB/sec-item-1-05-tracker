"""Tests for filing-family grouping (8-K + 8-K/A amendment chains)."""
from __future__ import annotations

from sec_item_1_05_tracker.family import group_by_family


def _filing(cik, accession, form, filed_at, period="",
            company="ACME CORP") -> dict:
    return {
        "cik": cik,
        "accession_no": accession,
        "form": form,
        "filed_at": filed_at,
        "period": period,
        "company_name": company,
        "sic": "7372",
        "sic_label": "Services - Prepackaged Software",
        "hq_state": "CA",
    }


def test_single_initial_no_amendments():
    filings = [_filing("0000000001", "a", "8-K", "2026-04-01")]
    fams = group_by_family(filings)
    assert len(fams) == 1
    assert fams[0].filing_count == 1
    assert fams[0].amendments == []


def test_initial_plus_amendment_grouped():
    filings = [
        _filing("0000000001", "a", "8-K", "2026-04-01", period="2026-03-30"),
        _filing("0000000001", "a2", "8-K/A", "2026-05-15", period="2026-03-30"),
    ]
    fams = group_by_family(filings)
    assert len(fams) == 1
    assert fams[0].filing_count == 2
    assert len(fams[0].amendments) == 1
    assert fams[0].initial["form"] == "8-K"


def test_two_initials_separate_families():
    """Different period-of-report → different families."""
    filings = [
        _filing("0000000001", "a", "8-K", "2026-01-01", period="2025-12-30"),
        _filing("0000000001", "b", "8-K", "2026-04-01", period="2026-03-30"),
    ]
    fams = group_by_family(filings)
    assert len(fams) == 2


def test_two_different_ciks_separate_families():
    filings = [
        _filing("0000000001", "a", "8-K", "2026-04-01", period="2026-03-30"),
        _filing("0000000002", "b", "8-K", "2026-04-01", period="2026-03-30"),
    ]
    fams = group_by_family(filings)
    assert len(fams) == 2


def test_amendments_only_still_group():
    """Scrape might miss the initial filing — amendments-only should
    still group together using the earliest as 'initial'."""
    filings = [
        _filing("0000000001", "a2", "8-K/A", "2026-05-15",
                period="2026-03-30"),
        _filing("0000000001", "a3", "8-K/A", "2026-06-15",
                period="2026-03-30"),
    ]
    fams = group_by_family(filings)
    assert len(fams) == 1
    assert fams[0].filing_count == 2
    # Earliest becomes initial
    assert fams[0].initial["accession_no"] == "a2"


def test_family_properties_populated():
    filings = [
        _filing("0000000001", "a", "8-K", "2026-04-01", period="2026-03-30"),
        _filing("0000000001", "a2", "8-K/A", "2026-05-15", period="2026-03-30"),
    ]
    fams = group_by_family(filings)
    fam = fams[0]
    assert fam.cik == "0000000001"
    assert fam.company_name == "ACME CORP"
    assert fam.sic == "7372"
    assert fam.first_filed == "2026-04-01"
    assert fam.last_filed == "2026-05-15"


def test_fallback_group_key_when_no_period():
    """When period isn't set, group by file-month."""
    filings = [
        _filing("0000000001", "a", "8-K", "2026-04-05", period=""),
        _filing("0000000001", "a2", "8-K/A", "2026-04-25", period=""),
    ]
    fams = group_by_family(filings)
    assert len(fams) == 1


def test_sort_within_family_newest_initial_first():
    """Initial filing should be identified as the earliest 8-K (not /A)
    regardless of input order."""
    filings = [
        _filing("0000000001", "a2", "8-K/A", "2026-05-15", period="2026-03-30"),
        _filing("0000000001", "a", "8-K", "2026-04-01", period="2026-03-30"),
    ]
    fams = group_by_family(filings)
    assert fams[0].initial["accession_no"] == "a"
