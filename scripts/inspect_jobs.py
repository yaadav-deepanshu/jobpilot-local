import sqlite3
import requests

conn = sqlite3.connect("instance/jobs.db")
c = conn.cursor()

c.execute("SELECT id, company, title, ats_type, url, description FROM portal_jobs ORDER BY id ASC")
rows = c.fetchall()

templated_ids = []
real_ids = []

for r in rows:
    j_id, company, title, ats, url, desc = r
    is_tpl = any(p in desc for p in [
        "is hiring a Cloud DevOps Engineer",
        "Core Reliability and Production Engineering",
        "Infrastructure & Platform Engineer",
        "Cloud Operations Architect",
        "Systems Engineer 1 focused on AWS"
    ])
    if is_tpl:
        templated_ids.append(r)
    else:
        real_ids.append(r)

print(f"Total jobs: {len(rows)}")
print(f"Templated jobs: {len(templated_ids)}")
print(f"Real scraped jobs: {len(real_ids)}")

print("\n--- SAMPLE REAL SCRAPED JOBS ---")
for r in real_ids[:15]:
    print(f"#{r[0]}: [{r[1]}] {r[2]} ({r[3]})\n  URL: {r[4]}")

print("\n--- SAMPLE TEMPLATED JOBS ---")
for r in templated_ids[:10]:
    print(f"#{r[0]}: [{r[1]}] {r[2]} ({r[3]})\n  URL: {r[4]}")
