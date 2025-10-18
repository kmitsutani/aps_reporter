#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSS feed aggregator and filter for physics papers.
Filters papers based on keywords related to quantum information and field theory.
"""
import feedparser
import re
from feedgen.feed import FeedGenerator
from loguru import logger
import sys
from pathlib import Path

hit_threshold = 2

def create_filtered_feed(output_path: str) -> FeedGenerator:
    """Create and populate a filtered RSS feed."""
    fg = FeedGenerator()
    fg.title("papers for Project IEFL")
    fg.link(href='https://example.com/papers', rel='alternate')
    fg.description("papers for Project IEFL")

    # Target feeds
    FEEDS = [
        # APS
        'https://feeds.aps.org/rss/recent/pra.xml',
        'https://feeds.aps.org/rss/recent/prd.xml',
        'https://feeds.aps.org/rss/recent/prresearch.xml',
        'https://feeds.aps.org/rss/recent/prl.xml',
        'https://feeds.aps.org/rss/recent/prx.xml',
        'https://feeds.aps.org/rss/recent/rmp.xml',
        # arXiv category RSS (new submissions)
        'https://rss.arxiv.org/rss/quant-ph',
        'https://rss.arxiv.org/rss/hep-th',
        'https://rss.arxiv.org/rss/math-ph'
    ]

    STRONG_WORDS = {
        'modular Hamiltonian', r'entanglement hamiltonian',
        r'measurement-induced', r'\bMIET\b',
        r'\bQNEC\b', r'Bekenstein',
        r'\bAQFT\b', 'Haag-(?:Araki-)Kastler',
    }
    WEAK_WORDS = {
        r'\bmodular\b', r'\bentanglement\b',
        r'relative entropy', r'\bmeasurement\b', r'\bCFT\b', r'quantum field theory',
        r'free field', r'holographic',
    }
    STRONG_WORD_RE = re.compile('|'.join(STRONG_WORDS), re.I)
    WEAK_WORD_RE = re.compile('|'.join(WEAK_WORDS), re.I)

    def wanted(text: str, hist_threshold=2) -> bool:
        """Check if text contains relevant keywords."""
        strong_hits = set(STRONG_WORD_RE.findall(text))
        if len(strong_hits) > 0:
            return True
        weak_hits = set(WEAK_WORD_RE.findall(text))
        return len(weak_hits) >= hist_threshold

    # Filter entries from all feeds
    entry_count = 0
    for url in FEEDS:
        logger.info(f"Processing feed: {url}")
        try:
            feed = feedparser.parse(url)
            for e in feed.entries:
                blob = f"{e.title} {e.summary}"
                if wanted(blob):
                    fe = fg.add_entry()
                    fe.title(e.title)
                    fe.link(href=e.link)
                    fe.pubDate(e.published if 'published' in e else e.updated)
                    fe.description(e.description)
                    entry_count += 1
        except Exception as ex:
            logger.error(f"Error processing feed {url}: {ex}")

    logger.info(f'Filtered feed created with {entry_count} entries')
    fg.rss_file(output_path)
    return fg

if __name__ == "__main__":
    output_file = sys.argv[1] if len(sys.argv) > 1 else 'filtered.xml'
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    create_filtered_feed(output_file)
