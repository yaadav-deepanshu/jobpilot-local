# 🚀 Getting Started — Job Finder Setup Guide

## Prerequisites

- Python 3.9+
- Windows 11 (or Linux/Mac)
- API key: Claude (Anthropic) **or** OpenAI GPT-4

## Step 1: Set Up Environment Variables

### Windows PowerShell
```powershell
$env:CLAUDE_API_KEY = "sk-ant-..."  # Get from https://console.anthropic.com
# Or for OpenAI:
$env:OPENAI_API_KEY = "sk-..."      # Get from https://platform.openai.com
```

### Linux/Mac
```bash
export CLAUDE_API_KEY="sk-ant-..."
# Or:
export OPENAI_API_KEY="sk-..."
```

## Step 2: Install Dependencies

```bash
cd G:\Geonix\vscode\ai\job-finder
pip install -r requirements.txt
```

This installs:
- Flask (web framework)
- SQLAlchemy (database ORM)
- python-jobspy (multi-platform scraper)
- anthropic / openai (AI APIs)
- APScheduler (background jobs)
- pyyaml (configuration)
- requests, BeautifulSoup (web scraping)

## Step 3: Create Configuration

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` and fill in:

```yaml
profile:
  name: "Deepanshu Yadav"
  email: "yaadav.deepanshu@gmail.com"
  phone: "+91 8728081860"
  resume_file: "resume.pdf"  # Put your resume in this directory

search:
  roles:
    - "Cloud Engineer"
    - "DevOps Engineer"
    - "SRE"
  location: "Bengaluru"
  remote: true
  max_applicants: 100  # ← YOUR FILTER

ai:
  provider: "anthropic"  # Choose one
  anthropic_api_key: "${CLAUDE_API_KEY}"
  anthropic_model: "claude-3-5-sonnet-20241022"

platforms:
  linkedin: { enabled: true }
  indeed: { enabled: true }
  naukri: { enabled: true }
  glassdoor: { enabled: true }
  wellfound: { enabled: true }
  cutshort: { enabled: true }
  foundit: { enabled: true }
```

## Step 4: Start the App

```bash
python main.py
```

You should see:
```
2026-10-09 08:30:00 - root - INFO - 🎯 Starting Job Finder...
2026-10-09 08:30:00 - root - INFO - ✓ Database initialized
2026-10-09 08:30:00 - root - INFO - ✓ Scheduler configured
============================================================
Job Finder is running!
============================================================
📱 Open your browser: http://127.0.0.1:5000
============================================================
```

## Step 5: Open Dashboard

Go to: **http://127.0.0.1:5000**

You should see:
- 📊 Dashboard with job counts
- 🎯 Recent jobs from all platforms
- 🔄 "Scrape Now" button to manually fetch jobs
- 📋 View All Jobs link to browse all filtered jobs

## Step 6: First Scrape

Click **"Scrape Now"** on the dashboard.

The app will:
1. 🔍 Scrape all 7 platforms
2. 🔎 Filter by your criteria (role, location, <100 applicants)
3. 🤖 (Optional) Generate AI-tailored resume for each
4. 💾 Save to local database

Wait 30-60 seconds for results to appear.

## Step 7: Review Jobs

Click **"📋 View All Jobs"** to see:
- Job title, company, location
- Platform badge (LinkedIn, Naukri, etc.)
- Number of applicants
- Posted date

## Step 8: Apply to a Job

Click any job card to:
1. See full details
2. View AI-tailored resume (highlights matching skills)
3. Click "Apply" → Opens job posting on platform
4. You apply manually (this keeps you safe from bans)
5. Mark as "Applied" when done

## Step 9: Track Applications

Back on job list:
- Mark jobs as: `Applied`, `Rejected`, `Saved`, `Pending`
- Add notes (e.g., "Waiting for response", "Interview scheduled")
- View all your applications in stats

## Automatic Scraping

After setup, the app will:
- ✅ Scrape every 6 hours automatically
- ✅ Save new jobs to database
- ✅ Run in background while you do other things
- ✅ Log all activity to `job_finder.log`

To change interval, edit `config.yaml`:
```yaml
scheduler:
  scrape_interval_hours: 6  # Change to 3, 12, 24, etc.
```

## Common Tasks

### Export Jobs to CSV
```python
import pandas as pd
from db.models import Job

jobs = Job.query.all()
df = pd.DataFrame([job.to_dict() for job in jobs])
df.to_csv('jobs_export.csv', index=False)
```

### View Logs
```bash
tail -f job_finder.log  # Linux/Mac
Get-Content job_finder.log -Tail 20  # PowerShell
```

### Stop the App
Press `Ctrl+C` in terminal

### Reset Database
```bash
rm jobs.db  # Linux/Mac
Remove-Item jobs.db  # PowerShell
python main.py  # Recreates empty database
```

## Troubleshooting

**"ModuleNotFoundError: No module named 'flask'"**
```bash
pip install -r requirements.txt
```

**"Failed to connect to Anthropic API"**
- Check `CLAUDE_API_KEY` is set
- Verify API key is valid
- Check internet connection

**"Port 5000 already in use"**
```bash
# Find what's using it
netstat -ano | findstr :5000
# Kill it
taskkill /PID <PID> /F
```

**"Jobs not showing up after scrape"**
- Check `config.yaml` platforms are enabled
- Check filters aren't too strict
- Verify `max_applicants: 100` is appropriate
- Check logs: `job_finder.log`

## Next Steps

1. ✅ Run for 1 week, let it auto-scrape
2. ✅ Review jobs daily on dashboard
3. ✅ Apply manually to 5-10 per day
4. ✅ Track responses to see what works
5. ✅ Adjust filters based on quality
6. ✅ (Optional) Build more features

---

**Questions?** Check `README.md` or the context files in `G:\Geonix\vscode\ai\.context\`
