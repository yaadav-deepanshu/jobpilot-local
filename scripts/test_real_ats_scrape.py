import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.portal_jobs_scanner import PortalJobsScanner

scanner = PortalJobsScanner()

print("Testing direct ATS scraping across companies...")

# Test Greenhouse
gh_targets = [
    ('cloudflare', 'Cloudflare', 'Cloud Hyperscalers & Infrastructure', 'https://boards-api.greenhouse.io/v1/boards/cloudflare/jobs?content=true'),
    ('twilio', 'Twilio', 'Top-Tier SaaS & Enterprise Software', 'https://boards-api.greenhouse.io/v1/boards/twilio/jobs?content=true'),
    ('mongodb', 'MongoDB', 'Top-Tier SaaS & Enterprise Software', 'https://boards-api.greenhouse.io/v1/boards/mongodb/jobs?content=true'),
    ('elastic', 'Elastic', 'Top-Tier SaaS & Enterprise Software', 'https://boards-api.greenhouse.io/v1/boards/elastic/jobs?content=true'),
    ('dropbox', 'Dropbox', 'Top-Tier SaaS & Enterprise Software', 'https://boards-api.greenhouse.io/v1/boards/dropbox/jobs?content=true'),
    ('stripe', 'Stripe', 'Global Capability Centers & FinTech', 'https://boards-api.greenhouse.io/v1/boards/stripe/jobs?content=true'),
    ('airbnb', 'Airbnb', 'High-Growth Tech & Unicorns', 'https://boards-api.greenhouse.io/v1/boards/airbnb/jobs?content=true'),
    ('inmobi', 'InMobi', 'High-Growth Tech & Unicorns', 'https://boards-api.greenhouse.io/v1/boards/inmobi/jobs?content=true'),
    ('databricks', 'Databricks', 'Top-Tier SaaS & Enterprise Software', 'https://boards-api.greenhouse.io/v1/boards/databricks/jobs?content=true'),
]

gh_jobs = []
for p_id, comp, cat, url in gh_targets:
    jobs = scanner._scrape_greenhouse(p_id, comp, cat, url)
    print(f"Greenhouse [{comp}]: Found {len(jobs)} tech jobs")
    gh_jobs.extend(jobs)

# Test Lever
lever_targets = [
    ('spotify', 'Spotify', 'High-Growth Tech & Unicorns', 'https://jobs.lever.co/spotify'),
    ('cred', 'Cred', 'High-Growth Tech & Unicorns', 'https://jobs.lever.co/cred'),
    ('meesho', 'Meesho', 'High-Growth Tech & Unicorns', 'https://jobs.lever.co/meesho'),
]

lever_jobs = []
for p_id, comp, cat, url in lever_targets:
    jobs = scanner._scrape_lever(p_id, comp, cat, url)
    print(f"Lever [{comp}]: Found {len(jobs)} tech jobs")
    lever_jobs.extend(jobs)

# Test Workday
workday_targets = [
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
for p_id, comp, cat, url in workday_targets:
    jobs = scanner._scrape_workday(p_id, comp, cat, url)
    print(f"Workday [{comp}]: Found {len(jobs)} tech jobs")
    wd_jobs.extend(jobs)

all_real = gh_jobs + lever_jobs + wd_jobs
print(f"\nTotal real ATS jobs scraped: {len(all_real)}")

# Now test qualification (< 4y)
qualified = []
for j in all_real:
    is_q, label, max_y = scanner.is_qualified_experience(j['title'], j['description'])
    if is_q:
        skills = scanner.match_resume_skills(f"{j['title']} {j['description']}")
        score = scanner.calculate_match_score(skills, j['title'], j['description'])
        j['matched_skills'] = skills
        j['match_score'] = score
        qualified.append(j)

print(f"Total qualified (< 4y) real ATS jobs: {len(qualified)}")
