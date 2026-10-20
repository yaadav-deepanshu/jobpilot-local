import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
from scraper.company_portals import BIG_COMPANY_PORTALS

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
}

print(f"Testing all {len(BIG_COMPANY_PORTALS)} company portal URLs...")

working = []
broken = []

for p in BIG_COMPANY_PORTALS:
    name = p['name']
    url = p.get('search_url') or p.get('portal_url')
    try:
        r = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
        txt = r.text.lower()
        is_bad = (
            r.status_code >= 400 or
            "doesn't seem to exist" in txt or
            "page not found" in txt or
            "link pointing here was faulty" in txt or
            "login.microsoftonline.com" in r.url
        )
        if is_bad:
            broken.append((name, r.status_code, url, r.url))
        else:
            working.append((name, r.status_code, url, r.url))
    except Exception as e:
        broken.append((name, 'EXC', url, str(e)))

print(f"\nWorking URLs: {len(working)} / {len(BIG_COMPANY_PORTALS)}")
print(f"Broken URLs: {len(broken)} / {len(BIG_COMPANY_PORTALS)}")

print("\n--- SAMPLE BROKEN URLS ---")
for b in broken[:20]:
    print(f"[{b[0]}] HTTP {b[1]}\n  Tried: {b[2]}\n  Got:   {b[3]}\n")
