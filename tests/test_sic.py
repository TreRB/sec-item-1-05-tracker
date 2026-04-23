"""Tests for SIC code lookup."""
from __future__ import annotations

from sec_item_1_05_tracker.sic import SIC_LABELS, sic_label, sic_sector


def test_sic_label_known_software():
    assert sic_label("7372") == "Services - Prepackaged Software"


def test_sic_label_known_hospital():
    assert sic_label("8060") == "Services - Hospitals"
    assert sic_label("8062") == "Services - General Medical & Surgical Hospitals"


def test_sic_label_known_banking():
    assert sic_label("6020") == "State Commercial Banks"
    assert sic_label("6021") == "National Commercial Banks"


def test_sic_label_aerospace_defense():
    """Defense / DIB SIC codes used for CMMC targeting."""
    assert "Aircraft" in sic_label("3721")
    assert "Guided Missiles" in sic_label("3760")


def test_sic_label_unknown_returns_empty():
    assert sic_label("") == ""
    assert sic_label("9999") == ""


def test_sic_label_strips_whitespace():
    assert sic_label("  7372  ") == "Services - Prepackaged Software"


def test_sic_sector_manufacturing():
    assert sic_sector("3711") == "Manufacturing"
    assert sic_sector("3841") == "Manufacturing"


def test_sic_sector_services():
    assert sic_sector("7372") == "Services"
    assert sic_sector("8060") == "Services"


def test_sic_sector_finance():
    assert sic_sector("6020") == "Finance, Insurance & Real Estate"


def test_sic_sector_transportation():
    assert sic_sector("4911") == "Transportation & Utilities"


def test_sic_sector_unknown_returns_empty():
    assert sic_sector("") == ""
    assert sic_sector("abc") == ""


def test_sic_labels_covers_key_industries():
    """Defensive: ensure the SIC table contains every industry we'd
    expect to see in Item 1.05 filings."""
    must_have = [
        "7372",  # prepackaged software
        "7371",  # computer programming
        "8060",  # hospitals
        "6020",  # banking
        "6311",  # life insurance
        "6321",  # accident/health insurance
        "3841",  # medical instruments
        "3711",  # motor vehicles
        "3721",  # aircraft
        "5411",  # grocery stores
        "5812",  # eating places
    ]
    for code in must_have:
        assert code in SIC_LABELS, f"missing SIC code in table: {code}"
