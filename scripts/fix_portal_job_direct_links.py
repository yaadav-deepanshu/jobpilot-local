#!/usr/bin/env python3
"""
Fix and modernize all Portal Job URLs in SQLite database (instance/jobs.db).
Replaces corporate wrapper homepage/search URLs with direct canonical ATS requisition URLs.
Specifically converts Greenhouse wrapper URLs (e.g. jobs.elastic.co/jobs, stripe.com/jobs/search,
mongodb.com/careers/job, databricks.com/company/careers/open-positions) into authentic
direct links: https://job-boards.greenhouse.io/{token}/jobs/{id}
"""

import sqlite3
import re
import urllib.parse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATHS = [
    PROJECT_ROOT / 'instance' / 'jobs.db',
    PROJECT_ROOT / 'data' / 'jobs.db'
]

GH_TOKEN_MAP = {
    'cloudflare': 'cloudflare', 'twilio': 'twilio', 'mongodb': 'mongodb',
    'elastic': 'elastic', 'dropbox': 'dropbox', 'stripe': 'stripe',
    'airbnb': 'airbnb', 'inmobi': 'inmobi', 'databricks': 'databricks',
    'okta': 'okta', 'gitlab': 'gitlab', 'canonical': 'canonical',
    'figma': 'figma', 'reddit': 'reddit', 'digitalocean': 'digitalocean',
    'hashicorp': 'hashicorp', 'postman': 'postman', 'coinbase': 'coinbase',
    'discord': 'discord', 'grafanalabs': 'grafanalabs', 'pagerduty': 'pagerduty',
    'pinterest': 'pinterest', 'airtable': 'airtable', 'instacart': 'instacart',
    'datadog': 'datadog', 'lyft': 'lyft', 'robinhood': 'robinhood',
    'scaleai': 'scaleai', 'deltek': 'deltek', 'questsoftware': 'questsoftware',
    'docusign': 'docusign', 'workiva': 'workiva', 'himsandhers': 'himsandhers',
    'goinstacare': 'goinstacare', 'abnormalsecurity': 'abnormalsecurity',
    'beekeeper': 'beekeeper', 'faire': 'faire', 'vastdata': 'vastdata'
}

def canonicalize_portal_job_url(company: str, portal_id: str, ats_type: str, url: str) -> str:
    """
    Given a portal job URL, ensure it is a direct, canonical job requisition link
    rather than a corporate homepage or search directory.
    """
    if not url:
        return ""
    
    clean_url = url.strip()
    parsed = urllib.parse.urlparse(clean_url)
    qs = urllib.parse.parse_qs(parsed.query)

    # 1. Greenhouse Job Resolution
    if ats_type == 'greenhouse' or 'greenhouse.io' in clean_url or 'gh_jid' in qs or portal_id in GH_TOKEN_MAP:
        token = GH_TOKEN_MAP.get(portal_id, portal_id)
        gh_id = None
        
        # Check query parameters
        if 'gh_jid' in qs and qs['gh_jid']:
            gh_id = qs['gh_jid'][0]
        # Check path patterns: /jobs/1234567, /positions/1234567, /listing/1234567
        if not gh_id:
            m = re.search(r'/(?:jobs|positions|listing)/(\d+)', parsed.path)
            if m:
                gh_id = m.group(1)

        if gh_id:
            return f"https://job-boards.greenhouse.io/{token}/jobs/{gh_id}"

    # 2. Workday Clean up - ensure deep link
    if 'myworkdayjobs.com' in clean_url:
        # Remove any duplicated parameters
        if parsed.query:
            # Keep clean URL
            clean_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

    # 3. Clean any trailing ? or ?#
    clean_url = re.sub(r'\?(#|$)', r'\1', clean_url)
    return clean_url


def migrate_database(db_path: Path):
    if not db_path.exists():
        return

    print(f"\nProcessing database: {db_path}...")
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # Check if portal_jobs table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='portal_jobs';")
    if not cur.fetchone():
        print(f"Table 'portal_jobs' not found in {db_path}.")
        conn.close()
        return

    cur.execute("SELECT id, company, portal_id, ats_type, url FROM portal_jobs;")
    rows = cur.fetchall()
    print(f"Total portal jobs in table: {len(rows)}")

    updated_count = 0
    for r in rows:
        job_id, company, portal_id, ats_type, old_url = r
        new_url = canonicalize_portal_job_url(company, portal_id, ats_type, old_url)
        if new_url and new_url != old_url:
            cur.execute("UPDATE portal_jobs SET url = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;", (new_url, job_id))
            updated_count += 1

    conn.commit()
    conn.close()
    print(f"✓ Updated {updated_count} jobs in {db_path} with direct canonical URLs.")


def main():
    print("=" * 60)
    print("PORTAL JOBS DIRECT REQUISITION LINK MIGRATION")
    print("=" * 60)
    for p in DB_PATHS:
        migrate_database(p)
    print("\nMigration complete.")


if __name__ == '__main__':
    main()
