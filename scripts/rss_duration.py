#!/usr/bin/env python3
"""
APS RSS feed duration checker.
Checks the time span of articles in APS RSS feeds and logs warnings if the span is too short.
"""
import re
import requests
import logging
import argparse
from datetime import datetime, timedelta

def setup_logger(log_level: str) -> logging.Logger:
    """Set up and configure logger."""
    logger = logging.getLogger("APS_RSS_Checker")
    logger.setLevel(getattr(logging, log_level))
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

def check_rss_duration(logger: logging.Logger):
    """Check the publication date span in APS RSS feeds."""
    # APS RSS feed URLs
    rss_feeds = {
        "RMP": "https://feeds.aps.org/rss/recent/rmp.xml",
        "PRX": "https://feeds.aps.org/rss/recent/prx.xml",
        "PRL": "https://feeds.aps.org/rss/recent/prl.xml",
        "PRResearch": "https://feeds.aps.org/rss/recent/prresearch.xml",
        "PRD": "https://feeds.aps.org/rss/recent/prd.xml",
        "PRA": "https://feeds.aps.org/rss/recent/pra.xml",
    }

    # dc:date extraction regex
    pubdate_re = re.compile(r"<dc:date>(.*?)</dc:date>")

    # Process each feed
    for name, url in rss_feeds.items():
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            matches = pubdate_re.findall(response.text)

            if not matches:
                logger.warning(f"{name}: No <dc:date> entries found.")
                continue

            dates = []
            for match in matches:
                try:
                    dt = datetime.strptime(match, "%Y-%m-%dT%H:%M:%S%z")
                    dates.append(dt)
                except Exception:
                    logger.debug(f"{name}: Failed to parse date string: {match}")
                    continue

            if not dates:
                logger.warning(f"{name}: No valid dates parsed.")
                continue

            earliest = min(dates)
            latest = max(dates)
            span = latest - earliest

            log_fn = logger.debug
            if span < timedelta(days=1.5):
                log_fn = logger.warning

            log_fn(f"{name}: {str(earliest)[:-6]} - {str(latest)[:-6]} (duration: {span})")

        except Exception as e:
            logger.error(f"{name}: Error fetching or parsing - {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APS RSS feed checker")
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: WARNING)"
    )
    args = parser.parse_args()

    logger = setup_logger(args.log_level)
    check_rss_duration(logger)
