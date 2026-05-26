#!/usr/bin/env python3
"""
Main runner for the Bangladesh rape-case news scraper.

Usage:
    python run_scraper.py                    # scrape all sources, 2015-2025
    python run_scraper.py --year 2020        # scrape one year only
    python run_scraper.py --source daily_star
    python run_scraper.py --extract-only     # re-run extractor on saved articles
    python run_scraper.py --stats            # show DB statistics
"""

import argparse
import logging
import sys
import os

# Make sure we can import from project root
sys.path.insert(0, os.path.dirname(__file__))

import db
from config import SEARCH_KEYWORDS_EN, START_DATE, END_DATE
from extractor import extract_case
from scrapers import ALL_SCRAPERS
from export_csv import export

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/scraper.log"),
    ],
)
logger = logging.getLogger("run_scraper")


def scrape(source_filter=None, year_filter=None):
    years = range(START_DATE.year, END_DATE.year + 1)
    if year_filter:
        years = [year_filter]

    active_scrapers = [
        S() for S in ALL_SCRAPERS
        if source_filter is None or S.SOURCE == source_filter
    ]
    if not active_scrapers:
        logger.error(f"No scraper found for source '{source_filter}'")
        return

    total_new = 0
    for scraper in active_scrapers:
        logger.info(f"=== Starting scraper: {scraper.SOURCE} ===")
        for year in years:
            for keyword in SEARCH_KEYWORDS_EN:
                logger.info(f"  keyword='{keyword}' year={year}")
                articles = scraper.get_article_urls(keyword, year)
                logger.info(f"  Found {len(articles)} candidate URLs")

                for art in articles:
                    url = art["url"]
                    if db.article_exists(url):
                        logger.debug(f"  [skip] already scraped: {url}")
                        continue

                    result = scraper.fetch_article_content(url)
                    if result is None:
                        continue
                    content, date = result
                    if not content:
                        continue

                    db.save_article(
                        source=scraper.SOURCE,
                        url=url,
                        title=art.get("title", ""),
                        date=date or art.get("date", ""),
                        content=content,
                    )
                    total_new += 1
                    logger.info(f"  [saved] {url}")

    logger.info(f"Scraping complete. {total_new} new articles saved.")


def run_extractor():
    articles = db.get_unprocessed_articles()
    logger.info(f"Processing {len(articles)} unprocessed articles...")
    extracted = 0
    for row in articles:
        case = extract_case(row)
        if case:
            db.save_case(case)
            extracted += 1
        db.mark_processed(row["id"])
    logger.info(f"Extraction complete. {extracted} cases saved from {len(articles)} articles.")


def show_stats():
    stats = db.get_stats()
    print(f"\n{'='*45}")
    print(f"  Total articles : {stats['total_articles']}")
    print(f"  Total cases    : {stats['total_cases']}")
    print(f"  By source:")
    for src, n in stats["by_source"].items():
        print(f"    {src:<20} {n}")
    print(f"{'='*45}\n")


def main():
    parser = argparse.ArgumentParser(description="Bangladesh rape-case news scraper")
    parser.add_argument("--year",         type=int, help="Scrape one specific year")
    parser.add_argument("--source",       type=str, help="Scrape one specific source")
    parser.add_argument("--extract-only", action="store_true", help="Skip scraping, only run extractor")
    parser.add_argument("--stats",        action="store_true", help="Show DB statistics and exit")
    args = parser.parse_args()

    db.init_db()

    if args.stats:
        show_stats()
        return

    if not args.extract_only:
        scrape(source_filter=args.source, year_filter=args.year)

    run_extractor()
    export()
    show_stats()


if __name__ == "__main__":
    main()
