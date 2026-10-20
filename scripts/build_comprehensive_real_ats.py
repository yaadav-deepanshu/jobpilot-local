import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import urllib.request
import urllib.parse
import ssl
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json',
}

from scraper.portal_jobs_scanner import PortalJobsScanner
scanner = PortalJobsScanner()

print("="*60)
print("TESTING ALL DIRECT ATS CONNECTORS")
print("="*60)

# 1. Workday
workday_portals = [
    ('broadcom', 'Broadcom / VMware', 'Cloud Hyperscalers & Infrastructure', 'https://broadcom.wd1.myworkdayjobs.com/External_Career'),
    ('redhat', 'Red Hat', 'Cloud Hyperscalers & Infrastructure', 'https://redhat.wd5.myworkdayjobs.com/jobs'),
    ('adobe', 'Adobe', 'Top-Tier SaaS & Enterprise Software', 'https://adobe.wd5.myworkdayjobs.com/external_experienced'),
    ('workday', 'Workday', 'Top-Tier SaaS & Enterprise Software', 'https://workday.wd5.myworkdayjobs.com/workday'),
    ('crowdstrike', 'CrowdStrike', 'Top-Tier SaaS & Enterprise Software', 'https://crowdstrike.wd5.myworkdayjobs.com/crowdstrikecareers'),
    ('mastercard', 'Mastercard', 'Global Capability Centers & FinTech', 'https://mastercard.wd1.myworkdayjobs.com/CorporateCareers'),
    ('rackspace', 'Rackspace Technology', 'Global IT Consultancies & Cloud Partners', 'https://rackspace.wd1.myworkdayjobs.com/External'),
    ('pwc', 'PwC', 'Global IT Consultancies & Cloud Partners', 'https://pwc.wd3.myworkdayjobs.com/Global_Experienced_Careers'),
    ('nvidia', 'Nvidia', 'Semiconductor & Hardware Giants', 'https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite')
]

wd_jobs = []
for p_id, comp, cat, url in workday_portals:
    jobs = scanner._scrape_workday(p_id, comp, cat, url)
    print(f"✓ Workday [{comp}]: {len(jobs)} tech jobs")
    wd_jobs.extend(jobs)

# 2. Greenhouse
gh_targets = [
    ('cloudflare', 'Cloudflare', 'Cloud Hyperscalers & Infrastructure', 'cloudflare'),
    ('twilio', 'Twilio', 'Top-Tier SaaS & Enterprise Software', 'twilio'),
    ('mongodb', 'MongoDB', 'Top-Tier SaaS & Enterprise Software', 'mongodb'),
    ('elastic', 'Elastic', 'Top-Tier SaaS & Enterprise Software', 'elastic'),
    ('dropbox', 'Dropbox', 'Top-Tier SaaS & Enterprise Software', 'dropbox'),
    ('stripe', 'Stripe', 'Global Capability Centers & FinTech', 'stripe'),
    ('airbnb', 'Airbnb', 'High-Growth Tech & Unicorns', 'airbnb'),
    ('inmobi', 'InMobi', 'High-Growth Tech & Unicorns', 'inmobi'),
    ('databricks', 'Databricks', 'Top-Tier SaaS & Enterprise Software', 'databricks'),
    ('okta', 'Okta', 'Top-Tier SaaS & Enterprise Software', 'okta'),
    ('gitlab', 'GitLab', 'Top-Tier SaaS & Enterprise Software', 'gitlab'),
    ('canonical', 'Canonical / Ubuntu', 'Cloud Hyperscalers & Infrastructure', 'canonical'),
    ('figma', 'Figma', 'Top-Tier SaaS & Enterprise Software', 'figma'),
    ('reddit', 'Reddit', 'High-Growth Tech & Unicorns', 'reddit'),
]

gh_jobs = []
for p_id, comp, cat, token in gh_targets:
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    jobs = scanner._scrape_greenhouse(p_id, comp, cat, url)
    print(f"✓ Greenhouse [{comp}]: {len(jobs)} tech jobs")
    gh_jobs.extend(jobs)

# 3. Lever
lever_targets = [
    ('spotify', 'Spotify', 'High-Growth Tech & Unicorns', 'spotify'),
    ('cred', 'Cred', 'High-Growth Tech & Unicorns', 'cred'),
    ('meesho', 'Meesho', 'High-Growth Tech & Unicorns', 'meesho'),
]

lever_jobs = []
for p_id, comp, cat, token in lever_targets:
    url = f"https://jobs.lever.co/{token}"
    jobs = scanner._scrape_lever(p_id, comp, cat, url)
    print(f"✓ Lever [{comp}]: {len(jobs)} tech jobs")
    lever_jobs.extend(jobs)

# 4. SmartRecruiters function
def scrape_smartrecruiters(p_id, comp, cat, comp_id):
    jobs = []
    api_url = f"https://api.smartrecruiters.com/v1/companies/{comp_id}/postings?limit=100"
    try:
        req = urllib.request.Request(api_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            postings = data.get('content', [])
            for p in postings:
                title = p.get('name', '')
                loc_obj = p.get('location', {})
                loc = f"{loc_obj.get('city', '')}, {loc_obj.get('country', '')}".strip(', ') or "Remote"
                job_id = p.get('id', '')
                job_url = f"https://jobs.smartrecruiters.com/{comp_id}/{job_id}"

                # Check if tech role
                if not any(k in title.lower() for k in [
                    'engineer', 'developer', 'devops', 'sre', 'cloud', 'architect',
                    'infrastructure', 'platform', 'systems', 'software', 'site reliability'
                ]):
                    continue

                # We can construct full description if needed or use title
                desc = f"{title} at {comp} in {loc}. Official opening on SmartRecruiters."
                jobs.append({
                    'portal_id': p_id,
                    'company': comp,
                    'category': cat,
                    'title': title,
                    'location': loc,
                    'url': job_url,
                    'description': desc,
                    'ats_type': 'smartrecruiters',
                    'experience_level': 'Junior / Mid'
                })
    except Exception as e:
        print(f"SmartRecruiters error for {comp}: {e}")
    return jobs

sr_targets = [
    ('servicenow', 'ServiceNow', 'Top-Tier SaaS & Enterprise Software', 'ServiceNow'),
    ('westerndigital', 'Western Digital', 'Semiconductor & Hardware Giants', 'WesternDigital'),
    ('freshworks', 'Freshworks', 'High-Growth Tech & Unicorns', 'Freshworks')
]

sr_jobs = []
for p_id, comp, cat, cid in sr_targets:
    jobs = scrape_smartrecruiters(p_id, comp, cat, cid)
    print(f"✓ SmartRecruiters [{comp}]: {len(jobs)} tech jobs")
    sr_jobs.extend(jobs)

# 5. Amazon Jobs function
def scrape_amazon(p_id, comp, cat):
    jobs = []
    for q in ['DevOps', 'Cloud', 'Infrastructure', 'Systems']:
        try:
            api_url = f"https://www.amazon.jobs/en/search.json?base_query={q}&country=IND&result_limit=20"
            req = urllib.request.Request(api_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                for j in data.get('jobs', []):
                    title = j.get('title', '')
                    loc = f"{j.get('city', '')}, {j.get('country_code', '')}" or "Bengaluru, India"
                    job_path = j.get('job_path', '')
                    job_url = f"https://www.amazon.jobs{job_path}"
                    desc = j.get('description_short', '') or j.get('basic_qualifications', '') or title
                    jobs.append({
                        'portal_id': p_id,
                        'company': comp,
                        'category': cat,
                        'title': title,
                        'location': loc,
                        'url': job_url,
                        'description': desc,
                        'ats_type': 'amazon_jobs',
                        'experience_level': 'Direct Requisition'
                    })
        except Exception as e:
            print(f"Amazon jobs query error {q}: {e}")
    # Deduplicate by URL
    seen = set()
    dedup = []
    for j in jobs:
        if j['url'] not in seen:
            seen.add(j['url'])
            dedup.append(j)
    return dedup

amz_jobs = scrape_amazon('amazon_aws', 'Amazon / AWS', 'Cloud Hyperscalers & Infrastructure')
print(f"✓ Amazon Jobs [Amazon / AWS]: {len(amz_jobs)} tech jobs")

all_scraped = wd_jobs + gh_jobs + lever_jobs + sr_jobs + amz_jobs
print(f"\n==========================================")
print(f"TOTAL REAL ATS JOBS SCRAPED: {len(all_scraped)}")
print(f"==========================================")

# Now qualify matching Deepanshu's profile (< 4y experience)
qualified = []
for j in all_scraped:
    is_q, label, max_y = scanner.is_qualified_experience(j['title'], j['description'])
    if is_q:
        skills = scanner.match_resume_skills(f"{j['title']} {j['description']}")
        score = scanner.calculate_match_score(skills, j['title'], j['description'])
        j['matched_skills'] = skills
        j['match_score'] = score
        j['experience_level'] = label
        qualified.append(j)

print(f"TOTAL QUALIFIED (< 4y) REAL JOBS: {len(qualified)}")
print("Sample of 10 qualified jobs with their EXACT URLs:")
for q in qualified[:10]:
    print(f"  [{q['company']}] {q['title']} (Score: {q['match_score']}%, Exp: {q['experience_level']})")
    print(f"    URL: {q['url']}")
