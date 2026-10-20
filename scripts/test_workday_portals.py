import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import re
import json
import urllib.request
from scraper.company_portals import BIG_COMPANY_PORTALS

workday_portals = [p for p in BIG_COMPANY_PORTALS if p.get('ats_type') == 'workday' or 'myworkdayjobs.com' in p.get('search_url', '') or 'myworkdayjobs.com' in p.get('portal_url', '')]

print(f"Total Workday portals: {len(workday_portals)}")

for p in workday_portals:
    p_id = p['id']
    name = p['name']
    base_url = p.get('search_url') or p.get('portal_url')

    m = re.search(r'https?://([^.]+)\.([^.]+)\.myworkdayjobs\.com/(?:[a-zA-Z-]+/)?([^/?#]+)', base_url)
    if not m:
        print(f"FAILED TO PARSE WORKDAY URL: {name} -> {base_url}")
        continue
    tenant, host, site = m.group(1), m.group(2), m.group(3)
    api_url = f"https://{tenant}.{host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"

    payload = json.dumps({
        "appliedFacets": {},
        "limit": 10,
        "offset": 0,
        "searchText": ""
    }).encode('utf-8')

    req = urllib.request.Request(
        api_url,
        data=payload,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                postings = data.get('jobPostings', [])
                total = data.get('total', 0)
                print(f"SUCCESS: {name} ({tenant}) -> {len(postings)} jobs (total {total})")
            else:
                print(f"HTTP {resp.status}: {name} -> {api_url}")
    except Exception as e:
        print(f"ERROR: {name} ({api_url}) -> {e}")
