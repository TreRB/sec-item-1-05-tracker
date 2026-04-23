"""CLI entrypoint for sec-item-1-05-tracker."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .core import (
    fetch_filings,
    filter_item_1_05,
    enrich_filing,
    write_feeds,
    load_cache,
    save_cache,
    merge_new_filings,
)


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Track SEC Form 8-K Item 1.05 (Material Cybersecurity Incident) "
            "filings via EDGAR full-text search. Outputs JSON + RSS feeds."
        )
    )
    ap.add_argument(
        "--since",
        default=(datetime.now(timezone.utc) - timedelta(days=30))
        .strftime("%Y-%m-%d"),
        help="ISO date, default 30 days ago",
    )
    ap.add_argument(
        "--until",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        help="ISO date, default today",
    )
    ap.add_argument(
        "--output-dir",
        default=".",
        help="Where to write feed.json / feed.rss / latest.json",
    )
    ap.add_argument(
        "--include-amendments",
        action="store_true",
        default=True,
        help="Also include 8-K/A amendments (default: true)",
    )
    ap.add_argument(
        "--json-only",
        action="store_true",
        help="Skip writing the RSS feed",
    )
    ap.add_argument(
        "--rss-only",
        action="store_true",
        help="Skip writing the JSON feeds",
    )
    ap.add_argument(
        "--max-results",
        type=int,
        default=1000,
        help="Cap on EDGAR pagination",
    )
    ap.add_argument(
        "--cache-path",
        default=os.path.expanduser(
            "~/.sec-item-1-05-tracker/cache.json"
        ),
        help="Local dedup cache path",
    )
    ap.add_argument(
        "--latest-n",
        type=int,
        default=20,
        help="Number of filings to include in latest.json",
    )
    ap.add_argument(
        "--verbose",
        action="store_true",
    )
    args = ap.parse_args(argv)

    since = _parse_date(args.since)
    until = _parse_date(args.until)
    output_dir = Path(args.output_dir).expanduser().resolve()
    cache_path = Path(args.cache_path).expanduser().resolve()

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
    )
    if args.verbose:
        print(f"Raw hits: {len(raw)}", file=sys.stderr)

    filtered = filter_item_1_05(raw)
    if args.verbose:
        print(f"Item 1.05 filings: {len(filtered)}", file=sys.stderr)

    enriched = [enrich_filing(h) for h in filtered]

    cache = load_cache(cache_path)
    merged, new_count = merge_new_filings(cache, enriched)
    save_cache(cache_path, cache)

    write_feeds(
        merged,
        output_dir,
        json_only=args.json_only,
        rss_only=args.rss_only,
        latest_n=args.latest_n,
    )

    if args.verbose:
        print(
            f"Wrote {len(merged)} total filings "
            f"({new_count} new) → {output_dir}",
            file=sys.stderr,
        )
    else:
        print(
            f"sec-item-1-05-tracker: {len(merged)} filings "
            f"({new_count} new since last run)"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
