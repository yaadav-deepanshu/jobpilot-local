"""
Smart Job Filter Engine
Filters jobs by roles (with synonym matching), location, applicant count, keywords, and recency
"""

import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

class FilterEngine:
    """Intelligent job filter matching target profile"""

    # Common technical synonyms and role abbreviations
    ROLE_SYNONYMS = {
        'sre': ['site reliability engineer', 'site reliability', 'reliability engineer', 'sre'],
        'site reliability engineer': ['sre', 'site reliability', 'reliability engineer'],
        'devops': ['devops engineer', 'devops', 'cloud devops', 'devsecops'],
        'devops engineer': ['devops', 'cloud devops', 'devsecops', 'site reliability engineer', 'platform engineer'],
        'cloud engineer': ['cloud', 'aws engineer', 'azure engineer', 'gcp engineer', 'cloud infrastructure', 'cloud specialist'],
        'platform engineer': ['platform', 'infrastructure engineer', 'systems engineer', 'devops'],
        'infrastructure engineer': ['infrastructure', 'cloud infrastructure', 'iac', 'systems engineer'],
    }

    # Core tech skills matching the profile
    CORE_SKILLS = [
        'aws', 'azure', 'gcp', 'cloud', 'docker', 'kubernetes', 'k8s',
        'terraform', 'ansible', 'jenkins', 'ci/cd', 'python', 'linux',
        'bash', 'git', 'helm', 'prometheus', 'grafana', 'devops', 'sre'
    ]

    def __init__(self, config: dict):
        self.config = config
        self.search_config = config.get('search', {})
        self.target_roles = [r.lower() for r in self.search_config.get('roles', [])]
        self.target_location = self.search_config.get('location', '').lower()
        self.max_applicants = self.search_config.get('max_applicants', 100)
        self.exclude_keywords = [k.lower() for k in self.search_config.get('exclude_keywords', [])]

    def filter_jobs(self, jobs: List[Dict[str, Any]], today_only: bool = False, max_hours: Optional[int] = None, location_mode: str = 'both') -> List[Dict[str, Any]]:
        """Run jobs through all filters and return matching ones in platform priority order"""
        initial_count = len(jobs)
        logger.info(f"🔎 Filtering {initial_count} jobs (today_only={today_only}, max_hours={max_hours}, location_mode={location_mode})...")

        filtered = jobs

        # 1. Recency filter
        if max_hours is not None:
            filtered = self._filter_by_recency(filtered, max_hours=max_hours)
        elif today_only:
            filtered = self._filter_by_recency(filtered, max_hours=24)
        else:
            filtered = self._filter_by_recency(filtered, max_hours=24 * 30)

        # 2. Exclude negative keywords (internship, unpaid, etc.)
        filtered = self._filter_by_excluded_keywords(filtered)

        # 3. Experience filter (strictly exclude jobs requiring > 4 years, e.g. 5+, 8+ years)
        filtered = self._filter_by_experience(filtered)

        # 4. Role and skill matching (flexible)
        filtered = self._filter_by_role_and_skills(filtered)

        # 5. Location match
        filtered = self._filter_by_location(filtered, location_mode=location_mode)

        # 6. Applicant threshold (max 100 applicants)
        filtered = self._filter_by_applicants(filtered)

        # 7. Final deduplication
        filtered = self._deduplicate(filtered)

        # 8. Sort by platform priority: LinkedIn -> Indeed -> Naukri -> Rest
        filtered = self._sort_by_platform_priority(filtered)

        logger.info(f"✓ Filter result: {initial_count} → {len(filtered)} jobs matched")
        return filtered

    def _filter_by_recency(self, jobs: List[Dict], max_hours: int = 24) -> List[Dict]:
        """Keep jobs posted within max_hours"""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=max_hours)
        passed = []

        for j in jobs:
            posted = j.get('date_posted')
            if not posted:
                passed.append(j)
                continue

            try:
                if isinstance(posted, str):
                    posted = datetime.fromisoformat(posted.replace('Z', '+00:00'))
                if hasattr(posted, 'tzinfo') and posted.tzinfo is None:
                    posted = posted.replace(tzinfo=timezone.utc)
                if posted >= cutoff:
                    passed.append(j)
            except Exception:
                # If date can't be parsed, keep it conservatively
                passed.append(j)

        return passed

    def _filter_by_excluded_keywords(self, jobs: List[Dict]) -> List[Dict]:
        """Exclude jobs containing forbidden keywords like internship, unpaid"""
        if not self.exclude_keywords:
            return jobs

        passed = []
        for j in jobs:
            title = j.get('title', '').lower()
            desc = j.get('description', '').lower()[:300]
            job_type = j.get('job_type', '').lower()
            text = f"{title} {job_type} {desc}"

            if not any(k in text for k in self.exclude_keywords):
                passed.append(j)

        return passed

    def _filter_by_role_and_skills(self, jobs: List[Dict]) -> List[Dict]:
        """
        Match if:
        1. Job title matches any target role or synonym, OR
        2. Job description contains 3+ relevant DevOps/Cloud skills
        """
        if not self.target_roles:
            return jobs

        # Build expanded terms
        all_terms = set(self.target_roles)
        for r in self.target_roles:
            for syn in self.ROLE_SYNONYMS.get(r, []):
                all_terms.add(syn.lower())

        passed = []
        for j in jobs:
            title = j.get('title', '').lower()
            desc = j.get('description', '').lower()

            # Exact or partial title match
            if any(term in title for term in all_terms):
                passed.append(j)
                continue

            # Skill-based match: title has 'engineer' or 'developer' or 'lead' + multiple skills
            if any(w in title for w in ['engineer', 'developer', 'lead', 'architect', 'specialist']):
                skill_count = sum(1 for s in self.CORE_SKILLS if s in desc)
                if skill_count >= 3:
                    passed.append(j)

        return passed

    def _filter_by_location(self, jobs: List[Dict], location_mode: str = 'both') -> List[Dict]:
        """Match preferred location, supporting segregation modes: 'remote', 'bengaluru', 'both'"""
        mode = (location_mode or 'both').lower().strip()

        if mode == 'remote':
            passed = []
            for j in jobs:
                loc = (j.get('location') or '').lower()
                title = (j.get('title') or '').lower()
                desc = (j.get('description') or '').lower()
                job_type = (j.get('job_type') or '').lower()
                text = f"{loc} {title} {desc} {job_type}"
                if any(w in text for w in ['remote', 'work from home', 'wfh']):
                    passed.append(j)
            return passed

        if mode == 'bengaluru':
            passed = []
            for j in jobs:
                loc = (j.get('location') or '').lower()
                if 'bengaluru' in loc or 'bangalore' in loc:
                    passed.append(j)
            return passed

        if not self.target_location:
            return jobs

        allow_remote = self.search_config.get('remote', True)
        allow_hybrid = self.search_config.get('hybrid', True)
        passed = []

        for j in jobs:
            loc = j.get('location', '').lower()

            # Location match (e.g. Bengaluru, Bangalore, India)
            if self.target_location in loc:
                passed.append(j)
            elif 'bangalore' in loc and 'bengaluru' in self.target_location:
                passed.append(j)
            elif 'bengaluru' in loc and 'bangalore' in self.target_location:
                passed.append(j)
            elif 'india' in loc or 'all' in loc:
                passed.append(j)
            elif allow_remote and 'remote' in loc:
                passed.append(j)
            elif allow_hybrid and 'hybrid' in loc:
                passed.append(j)
            elif not loc or loc == 'not specified':
                passed.append(j)

        return passed

    def _filter_by_experience(self, jobs: List[Dict]) -> List[Dict]:
        """
        Exclude jobs requiring more experience than user's target profile (target: 0-4 years).
        Matches patterns like '8+ years', 'minimum 8 years', '5-8 years', '3-5 years', 'expert level', etc.
        Also excludes executive/director/principal/architect/lead/manager titles.
        """
        max_exp = self.search_config.get('max_experience_years', 4)
        senior_titles = ['principal', 'director', 'vp', 'vice president', 'staff', 'head of', 'architect', 'manager', 'lead']
        if max_exp <= 4:
            senior_titles.extend(['senior', 'sr.', 'sr ', 'sr/', 'lead ', 'mgr'])

        # Explicit forbidden experience phrases (exceeding 4 years)
        excessive_phrases = [
            '5+ years', '6+ years', '7+ years', '8+ years', '9+ years', '10+ years',
            '5+ yrs', '6+ yrs', '7+ yrs', '8+ yrs', '9+ yrs', '10+ yrs',
            '5 years of experience', '6 years of experience', '7 years of experience',
            '8 years of experience', '10 years of experience',
            '5-8 years', '6-9 years', '5-9 years', '5-7 years', '6-8 years', '7-10 years', '8-10 years',
            'expert level', 'senior level'
        ]

        passed = []
        for j in jobs:
            title = j.get('title', '').lower()
            desc = j.get('description', '').lower()

            # Reject executive, senior, lead, architect, or manager titles
            if any(st in title for st in senior_titles):
                continue

            # Quick check for explicit excessive phrases
            if any(phrase in desc for phrase in excessive_phrases):
                continue

            too_senior = False

            # Pattern 1: e.g. "8+ years of experience", "5-7 years of experience", "3-5 years"
            matches = re.findall(r'(\d+)\s*(?:\+|plus)?\s*(?:-|to)?\s*(\d+)?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp)', desc)
            for m in matches:
                try:
                    min_req = int(m[0])
                    if min_req > max_exp:
                        too_senior = True
                        break
                    # If upper bound of range exceeds max_exp + 1 (e.g. 3-6 years or 4-7 years), reject
                    if m[1]:
                        max_req = int(m[1])
                        if max_req > max_exp + 1:
                            too_senior = True
                            break
                except (ValueError, TypeError):
                    pass

            # Pattern 2: e.g. "minimum 8 years", "at least 5 years", "min 5 yrs"
            if not too_senior:
                min_matches = re.findall(r'(?:minimum|at\s+least|min\.?)\s+(\d+)\s*(?:\+|plus)?\s*(?:years?|yrs?)', desc)
                for m in min_matches:
                    try:
                        min_req = int(m)
                        if min_req > max_exp:
                            too_senior = True
                            break
                    except (ValueError, TypeError):
                        pass

            # Pattern 3: e.g. "8+ years", "6+ yrs", "5+ years"
            if not too_senior:
                plus_matches = re.findall(r'(\d+)\s*\+\s*(?:years?|yrs?)', desc)
                for m in plus_matches:
                    try:
                        min_req = int(m)
                        if min_req > max_exp:
                            too_senior = True
                            break
                    except (ValueError, TypeError):
                        pass

            # Pattern 4: e.g. "5 to 8 years", "6 to 9 yrs"
            if not too_senior:
                range_matches = re.findall(r'(\d+)\s*to\s*(\d+)\s*(?:years?|yrs?)', desc)
                for m in range_matches:
                    try:
                        if int(m[0]) > max_exp or int(m[1]) > max_exp + 1:
                            too_senior = True
                            break
                    except (ValueError, TypeError):
                        pass

            if not too_senior:
                passed.append(j)

        return passed

    def _filter_by_applicants(self, jobs: List[Dict]) -> List[Dict]:
        """Filter out jobs with too many applicants (> max_applicants or over 100)"""
        max_limit = self.max_applicants or 100

        passed = []
        for j in jobs:
            count = j.get('num_applicants')
            if count is not None and count > max_limit:
                continue

            # Check textual applicant indicators in description
            desc = j.get('description', '').lower()
            if any(term in desc for term in [
                'over 100', '100+ applicants', '100+ people', '150+ applicants',
                '200+ applicants', 'more than 100', 'over 100 clicked apply',
                'over 100 people clicked apply', 'over 100 applicants'
            ]):
                continue

            # Regex search for applicant counts e.g. "120 applicants", "250 people applied"
            app_matches = re.findall(r'(\d+)\s*(?:\+|plus)?\s*(?:people\s+clicked\s+apply|applicants|people\s+applied|applied)', desc)
            too_many_apps = False
            for am in app_matches:
                try:
                    if int(am) > max_limit:
                        too_many_apps = True
                        break
                except (ValueError, TypeError):
                    pass

            if too_many_apps:
                continue

            passed.append(j)

        return passed

    def _deduplicate(self, jobs: List[Dict]) -> List[Dict]:
        """Remove duplicates by URL or Company+Title"""
        seen_urls = set()
        seen_titles = set()
        unique = []

        for j in jobs:
            url = j.get('url', '').strip()
            key = f"{j.get('company', '').lower()}|{j.get('title', '').lower()}"

            if url and url not in seen_urls and key not in seen_titles:
                seen_urls.add(url)
                seen_titles.add(key)
                unique.append(j)

        return unique

    @staticmethod
    def _sort_by_platform_priority(jobs: List[Dict]) -> List[Dict]:
        """Sort jobs: LinkedIn (1) -> Indeed (2) -> Naukri (3) -> Rest (4), then date_posted desc"""
        priority_map = {'linkedin': 1, 'indeed': 2, 'naukri': 3}
        def get_sort_key(j):
            p = priority_map.get((j.get('platform') or '').lower(), 4)
            dt = j.get('date_posted')
            ts = 0.0
            if dt:
                if hasattr(dt, 'timestamp'):
                    try:
                        ts = dt.timestamp()
                    except Exception:
                        ts = 0.0
                elif isinstance(dt, str):
                    try:
                        ts = datetime.fromisoformat(dt.replace('Z', '+00:00')).timestamp()
                    except Exception:
                        ts = 0.0
            return (p, -ts)
        return sorted(jobs, key=get_sort_key)
