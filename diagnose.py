#!/usr/bin/env python3
"""
Diagnostic script — checks what each newspaper's search page
actually returns so we can fix the scrapers.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import requests
from html_utils import extract_links

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

SOURCES = [
    ('Daily Star search',    'https://www.thedailystar.net/search?query=rape&page=0'),
    ('Daily Star tag',       'https://www.thedailystar.net/tags/rape'),
    ('Dhaka Tribune search', 'https://www.dhakatribune.com/search?q=rape&page=1'),
    ('bdnews24 search',      'https://bdnews24.com/search?query=rape&page=1'),
]

for name, url in SOURCES:
    print(f'\n{"="*60}')
    print(f'SOURCE : {name}')
    print(f'URL    : {url}')
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        print(f'Status : {r.status_code}  |  Size: {len(r.text):,} chars')
        links = extract_links(r.text)
        article_links = [
            (href, text) for href, text in links
            if href and len(text.strip()) > 20 and href.startswith('http')
        ]
        print(f'Links  : {len(links)} total, {len(article_links)} look like articles')
        print('\nSample article links:')
        for href, text in article_links[:10]:
            print(f'  {href[:80]}')
            print(f'  -> {text.strip()[:60]}')
        if not article_links:
            print('  (none found — showing raw links sample)')
            for href, text in links[:10]:
                print(f'  {href[:80]} | {text.strip()[:40]}')
    except Exception as e:
        print(f'ERROR  : {e}')

print('\nDone.')
