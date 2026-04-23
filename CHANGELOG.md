# Changelog

## [0.2.0] - 2026-04-23

Major expansion: body extraction, ticker lookup, expanded SIC codes,
CSV/HTML/Slack/Discord output, amendment-family grouping. Test count
14 → 73.

### Added

- **Filing body fetch + incident fact extraction** via `--fetch-bodies`.
  Pulls the primary 8-K document from EDGAR, strips HTML, and runs
  pattern-based extractors for:
  - Ransomware mention
  - Unauthorized data access / exfiltration
  - Containment status
  - Forensic firm engagement
  - Law-enforcement notification (FBI / CISA / Secret Service)
  - Materiality language ("does not believe ... material impact" vs
    "continues to assess")
  - Explicit "did not pay a ransom" language
  - Operational disruption signals
  Emits a `severity_hint` per filing based on signal count.
- **Authoritative CIK→ticker lookup** via SEC's
  `company_tickers.json`. Cached locally to
  `~/.sec-item-1-05-tracker/company_tickers.json` by default.
  `--refresh-tickers` forces a re-download. `--no-tickers` skips the
  enrichment step entirely.
- **CSV output format** (`--format csv`) for spreadsheet and BI-tool
  consumption. Includes body-derived columns when `--fetch-bodies` was
  used.
- **HTML dashboard** (`--format html`) — single-file dark-mode
  incident feed with severity hint highlighting and amendment-marker
  CSS class. Drop at `/feed.html` for a read-only static tracker.
- **Slack webhook notifier** (`--webhook https://hooks.slack.com/...`).
  Auto-detects Slack vs Discord from the URL. Default: fires only
  when new filings are detected since last run. Use `--notify-all` to
  post on every run.
- **Discord webhook notifier** — same flag, detects and posts
  Discord-formatted embeds.
- **Filing-family grouping** (`family.py`, `group_by_family`). Groups
  initial 8-K + subsequent 8-K/A amendments about the same incident.
- **Expanded SIC code catalogue** (35 → 150+ entries) covering every
  industry with non-trivial Item 1.05 filing volume: software, banking,
  insurance, hospitals, medical devices, aerospace / defense, energy,
  telecom, retail, manufacturing, transportation.
- **SIC sector helper** (`sic_sector`) returning the high-level category
  (Manufacturing, Services, Finance/Insurance/Real Estate, etc.) used
  by the HTML dashboard and analytics.
- **`--format comma,separated`** multi-format selector
  (e.g. `--format json,csv,html`).
- **`--throttle`** flag for EDGAR request spacing (default 0.15s,
  respects SEC's ≤10/s guideline).
- **GitHub Actions workflow templates** at `.github/workflows/test.yml`
  (CI for this repo) and `example-scan.yml` (drop-in for user repos).

### Fixed

- **EDGAR accession parsing** correctly splits on `:` to handle the
  `0001193125-26-149607:primary_doc.htm` format.
- **Ticker fallback** now draws from SEC company_tickers.json when
  EDGAR's `display_names` doesn't include a ticker in parentheses.
- **Regex precision** for forensic-firm-engaged and immaterial-impact
  language (previously missed common phrasings).

### Changed

- Module split from 2 files (cli, core) to 7 (cli, core, body, family,
  reporter, sic, tickers) with matching per-module test files.
- `enrich_filing` now accepts an optional `tickers_index` kwarg for
  authoritative ticker lookup.
- JSON output now includes `sector`, body-derived fact flags (when
  fetched), and `severity_hint`.
- RSS output includes severity hint in item description.
- Test count: 14 → 73 (files: test_core, test_body, test_sic,
  test_tickers, test_family, test_reporter).

### Previously in 0.1.0

- Core EDGAR FTS poll + filter + normalize.
- JSON + RSS + latest outputs.
- 35-entry SIC label table.
- Display-name-based ticker parsing.
- Simple cache for dedup.
