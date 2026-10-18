"""
Enhanced filter engine with flexible skill matching
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class FlexibleFilterEngine:
    """Enhanced filter with flexible skill matching + TODAY ONLY"""

    def __init__(self, config: dict):
        self.config = config
        self.search_config = config['search']

        # Your core skills (from resume)
        self.core_skills = [
            'aws', 'azure', 'gcp', 'cloud',
            'terraform', 'cloudformation', 'ansible', 'iac',
            'docker', 'kubernetes', 'ecs', 'ecr', 'container',
            'ci/cd', 'jenkins', 'github', 'gitlab', 'codepipeline',
            'python', 'bash', 'shell', 'scripting',
            'cloudwatch', 'prometheus', 'grafana', 'elk', 'monitoring',
            'iam', 'security', 'kms', 'waf', 'sso',
            'lambda', 'automation', 'devops', 'sre', 'infrastructure'
        ]

    def filter_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply flexible filters"""
        logger.info(f"🔎 Filtering {len(jobs)} jobs (flexible + TODAY ONLY)...")

        filtered = jobs
        initial_count = len(jobs)

        # Filter 1: TODAY ONLY (last 24 hours)
        filtered = self._filter_by_recency_strict(filtered)

        # Filter 2: Flexible role matching
        filtered = self._filter_by_flexible_role(filtered)

        # Filter 3: Location
        filtered = self._filter_by_location(filtered)

        # Filter 4: Applicants
        filtered = self._filter_by_applicants(filtered)

        # Filter 5: Excluded keywords
        filtered = self._filter_by_keywords(filtered)

        # Filter 6: Dedup
        filtered = self._filter_duplicates(filtered)

        logger.info(f"✓ Filtered: {initial_count} → {len(filtered)} jobs (TODAY ONLY)")
        return filtered

    def _filter_by_recency_strict(self, jobs: List[Dict]) -> List[Dict]:
        """Filter to TODAY ONLY (last 24 hours)"""
        cutoff_date = datetime.now() - timedelta(hours=24)

        filtered = []
        for job in jobs:
            try:
                posted = datetime.fromisoformat(job.get('date_posted', datetime.now().isoformat()))
                if posted >= cutoff_date:
                    filtered.append(job)
            except:
                # If we can't parse, include it
                filtered.append(job)

        logger.debug(f"  TODAY filter: {len(jobs)} → {len(filtered)} (last 24 hours)")
        return filtered

    def _filter_by_flexible_role(self, jobs: List[Dict]) -> List[Dict]:
        """
        Flexible role matching:
        - Exact match: DevOps, SRE, Cloud Engineer, etc (PRIMARY)
        - Skill-based: If title contains skill keywords + relevant context
        """
        primary_roles = [r.lower() for r in self.search_config['roles']]

        # Flexible roles that match your skillset
        flexible_keywords = [
            'infrastructure', 'automation', 'operations', 'ops',
            'engineer', 'architect', 'specialist',
            'platform', 'build', 'release', 'deployment',
            'kubernetes', 'container', 'docker',
            'terraform', 'iac',
            'observability', 'monitoring', 'reliability',
            'backend', 'systems',
        ]

        filtered = []
        for job in jobs:
            title = job.get('title', '').lower()
            description = job.get('description', '').lower()
            full_text = f"{title} {description}"

            # PRIMARY: Exact role match
            if any(role in title for role in primary_roles):
                filtered.append(job)
                continue

            # FLEXIBLE: Has multiple skill keywords
            skill_count = sum(1 for skill in self.core_skills if skill in full_text)
            keyword_count = sum(1 for keyword in flexible_keywords if keyword in title)

            # If job has 3+ of your skills AND 1+ relevant keyword = FLEXIBLE MATCH
            if skill_count >= 3 and keyword_count >= 1:
                filtered.append(job)
                logger.debug(f"  Flexible match: {job.get('title')} ({skill_count} skills, {keyword_count} keywords)")
                continue

        logger.debug(f"  Role filter: {len(jobs)} → {len(filtered)}")
        return filtered

    def _filter_by_location(self, jobs: List[Dict]) -> List[Dict]:
        """Filter by location"""
        target_location = self.search_config['location'].lower()
        allow_remote = self.search_config.get('remote', True)

        filtered = []
        for job in jobs:
            location = job.get('location', '').lower()

            if target_location in location or 'all' in location:
                filtered.append(job)
            elif allow_remote and 'remote' in location:
                filtered.append(job)

        logger.debug(f"  Location filter: {len(jobs)} → {len(filtered)}")
        return filtered

    def _filter_by_applicants(self, jobs: List[Dict]) -> List[Dict]:
        """Filter by applicant count"""
        max_applicants = self.search_config.get('max_applicants', 100)

        filtered = []
        for job in jobs:
            num_applicants = job.get('num_applicants')

            # Include if unknown or under threshold
            if num_applicants is None or num_applicants <= max_applicants:
                filtered.append(job)

        logger.debug(f"  Applicant filter: {len(jobs)} → {len(filtered)}")
        return filtered

    def _filter_by_keywords(self, jobs: List[Dict]) -> List[Dict]:
        """Exclude unwanted keywords"""
        exclude_keywords = [k.lower() for k in self.search_config.get('exclude_keywords', [])]

        filtered = []
        for job in jobs:
            title = job.get('title', '').lower()
            description = job.get('description', '').lower()
            full_text = f"{title} {description}"

            if not any(keyword in full_text for keyword in exclude_keywords):
                filtered.append(job)

        logger.debug(f"  Keyword filter: {len(jobs)} → {len(filtered)}")
        return filtered

    def _filter_duplicates(self, jobs: List[Dict]) -> List[Dict]:
        """Remove duplicates"""
        seen = set()
        filtered = []

        for job in jobs:
            key = f"{job['company'].lower()}|{job['title'].lower()}"

            if key not in seen:
                seen.add(key)
                filtered.append(job)

        logger.debug(f"  Dedup filter: {len(jobs)} → {len(filtered)}")
        return filtered
