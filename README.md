# sec-item-1-05-tracker

Track every SEC Form 8-K Item 1.05 (Material Cybersecurity Incident)
filing as it lands on EDGAR. Outputs JSON, RSS, CSV, and a standalone
HTML dashboard, with optional body extraction for incident-fact flags
and Slack / Discord webhook notifications.

Built by [Valtik Studios](https://valtikstudios.com). MIT licensed.
Zero API-key required.

- **Body-fetch + fact extraction**: ransomware mention, data access,
  containment, forensic firm engagement, law-enforcement notification,
  materiality language, explicit ransom-not-paid, operational disruption
- **Severity hint** per filing (`low` / `medium` / `high`) from signal count
- **Authoritative CIK→ticker lookup** via SEC's `company_tickers.json`
- **150+ SIC code labels** with high-level sector bucketing
- **Four output formats**: `json`, `rss`, `csv`, `html`
- **Slack + Discord webhooks** on new filings
- **Amendment-family grouping** (8-K + 8-K/A chains)
- **73 tests**, pure stdlib, zero external dependencies

## Why this exists

Since December 2023, every US-listed reporting company must file an
Item 1.05 Form 8-K within four business days of determining that a
cybersecurity incident is material. The aggregate ledger of those
filings is the most under-read dataset in US corporate cybersecurity.

EDGAR's web UI paginates 10-at-a-time, rate-limits aggressively, and
does not emit a feed. This tool wraps the EDGAR full-text-search JSON
API (100 results per page), deduplicates against a local cache, enriches
each filing with ticker / industry / optional body facts, and emits a
normalized feed that any SIEM, vendor-risk platform, or board-reporting
tool can subscribe to.

It powers the analysis in our
[two-years-of-Item-1.05 blog post](https://valtikstudios.com/blog/sec-8k-item-1-05-two-years-in-what-filings-actually-say).

## Install

```bash
pipx install valtik-sec-item-1-05-tracker
# or
pip install valtik-sec-item-1-05-tracker
# or from source
git clone https://github.com/TreRB/sec-item-1-05-tracker
cd sec-item-1-05-tracker
pip install -e ".[dev]"
```

## Use

### Default run (last 30 days, JSON + RSS to current dir)

```bash
sec-item-1-05-tracker
```

### Full run (all formats, body extraction, Slack webhook, 90-day window)

```bash
sec-item-1-05-tracker \
    --since 2026-01-01 \
    --output-dir /var/www/sec-feed \
    --format json,rss,csv,html \
    --fetch-bodies \
    --webhook "https://hooks.slack.com/services/T00/B00/xxxx" \
    --verbose
```

### Run on a schedule

Cron, every 3 hours:

```cron
0 */3 * * * /usr/local/bin/sec-item-1-05-tracker --output-dir /var/www/sec-feed --format json,rss,html --webhook "$SLACK_URL"
```

### Full CLI flags

| Group | Flag | Effect |
|-------|------|--------|
| scan | `--since DATE` | ISO date, default 30 days ago |
| scan | `--until DATE` | ISO date, default today |
| scan | `--include-amendments` | Include 8-K/A amendments (default: true) |
| scan | `--fetch-bodies` | Download each filing body and extract incident facts |
| scan | `--max-results N` | Cap on EDGAR pagination (default 1000) |
| scan | `--throttle N` | Seconds between EDGAR page fetches (default 0.15) |
| output | `--output-dir PATH` | Where to write outputs (default `.`) |
| output | `--format FMT[,FMT…]` | Subset of `json,rss,csv,html`. Default: `json,rss` |
| output | `--json-only` / `--rss-only` | Shortcut aliases |
| output | `--latest-n N` | Entries in `latest.json` (default 20) |
| state | `--cache-path PATH` | Local dedup cache (default `~/.sec-item-1-05-tracker/cache.json`) |
| state | `--tickers-cache PATH` | CIK→ticker index cache |
| state | `--refresh-tickers` | Force re-download of `company_tickers.json` |
| state | `--no-tickers` | Skip CIK→ticker enrichment entirely |
| notify | `--webhook URL` | POST new-filing notifications. Repeatable. Auto-detects Slack vs Discord. |
| notify | `--notify-all` | Post to webhooks even when no new filings |
| | `--verbose` | Log progress to stderr |
| | `-V` | Print version |

## What the outputs look like

### `feed.json`

```json
[
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
    "filing_url": "https://www.sec.gov/Archives/edgar/data/310764/...",
    "mentions_ransomware": true,
    "mentions_data_access": true,
    "incident_contained": false,
    "forensic_firm_engaged": true,
    "law_enforcement_notified": true,
    "materiality_still_assessing": true,
    "ransom_explicitly_not_paid": false,
    "operations_disrupted": true,
    "severity_hint": "high"
  }
]
```

### `feed.rss`

Standard RSS 2.0. Plug into any feed reader, SIEM, or Slack RSS
integration. Severity hint is in each item's description line.

### `feed.csv`

Rows sorted newest first, headers:
`filed_at, period, company_name, ticker, cik, form, sic, sic_label,
sector, hq_state, inc_state, accession_no, filing_url, items,
mentions_ransomware, mentions_data_access, incident_contained,
forensic_firm_engaged, law_enforcement_notified,
materiality_claimed_immaterial, materiality_still_assessing,
operations_disrupted, severity_hint`.

Body-derived columns are empty strings for filings that weren't fetched
with `--fetch-bodies`.

### `feed.html`

Single-file dark-mode incident feed. No JavaScript. Drop at
`/feed.html` on any static host and you have a read-only dashboard.
Severity-hint column is color-coded; amendments (8-K/A) get a distinct
style. Example output:

<img width="900" alt="HTML dashboard screenshot" src="https://valtikstudios.com/og/sec-item-1-05-tracker-dashboard.png">

### Slack webhook

Block Kit payload with a header + one section per filing (capped at 10).
Each filing shows company name, ticker, filed date, form, SIC label,
and a hyperlink to the EDGAR filing page. Severity-hint emoji (🔴 high,
🟡 medium, 🟢 low).

### Discord webhook

Embeds payload with one embed per filing. Color-coded by severity
hint (red/amber/gray). Same fields as Slack.

## Fact extraction details

With `--fetch-bodies`, each filing's primary document is downloaded
from EDGAR, HTML-stripped to text, and scanned for these patterns:

| Fact | Pattern example |
|------|-----------------|
| `mentions_ransomware` | "ransomware", "encrypted data", "demanded payment" |
| `mentions_data_access` | "unauthorized access", "personal information was accessed" |
| `incident_contained` | "incident has been contained", "no longer active access" |
| `still_investigating` | "investigation remains ongoing", "in early stages" |
| `forensic_firm_engaged` | "engaged a leading cybersecurity firm" (or forensic / IR firm) |
| `law_enforcement_notified` | FBI, US Secret Service, CISA, "law enforcement" |
| `materiality_claimed_immaterial` | "does not believe ... material impact" |
| `materiality_still_assessing` | "continues to assess the potential impact" |
| `ransom_explicitly_not_paid` | "the Company did not pay a ransom" |
| `operations_disrupted` | "systems were taken offline", "services are not currently available" |

The patterns are heuristics, tuned for the template language that SEC
counsel actually uses in 2024-2026 filings. False positives are
acceptable because the tool's goal is to surface filings for human
review, not to auto-classify.

## Severity hint

A rough bucket based on how many of the three strongest signals appear:

- `high`: 2+ of { mentions_ransomware, mentions_data_access, operations_disrupted }
- `medium`: exactly 1
- `low`: none

This is a triage hint, not a materiality determination. The actual
materiality is in the filing itself.

## Publishing a live public feed

See [`.github/workflows/publish-feed.yml`](.github/workflows/publish-feed.yml)
for a drop-in GitHub Actions workflow that:

1. Runs the tracker every 3 hours against the last 90 days
2. Commits outputs to a `gh-pages` branch
3. Publishes JSON / RSS / CSV / HTML to GitHub Pages
4. Optionally fires a Slack webhook on new filings

A single repo + Actions workflow gets you a zero-infrastructure live
incident tracker.

## Development

```bash
git clone https://github.com/TreRB/sec-item-1-05-tracker
cd sec-item-1-05-tracker
pip install -e ".[dev]"
pytest tests/ -v
```

73 tests across six test files:

- `test_core.py`: EDGAR FTS parsing, enrichment, cache roundtrip
- `test_body.py`: HTML stripping, fact extraction, severity hint
- `test_sic.py`: SIC label + sector mapping
- `test_tickers.py`: CIK→ticker lookup, cache behavior
- `test_family.py`: amendment-chain grouping
- `test_reporter.py`: JSON/RSS/CSV/HTML/Slack/Discord output shape

## Architecture

```
sec_item_1_05_tracker/
├── __init__.py      # public API
├── cli.py           # argparse + orchestration
├── core.py          # EDGAR fetch/filter/enrich
├── body.py          # body fetch + fact extraction
├── family.py        # amendment grouping
├── reporter.py      # JSON / RSS / CSV / HTML / webhook formatters
├── sic.py           # SIC code labels + sector lookup
└── tickers.py       # CIK→ticker from SEC company_tickers.json
```

## Limitations

- EDGAR indexes filings within minutes of submission, but there is a
  small lag. Very fresh filings may not appear until the next poll.
- SIC codes are coarse. They're adequate for industry bucketing but
  won't distinguish (e.g.) general hospitals from specialty clinics.
- Body fetching adds ~0.5s per filing. Use it on smaller windows
  (--since a few weeks back) or let it run in the background on cron.
- Pattern-based fact extraction is a heuristic. It handles template
  language in most 2024-2026 filings but will miss creative phrasings.
  Feed the output to a human for critical decisions.

## See also

- [Valtik Studios: Two years of SEC Item 1.05](https://valtikstudios.com/blog/sec-8k-item-1-05-two-years-in-what-filings-actually-say) — the aggregate analysis this tool powered
- [SEC 4-day breach disclosure rule guide](https://valtikstudios.com/blog/sec-4-day-breach-disclosure-rule)
- [EDGAR full-text search](https://efts.sec.gov/LATEST/search-index?q=%22Item+1.05%22&forms=8-K)
- [SEC Corporation Finance Disclosure Guidance](https://www.sec.gov/corpfin/secg-cybersecurity)

## License

MIT. See [LICENSE](LICENSE).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Author

Built by Phillip (Tre) Bucchi at [Valtik Studios](https://valtikstudios.com).
Cybersecurity consulting for SaaS and platform teams: penetration
testing, SOC 2 / PCI DSS 4.0 / HIPAA / CMMC 2.0 / NYDFS 500 readiness,
Supabase + Next.js security reviews, board cyber governance
engagements. Based in Connecticut, serving Dallas-Fort Worth and
nationwide.

Reach us at tre@valtikstudios.com.
