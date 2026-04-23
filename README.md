# sec-item-1-05-tracker

Track every SEC Form 8-K Item 1.05 (Material Cybersecurity Incidents)
filing via the EDGAR full-text search API. Outputs a normalized JSON
feed of filings (with CIK, ticker, filing date, period, URL, industry
SIC code) and an RSS 2.0 feed for subscribers. Zero API key required.

Built by [Valtik Studios](https://valtikstudios.com). MIT licensed.

## Why this exists

Since December 2023, every US-listed reporting company must file an
Item 1.05 Form 8-K within four business days of determining that a
cybersecurity incident is material. The aggregate ledger of those
filings is the most under-read dataset in US corporate cybersecurity.

Most practitioners monitor the regulator (SEC) or the press (Reuters,
Bloomberg, CyberSecurityDive). Both channels are biased toward the
loudest names. The EDGAR full-text-search API gives you every single
filing as soon as it lands — including the mid-cap and small-cap
filings most cyber-press ignores.

This tool polls EDGAR, filters to 8-K (and 8-K/A amendments) that cite
Item 1.05 in the Items field, normalizes the metadata, and emits a JSON
and RSS feed you can consume from your SIEM, your vendor-risk platform,
your board-reporting tool, or your newsletter subscribers.

We use it ourselves at Valtik Studios to watch for client-ecosystem
counterparties that file an Item 1.05. It powers the analysis in our
[two-years-of-Item-1.05 blog post](https://valtikstudios.com/blog/sec-8k-item-1-05-two-years-in-what-filings-actually-say).

## What it does

1. Polls `https://efts.sec.gov/LATEST/search-index?q="Item 1.05"&forms=8-K`
   (EDGAR's public full-text search index).
2. Pulls each hit's metadata: CIK, company name, ticker, filing date,
   period of report, accession number, SIC code, filing URL.
3. Deduplicates against a local cache (`~/.sec-item-1-05-tracker/seen.json`)
   so each filing is emitted once.
4. Optionally extracts the state of incorporation and HQ location from
   the primary filing's header.
5. Writes:
   - `feed.json` — normalized JSON array of all filings seen
   - `feed.rss` — RSS 2.0 feed for subscribers
   - `latest.json` — just the most recent N filings (default 20)

## Install

```bash
pip install valtik-sec-item-1-05-tracker
```

Or from source:

```bash
git clone https://github.com/TreRB/sec-item-1-05-tracker
cd sec-item-1-05-tracker
pip install -e .
```

## Usage

Default run (last 30 days, writes to current directory):

```bash
sec-item-1-05-tracker
```

Full options:

```bash
sec-item-1-05-tracker \
    --since 2024-01-01 \
    --output-dir ./sec-feed \
    --include-amendments \
    --verbose
```

Output files:

```
sec-feed/
├── feed.json        # full list, newest first
├── feed.rss         # RSS 2.0, last 100
├── latest.json      # just the last 20
└── cache.json       # internal dedup cache
```

### Sample JSON entry

```json
{
  "cik": "0001234567",
  "company_name": "EXAMPLE CORP",
  "ticker": "EXMP",
  "sic": "7372",
  "sic_label": "Services-Prepackaged Software",
  "filed_at": "2026-04-15",
  "period": "2026-04-11",
  "accession_no": "0001193125-26-123456",
  "form": "8-K",
  "items": ["1.05"],
  "filing_url": "https://www.sec.gov/Archives/edgar/data/1234567/...",
  "inc_state": "DE",
  "hq_state": "CA",
  "first_seen": "2026-04-15T14:22:01Z"
}
```

### Sample CLI flags

```
--since 2024-01-01           ISO date, default 30 days ago
--until 2026-04-23           ISO date, default today
--output-dir ./              Where to write feed.json/feed.rss
--include-amendments         Also include 8-K/A (default: both)
--json-only                  Skip RSS output
--rss-only                   Skip JSON output
--max-results 1000           Cap EDGAR pagination
--verbose                    Log every filing to stderr
--cache-path PATH            Override cache location
```

### Running on a schedule

Cron, every 3 hours:

```cron
0 */3 * * * /usr/bin/sec-item-1-05-tracker --output-dir /var/www/sec-feed
```

The RSS feed will be at `/var/www/sec-feed/feed.rss`, ready to point
any RSS reader at.

## Why trust this over manual SEC searches

1. **Coverage.** EDGAR's web UI paginates at 10 results per page and
   rate-limits aggressively. Our tool uses the JSON search API which
   returns 100 at a time and handles backoff.

2. **Dedup.** A single incident can generate an initial 8-K plus one or
   more 8-K/A amendments. We track them together so your feed shows the
   current state, not redundant entries.

3. **Full-text match.** EDGAR's FTS sometimes returns filings where
   Item 1.05 is mentioned in a reference rather than as a filed item.
   We re-check the `items` field before emitting.

4. **Speed.** A filing that lands on EDGAR at 4:02pm ET appears in this
   feed the next poll cycle, typically within 30 minutes.

## Architecture

```
EDGAR FTS API
  │
  ▼
┌─────────────────────┐
│   poll_edgar()       │  → raw hits
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ filter_item_1_05()   │  → only 8-K / 8-K/A with '1.05' in items
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ enrich_filing()      │  → pull CIK+SIC+state from company-tickers.json
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ dedup_against_cache()│  → skip anything in seen.json
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ write_feeds()        │  → feed.json + feed.rss + latest.json
└─────────────────────┘
```

## Limitations

- EDGAR sometimes delays full-text indexing by 10-30 minutes after a
  filing hits. We poll but don't push; a very fresh filing may not
  appear until the next cycle.
- SIC codes are ~4-decade-old industry classifications. They're good
  enough for high-level routing but imperfect.
- The tool does NOT read the filing body. If you want to classify the
  incident type, ransom payment language, or extracted data categories,
  pair this with a body-extraction step.

## See also

- [Valtik Studios: Two years of SEC Item 1.05](https://valtikstudios.com/blog/sec-8k-item-1-05-two-years-in-what-filings-actually-say) — the aggregate analysis this tool powered.
- [SEC 4-day breach disclosure rule guide](https://valtikstudios.com/blog/sec-4-day-breach-disclosure-rule) — the underlying rule.
- [EDGAR full-text search](https://efts.sec.gov/LATEST/search-index?q=%22Item+1.05%22&forms=8-K) — the raw source.
- [SEC Corporation Finance Disclosure Guidance](https://www.sec.gov/corpfin/secg-cybersecurity)

## License

MIT. Do what you want. We'd appreciate a backlink if you build something
cool with this.

## Author

Built by Phillip (Tre) Bucchi at [Valtik Studios](https://valtikstudios.com).
We're a cybersecurity consulting firm based in Connecticut and serving
Dallas-Fort Worth + US nationwide. Penetration testing, compliance
readiness (SOC 2, PCI DSS 4.0, HIPAA, CMMC 2.0, NYDFS 500), and
board-cyber-governance engagements. Reach us at tre@valtikstudios.com.
