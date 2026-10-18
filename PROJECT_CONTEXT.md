# Job Finder — Project Context & System Architecture

**Last Updated:** October 10, 2026  
**Status:** Fully functional, 100% automated test pass rate (46/46 tests passing), interactive time-window slider (2h, 6h, 12h, 24h), platform priority sorting (LinkedIn → Indeed → Naukri → Rest), strict 0–4 year experience cap, ≤ 100 applicants limit, abroad platform integration, and one-command snapshot rollback.

---

## 1. Candidate Profile & Search Criteria
* **User:** Deepanshu Yadav (`yaadav.deepanshu@gmail.com`)
* **Experience Level:** **3 years of professional experience** in Cloud / DevOps / SRE.
* **Target Experience Range:** **0 to 4 years** (Junior, Associate, and Mid-level Engineer roles).
* **Target Roles:**
  * Cloud Engineer
  * DevOps Engineer
  * Site Reliability Engineer (SRE)
  * Platform Engineer
  * Systems Engineer
* **Target Location:** Bengaluru / India (with Remote & Hybrid enabled).
* **Strict Exclusions:**
  * Postings requiring **5+, 6+, 7+, 8+, 10+ years** of experience.
  * Senior titles: `Senior`, `Sr.`, `Sr `, `Lead`, `Principal`, `Staff`, `Architect`, `Director`, `VP`, `AVP`, `Head of`.
  * Job postings with **> 100 applicants** or marked "over 100 people clicked apply".
  * Negative keywords: `internship`, `volunteer`, `unpaid`, `part-time`.

---

## 2. System Architecture

```
G:\Geonix\vscode\ai\job-finder\
├── config.yaml               # User search configuration, filters, roles, platforms
├── main.py                   # App entry point (configurable PORT/HOST, UTF-8 logging)
├── scheduler.py              # APScheduler periodic background scraping
├── db/
│   └── models.py             # SQLAlchemy models (Job, ApplicationLog, init_db)
├── scraper/
│   └── multi_platform.py     # RealJobScraper (JobSpy: LinkedIn, Indeed, Naukri with fetch_description=True & NaN safety)
├── filter/
│   └── engine.py             # FilterEngine (experience 0-4y regex, senior exclusions, applicant threshold, deduplication)
├── web/
│   ├── app.py                # Flask app factory (create_app)
│   ├── routes.py             # Views (/, /jobs), API endpoints (/api/scrape, /api/flexible-scrape, /api/bulk-scrape, /api/stats, etc.)
│   └── templates/
│       ├── index.html        # Modern indigo-gradient dashboard, live status monitor, timer, filters
│       └── jobs.html         # Full tabular view with platform badges, filters, and direct application links
├── export/
│   ├── jobs_exporter.py      # JobExporter (multi-sheet Excel, ReportLab PDF, interactive Chart.js HTML)
│   └── routes.py             # Export download endpoints (/export/download/excel, /pdf, /html)
├── backup_snapshot/          # Standalone safety backup snapshot of verified working state
├── revert_to_snapshot.py     # Instant one-command rollback script
└── tests/
    └── test_all.py           # 46 automated unit & end-to-end integration tests (100% pass)
```

---

## 3. Key Features & Protections Implemented

1. **Interactive Time-Window Slider (2h, 6h, 12h, 24h):**
   * Intuitive frontend slider component with discrete stops at **2 hours, 6 hours, 12 hours, and 24 hours**.
   * Allows the candidate to target newly posted jobs before they accumulate high applicant counts.
   * Selected window seamlessly forwards `hours_old` to JobSpy upstream scraper and `max_hours` to `FilterEngine` recency validator.
   * Retains dual options for window scrape and full all-time scrape.

2. **Platform Priority Sorting (LinkedIn → Indeed → Naukri → Rest):**
   * Strictly prioritizes postings by platform tier:
     1. **LinkedIn** postings appear first.
     2. **Indeed** postings appear second.
     3. **Naukri** postings appear third.
     4. **Rest** (Glassdoor, ZipRecruiter, Google Jobs, Bayt, etc.) follow.
   * Secondary sort within each platform tier orders postings chronologically by newest first (`date_posted.desc()`, `created_at.desc()`).
   * Enforced at the SQL query layer (`get_sorted_job_query` via SQLAlchemy `case`) and replicated in Python memory sorting (`_sort_by_platform_priority`) across dashboard, table view, APIs, and Excel/PDF/HTML exporters.

3. **Strict 0–4 Year Experience Cap & Exclusion of Senior Titles:**
   * Absolute cap of 4 years maximum required experience (`max_experience_years: 4`).
   * Eliminates postings requiring 5+, 6+, 7+, 8+, 10+ years or ranges like 5–8 years, 6–9 years.
   * Excludes titles with `Senior`, `Sr.`, `Sr `, `Lead`, `Principal`, `Staff`, `Architect`, `Director`, `Manager`, `Head of`, `VP`, `Vice President`.
   * Enforced at 3 layers: Ingestion filtering (`FilterEngine`), database hygiene (`purge_unqualified_jobs`), and SQL query gating (`get_filtered_job_query` with SQL NULL safety).

4. **Strict Applicant Limit (≤ 100 Applicants):**
   * Drops any job exceeding 100 applicants numerically.
   * Parses textual indicators ("over 100 people clicked apply", "over 100 applicants", "100+ applicants") and flags them as 101 applicants to guarantee rejection.
   * Gated at database query time so jobs with > 100 applicants never appear on the dashboard, `/jobs` table, or export files.

5. **Expanded Abroad Job Search Platforms:**
   * Supported via JobSpy: **ZipRecruiter** (US, UK, Canada), **Google Jobs** (worldwide aggregator), and **Bayt** (Middle East / Gulf region), alongside LinkedIn, Indeed, Naukri, and Glassdoor.
   * Includes platform badges (`.badge-zip_recruiter`, `.badge-google`, `.badge-bayt`) and filter dropdown options.

6. **One-Command Safety Snapshot & Rollback:**
   * Standalone backup snapshot directory `backup_snapshot/` preserving clean state and database.
   * Rollback script `revert_to_snapshot.py` to restore working state instantly:
     ```bash
     python revert_to_snapshot.py
     ```

7. **Scraper Progress & Timer:**
   * Robust NaN handling in pandas data normalization.
   * Live status monitor (`/api/scrape-status`) with real client-side timer (`⏱️ M:SS`).

8. **Location Segregation Toggles (Remote / Bengaluru / Both):**
   * UI toggles and filter support across dashboard, jobs table, and API queries.
   * Allows the user to segregate jobs into **Remote Only**, **Bengaluru Only**, or **Both (Bengaluru & Remote)**.
   * SQL query filtering dynamically isolates postings matching remote indicators or Bengaluru/Bangalore location.

---

## 4. Running & Verification

### Run Automated Tests
```bash
pytest tests/test_all.py -v
```
*(All 50 tests pass with 100% pass rate)*

### Start Application
```bash
python main.py
```
* **Dashboard:** [http://127.0.0.1:5050](http://127.0.0.1:5050)
* **Table View:** [http://127.0.0.1:5050/jobs](http://127.0.0.1:5050/jobs)
* **Stats API:** `GET /api/stats`
* **Scrape Endpoints:** `POST /api/flexible-scrape`, `POST /api/bulk-scrape`, `POST /api/scrape`
* **Exports:** `/export/download/excel`, `/export/download/pdf`, `/export/download/html`
* **Rollback Script:** `python revert_to_snapshot.py`
