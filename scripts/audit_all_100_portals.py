import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.company_portals import BIG_COMPANY_PORTALS
from scraper.portal_jobs_scanner import PortalJobsScanner

scanner = PortalJobsScanner()

print(f"Total portals in catalog: {len(BIG_COMPANY_PORTALS)}")
ats_counts = {}
for p in BIG_COMPANY_PORTALS:
    ats = p.get('ats_type', 'unknown')
    ats_counts[ats] = ats_counts.get(ats, 0) + 1

print("\nATS Types Breakdown:")
for ats, count in sorted(ats_counts.items(), key=lambda x: -x[1]):
    print(f"  {ats:25}: {count}")

print("\nDetailed Portals by ATS:")
for p in sorted(BIG_COMPANY_PORTALS, key=lambda x: (x.get('ats_type', ''), x['name'])):
    p_id = p['id']
    name = p['name']
    ats = p.get('ats_type', 'unknown')
    url = p.get('search_url', p.get('portal_url', ''))
    print(f"{p_id:20} | {name:25} | ATS: {ats:20} | URL: {url}")
