"""Tests for body parsing + incident fact extraction."""
from __future__ import annotations

from sec_item_1_05_tracker.body import (
    IncidentFacts,
    extract_facts,
    strip_html,
)


# ──────────── strip_html ────────────


def test_strip_html_drops_tags():
    assert strip_html("<p>hello</p>") == "hello"


def test_strip_html_normalizes_entities():
    assert "&" in strip_html("<p>A &amp; B</p>")
    assert "&amp;" not in strip_html("<p>A &amp; B</p>")


def test_strip_html_paragraph_becomes_newline():
    text = strip_html("<p>a</p><p>b</p>")
    assert "a" in text and "b" in text
    assert "ab" not in text  # separated


# ──────────── extract_facts ────────────


def _body_ransomware() -> str:
    return """
    Item 1.05 Material Cybersecurity Incidents.
    On April 10 2026, the Company identified a ransomware attack on
    certain of its information technology systems. Files were encrypted
    and the threat actor demanded payment. The Company engaged a leading
    third-party cybersecurity firm and has notified the FBI and CISA.
    The Company did not pay a ransom. Certain systems were temporarily
    taken offline as a precautionary measure.
    """


def _body_data_access() -> str:
    return """
    Item 1.05 Material Cybersecurity Incidents.
    Unauthorized access occurred to the Company's environment. Personal
    information was accessed. The investigation is in early stages.
    The Company does not currently believe the incident will have a
    material impact on its financial condition.
    """


def _body_contained() -> str:
    return """
    The incident has been contained. The Company continues to assess the
    potential impact. No evidence of active threat-actor access remains.
    """


def test_facts_ransomware_body_positive():
    f = extract_facts(_body_ransomware())
    assert f.has_item_1_05_section
    assert f.mentions_ransomware
    assert f.forensic_firm_engaged
    assert f.law_enforcement_notified
    assert f.ransom_explicitly_not_paid
    assert f.operations_disrupted


def test_facts_data_access_body():
    f = extract_facts(_body_data_access())
    assert f.has_item_1_05_section
    assert f.mentions_data_access
    assert f.still_investigating
    assert f.materiality_claimed_immaterial
    assert not f.mentions_ransomware


def test_facts_contained_body():
    f = extract_facts(_body_contained())
    assert f.incident_contained
    assert f.materiality_still_assessing


def test_facts_empty_body_has_all_false():
    f = extract_facts("")
    assert not f.has_item_1_05_section
    assert not f.mentions_ransomware
    assert not f.mentions_data_access
    assert f.body_length == 0


def test_facts_body_without_item_section_falls_back_to_full_body():
    """When the Item 1.05 header isn't found, we still scan the whole
    body for the signal patterns."""
    text = (
        "Form 8-K Current Report. We experienced a ransomware attack "
        "on our systems."
    )
    f = extract_facts(text)
    assert not f.has_item_1_05_section
    assert f.mentions_ransomware


def test_severity_hint_high_when_multiple_signals():
    body = (
        "Item 1.05. The ransomware attack encrypted data and "
        "certain systems were temporarily taken offline. "
        "Personal information was accessed."
    )
    f = extract_facts(body)
    assert f.severity_hint == "high"


def test_severity_hint_medium_when_one_signal():
    body = "Item 1.05. Unauthorized access occurred to the network."
    f = extract_facts(body)
    assert f.severity_hint == "medium"


def test_severity_hint_low_when_no_signals():
    body = (
        "Item 1.05. The Company identified suspicious activity. "
        "The investigation is ongoing."
    )
    f = extract_facts(body)
    assert f.severity_hint == "low"


def test_body_sample_capped():
    long_body = "Item 1.05. " + ("a" * 5000)
    f = extract_facts(long_body)
    assert len(f.body_sample) <= 1200
