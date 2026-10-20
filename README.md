# 🎯 JobPilot — Autonomous Cloud & DevOps Job Intelligence Platform

> **High-Signal Job Discovery, Direct Enterprise Portal Scanner, Resume Match Scoring & Semi-Automated Application Engine**  
> Tailored specifically for **Cloud / DevOps / SRE / Platform Engineering** profiles (0–4 years experience cap).

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)](https://flask.palletsprojects.com/)
[![Tests](https://img.shields.io/badge/Tests-136%20Passed%20(100%25)-success)](#automated-testing)
[![Portals](https://img.shields.io/badge/Enterprise%20Portals-100%20Companies-indigo)](#enterprise-career-portals)
[![Experience Cap](https://img.shields.io/badge/Experience%20Cap-%3C%204%20Years-emerald)](#strict-experience-cap)

---

## ⚡ Key Highlights & Core Capabilities

### 1. 🏢 Enterprise Career Portal Jobs Scanner (`/portal-jobs`)
Directly scans and scrapes job postings straight from official enterprise ATS platforms and company career boards:
- **100 Big Company Portals** across 6 key industries (Hyperscalers, Enterprise SaaS, Global Capability Centers & FinTech, Unicorns, Consultancies, and Semiconductor Giants).
- **24 Specialized Tech Job Websites** (RemoteOK, Y Combinator Work at a Startup, DevOpsJobs, Remotive, WeWorkRemotely, Wellfound, etc.).
- **ATS Platform Connectors**: Automated deep links and query formulation for Workday, Greenhouse, Lever, SmartRecruiters, Taleo, SuccessFactors, and custom enterprise portals.

### 2. 🎯 Strict Experience Qualification (< 4 Years Cap)
Automated filter engine that enforces candidate career level constraints:
- **Hard Exclusions**: Automatically rejects any posting with senior-level prefixes (`Senior`, `Sr.`, `Lead`, `Principal`, `Staff`, `Director`, `Manager`, `VP`, `Head of`).
- **Experience Requirement Gate**: Evaluates regex patterns to discard roles requiring $\ge 5$ years (`5+ years`, `7+ years`, `min 6 years`, `5-8 years`).
- **Qualified Range**: Qualifies entry and mid-level roles (`0-2 years`, `1-3 years`, `2-4 years`, `3-4 years`, `freshers`, `associate`, `junior`).

### 3. 🧠 Resume Skill Matching & Match Scoring
Extracts candidate technical stack directly from Deepanshu Yadav's verified resume (Swiggy System Engineer 1, Starwatt Cloud Engineer, AWS Certified Developer – Associate):
- **Core Technologies**: AWS, Docker, Kubernetes, Terraform, CloudFormation, CI/CD, Python, Linux, Bash, Prometheus, Grafana, IAM, VPC, Jenkins, GitHub Actions.
- **Weighted Scoring Algorithm**: Generates a dynamic $0-100\%$ match score for every opportunity with color-coded badges ($90\%+$ emerald, $75-89\%$ cyan, $60-74\%$ amber).

### 4. ♾️ Dual-Mode Pagination (Infinite Scroll + Classic Pages)
Seamless pagination on both the Primary Dashboard (`/`) and the Portal Jobs Dashboard (`/portal-jobs`):
- **Mode Toggle**: Switch between **Infinite Scroll** and **Classic Pages** with your preference preserved in `localStorage`.
- **Infinite Scroll**: Auto-loads batches as you scroll via `IntersectionObserver`, featuring progress indicators, count tickers, and a fallback "Load More" button.
- **Classic Pages**: Traditional pagination with page number buttons (`1`, `2`, `3`, ..., `N`), items-per-page selector (`15`, `25`, `50`, `100`), and smooth auto-scroll to results top.
- **Floating Back-to-Top**: Quick-return button for fast navigation.

### 5. 🌐 Multi-Platform Aggregated Scraper
Collects postings across standard job boards:
- LinkedIn, Indeed, Naukri, Glassdoor, and ZipRecruiter via JobSpy.
- **Discovery Window Scrapes**: Filter and scrape fresh opportunities within the last 4h, 8h, 12h, 24h, 48h, or 72 hours.
- Automatic purge of legacy or over-subscribed postings ($>100$ applicants).

### 6. 📊 Multi-Format Reporting & Exports
Export filtered opportunities on demand:
- **Excel (`.xlsx`)**: Formatted spreadsheets with match scores, requirements, and direct application links.
- **PDF Report (`.pdf`)**: Formatted executive document ready for offline tracking.
- **Interactive HTML Report (`.html`)**: Self-contained web view for sharing.

---

## 🧭 Application URL Directory

| Route / Interface | Description |
|---|---|
| [`http://127.0.0.1:5050`](http://127.0.0.1:5050) | **Primary Dashboard**: Aggregated job feed, radar scrapes, hourly discovery filters |
| [`http://127.0.0.1:5050/portal-jobs`](http://127.0.0.1:5050/portal-jobs) | **Portal Jobs (< 4y)**: Scanned career portal opportunities scored against candidate resume |
| [`http://127.0.0.1:5050/portals`](http://127.0.0.1:5050/portals) | **Portals Catalog**: Directory of 100 enterprise portals & 24 specialized tech boards |
| [`http://127.0.0.1:5050/jobs`](http://127.0.0.1:5050/jobs) | **Tabular Grid View**: Dense spreadsheet-like inspection view |
| [`http://127.0.0.1:5050/api/portal-jobs`](http://127.0.0.1:5050/api/portal-jobs) | **REST API**: JSON endpoint for filtering, searching, and pagination |

*(Note: If port 5050 is in use, the application automatically supports companion port 5000 or any custom port configured via `PORT=5051`).*

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.11** or **Python 3.12**
- Git

### 2. Clone & Install
```bash
# Clone the repository
git clone https://github.com/yaadav-deepanshu/jobpilot-local.git
cd jobpilot-local

# Create and activate a virtual environment
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 3. Configuration
The repository includes a default `config.yaml` with pre-tuned search roles, skill taxonomies, and portal catalogs:
```yaml
profile:
  name: "Deepanshu Yadav"
  email: "yaadav.deepanshu@gmail.com"
  phone: "+91 8728081860"
  experience_years: 3
  max_experience_target: 4

search:
  roles:
    - "Cloud Engineer"
    - "DevOps Engineer"
    - "Site Reliability Engineer"
    - "Platform Engineer"
    - "Infrastructure Engineer"
    - "Cloud Operations Architect"
  location: "Bengaluru"
  max_applicants: 100
  experience_cap_years: 4
```

### 4. Run the Application

**Standard Run (Ports 5050 & 5000):**
```bash
python main.py
```

**Run on a Custom Port (e.g., 5051):**
```powershell
# Windows PowerShell
$env:PORT="5051"; python main.py

# Linux / macOS
PORT=5051 python3 main.py
```

---

## 🧪 Automated Testing

The project includes a comprehensive automated test suite covering all scrapers, database models, ATS connectors, experience filters, rollback utilities, template null safety, and frontend JavaScript syntax:

```bash
# Run all tests
pytest tests/test_all.py -v

# Run only portal jobs scanner tests
pytest tests/test_all.py -k "TestPortalJobsScanner" -v
```

**Test Suite Coverage Summary:**
- **136 total tests** passing ($100\%$ success rate).
- Validates:
  - Rollback safeguards and backup integrity (`revert_portal_jobs.py`).
  - Strict $<4\text{y}$ experience qualification and senior title exclusion.
  - Candidate resume skill extraction and weighted scoring formula.
  - SQLAlchemy model CRUD, serialization, and status updates (`new`, `applied`, `saved`, `rejected`).
  - Web routes, URL aliases, and slash variations returning HTTP 200.
  - REST API filtering, pagination, and stats aggregation.
  - Direct career openings and verified search links across all 100 enterprise portals and 24 specialized sites.
  - Template null safety and frontend JavaScript syntax verification via `node --check`.

---

## 📂 Project Architecture

```
jobpilot-local/
├── db/
│   ├── models.py                   # SQLAlchemy ORM (Job, PortalJob, AuditLog)
│   └── __init__.py
├── scraper/
│   ├── portal_jobs_scanner.py      # Direct enterprise portal scanner (<4y qualification)
│   ├── company_portals.py          # 100 enterprise career portals catalog & ATS URLs
│   ├── websites_scraper.py         # 24 specialized tech job websites directory
│   ├── multi_platform.py           # Multi-board aggregator (JobSpy)
│   └── flexible_scraper.py         # Hourly discovery window radar scraper
├── filter/
│   ├── engine.py                   # Regex keyword matching & experience qualification
│   └── flexible_engine.py          # Word-boundary filtering rules
├── web/
│   ├── app.py                      # Flask factory & blueprint registration
│   ├── routes.py                   # View routes & REST API endpoints
│   └── templates/
│       ├── base.html               # Shared navbar & footer layout
│       ├── index.html              # Primary dashboard with radar scrapes & infinite scroll
│       ├── portal_jobs.html        # Enterprise career portals dashboard (<4y exp)
│       ├── portals.html            # 100 Companies + 24 Tech Sites directory
│       └── jobs.html               # Tabular grid view
├── export/
│   ├── jobs_exporter.py            # Excel, PDF, and HTML report generation
│   └── routes.py                   # Export download endpoints
├── tests/
│   └── test_all.py                 # 136 comprehensive test cases
├── memory/                         # Persistent architecture & context tracking
│   ├── MEMORY.md                   # Auto-memory index
│   ├── portal-jobs-scanner.md      # Portal jobs scanner architecture & filters
│   └── user-profile.md             # Candidate experience profile & preferences
├── config.yaml                     # Application settings & search parameters
├── main.py                         # Server entrypoint with dual-port listener
└── revert_portal_jobs.py           # 1-click safety rollback script
```

---

## 🛡️ Safety, Privacy & Rollback Guarantees

- **No Credential Harvesting**: Never stores platform passwords; application links navigate directly to official career pages.
- **Never Auto-Submits**: You stay in control — click "Apply" to open the official company career portal with verified match insights.
- **Built-in Rollback Script**: `revert_portal_jobs.py` allows instant 1-click reversion of the portal jobs feature from `.portal_jobs_backup` snapshots if ever needed.
- **Fail-Safe Startup**: Cleans legacy unqualified postings and creates SQLite schema automatically.

---

## 👥 Authors & Attribution

- **Candidate Profile**: Deepanshu Yadav ([yaadav.deepanshu@gmail.com](mailto:yaadav.deepanshu@gmail.com))
- **Engineered with**: Claude Code (`Co-Authored-By: Claude Code <noreply@anthropic.com>`)
- **License**: MIT
