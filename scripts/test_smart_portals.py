import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import urllib.request
from scraper.company_portals import BIG_COMPANY_PORTALS

smart_portals = [p for p in BIG_COMPANY_PORTALS if p.get('ats_type') == 'smartrecruiters' or 'smartrecruiters.com' in p.get('search_url', '') or 'smartrecruiters.com' in p.get('portal_url', '')]

print(f"Total SmartRecruiters portals: {len(smart_portals)}")

for p in smart_portals:
    p_id = p['id']
    name = p['name']
    # Try different id formats if needed
    for test_id in [p_id, name.replace(' ', '')]:
        api_url = f"https://api.smartrecruiters.com/v1/companies/{test_id}/postings"
        req = urllib.request.Request(
            api_url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        try:
            with urllib.request.urlopen(req, timeout=4) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    print(f"SUCCESS: {name} ({test_id}) -> {len(data.get('content', []))} jobs")
                    break
        except Exception as e:
            pass
    else:
        print(f"FAILED: {name} ({p_id})")
