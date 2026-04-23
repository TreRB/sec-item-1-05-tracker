"""CLI entrypoint for sec-item-1-05-tracker."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from . import __version__
from .core import (
    enrich_filing,
    enrich_with_body,
    fetch_filings,
    filter_item_1_05,
    load_cache,
    merge_new_filings,
    save_cache,
)
from .reporter import (
    detect_webhook_kind,
    discord_payload,
    html_dashboard,
    post_webhook,
    rss_document,
    slack_blocks,
    write_csv,
    write_json_feed,
    write_latest,
)
from .tickers import fetch_tickers


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="sec-item-1-05-tracker",
        description=(
            "Track SEC Form 8-K Item 1.05 (Material Cybersecurity Incident) "
            "filings via EDGAR full-text search. Outputs JSON + RSS + CSV + "
            "HTML dashboard, with optional body fetching for incident-fact "
            "extraction and Slack/Discord webhook notifications on new filings."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Nightly cron: JSON + RSS + HTML + Slack webhook\n"
            "  sec-item-1-05-tracker --output-dir /var/www/sec-feed \\\n"
            "      --webhook https://hooks.slack.com/services/...\n\n"
            "  # Deep scan with body extraction\n"
            "  sec-item-1-05-tracker --since 2026-01-01 \\\n"
            "      --fetch-bodies --format csv,html,json\n\n"
            "  # Fresh ticker index, force re-download\n"
            "  sec-item-1-05-tracker --refresh-tickers"
        ),
    )
    scan = ap.add_argument_group("scan")
    scan.add_argument(
        "--since",
        default=(datetime.now(timezone.utc) - timedelta(days=30))
        .strftime("%Y-%m-%d"),
        help="ISO date, default 30 days ago",
    )
    scan.add_argument(
        "--until",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        help="ISO date, default today",
    )
    scan.add_argument(
        "--include-amendments",
        action="store_true",
        default=True,
        help="Also include 8-K/A amendments (default: true)",
    )
    scan.add_argument(
        "--max-results",
        type=int,
        default=1000,
        help="Cap on EDGAR pagination",
    )
    scan.add_argument(
        "--fetch-bodies",
        action="store_true",
        help="Fetch each filing body from EDGAR and extract incident "
             "facts (ransomware mention, containment, forensic firm, "
             "law enforcement, materiality language). Slower but adds "
             "'severity_hint' and per-filing fact flags.",
    )
    scan.add_argument(
        "--throttle",
        type=float,
        default=0.15,
        help="Seconds between EDGAR page fetches (default 0.15, SEC asks for ≤10/s)",
    )

    output = ap.add_argument_group("output")
    output.add_argument(
        "--output-dir",
        default=".",
        help="Where to write outputs (default: current dir)",
    )
    output.add_argument(
        "--format",
        default="json,rss",
        help="Comma-separated subset of: json, rss, csv, html. Default: json,rss",
    )
    output.add_argument(
        "--json-only", action="store_true",
        help="Alias for --format json",
    )
    output.add_argument(
        "--rss-only", action="store_true",
        help="Alias for --format rss",
    )
    output.add_argument(
        "--latest-n",
        type=int,
        default=20,
        help="How many filings to include in latest.json",
    )

    cache = ap.add_argument_group("state")
    cache.add_argument(
        "--cache-path",
        default=os.path.expanduser(
            "~/.sec-item-1-05-tracker/cache.json"
        ),
        help="Local dedup cache path",
    )
    cache.add_argument(
        "--tickers-cache",
        default=os.path.expanduser(
            "~/.sec-item-1-05-tracker/company_tickers.json"
        ),
        help="Local cache for SEC company_tickers.json",
    )
    cache.add_argument(
        "--refresh-tickers",
        action="store_true",
        help="Force re-download of SEC company_tickers.json",
    )
    cache.add_argument(
        "--no-tickers",
        action="store_true",
        help="Skip CIK→ticker lookup entirely",
    )

    notify = ap.add_argument_group("notifications")
    notify.add_argument(
        "--webhook",
        action="append",
        default=[],
        help="POST new-filing notifications to this URL. "
             "Auto-detects Slack vs Discord from URL. Repeatable.",
    )
    notify.add_argument(
        "--notify-all", action="store_true",
        help="Send webhook on every run (default: only when new filings arrive)",
    )

    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("-V", "--version", action="version",
                    version=f"sec-item-1-05-tracker {__version__}")
    args = ap.parse_args(argv)

    since = _parse_date(args.since)
    until = _parse_date(args.until)
    output_dir = Path(args.output_dir).expanduser().resolve()
    cache_path = Path(args.cache_path).expanduser().resolve()

    # Format parsing
    formats = set((args.format or "").split(","))
    formats = {f.strip() for f in formats if f.strip()}
    if args.json_only:
        formats = {"json"}
    if args.rss_only:
        formats = {"rss"}

    # Tickers index
    tickers_index = None
    if not args.no_tickers:
        try:
            if args.verbose:
                print(
                    "Loading SEC company_tickers.json index",
                    file=sys.stderr,
                )
            tickers_index = fetch_tickers(
                cache_path=Path(args.tickers_cache),
                force=args.refresh_tickers,
            )
        except Exception as e:
            if args.verbose:
                print(f"tickers index unavailable: {e}", file=sys.stderr)

    if args.verbose:
        print(
            f"Polling EDGAR for Item 1.05 filings {args.since} → {args.until}",
            file=sys.stderr,
        )

    raw = fetch_filings(
        since,
        until,
        include_amendments=args.include_amendments,
        max_results=args.max_results,
        verbose=args.verbose,
        throttle=args.throttle,
    )
    if args.verbose:
        print(f"Raw hits: {len(raw)}", file=sys.stderr)

    filtered = filter_item_1_05(raw)
    if args.verbose:
        print(f"Item 1.05 filings: {len(filtered)}", file=sys.stderr)

    enriched = [enrich_filing(h, tickers_index=tickers_index)
                for h in filtered]

    # Body enrichment (optional, slower)
    if args.fetch_bodies:
        if args.verbose:
            print("Fetching filing bodies…", file=sys.stderr)
        enriched = [enrich_with_body(f, verbose=args.verbose)
                    for f in enriched]

    # Merge into cache
    cache = load_cache(cache_path)
    merged, new_filings = merge_new_filings(cache, enriched)
    save_cache(cache_path, cache)

    # Write outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    if "json" in formats:
        write_json_feed(merged, output_dir / "feed.json")
        write_latest(merged, output_dir / "latest.json", n=args.latest_n)
    if "rss" in formats:
        (output_dir / "feed.rss").write_text(rss_document(merged))
    if "csv" in formats:
        write_csv(merged, output_dir / "feed.csv")
    if "html" in formats:
        (output_dir / "feed.html").write_text(html_dashboard(merged))

    # Webhook notifications
    webhooks_sent = 0
    if args.webhook and (new_filings or args.notify_all):
        to_post = new_filings if new_filings else merged[:5]
        for url in args.webhook:
            kind = detect_webhook_kind(url)
            payload = slack_blocks(to_post) if kind == "slack" \
                else discord_payload(to_post)
            status = post_webhook(url, payload)
            if args.verbose:
                print(f"webhook ({kind}): {status}", file=sys.stderr)
            if 200 <= status < 300:
                webhooks_sent += 1

    if args.verbose:
        print(
            f"Wrote {len(merged)} total filings "
            f"({len(new_filings)} new) → {output_dir}; "
            f"formats={','.join(sorted(formats))}; "
            f"webhooks={webhooks_sent}",
            file=sys.stderr,
        )
    else:
        print(
            f"sec-item-1-05-tracker: {len(merged)} filings "
            f"({len(new_filings)} new since last run)"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
