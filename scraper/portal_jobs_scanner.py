"""
Portal Jobs Scanner Engine
Scans and scrapes job postings directly from 100 Big Company Career Portals
and 24 Specialized Tech Job Websites. Filters postings for < 4 years experience
and scores them against Deepanshu Yadav's Cloud/DevOps resume skills.
"""

import os
import re
import time
import json
import logging
import threading
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Callable, Set

from scraper.company_portals import BIG_COMPANY_PORTALS, CompanyPortalsManager
from scraper.websites_scraper import SPECIALIZED_JOB_WEBSITES, WebsitesManager
from filter.engine import FilterEngine

logger = logging.getLogger(__name__)

# Deepanshu Yadav's Core Technical Skills from Resume
# (Swiggy System Engineer 1, Starwatt Cloud Engineer, AWS Certified Developer - Associate)
RESUME_SKILLS_TAXONOMY = {
    'primary_cloud': ['AWS', 'Azure', 'GCP', 'Google Cloud', 'Multi-Cloud'],
    'containers_orchestration': ['Docker', 'Kubernetes', 'K8s', 'Amazon ECS', 'Amazon ECR', 'Helm'],
    'iac_config': ['Terraform', 'CloudFormation', 'Ansible'],
    'cicd_gitops': ['GitOps', 'CI/CD', 'Jenkins', 'GitHub Actions', 'GitLab', 'AWS CodePipeline', 'CodeBuild', 'CodeDeploy'],
    'scripting_systems': ['Python', 'Bash', 'Shell', 'Linux', 'SQL', 'JavaScript'],
    'observability_telemetry': ['CloudWatch', 'CloudTrail', 'Prometheus', 'Grafana', 'ELK', 'Datadog', 'Observability'],
    'security_networking': ['IAM', 'AWS SSO', 'WAF', 'VPC', 'Security Groups', 'Route 53', 'KMS', 'Secrets Manager', 'TLS'],
    'architecture_platforms': ['Microservices', 'Distributed Systems', 'Event-Driven', 'ElastiCache', 'OpenSearch', 'SRE', 'High Availability']
}

# Flat list of prioritized core skills
FLAT_RESUME_SKILLS = [
    'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Terraform', 'CI/CD',
    'Python', 'Linux', 'Bash', 'GitOps', 'Jenkins', 'GitHub Actions',
    'CloudWatch', 'Prometheus', 'Grafana', 'IAM', 'WAF', 'VPC', 'Route 53',
    'ECS', 'ECR', 'Helm', 'Ansible', 'CodePipeline', 'OpenSearch', 'ElastiCache'
]

# Patterns for strict senior title rejection
SENIOR_TITLE_RE = re.compile(
    r'\b(?:senior|sr\.?|lead|principal|staff|director|vp|vice\s+president|head\s+of|manager|mgr)\b',
    re.IGNORECASE
)

# Patterns for experience requirements >= 5 years (strictly rejected)
UNQUALIFIED_EXP_PATTERNS = [
    re.compile(r'\b(?:[5-9]|1\d)\s*\+\s*(?:years?|yrs?)\b', re.IGNORECASE),
    re.compile(r'\b(?:minimum|at\s+least|min)\s+(?:[5-9]|1\d)\s*(?:years?|yrs?)\b', re.IGNORECASE),
    re.compile(r'\b(?:5\s*-\s*[8-9]|6\s*-\s*[8-9]|7\s*-\s*10|8\s*-\s*12)\s*(?:years?|yrs?)\b', re.IGNORECASE),
    re.compile(r'\b(?:5|6|7|8|9|10)\s*(?:to|-)\s*(?:[6-9]|1\d)\s*(?:years?|yrs?)\b', re.IGNORECASE),
]

# Patterns for experience requirements <= 4 years (qualified)
QUALIFIED_EXP_PATTERNS = [
    (re.compile(r'\b(?:0\s*-\s*2|0\s*-\s*3|0\s*-\s*4|1\s*-\s*3|1\s*-\s*4|2\s*-\s*4|3\s*-\s*4)\s*(?:years?|yrs?)\b', re.IGNORECASE), '0-4 years'),
    (re.compile(r'\b(?:1|2|3|4)\s*\+\s*(?:years?|yrs?)\b', re.IGNORECASE), '1-4 years'),
    (re.compile(r'\b(?:minimum|at\s+least|min)\s+(?:1|2|3)\s*(?:years?|yrs?)\b', re.IGNORECASE), '1-3 years'),
    (re.compile(r'\b(?:freshers?|entry\s*level|junior|associate|graduate)\b', re.IGNORECASE), '0-2 years (Entry/Associate)'),
    (re.compile(r'\b(?:2|3)\s*(?:years?|yrs?)\s+of\s+experience\b', re.IGNORECASE), '2-3 years'),
]


class PortalJobsScanner:
    """
    Scanner engine that discovers, scrapes, filters, and scores job postings
    from 100 Big Company Career Portals and 24 Specialized Job Websites.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.c_mgr = CompanyPortalsManager(self.config)
        self.w_mgr = WebsitesManager(self.config)
        self.filter_engine = FilterEngine(self.config)

        # Thread-safe status tracking
        self._lock = threading.Lock()
        self._is_running = False
        self._stop_requested = False
        self._status = {
            'running': False,
            'progress_pct': 0,
            'current_company': 'Idle',
            'companies_scanned': 0,
            'total_companies': 0,
            'jobs_found': 0,
            'jobs_qualified': 0,
            'started_at': None,
            'finished': False,
            'error': None
        }

    def get_status(self) -> Dict[str, Any]:
        """Return a copy of the current scanner status"""
        with self._lock:
            return dict(self._status)

    def stop(self):
        """Signal the scanner to stop immediately"""
        with self._lock:
            self._stop_requested = True
            self._status['current_phase'] = 'Stopping scan...'

    def is_running(self) -> bool:
        with self._lock:
            return self._is_running

    def match_resume_skills(self, text: str) -> List[str]:
        """
        Extract all candidate resume skills mentioned in job title/description.
        Uses FilterEngine word-boundary regex for zero false-positive collisions.
        """
        matched = set()
        if not text:
            return []

        # Use FilterEngine's compiled regex map
        if hasattr(self.filter_engine, 'get_matching_skills'):
            raw_matched = self.filter_engine.get_matching_skills(text)
            for skill_key in raw_matched:
                matched.add(self._canonicalize_skill_name(skill_key))

        # Also check flat core resume skills
        for skill in FLAT_RESUME_SKILLS:
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                matched.add(skill)

        # Sort with highest priority skills first
        priority_order = {s: i for i, s in enumerate(FLAT_RESUME_SKILLS)}
        return sorted(list(matched), key=lambda x: priority_order.get(x, 999))

    def _canonicalize_skill_name(self, raw_skill: str) -> str:
        """Map raw skill key to clean resume display format"""
        lookup = {
            'aws': 'AWS', 'azure': 'Azure', 'gcp': 'GCP', 'k8s': 'Kubernetes',
            'kubernetes': 'Kubernetes', 'docker': 'Docker', 'terraform': 'Terraform',
            'cicd': 'CI/CD', 'ci/cd': 'CI/CD', 'gitops': 'GitOps', 'python': 'Python',
            'linux': 'Linux', 'bash': 'Bash', 'jenkins': 'Jenkins', 'cloudwatch': 'CloudWatch',
            'prometheus': 'Prometheus', 'grafana': 'Grafana', 'iam': 'IAM', 'waf': 'WAF',
            'vpc': 'VPC', 'route53': 'Route 53', 'ecs': 'Amazon ECS', 'ecr': 'Amazon ECR',
            'helm': 'Helm', 'ansible': 'Ansible', 'codepipeline': 'AWS CodePipeline',
            'opensearch': 'OpenSearch', 'elasticache': 'ElastiCache', 'sre': 'SRE',
            'microservices': 'Microservices', 'sql': 'SQL', 'go': 'Go/Golang'
        }
        return lookup.get(raw_skill.lower().strip(), raw_skill.capitalize())

    def calculate_match_score(self, matched_skills: List[str], title: str, description: str) -> int:
        """
        Calculate match score (0-100%) against Deepanshu Yadav's resume.
        Weight factors:
        - Core Cloud/DevOps skills (AWS, Docker, K8s, Terraform, CI/CD, Python)
        - Title relevance (DevOps, Cloud, SRE, Platform, Systems)
        - Experience fit (< 4 years)
        """
        if not matched_skills and not title:
            return 0

        score = 0
        matched_lower = {s.lower() for s in matched_skills}

        # 1. High-Value Core Skills (up to 50 pts)
        core_cloud_skills = {'aws', 'azure', 'gcp', 'cloud'}
        if matched_lower & core_cloud_skills:
            score += 15  # Primary cloud match

        if any(k in matched_lower for k in ['kubernetes', 'k8s', 'docker', 'openshift', 'container']):
            score += 10  # Containers

        if 'terraform' in matched_lower or 'cloudformation' in matched_lower or 'ansible' in matched_lower:
            score += 10  # IaC

        if 'ci/cd' in matched_lower or 'gitops' in matched_lower or 'jenkins' in matched_lower or 'aws codepipeline' in matched_lower:
            score += 8   # CI/CD & Automation

        if any(k in matched_lower for k in ['python', 'bash', 'linux', 'redhat', 'rhel']):
            score += 7   # Scripting & OS

        # 2. Observability & Security (up to 20 pts)
        if 'cloudwatch' in matched_lower or 'prometheus' in matched_lower or 'grafana' in matched_lower:
            score += 10
        if 'iam' in matched_lower or 'waf' in matched_lower or 'vpc' in matched_lower or 'route 53' in matched_lower:
            score += 10

        # 3. Target Role Title Alignment (up to 25 pts)
        title_lower = title.lower()
        if 'cloud' in title_lower and ('engineer' in title_lower or 'ops' in title_lower):
            score += 25
        elif 'devops' in title_lower or 'sre' in title_lower or 'site reliability' in title_lower:
            score += 25
        elif 'platform' in title_lower or 'infrastructure' in title_lower or 'system' in title_lower:
            score += 20
        elif 'architect' in title_lower and any(kw in title_lower for kw in ['cloud', 'devops', 'operations', 'solutions', 'openshift']):
            score += 20
        elif any(kw in title_lower for kw in ['consultant', 'specialist']) and ('cloud' in title_lower or 'openshift' in title_lower):
            score += 20
        else:
            score += 10

        # 4. Swiggy & Starwatt specific tech match bonus (up to 5 pts)
        if any(term in title_lower or term in description.lower() for term in ['safekill', 'aws nuke', 'sso', 'lambda', 'sqs']):
            score += 5

        # Cap between 15 and 98%
        return min(max(score, 20), 98)

    def is_qualified_experience(self, title: str, description: str) -> tuple[bool, str, int]:
        """
        Enforce strict < 4 years experience constraint:
        - Strictly reject senior title prefixes (Senior, Lead, Principal, Staff, Director, Manager).
        - Strictly reject requirements >= 5 years (5+, 6+, 7+, 8+, 10+, 5-8y, 6-9y).
        - Allows 0-4 years (0-2y, 1-3y, 2-4y, 3-4y, junior, associate, freshers).
        - Returns (is_qualified, experience_label, max_years).
        """
        # Title check: reject senior prefixes
        if SENIOR_TITLE_RE.search(title):
            return False, 'Rejected: Senior Title', 99

        full_text = f"{title} {description}"

        # Check for excessive experience patterns (>= 5 years)
        for pattern in UNQUALIFIED_EXP_PATTERNS:
            match = pattern.search(full_text)
            if match:
                # Check if it's describing company age rather than candidate experience
                surrounding = full_text[max(0, match.start() - 30):min(len(full_text), match.end() + 30)].lower()
                if any(phrase in surrounding for phrase in ['company', 'operating for', 'founded', 'track record', 'serving', 'history']):
                    continue
                return False, f"Rejected: {match.group(0)} (> 4y)", 99

        # Check for qualified experience patterns (< 4 years)
        for pattern, label in QUALIFIED_EXP_PATTERNS:
            match = pattern.search(full_text)
            if match:
                return True, label, 4

        # If no explicit experience pattern is detected, check if title is junior/associate or mid-level
        title_lower = title.lower()
        if any(term in title_lower for term in ['associate', 'junior', 'entry', 'trainee', 'graduate', '1', 'i', 'level 1', 'engineer 1']):
            return True, '0-2 years (Associate/Junior)', 2

        # Standard mid-level role without excessive flags defaults to 2-4 years
        return True, '1-4 years (Mid-Level Fit)', 4

    def scan(
        self,
        mode: str = 'all',
        category: Optional[str] = None,
        portal_ids: Optional[List[str]] = None,
        max_jobs_per_company: int = 15,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        direct_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Execute scan across company career portals and specialized sites.
        mode: 'all', 'quick' (top 20 companies), 'category', or 'custom'.
        Returns list of normalized, qualified jobs requiring < 4 years experience.
        """
        with self._lock:
            self._is_running = True
            self._stop_requested = False
            self._status.update({
                'running': True,
                'progress_pct': 0,
                'current_company': 'Initializing scanner...',
                'companies_scanned': 0,
                'total_companies': 0,
                'jobs_found': 0,
                'jobs_qualified': 0,
                'started_at': datetime.now(timezone.utc).isoformat(),
                'finished': False,
                'error': None
            })

        logger.info(f"🚀 Starting Portal Jobs Scanner in mode='{mode}', category='{category}'")

        # 1. Determine targets to scan
        targets: List[Dict[str, Any]] = []
        all_portals = self.c_mgr.get_portals()

        if portal_ids:
            target_ids = set(portal_ids)
            targets = [p for p in all_portals if p['id'] in target_ids]
        elif mode == 'quick':
            # Premier enterprise companies with live direct ATS APIs (Workday, Greenhouse, Lever, SmartRecruiters, Ashby, Amazon)
            quick_ids = {
                'amazon_aws', 'redhat', 'salesforce', 'adobe', 'nvidia',
                'cisco', 'intel', 'snowflake', 'servicenow', 'capitalone',
                'cloudflare', 'elastic', 'mongodb', 'databricks', 'airbnb',
                'workday', 'crowdstrike', 'mastercard', 'broadcom_vmware',
                'pwc', 'spotify', 'inmobi', 'target', 'autodesk', 'boeing',
                'paypal', 'blackrock', 'zoom', 'westerndigital', 'freshworks'
            }
            targets = [p for p in all_portals if p['id'] in quick_ids]
        elif category:
            targets = [p for p in all_portals if p.get('category', '').lower() == category.lower()]
        else:
            targets = all_portals

        with self._lock:
            self._status['total_companies'] = len(targets)

        discovered_jobs: List[Dict[str, Any]] = []
        seen_urls: Set[str] = set()

        total = len(targets)
        for idx, portal in enumerate(targets):
            with self._lock:
                if self._stop_requested:
                    logger.info("Scan stopped by user request.")
                    break
                self._status['current_company'] = portal['name']
                self._status['companies_scanned'] = idx + 1
                self._status['progress_pct'] = int(((idx + 1) / max(total, 1)) * 100)

            msg = f"Scanning {portal['name']} ({portal.get('ats_type', 'portal')})..."
            logger.info(f"[{idx+1}/{total}] {msg}")

            if progress_callback:
                progress_callback(msg, len(discovered_jobs), idx + 1)

            # Discover jobs for this company
            company_jobs = self._discover_portal_jobs(portal, max_jobs=max_jobs_per_company)

            # Process, filter, and score each job
            for job in company_jobs:
                url = job.get('url', '').strip()
                if not url or url in seen_urls:
                    continue

                if direct_only and job.get('is_synthetic'):
                    continue

                seen_urls.add(url)
                title = job.get('title', '').strip()
                desc = job.get('description', '')

                with self._lock:
                    self._status['jobs_found'] += 1

                # Check strict < 4 years experience qualification
                is_qualified, exp_label, exp_max = self.is_qualified_experience(title, desc)
                if not is_qualified:
                    continue

                # Match resume skills
                matched_skills = self.match_resume_skills(f"{title} {desc}")
                # Compute match score
                score = self.calculate_match_score(matched_skills, title, desc)
                if job.get('is_synthetic'):
                    # Capped at 35% so synthetic search links never outrank real live requisitions
                    score = min(score, 35)
                else:
                    # Verified direct live ATS requisition boost (+15 pts)
                    score = min(score + 15, 98)

                job['experience_req'] = exp_label
                job['experience_max'] = exp_max
                job['matched_skills'] = matched_skills
                job['match_score'] = score
                job['skills_count'] = len(matched_skills)

                discovered_jobs.append(job)

                with self._lock:
                    self._status['jobs_qualified'] = len(discovered_jobs)

            # Short polite delay
            time.sleep(0.05)

        # Sort jobs by Match Score descending, then by date_posted descending
        discovered_jobs.sort(key=lambda j: (j.get('match_score', 0), len(j.get('matched_skills', []))), reverse=True)

        with self._lock:
            self._is_running = False
            self._status['running'] = False
            self._status['finished'] = True
            self._status['progress_pct'] = 100
            self._status['current_company'] = 'Completed'

        logger.info(f"✓ Portal scan complete: Discovered {len(discovered_jobs)} qualified jobs (<4y exp)")
        return discovered_jobs

    def _discover_portal_jobs(self, portal: Dict[str, Any], max_jobs: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve postings for a specific company portal.
        Combines direct ATS APIs, structured feeds, and curated active listings.
        """
        p_id = portal.get('id', '')
        company = portal.get('name', 'Enterprise Tech')
        category = portal.get('category', 'Cloud Hyperscalers & Infrastructure')
        ats_type = portal.get('ats_type', 'custom')
        portal_url = portal.get('portal_url', '')
        search_url = portal.get('search_url', '')

        # Attempt ATS-specific scraping if applicable
        jobs = []
        gh_map = {
            'cloudflare': 'cloudflare', 'twilio': 'twilio', 'mongodb': 'mongodb',
            'elastic': 'elastic', 'dropbox': 'dropbox', 'stripe': 'stripe',
            'airbnb': 'airbnb', 'inmobi': 'inmobi', 'databricks': 'databricks',
            'okta': 'okta', 'gitlab': 'gitlab', 'canonical': 'canonical',
            'figma': 'figma', 'reddit': 'reddit', 'digitalocean': 'digitalocean',
            'hashicorp': 'hashicorp', 'postman': 'postman',
            'coinbase': 'coinbase', 'discord': 'discord', 'grafanalabs': 'grafanalabs',
            'pagerduty': 'pagerduty', 'pinterest': 'pinterest', 'airtable': 'airtable',
            'instacart': 'instacart', 'datadog': 'datadog', 'lyft': 'lyft',
            'robinhood': 'robinhood', 'scaleai': 'scaleai'
        }
        lever_map = {
            'spotify': 'spotify', 'cred': 'cred', 'meesho': 'meesho',
            'razorpay': 'razorpay', 'zepto': 'zepto', 'palantir': 'palantir',
            'canonical': 'canonical'
        }
        sr_map = {
            'servicenow': 'ServiceNow', 'westerndigital': 'WesternDigital',
            'freshworks': 'Freshworks', 'paloaltonetworks': 'PaloAltoNetworks',
            'visa': 'Visa', 'bosch': 'BoschGroup'
        }
        ashby_map = {
            'snowflake': 'snowflake', 'docker': 'docker', 'snyk': 'snyk',
            'notion': 'notion', 'supabase': 'supabase', 'perplexity': 'perplexity',
            'cohere': 'cohere', 'linear': 'linear', 'ramp': 'ramp'
        }
        wd_map = {
            'cisco': 'https://cisco.wd5.myworkdayjobs.com/Cisco_Careers',
            'splunk': 'https://cisco.wd5.myworkdayjobs.com/Cisco_Careers',
            'intel': 'https://intel.wd1.myworkdayjobs.com/External',
            'blackrock': 'https://blackrock.wd1.myworkdayjobs.com/BlackRock_Professional',
            'paypal': 'https://paypal.wd1.myworkdayjobs.com/jobs',
            'zoom': 'https://zoom.wd5.myworkdayjobs.com/Zoom',
            'capitalone': 'https://capitalone.wd12.myworkdayjobs.com/Capital_One',
            'broadcom': 'https://broadcom.wd1.myworkdayjobs.com/External_Career',
            'broadcom_vmware': 'https://broadcom.wd1.myworkdayjobs.com/External_Career',
            'redhat': 'https://redhat.wd5.myworkdayjobs.com/jobs',
            'adobe': 'https://adobe.wd5.myworkdayjobs.com/external_experienced',
            'workday': 'https://workday.wd5.myworkdayjobs.com/workday',
            'crowdstrike': 'https://crowdstrike.wd5.myworkdayjobs.com/crowdstrikecareers',
            'mastercard': 'https://mastercard.wd1.myworkdayjobs.com/CorporateCareers',
            'rackspace': 'https://rackspace.wd1.myworkdayjobs.com/External',
            'pwc': 'https://pwc.wd3.myworkdayjobs.com/Global_Experienced_Careers',
            'nvidia': 'https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite',
            'salesforce': 'https://salesforce.wd12.myworkdayjobs.com/External_Career_Site',
            'autodesk': 'https://autodesk.wd1.myworkdayjobs.com/Ext',
            'target': 'https://target.wd5.myworkdayjobs.com/targetcareers',
            'boeing': 'https://boeing.wd1.myworkdayjobs.com/EXTERNAL_CAREERS',
            'micron': 'https://micron.wd1.myworkdayjobs.com/External'
        }

        if p_id in gh_map or ats_type == 'greenhouse':
            board_token = gh_map.get(p_id, p_id)
            jobs = self._scrape_greenhouse(p_id, company, category, search_url or portal_url, board_token=board_token)
        elif p_id in lever_map or ats_type == 'lever':
            comp_token = lever_map.get(p_id, p_id)
            jobs = self._scrape_lever(p_id, company, category, search_url or portal_url, comp_token=comp_token)
        elif p_id in sr_map or ats_type == 'smartrecruiters':
            comp_id = sr_map.get(p_id, p_id)
            jobs = self._scrape_smartrecruiters(p_id, company, category, search_url or portal_url, comp_id=comp_id)
        elif p_id in ashby_map or ats_type == 'ashby':
            board_token = ashby_map.get(p_id, p_id)
            jobs = self._scrape_ashby(p_id, company, category, search_url or portal_url, board_token=board_token)
        elif p_id == 'amazon_aws' or ats_type == 'amazon_jobs':
            jobs = self._scrape_amazon(p_id, company, category, search_url or portal_url)
        elif p_id in wd_map or ats_type == 'workday' or 'myworkdayjobs.com' in (search_url or portal_url):
            target_wd_url = wd_map.get(p_id, search_url or portal_url)
            jobs = self._scrape_workday(p_id, company, category, target_wd_url)

        # If direct ATS retrieval returned jobs, use them.
        # Portals without direct ATS APIs should not generate synthetic placeholder links.
        return jobs[:max_jobs]

    def _scrape_greenhouse(self, p_id: str, company: str, category: str, base_url: str, board_token: str = None) -> List[Dict[str, Any]]:
        """Query Greenhouse public boards API"""
        import urllib.request
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        token = board_token or p_id
        jobs = []
        try:
            api_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
            req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    raw_jobs = data.get('jobs', [])
                    for rj in raw_jobs:
                        t = rj.get('title', '')
                        if any(kw in t.lower() for kw in ['engineer', 'developer', 'devops', 'sre', 'cloud', 'platform', 'infrastructure', 'systems', 'operations', 'architect']):
                            loc = rj.get('location', {}).get('name', 'Bengaluru / Remote')
                            job_url = rj.get('absolute_url') or f"https://boards.greenhouse.io/{token}/jobs/{rj.get('id')}"
                            desc = rj.get('content', '') or f"{t} opportunity at {company}"
                            jobs.append({
                                'portal_id': p_id,
                                'company': company,
                                'category': category,
                                'ats_type': 'greenhouse',
                                'title': t,
                                'location': loc,
                                'url': job_url,
                                'description': desc,
                                'date_posted': datetime.now(timezone.utc),
                                'salary': 'Competitive Tech Salary',
                                'job_type': 'Full-time'
                            })
        except Exception as e:
            logger.debug(f"Greenhouse API query skipped for {p_id}: {e}")
        return jobs

    def _scrape_lever(self, p_id: str, company: str, category: str, base_url: str, comp_token: str = None) -> List[Dict[str, Any]]:
        """Query Lever public API"""
        import urllib.request
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        token = comp_token or p_id
        jobs = []
        try:
            api_url = f"https://api.lever.co/v0/postings/{token}?mode=json"
            req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    for rj in data:
                        t = rj.get('text', '')
                        if any(kw in t.lower() for kw in ['engineer', 'developer', 'devops', 'sre', 'cloud', 'platform', 'infrastructure', 'systems', 'architect']):
                            loc = rj.get('categories', {}).get('location', 'Bengaluru / Remote')
                            job_url = rj.get('hostedUrl') or f"https://jobs.lever.co/{token}/{rj.get('id')}"
                            desc = rj.get('descriptionPlain', '') or f"{t} opportunity at {company}"
                            jobs.append({
                                'portal_id': p_id,
                                'company': company,
                                'category': category,
                                'ats_type': 'lever',
                                'title': t,
                                'location': loc,
                                'url': job_url,
                                'description': desc,
                                'date_posted': datetime.now(timezone.utc),
                                'salary': 'Competitive Tech Salary',
                                'job_type': 'Full-time'
                            })
        except Exception as e:
            logger.debug(f"Lever API query skipped for {p_id}: {e}")
        return jobs

    def _scrape_smartrecruiters(self, p_id: str, company: str, category: str, base_url: str, comp_id: str = None) -> List[Dict[str, Any]]:
        """Query SmartRecruiters public API"""
        import urllib.request
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        cid = comp_id or p_id
        jobs = []
        try:
            api_url = f"https://api.smartrecruiters.com/v1/companies/{cid}/postings?limit=100"
            req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    content = data.get('content', [])
                    for rj in content:
                        t = rj.get('name', '')
                        if any(kw in t.lower() for kw in ['engineer', 'developer', 'devops', 'sre', 'cloud', 'platform', 'infrastructure', 'systems', 'architect']):
                            loc_info = rj.get('location', {})
                            city = loc_info.get('city', '')
                            country = loc_info.get('country', '')
                            loc = f"{city}, {country}".strip(', ') or "Bengaluru / Remote"
                            job_id = rj.get('id')
                            job_url = f"https://jobs.smartrecruiters.com/{cid}/{job_id}"
                            desc = f"{t} opportunity at {company} ({loc}). Official requisition on SmartRecruiters."
                            jobs.append({
                                'portal_id': p_id,
                                'company': company,
                                'category': category,
                                'ats_type': 'smartrecruiters',
                                'title': t,
                                'location': loc,
                                'url': job_url,
                                'description': desc,
                                'date_posted': datetime.now(timezone.utc),
                                'salary': 'Competitive Tech Salary',
                                'job_type': 'Full-time'
                            })
        except Exception as e:
            logger.debug(f"SmartRecruiters API query skipped for {p_id}: {e}")
        return jobs

    def _scrape_ashby(self, p_id: str, company: str, category: str, base_url: str, board_token: str = None) -> List[Dict[str, Any]]:
        """Query Ashby public posting API to retrieve live job postings with exact requisition URLs"""
        import urllib.request
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        token = board_token or p_id
        jobs = []
        try:
            api_url = f"https://api.ashbyhq.com/posting-api/job-board/{token}"
            req = urllib.request.Request(api_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json'
            })
            with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    now = datetime.now(timezone.utc)
                    for rj in data.get('jobs', []):
                        t = rj.get('title', '')
                        if not any(kw in t.lower() for kw in ['engineer', 'developer', 'devops', 'sre', 'cloud', 'platform', 'infrastructure', 'systems', 'architect', 'analyst', 'tech', 'software', 'site reliability']):
                            continue
                        direct_url = rj.get('jobUrl') or f"https://jobs.ashbyhq.com/{token}/{rj.get('id')}"
                        loc = rj.get('location', 'Bengaluru / Remote')
                        desc = f"{t} opportunity at {company}. Direct career application on official Ashby requisition page."
                        jobs.append({
                            'portal_id': p_id,
                            'company': company,
                            'category': category,
                            'ats_type': 'ashby',
                            'title': t,
                            'location': loc,
                            'url': direct_url,
                            'description': desc,
                            'date_posted': now,
                            'salary': 'Competitive Tech Salary',
                            'job_type': 'Full-time'
                        })
        except Exception as e:
            logger.debug(f"Ashby API query skipped for {p_id}: {e}")
        return jobs

    def _scrape_amazon(self, p_id: str, company: str, category: str, base_url: str) -> List[Dict[str, Any]]:
        """Query Amazon Jobs public JSON search API"""
        import urllib.request
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        jobs = []
        seen = set()
        for q in ['DevOps', 'Cloud', 'Infrastructure', 'Systems']:
            try:
                api_url = f"https://www.amazon.jobs/en/search.json?base_query={q}&country=IND&result_limit=25"
                req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode('utf-8'))
                        for rj in data.get('jobs', []):
                            path = rj.get('job_path', '')
                            if not path:
                                continue
                            full_url = f"https://www.amazon.jobs{path}"
                            if full_url in seen:
                                continue
                            seen.add(full_url)
                            t = rj.get('title', '')
                            loc = f"{rj.get('city', 'Bengaluru')}, {rj.get('country_code', 'IND')}"
                            desc = rj.get('description_short', '') or rj.get('basic_qualifications', '') or f"{t} at {company}"
                            jobs.append({
                                'portal_id': p_id,
                                'company': company,
                                'category': category,
                                'ats_type': 'amazon_jobs',
                                'title': t,
                                'location': loc,
                                'url': full_url,
                                'description': desc,
                                'date_posted': datetime.now(timezone.utc),
                                'salary': 'Competitive Tech Salary',
                                'job_type': 'Full-time'
                            })
            except Exception as e:
                logger.debug(f"Amazon Jobs API query error: {e}")
        return jobs

    def _scrape_workday(self, p_id: str, company: str, category: str, base_url: str) -> List[Dict[str, Any]]:
        """Query Workday public CXS jobs API to retrieve actual live job postings with exact requisition URLs"""
        import urllib.request
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        jobs = []
        seen_ext = set()
        try:
            m = re.search(r'https?://([^.]+)\.([^.]+)\.myworkdayjobs\.com/(?:[a-zA-Z-]+/)?([^/?#]+)', base_url)
            if not m:
                return []
            tenant, host, site = m.group(1), m.group(2), m.group(3)
            api_url = f"https://{tenant}.{host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            # Query Workday across domain search terms (Workday CXS enforces max limit of 20)
            for query in ['DevOps', 'Cloud', 'Infrastructure', 'Systems', '']:
                payload = json.dumps({
                    "appliedFacets": {},
                    "limit": 20,
                    "offset": 0,
                    "searchText": query
                }).encode('utf-8')
                req = urllib.request.Request(api_url, data=payload, headers=headers)
                try:
                    with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                        if response.status == 200:
                            data = json.loads(response.read().decode('utf-8'))
                            for rj in data.get('jobPostings', []):
                                ext = rj.get('externalPath', '')
                                if not ext or ext in seen_ext:
                                    continue
                                seen_ext.add(ext)
                                t = rj.get('title', '')
                                if not any(kw in t.lower() for kw in ['engineer', 'developer', 'devops', 'sre', 'cloud', 'platform', 'infrastructure', 'systems', 'architect', 'analyst', 'tech', 'software', 'site reliability']):
                                    continue
                                direct_url = f"https://{tenant}.{host}.myworkdayjobs.com/en-US/{site}{ext}"
                                loc = rj.get('locationsText', 'Bengaluru / Remote')
                                jobs.append({
                                    'portal_id': p_id,
                                    'company': company,
                                    'category': category,
                                    'ats_type': 'workday',
                                    'title': t,
                                    'location': loc,
                                    'url': direct_url,
                                    'description': f"{t} opportunity at {company}. Direct career application on official Workday requisition page.",
                                    'date_posted': datetime.now(timezone.utc),
                                    'salary': 'Competitive Tech Salary',
                                    'job_type': 'Full-time'
                                })
                except Exception as req_err:
                    logger.debug(f"Workday query '{query}' failed for {tenant}: {req_err}")
                    continue
        except Exception as e:
            logger.debug(f"Workday API query skipped for {p_id}: {e}")
        return jobs

    def _get_company_active_postings(self, portal: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate high-fidelity active career portal opportunities for the given company.
        Tailored specifically to Deepanshu Yadav's profile:
        - Strict 0-4 years experience (2-4y, 1-3y, 0-2y, 3-4y)
        - Cloud, DevOps, SRE, Platform, Systems, and Cloud Operations Architect roles
        - Matches candidate credentials (AWS Certified Developer, Terraform, Kubernetes, Python, Linux)
        """
        p_id = portal.get('id', '')
        company = portal.get('name', 'Enterprise Tech')
        category = portal.get('category', 'Cloud Hyperscalers & Infrastructure')
        ats_type = portal.get('ats_type', 'workday')
        base_search_url = portal.get('search_url', portal.get('portal_url', ''))

        now = datetime.now(timezone.utc)

        # Company-specific career post generator templates
        templates = [
            {
                'title_suffix': 'Cloud DevOps Engineer',
                'exp': '2-4 years',
                'desc': f"{company} is hiring a Cloud DevOps Engineer to join our infrastructure platform engineering team. Responsibilities include managing AWS/Azure multi-cloud environments, building automated CI/CD pipelines using GitHub Actions and Jenkins, and managing infrastructure as code with Terraform. Hands-on experience with Docker, Kubernetes, Linux systems, and CloudWatch observability is required. Requirements: 2 to 4 years of relevant cloud engineering experience.",
                'loc': 'Bengaluru, Karnataka (Hybrid)',
                'salary': '₹18,00,000 - ₹28,00,000'
            },
            {
                'title_suffix': 'Site Reliability Engineer (SRE)',
                'exp': '1-3 years',
                'desc': f"Join {company}'s Core Reliability and Production Engineering team as an SRE. You will monitor high-throughput distributed microservices, define SLOs/SLIs, configure Prometheus and Grafana dashboards, and automate operational incident remediation with Python and Bash. Requirements: 1 to 3 years experience in Linux, Docker containers, AWS cloud infrastructure, and observability tooling.",
                'loc': 'India (Remote)',
                'salary': '₹16,00,000 - ₹26,00,000'
            },
            {
                'title_suffix': 'Cloud Infrastructure & Platform Engineer',
                'exp': '2-4 years',
                'desc': f"{company} is seeking an Infrastructure & Platform Engineer with 2-4 years of experience. You will collaborate on Terraform modules, AWS IAM policies, VPC networking, security groups, and Helm charts for Kubernetes clusters. Knowledge of AWS CodePipeline, GitOps workflows, and Python scripting is strongly desired.",
                'loc': 'Bengaluru / Remote',
                'salary': '₹20,00,000 - ₹30,00,000'
            },
            {
                'title_suffix': 'Cloud Operations Architect (Mid-Level)',
                'exp': '3-4 years',
                'desc': f"As a Cloud Operations Architect at {company}, you will assist in cloud architecture design, AWS resource lifecycle automation (SafeKill/AWS Nuke patterns), and cost optimization across cloud accounts. Candidate should have 3-4 years hands-on experience in AWS services (EC2, S3, Lambda, SQS, ElastiCache, OpenSearch), Terraform, and CI/CD automation.",
                'loc': 'Bengaluru, Karnataka',
                'salary': '₹22,00,000 - ₹34,00,000'
            },
            {
                'title_suffix': 'Systems Engineer 1 - Cloud & Automation',
                'exp': '1-3 years',
                'desc': f"Exciting opportunity at {company} for a Systems Engineer 1 focused on AWS cloud automation, Linux administration, and IAM security. Experience with Python script runners, AWS Lambda, Docker containers, and CI/CD workflows required. Experience required: 1 to 3 years.",
                'loc': 'Bengaluru / Hyderabad',
                'salary': '₹15,00,000 - ₹24,00,000'
            }
        ]

        # Select 2 to 4 appropriate opportunities for this company
        company_jobs = []
        selected_templates = templates[:3] if p_id != 'amazon_aws' and p_id != 'google' else templates

        for idx, tpl in enumerate(selected_templates):
            job_url = self._format_direct_job_url(base_search_url, tpl['title_suffix'], p_id, idx)
            company_jobs.append({
                'portal_id': p_id,
                'company': company,
                'category': category,
                'ats_type': ats_type,
                'title': f"{tpl['title_suffix']}",
                'location': tpl['loc'],
                'url': job_url,
                'description': tpl['desc'],
                'date_posted': now - timedelta(hours=(idx * 4 + 2)),
                'salary': tpl['salary'],
                'job_type': 'Full-time',
                'is_synthetic': True
            })

        return company_jobs

    @staticmethod
    def _format_direct_job_url(base_url: str, role_title: str, p_id: str, idx: int) -> str:
        """
        Format clean, direct job search/posting URL without breaking client-side routers
        or appending dummy parameters that cause 400/500 errors or redirects to corporate homepages.
        For Workday/Red Hat, points to exact live requisition URLs.
        For portals with recognized search queries, specializes queries (e.g. q=, search=, keywords=) for the role.
        Never injects broken or unsupported '?role=' parameters.
        """
        if not base_url:
            return ""

        # 1. Red Hat live Workday requisition deep links
        if p_id == 'redhat':
            redhat_reqs = [
                "https://redhat.wd5.myworkdayjobs.com/en-US/jobs/job/Pune/Senior-Software-Engineer--Cloud-Infrastructure--Kubernetes--Golang-Python_R-057038-1",
                "https://redhat.wd5.myworkdayjobs.com/en-US/jobs/job/Remote-Brazil/Cloud-Consultant_R-059961-1",
                "https://redhat.wd5.myworkdayjobs.com/en-US/jobs/job/Remote-Mexico/OpenShift-Architect_R-059537-1",
                "https://redhat.wd5.myworkdayjobs.com/en-US/jobs/job/Madrid/Territory-Services-Manager_R-059980-2",
                "https://redhat.wd5.myworkdayjobs.com/en-US/jobs/job/Melbourne/Principal-Architect_R-059673-1"
            ]
            return redhat_reqs[idx % len(redhat_reqs)]

        if idx == 0:
            return base_url.strip()

        parsed = urllib.parse.urlparse(base_url.strip())
        qs = urllib.parse.parse_qs(parsed.query)

        query_map = {
            'Cloud DevOps Engineer': 'Cloud DevOps',
            'Site Reliability Engineer (SRE)': 'Site Reliability Engineer',
            'Cloud Infrastructure & Platform Engineer': 'Infrastructure Platform',
            'Cloud Operations Architect (Mid-Level)': 'Cloud Architect',
            'Systems Engineer 1 - Cloud & Automation': 'Systems Engineer'
        }
        kw = query_map.get(role_title, role_title)

        # Detect search query keys supported by the remote ATS/portal
        search_keys = ['q', 'search', 'keywords', 'base_query', 'jk', 'keyword', 'query']
        found_key = None
        for k in search_keys:
            if k in qs:
                found_key = k
                break

        if found_key:
            # Specialize existing search query for this role
            new_qs = dict(qs)
            new_qs[found_key] = [kw]
            new_query = urllib.parse.urlencode(new_qs, doseq=True)
            return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
        else:
            # Clean base URL without injecting unsupported parameters
            return base_url.strip()

    def save_jobs_to_db(self, jobs: List[Dict[str, Any]], app=None) -> int:
        """
        Persist discovered portal jobs into SQLite database (`PortalJob` model).
        Updates existing postings if already present.
        """
        from db.models import db, PortalJob

        def _do_save():
            db.create_all()
            saved_count = 0
            for j in jobs:
                url = j.get('url', '').strip()
                if not url:
                    continue

                existing = PortalJob.query.filter_by(url=url).first()
                matched_str = ', '.join(j.get('matched_skills', [])) if isinstance(j.get('matched_skills'), list) else (j.get('matched_skills') or '')

                if existing:
                    # Update metrics and timestamp
                    existing.title = j.get('title', existing.title)
                    existing.company = j.get('company', existing.company)
                    existing.category = j.get('category', existing.category)
                    existing.ats_type = j.get('ats_type', existing.ats_type)
                    existing.location = j.get('location', existing.location)
                    existing.description = j.get('description', existing.description)
                    existing.experience_req = j.get('experience_req', existing.experience_req)
                    existing.experience_max = j.get('experience_max', existing.experience_max)
                    existing.matched_skills = matched_str
                    existing.match_score = j.get('match_score', existing.match_score)
                    existing.skills_count = j.get('skills_count', len(j.get('matched_skills', [])))
                    existing.salary = j.get('salary', existing.salary)
                    existing.updated_at = datetime.now(timezone.utc)
                else:
                    new_job = PortalJob(
                        portal_id=j.get('portal_id', 'custom'),
                        company=j.get('company', 'Enterprise Tech'),
                        category=j.get('category', 'Cloud Hyperscalers & Infrastructure'),
                        ats_type=j.get('ats_type', 'portal'),
                        title=j.get('title', 'Cloud DevOps Engineer'),
                        location=j.get('location', 'Bengaluru / Remote'),
                        url=url,
                        description=j.get('description', ''),
                        experience_req=j.get('experience_req', '< 4 years'),
                        experience_max=j.get('experience_max', 4),
                        matched_skills=matched_str,
                        match_score=j.get('match_score', 0),
                        skills_count=j.get('skills_count', 0),
                        salary=j.get('salary', ''),
                        date_posted=j.get('date_posted') or datetime.now(timezone.utc),
                        job_type=j.get('job_type', 'Full-time'),
                        status='new'
                    )
                    db.session.add(new_job)
                    saved_count += 1

            db.session.commit()
            return saved_count

        if app:
            with app.app_context():
                return _do_save()
        return _do_save()
