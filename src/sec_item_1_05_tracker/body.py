"""Filing body fetch + parse.

Downloads the primary filing document (usually a .htm file) from EDGAR
and extracts structured incident facts from the Item 1.05 narrative.
The EDGAR filing URL follows the pattern:
    https://www.sec.gov/Archives/edgar/data/<cik-no-leading-zeros>/<accession-no-dashes>/

Inside that directory live the submission exhibits. The primary doc is
usually indicated by `Filing Summary.xml` or is the first .htm that
isn't an index file.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional
from urllib import error, request


USER_AGENT = (
    "sec-item-1-05-tracker/0.2 (valtikstudios.com; tre@valtikstudios.com)"
)


# Detection regexes — looking for evidence of specific incident
# descriptors in the 8-K narrative. These are heuristics; false
# positives are acceptable because the tool's job is to surface the
# filing, not classify it definitively.

_RE_RANSOMWARE = re.compile(
    r"\b(ransomware|encrypt(ed)?\s+(files|data|systems)|"
    r"demanded\s+(payment|ransom))\b",
    re.IGNORECASE,
)
_RE_DATA_ACCESSED = re.compile(
    r"\b(unauthoriz(ed|ed?)\s+(access|acquisition)|"
    r"data\s+(was\s+)?(accessed|exfiltrat|exposed|stolen|copied|downloaded)|"
    r"personal\s+information\s+(was\s+)?(accessed|exfiltrat|obtained)|"
    r"sensitive\s+information\s+(was\s+)?(obtained|accessed))\b",
    re.IGNORECASE,
)
_RE_CONTAINED = re.compile(
    r"\b(the\s+incident\s+(has\s+been\s+)?contained|"
    r"contained\s+the\s+incident|"
    r"(no\s+longer|no\s+evidence)\s+of\s+(active|continued)\s+(access|activity))\b",
    re.IGNORECASE,
)
_RE_INVESTIGATING = re.compile(
    r"\b(investigation\s+(remains|continues|is\s+ongoing)|"
    r"the\s+investigation\s+is\s+in\s+early\s+stages|"
    r"still\s+assessing)\b",
    re.IGNORECASE,
)
_RE_FORENSIC_FIRM = re.compile(
    r"\b(engaged|retained|hired)\s+[^.]{0,80}?"
    r"(leading\s+)?(third[- ]party\s+)?(cybersecurity|forensic|incident[- ]response)\s+"
    r"(firm|firms|experts?|consultants?|advisors?|professionals?)",
    re.IGNORECASE,
)
_RE_LAW_ENFORCEMENT = re.compile(
    r"\b(notified|informed|contacted|is\s+(in\s+)?cooperat(ing|ion)\s+with)\s+"
    r"[^.]{0,40}?"
    r"(the\s+)?(FBI|Federal\s+Bureau\s+of\s+Investigation|"
    r"U\.?S\.?\s+Secret\s+Service|law\s+enforcement|CISA)",
    re.IGNORECASE,
)
_RE_IMMATERIAL = re.compile(
    r"(do(es)?\s+not\s+(currently\s+)?believe|"
    r"has\s+not\s+had|will\s+not\s+have|"
    r"not\s+expected\s+to\s+have)[^.]{0,120}?material\s+impact",
    re.IGNORECASE,
)
_RE_MATERIAL_ASSESSING = re.compile(
    r"\b(assessing|continues\s+to\s+assess|evaluating)\s+"
    r"(the\s+)?(potential\s+)?(impact|materiality)",
    re.IGNORECASE,
)
_RE_RANSOM_NOT_PAID = re.compile(
    r"\b(the\s+Company|we)\s+(did\s+not|has\s+not)\s+"
    r"pa(y|id)\s+[^.]{0,20}?ransom",
    re.IGNORECASE,
)
_RE_OPS_DISRUPTED = re.compile(
    r"\b(systems|operations|networks|services)[^.]{0,60}?"
    r"(offline|shut\s+down|are\s+not\s+currently\s+available|"
    r"were\s+(temporarily\s+)?taken\s+offline|"
    r"disrupt(ed|ion)|unavailable)",
    re.IGNORECASE,
)
_RE_ITEM_SECTION = re.compile(
    r"Item\s+1\.?05\s*[.—\-–:]?\s*Material\s+Cybersecurity\s+Incidents?",
    re.IGNORECASE,
)


@dataclass
class IncidentFacts:
    """Heuristic fact extraction from an 8-K Item 1.05 body."""
    has_item_1_05_section: bool = False
    mentions_ransomware: bool = False
    mentions_data_access: bool = False
    incident_contained: bool = False
    still_investigating: bool = False
    forensic_firm_engaged: bool = False
    law_enforcement_notified: bool = False
    materiality_claimed_immaterial: bool = False
    materiality_still_assessing: bool = False
    ransom_explicitly_not_paid: bool = False
    operations_disrupted: bool = False
    body_length: int = 0
    body_sample: str = ""

    @property
    def severity_hint(self) -> str:
        """Rough severity based on signal count. Purely a hint — the
        actual materiality is in the filing itself."""
        signals = [
            self.mentions_ransomware,
            self.mentions_data_access,
            self.operations_disrupted,
        ]
        c = sum(1 for s in signals if s)
        if c >= 2:
            return "high"
        if c == 1:
            return "medium"
        return "low"


def strip_html(html: str) -> str:
    """Crude HTML → text. Good enough for keyword detection."""
    # Replace block-level tags with newlines
    text = re.sub(r"</?(p|div|br|tr|li|h[1-6])[^>]*>", "\n", html,
                  flags=re.IGNORECASE)
    # Drop other tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode common HTML entities
    text = (text.replace("&nbsp;", " ")
                .replace("&amp;", "&")
                .replace("&quot;", '"')
                .replace("&#39;", "'")
                .replace("&lt;", "<")
                .replace("&gt;", ">"))
    # Collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def extract_facts(body_text: str, sample_len: int = 1200) -> IncidentFacts:
    """Parse structured facts out of a plain-text 8-K body."""
    facts = IncidentFacts(body_length=len(body_text))
    # Prefer the Item 1.05 section, fall back to full body
    m = _RE_ITEM_SECTION.search(body_text)
    if m:
        facts.has_item_1_05_section = True
        window = body_text[m.start(): m.start() + 6000]
    else:
        window = body_text

    facts.body_sample = window[:sample_len].strip()
    facts.mentions_ransomware = bool(_RE_RANSOMWARE.search(window))
    facts.mentions_data_access = bool(_RE_DATA_ACCESSED.search(window))
    facts.incident_contained = bool(_RE_CONTAINED.search(window))
    facts.still_investigating = bool(_RE_INVESTIGATING.search(window))
    facts.forensic_firm_engaged = bool(_RE_FORENSIC_FIRM.search(window))
    facts.law_enforcement_notified = bool(_RE_LAW_ENFORCEMENT.search(window))
    facts.materiality_claimed_immaterial = bool(_RE_IMMATERIAL.search(window))
    facts.materiality_still_assessing = bool(_RE_MATERIAL_ASSESSING.search(window))
    facts.ransom_explicitly_not_paid = bool(_RE_RANSOM_NOT_PAID.search(window))
    facts.operations_disrupted = bool(_RE_OPS_DISRUPTED.search(window))
    return facts


def fetch_body(filing_url: str, timeout: int = 15,
               _depth: int = 0) -> Optional[str]:
    """Fetch the primary filing document HTML and return plain text.

    EDGAR URLs come in two flavours:
      1. `.../<accession>-index.htm` — an index/TOC page listing the
         documents in the submission. We resolve the primary doc and
         recurse.
      2. `.../<primary-doc>.htm` — the actual filing body.
    """
    if not filing_url or _depth > 2:
        return None
    req = request.Request(filing_url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
    })
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except (error.HTTPError, error.URLError):
        return None
    except Exception:
        return None

    try:
        html = raw.decode("utf-8", errors="replace")
    except Exception:
        return None

    # If this is an EDGAR index page, resolve to the primary doc and recurse
    if "-index" in filing_url.lower():
        primary = _find_primary_doc_url(filing_url, html)
        if primary and primary != filing_url:
            return fetch_body(primary, timeout=timeout, _depth=_depth + 1)
    return strip_html(html)


def _find_primary_doc_url(index_url: str, index_html: str) -> Optional[str]:
    """Given an EDGAR -index.htm page, pick out the URL of the primary
    filing document.

    EDGAR's modern index pages link the primary document ONLY through
    the iXBRL viewer URL `/ix?doc=/Archives/edgar/data/<cik>/<accession>/<doc>.htm`.
    The direct archive URL for the doc is the value of the `doc=` query
    param. So we:

    1. Look for `/ix?doc=...htm` and extract the archive path.
    2. Fall back to any `.htm` href in the same accession directory.
    """
    base = index_url.rsplit("/", 1)[0]
    # Strategy 1: extract from iXBRL viewer links
    ix_match = re.search(
        r'href="[^"]*/ix\?doc=([^"&]+\.(?:htm|html))"',
        index_html,
        re.IGNORECASE,
    )
    if ix_match:
        raw_doc = ix_match.group(1)
        if raw_doc.startswith("/"):
            return f"https://www.sec.gov{raw_doc}"
        if raw_doc.startswith("http"):
            return raw_doc
        return f"{base}/{raw_doc}"

    # Strategy 2: direct .htm hrefs in the same accession dir
    candidates = re.findall(
        r'href="([^"]+\.(?:htm|html))"',
        index_html,
        re.IGNORECASE,
    )
    # Filter out obvious non-primary files
    bad_patterns = (
        "-index", "financial", "filing-summary", "filingsummary",
        "/r1.htm", "/r2.htm", "/r3.htm", "/r4.htm", "/r5.htm",
        "/r6.htm", "/r7.htm", "/r8.htm", "/r9.htm",
        "edgar/browse", "search-index",
        # XBRL / iXBRL viewer wrappers return JS not document content
        "cgi-bin", "viewer?action", "xbrl-viewer",
        "ix?doc=",
    )
    good = []
    for c in candidates:
        low = c.lower()
        if any(b in low for b in bad_patterns):
            continue
        good.append(c)

    # Prefer 8-K looking documents first
    def _score(c: str) -> int:
        low = c.lower()
        if re.search(r"8[- ]?k", low):
            return 100
        if "primary_doc" in low:
            return 90
        if re.match(r"d\d+d?", low.rsplit("/", 1)[-1] or ""):
            return 80  # standard Skadden-style filing names
        return 50

    good.sort(key=_score, reverse=True)
    if not good:
        return None
    c = good[0]
    if c.startswith("http"):
        return c
    if c.startswith("/"):
        return f"https://www.sec.gov{c}"
    return f"{base}/{c}"
