"""Filing family de-dup + amendment chains.

One cybersecurity incident often produces multiple 8-K filings over
time: the initial 8-K, then one or more 8-K/A amendments as scope is
better understood. For most downstream analysis you want to treat the
chain as a single logical entity with a timeline.

We group by (CIK, original accession-family). Amendments reference the
original via the accession number's common prefix (`0001193125-26-123456`
and its amendment will share a numeric root but get a fresh accession).
Since the reference link is inside the filing body and not always in
the FTS metadata, we use a heuristic: same CIK + same SEC filing date
window + same or adjacent period-of-report.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class Family:
    """A chain of one initial 8-K plus zero or more 8-K/A amendments
    about the same incident."""
    key: str
    cik: str
    company_name: str
    ticker: str = ""
    sic: str = ""
    sic_label: str = ""
    hq_state: str = ""
    initial: dict = field(default_factory=dict)
    amendments: list[dict] = field(default_factory=list)

    @property
    def first_filed(self) -> str:
        return self.initial.get("filed_at", "") if self.initial else ""

    @property
    def last_filed(self) -> str:
        if self.amendments:
            return max(a.get("filed_at", "") for a in self.amendments)
        return self.first_filed

    @property
    def filing_count(self) -> int:
        return (1 if self.initial else 0) + len(self.amendments)


def _group_key(filing: dict) -> str:
    """Synthetic key for grouping filings about the same incident.
    Groups by CIK + the 'period' (reporting period). If period isn't
    set, falls back to CIK + file date rounded to nearest month."""
    cik = (filing.get("cik", "") or "").zfill(10)
    period = filing.get("period", "")
    if period:
        return f"{cik}:{period}"
    filed_at = filing.get("filed_at", "")
    # Fall back to filing month
    month = filed_at[:7] if filed_at else "unknown"
    return f"{cik}:{month}"


def group_by_family(filings: list[dict]) -> list[Family]:
    """Given a list of individual 8-K filings, group them into families.

    Algorithm:
    1. Sort by filed_at ascending so initial 8-Ks come before
       amendments.
    2. Bucket by _group_key.
    3. Within each bucket, the first record (earliest filed_at, form=8-K)
       is the initial; subsequent records are amendments.
    """
    # Sort ascending by file date so the initial 8-K appears first
    sorted_filings = sorted(
        filings,
        key=lambda f: (f.get("filed_at", ""), f.get("accession_no", "")),
    )

    buckets: dict[str, list[dict]] = defaultdict(list)
    for f in sorted_filings:
        buckets[_group_key(f)].append(f)

    families: list[Family] = []
    for key, items in buckets.items():
        initial = None
        amendments: list[dict] = []
        for f in items:
            form = (f.get("form") or "").upper()
            if initial is None and not form.endswith("/A"):
                initial = f
            else:
                amendments.append(f)
        # Edge case: only amendments, no initial (happens when the scrape
        # window missed the initial). Treat earliest as the "initial".
        if initial is None and items:
            initial = items[0]
            amendments = items[1:]

        cik = (initial.get("cik") or "").zfill(10) if initial else ""
        families.append(Family(
            key=key,
            cik=cik,
            company_name=(initial or {}).get("company_name", ""),
            ticker=(initial or {}).get("ticker", ""),
            sic=(initial or {}).get("sic", ""),
            sic_label=(initial or {}).get("sic_label", ""),
            hq_state=(initial or {}).get("hq_state", ""),
            initial=initial or {},
            amendments=amendments,
        ))

    return families
