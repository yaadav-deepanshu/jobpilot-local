import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import urllib.request
from scraper.company_portals import BIG_COMPANY_PORTALS

greenhouse_portals = [p for p in BIG_COMPANY_PORTALS if p.get('ats_type') == 'greenhouse' or 'greenhouse.io' in p.get('search_url', '') or 'greenhouse.io' in p.get('portal_url', '')]

print(f"Total Greenhouse portals: {len(greenhouse_portals)}")

for p in greenhouse_portals:
    p_id = p['id']
    name = p['name']
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{p_id}/jobs"
    req = urllib.request.Request(
        api_url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                jobs = data.get('jobs', [])
                print(f"SUCCESS: {name} ({p_id}) -> {len(jobs)} jobs")
            else:
                print(f"HTTP {resp.status}: {name} ({p_id})")
    except Exception as e:
        print(f"ERROR: {name} ({p_id}) -> {e}")
