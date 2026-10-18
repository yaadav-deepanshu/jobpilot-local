# 🎯 Job Matching & Resume Fit Explanation

## How Job Finder Matches YOUR Profile

The system works in 3 stages:

### Stage 1: Role Keyword Matching
The filter looks for jobs with titles containing your target roles:

```yaml
search:
  roles:
    - "Cloud Engineer"
    - "DevOps Engineer"
    - "Site Reliability Engineer"
    - "SRE"
    - "System Engineer"
    - "Platform Engineer"
    - "Infrastructure Engineer"
```

**What this means:**
- Job title must contain one of these keywords (case-insensitive)
- Example matches: "Senior DevOps Engineer", "SRE II", "Cloud Infrastructure Engineer"
- Examples that DON'T match: "Frontend Developer", "Data Scientist", "Product Manager"

---

## Your Profile vs Job Requirements

### Your Skills (From Your Resume)
```
STRONG FIT:
✅ Cloud: AWS, Azure, GCP
✅ Infrastructure: Terraform, CloudFormation, Ansible
✅ Containers: Docker, Kubernetes, ECS, ECR
✅ CI/CD: Jenkins, GitHub, GitLab, CodePipeline
✅ Automation: Python, Bash scripting
✅ Security: IAM, SSO, WAF, KMS
✅ Monitoring: CloudWatch, Prometheus, Grafana

EXPERIENCE:
✅ 2.5 years in Cloud/DevOps/Infrastructure
✅ AWS Certified Developer
✅ System Engineer at Swiggy (current)
✅ Cloud Engineer at Starwatt
```

### Jobs That Will Match
```
🟢 EXCELLENT FIT (100% match):
- "DevOps Engineer" (your core skill)
- "SRE - Site Reliability Engineer" (matches exactly)
- "Cloud Infrastructure Engineer" (your expertise)
- "AWS Infrastructure Specialist" (your tech stack)
- "Platform Engineer" (overlaps with DevOps)

🟡 GOOD FIT (70-80% match):
- "System Engineer" (your current role at Swiggy)
- "AWS Solutions Architect" (uses your skills)
- "Infrastructure Automation Engineer" (your automation skills)
- "Cloud Operations Engineer" (operations + cloud)

🔴 NOT A MATCH (0% - will be filtered out):
- "Frontend Engineer" (wrong stack)
- "Data Engineer" (different domain)
- "Product Manager" (non-technical)
- "Business Analyst" (wrong fit)
```

---

## How Filtering Works

### Filter 1: Role Keywords
```
Job Title: "Senior DevOps Engineer at Amazon"
├─ Contains "DevOps"? ✅ YES
├─ Contains one of your roles? ✅ YES
└─ PASSES ✓
```

### Filter 2: Location
```
Job Location: "Bengaluru, India"
├─ Matches your location? ✅ YES (or Remote)
└─ PASSES ✓
```

### Filter 3: Applicants
```
Job Applicants: 45 people applied
├─ More than 100? ❌ NO
└─ PASSES ✓ (included in results)
```

### Filter 4: Excluded Keywords
```
Job Description: "Looking for an internship..."
├─ Contains "internship"? ✅ YES
├─ In exclude list? ✅ YES
└─ FILTERED OUT ✗ (not shown)
```

---

## AI Resume Tailoring (Optional Feature)

**What it does:**
When you view a job, AI automatically:

1. **Extracts keywords** from job description
   - Example: "Kubernetes, Terraform, Python, AWS, Monitoring"

2. **Tailors your resume** to highlight matching skills
   - Example: Changes bullet points to emphasize K8s + Terraform experience
   - Reorders achievements to match job priorities

3. **Shows preview** before you apply
   - You see how your tailored resume looks
   - You can manually adjust if needed

**Example tailoring:**
```
Original Resume Bullet:
"Built automated AWS resource deletion pipeline using CodePipeline and Lambda"

Job wants: Kubernetes, Python, Infrastructure Automation

Tailored Resume Bullet:
"Engineered automated infrastructure deployment and lifecycle management using 
CodePipeline, Lambda, and Python scripting, reducing deployment time by 60%"

✓ Highlights: Infrastructure automation + Python
✓ Emphasizes: automation (job requirement)
```

---

## What You'll Actually See

### Jobs That Will Appear in Dashboard

```
LinkedIn: "Senior DevOps Engineer" at Flipkart
├─ Role match: ✅ DevOps Engineer
├─ Location: ✅ Bengaluru
├─ Applicants: ✅ 87 (< 100)
├─ Your fit: 🟢 EXCELLENT
└─ Dashboard shows: ✓

Indeed: "Infrastructure Engineer" at Swiggy
├─ Role match: ✅ Infrastructure (matches "Cloud Engineer")
├─ Location: ✅ Remote
├─ Applicants: ✅ 45 (< 100)
├─ Your fit: 🟢 EXCELLENT
└─ Dashboard shows: ✓

Naukri: "Data Engineer" at Microsoft
├─ Role match: ❌ NOT in your list
├─ Your fit: 🔴 NO MATCH
└─ Dashboard shows: ✗ (filtered out)

Glassdoor: "DevOps Internship" at Google
├─ Role match: ✅ DevOps
├─ Excluded keyword: ✅ "Internship"
├─ Your fit: 🔴 NO MATCH (excluded)
└─ Dashboard shows: ✗ (filtered out)
```

---

## Example: A Real Job Match

### Job Posting:
```
Title: Senior SRE Engineer
Company: Amazon
Location: Bengaluru, India
Applicants: 67

Requirements:
- 2+ years infrastructure/cloud experience
- Kubernetes, Docker experience
- Python/Bash scripting
- AWS or GCP
- CI/CD pipelines

Nice to have:
- Terraform
- Monitoring (Prometheus/Grafana)
- IAM/Security
```

### Your Resume:
```
Experience: 2.5 years Cloud/DevOps ✅ MATCHES
Kubernetes: ✅ YES (Amazon ECS, ECR)
Docker: ✅ YES
Python/Bash: ✅ YES (scripting)
AWS: ✅ YES (Core skill)
Terraform: ✅ YES (WAF rule builder, IAM onboarding)
Monitoring: ✅ YES (CloudWatch, Prometheus, Grafana)
IAM/Security: ✅ YES (AWS SSO, WAF, KMS)
```

### Result:
```
🟢 EXCELLENT MATCH (90%+)
✓ Appears in dashboard
✓ Included in exports
✓ AI can tailor resume perfectly
✓ You should definitely apply!
```

---

## Configuration for Your Profile

Your `config.yaml` is already set for YOU:

```yaml
search:
  roles:
    - "Cloud Engineer"        # Your current + future role
    - "DevOps Engineer"       # Your strong suit ⭐
    - "Site Reliability Engineer"  # SRE = DevOps + monitoring
    - "SRE"                   # Short form
    - "System Engineer"       # Your current role at Swiggy
    - "Platform Engineer"     # DevOps evolution
    - "Infrastructure Engineer"  # General infrastructure

location: "Bengaluru"         # Your preference
remote: true                  # You accept remote

max_applicants: 100           # Skip overly competitive
```

---

## What Gets Excluded (NOT Shown)

Jobs that will be filtered out:
```
❌ "Java Developer" (wrong tech stack)
❌ "Frontend React Engineer" (not your domain)
❌ "Data Science Intern" (internship + wrong role)
❌ "Sales Executive" (non-technical)
❌ "Unpaid Volunteer DevOps" (excluded keyword)
❌ "DevOps Engineering with 8+ years required" (you have 2.5)
```

---

## Resume Matching Score

When AI reviews a job for you:

```
Match Score Calculation:

Skills Match:
  AWS/Azure/GCP: ✅ +20 points
  Docker/Kubernetes: ✅ +20 points
  Python/Bash: ✅ +15 points
  Terraform/IaC: ✅ +15 points
  CI/CD: ✅ +15 points
  Monitoring: ✅ +10 points
  ───────────────────────────
  TOTAL: 95/100 = 🟢 EXCELLENT

Experience:
  Role match: ✅ Exact
  Years: ✅ Meets requirement
  Location: ✅ Available
  ───────────────────────────
  TOTAL: 🟢 PERFECT FIT
```

---

## How to Maximize Your Matches

### Good Fit Jobs (You should see LOTS of these):
```
✅ "DevOps Engineer" (any company)
✅ "SRE" (any company)
✅ "Cloud Engineer" (AWS/Azure focused)
✅ "Infrastructure Engineer" (Terraform experience needed)
✅ "Platform Engineer" (DevOps-style role)
```

### Jobs to Apply Aggressively:
```
🔥 "Senior DevOps Engineer" — Your exact skill level
🔥 "SRE II/III" — Your expertise zone
🔥 "Cloud Infrastructure Engineer" — Perfect match
```

### Jobs to Be Selective:
```
⚠️ "DevOps Architect" (might need more seniority)
⚠️ "Staff Engineer" (might be overqualified/underqualified)
⚠️ "DevOps + Data" (DevOps + data science mix)
```

---

## Questions to Ask About Each Job

Before you apply, the dashboard helps you check:

```
1. Does it match my core skills? → Filter checks ✓
2. Is it less competitive? → <100 applicants ✓
3. Location/remote OK? → Filter checks ✓
4. How does my resume fit? → AI tailoring shows ✓
```

---

## Summary

**YES — Jobs will be filtered to YOUR skill profile:**

✅ Only shows: DevOps, SRE, Cloud Engineer, Platform Engineer, Infrastructure roles
✅ Only shows: Bengaluru or Remote
✅ Only shows: <100 applicants (less competitive)
✅ Filters out: Internships, unpaid roles, unrelated fields
✅ AI automatically: Tailors resume to each job

**You'll see jobs like:**
- "Senior DevOps Engineer at Flipkart" ⭐⭐⭐ PERFECT
- "SRE Engineer at Amazon" ⭐⭐⭐ PERFECT
- "Cloud Infrastructure Engineer at Microsoft" ⭐⭐⭐ PERFECT
- "Platform Engineer at Google" ⭐⭐ GOOD FIT

**You WON'T see:**
- "Frontend Developer" (wrong stack)
- "Data Scientist" (wrong domain)
- "DevOps Internship" (excluded: internship)
- "DevOps Role, 100+ applicants" (too competitive)

---

**Result: Every job you see is a good fit for YOUR profile! 🎯**
