# 🎯 Hybrid Job Finder + Filter Tool

> Safe, semi-automated job discovery and one-click apply system
> No account bans, no ToS violations — you review before applying

## Features

✅ **Job Discovery Across Platforms**
- LinkedIn (via scraping)
- Indeed
- Naukri.com
- Glassdoor
- Wellfound

✅ **Smart Filtering**
- Skip jobs with > 100 applicants
- Match by role, location, experience
- Exclude keywords (internship, volunteer, etc.)
- Salary range filtering

✅ **AI Resume Tailoring**
- Uses Claude/OpenAI to tailor your resume per job
- Extracts keywords from job description
- Highlights matching skills

✅ **Safe Manual Apply**
- One-click apply links (opens job posting)
- Pre-fills resume data into application forms
- You stay in control — never auto-submits

✅ **Dashboard**
- View all filtered jobs
- Mark as applied, rejected, saved
- Export to CSV

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up your profile
cp config.example.yaml config.yaml
# Edit config.yaml with your details + API keys

# 3. Run the server
python main.py

# 4. Open http://localhost:5000
```

## Architecture

```
job-finder/
├── scraper/              # Job collection from platforms
│   ├── linkedin.py
│   ├── indeed.py
│   ├── naukri.py
│   └── glassdoor.py
├── filter/               # Filtering logic
│   └── engine.py
├── ai/                   # AI/LLM integrations
│   ├── resume_tailor.py
│   └── llm.py
├── db/                   # SQLite for job tracking
│   └── models.py
├── web/                  # Flask dashboard
│   ├── app.py
│   └── templates/
├── config.yaml           # Your settings
└── main.py               # Entry point
```

## Configuration

Edit `config.yaml`:

```yaml
profile:
  name: "Deepanshu Yadav"
  email: "yaadav.deepanshu@gmail.com"
  phone: "+91 8728081860"
  resume_file: "resume.pdf"

search:
  roles:
    - "Cloud Engineer"
    - "DevOps Engineer"
    - "SRE"
  location: "Bengaluru"
  remote: true
  max_applicants: 100

ai:
  provider: "anthropic"  # or "openai"
  api_key: "${CLAUDE_API_KEY}"
  model: "claude-3-5-sonnet-20241022"

platforms:
  linkedin:
    enabled: true
  indeed:
    enabled: true
  naukri:
    enabled: true
  glassdoor:
    enabled: true
```

## Workflow

1. **Scrape** — Fetch latest jobs from enabled platforms
2. **Filter** — Keep only matching jobs (role, location, applicants < 100)
3. **Tailor** — AI generates resume summary highlighting relevant skills
4. **Review** — Open dashboard, review jobs with tailored resume preview
5. **Apply** — Click "Apply" → redirects to job posting with pre-filled form data
6. **Track** — Mark as applied/rejected in dashboard

## Safety

✅ **Never auto-submits** — you always review and click apply manually
✅ **No credential storage** — uses OAuth/API keys, never stores passwords
✅ **Respects platform ToS** — uses official APIs where available, respects robots.txt
✅ **Rate limiting** — built-in delays to avoid blocking
✅ **No account automation** — just finds and filters, you handle applying

## Technologies

- **Backend**: Python 3.11, Flask
- **Scraping**: JobSpy (official multi-platform scraper)
- **AI**: Claude API / OpenAI
- **DB**: SQLite
- **Frontend**: React / vanilla JS + Bootstrap
- **Task Scheduling**: APScheduler (for recurring scrapes)

## Next Steps

1. Install dependencies: `pip install -r requirements.txt`
2. Configure: edit `config.yaml`
3. Add your Claude/OpenAI API key
4. Run: `python main.py`
5. Open browser to `http://localhost:5000`

---

**Questions?** Check the docs or open an issue.
