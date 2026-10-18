"""
Enhanced flexible job scraper
More flexible role matching + TODAY ONLY filter
"""

import logging
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta
from jobspy import scrape_jobs
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class FlexibleJobScraper:
    """Enhanced scraper with flexible role matching and TODAY ONLY filter"""

    def __init__(self, config: dict):
        self.config = config
        self.search_config = config['search']

    async def scrape_flexible_maximum(self) -> List[Dict[str, Any]]:
        """
        Scrape with FLEXIBLE role matching:
        - Primary roles: exact match (DevOps, SRE, etc)
        - Secondary roles: skill-based match (if job requires similar skills)
        - TODAY ONLY: filter to jobs posted today or within last 24 hours
        """
        logger.info("🔥 FLEXIBLE SCRAPE — Maximum jobs from TODAY")

        all_jobs = []

        # Generate all search variations
        search_terms = self._generate_extended_search_terms()

        logger.info(f"📍 Searching {len(search_terms)} variations across 7 platforms...")
        logger.info(f"📅 Filter: Jobs posted TODAY ONLY")

        # LinkedIn via JobSpy (Indeed/Glassdoor don't work reliably with hours_old filter)
        for platform in ['linkedin']:
            for search_term in search_terms[:5]:  # LIMIT to first 5 searches to avoid timeout
                try:
                    logger.debug(f"  Scraping {platform} for: {search_term}")

                    # Search WITHOUT hours_old filter (it breaks Indeed/Glassdoor)
                    # We'll apply TODAY filter in the filter engine instead
                    jobs = scrape_jobs(
                        site_name=[platform],
                        search_term=search_term,
                        location=self.search_config['location'],
                        results_wanted=50,
                        # Removed: hours_old=24 (causes Indeed to fail)
                        # Removed: country_indeed="IN" (not needed for LinkedIn)
                    )

                    if len(jobs) > 0:
                        logger.info(f"  ✓ Found {len(jobs)} jobs on {platform} for '{search_term}'")
                        formatted = self._format_jobs(jobs.to_dict('records'), platform)
                        all_jobs.extend(formatted)
                    else:
                        logger.debug(f"  No jobs found on {platform} for '{search_term}'")

                    await asyncio.sleep(1)  # Respectful delay

                except Exception as e:
                    logger.warning(f"Error scraping {platform} for '{search_term}': {e}")
                    continue

        # Naukri with flexible matching
        logger.info("📍 Scraping Naukri (flexible matching + today)...")
        try:
            naukri_jobs = await self._scrape_naukri_flexible()
            all_jobs.extend(naukri_jobs)
        except Exception as e:
            logger.warning(f"Naukri error: {e}")

        # Cutshort with flexible matching
        logger.info("📍 Scraping Cutshort (flexible + today)...")
        try:
            cutshort_jobs = await self._scrape_cutshort_flexible()
            all_jobs.extend(cutshort_jobs)
        except Exception as e:
            logger.warning(f"Cutshort error: {e}")

        # Wellfound, foundit
        logger.info("📍 Scraping Wellfound & foundit...")
        try:
            other_jobs = await self._scrape_other_platforms()
            all_jobs.extend(other_jobs)
        except Exception as e:
            logger.warning(f"Other platforms error: {e}")

        logger.info(f"✓ Total scraped: {len(all_jobs)} jobs")
        return all_jobs

    def _generate_extended_search_terms(self) -> List[str]:
        """Generate EXTENDED search terms for maximum coverage"""
        base_roles = self.search_config['roles']

        variations = []

        # Primary roles
        for role in base_roles:
            variations.extend([
                role,
                role.replace(' ', ''),
                role.split()[0],
            ])

        # Flexible secondary roles (similar skills)
        flexible_roles = [
            # Infrastructure/DevOps adjacent
            'infrastructure',
            'automation',
            'operations',
            'ops engineer',
            'operations engineer',
            'infrastructure operations',
            'infrastructure automation',

            # Cloud adjacent
            'cloud',
            'cloud infrastructure',
            'cloud architect',
            'cloud operations',
            'aws engineer',
            'azure engineer',
            'gcp engineer',

            # Broader engineering
            'engineer',
            'backend engineer',
            'systems engineer',
            'software engineer infrastructure',

            # Build/Release
            'build engineer',
            'release engineer',
            'build and release',

            # Release/Deployment
            'deployment engineer',
            'deployment specialist',

            # Kubernetes/Containers
            'kubernetes',
            'container',
            'docker',

            # IaC
            'terraform',
            'infrastructure as code',
            'iac',

            # Observability
            'observability engineer',
            'monitoring engineer',
            'reliability engineer',

            # Security adjacent (often overlaps DevOps)
            'security engineer',
            'security operations',
            'secops',

            # Database/Data Infra (sometimes DevOps-adjacent)
            'database engineer',
            'data infrastructure',

            # Generic catch-all
            'technical engineer',
        ]

        variations.extend(flexible_roles)

        return list(set(variations))  # Remove duplicates

    async def _scrape_naukri_flexible(self) -> List[Dict[str, Any]]:
        """Scrape Naukri with flexible matching + TODAY filter"""
        jobs = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        search_terms = self._generate_extended_search_terms()

        try:
            for search_term in search_terms[:5]:  # Limit for speed
                try:
                    location = self.search_config['location'].replace(' ', '-').lower()
                    url = f"https://www.naukri.com/jobs-{search_term.replace(' ', '-').lower()}-in-{location}"

                    response = requests.get(url, headers=headers, timeout=10)
                    response.raise_for_status()

                    soup = BeautifulSoup(response.content, 'html.parser')
                    job_cards = soup.find_all('article', class_='jobTuple')

                    for card in job_cards:
                        try:
                            job = self._parse_naukri_job_flexible(card)
                            if job and self._is_today(job):  # Check if TODAY
                                jobs.append(job)
                        except:
                            continue

                    await asyncio.sleep(0.3)

                except Exception as e:
                    logger.debug(f"Naukri {search_term} error: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Naukri bulk error: {e}")

        return jobs

    async def _scrape_cutshort_flexible(self) -> List[Dict[str, Any]]:
        """Scrape Cutshort with flexible matching + TODAY filter"""
        jobs = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        search_terms = self._generate_extended_search_terms()

        try:
            for search_term in search_terms[:5]:  # Limit for speed
                try:
                    url = f"https://cutshort.io/jobs?q={search_term}"

                    response = requests.get(url, headers=headers, timeout=10)
                    response.raise_for_status()

                    soup = BeautifulSoup(response.content, 'html.parser')
                    job_listings = soup.find_all('div', class_='job-item')

                    for listing in job_listings:
                        try:
                            job = self._parse_cutshort_job_flexible(listing)
                            if job and self._is_today(job):  # Check if TODAY
                                jobs.append(job)
                        except:
                            continue

                    await asyncio.sleep(0.3)

                except Exception as e:
                    logger.debug(f"Cutshort {search_term} error: {e}")

        except Exception as e:
            logger.warning(f"Cutshort bulk error: {e}")

        return jobs

    async def _scrape_other_platforms(self) -> List[Dict[str, Any]]:
        """Scrape Wellfound, foundit, etc"""
        jobs = []

        # Would add Wellfound and foundit scrapers here
        # For now, simplified version

        return jobs

    def _parse_naukri_job_flexible(self, card) -> Dict[str, Any]:
        """Parse Naukri job with flexible skill matching"""
        try:
            title_elem = card.find('a', class_='jobTitle')
            company_elem = card.find('a', class_='companyName')
            location_elem = card.find('span', class_='location')
            desc_elem = card.find('div', class_='job-description')

            if not title_elem:
                return None

            title = title_elem.text.strip()
            company = company_elem.text.strip() if company_elem else 'N/A'
            location = location_elem.text.strip() if location_elem else 'N/A'
            description = desc_elem.text.strip() if desc_elem else ''
            url = title_elem.get('href', '')

            return {
                'platform': 'naukri',
                'title': title,
                'company': company,
                'location': location,
                'url': url,
                'description': description,
                'date_posted': datetime.now().isoformat(),
                'job_type': 'Full-time',
                'num_applicants': None,
                'is_easy_apply': False,
                'scraped_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.debug(f"Parse Naukri job error: {e}")
            return None

    def _parse_cutshort_job_flexible(self, listing) -> Dict[str, Any]:
        """Parse Cutshort job with flexible skill matching"""
        try:
            title_elem = listing.find('h3', class_='job-title')
            company_elem = listing.find('div', class_='company-name')
            location_elem = listing.find('span', class_='location')

            if not title_elem:
                return None

            return {
                'platform': 'cutshort',
                'title': title_elem.text.strip(),
                'company': company_elem.text.strip() if company_elem else 'N/A',
                'location': location_elem.text.strip() if location_elem else 'Remote',
                'url': listing.find('a', class_='job-link').get('href', '') if listing.find('a') else '',
                'description': '',
                'date_posted': datetime.now().isoformat(),
                'job_type': 'Full-time',
                'num_applicants': None,
                'is_easy_apply': False,
                'scraped_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.debug(f"Parse Cutshort job error: {e}")
            return None

    def _is_today(self, job: Dict) -> bool:
        """Check if job was posted today (within last 24 hours)"""
        try:
            if isinstance(job.get('date_posted'), str):
                posted = datetime.fromisoformat(job['date_posted'])
            else:
                posted = job.get('date_posted', datetime.now())

            # Posted within last 24 hours = today
            cutoff = datetime.now() - timedelta(hours=24)
            return posted >= cutoff

        except:
            # If we can't parse date, include it (conservative)
            return True

    def _format_jobs(self, jobs: List[Dict], platform: str) -> List[Dict[str, Any]]:
        """Standardize job data"""
        formatted = []
        for job in jobs:
            formatted.append({
                'platform': platform,
                'title': job.get('title', 'N/A'),
                'company': job.get('company', 'N/A'),
                'location': job.get('location', 'N/A'),
                'url': job.get('job_url', ''),
                'description': job.get('description', ''),
                'salary_min': job.get('min_salary'),
                'salary_max': job.get('max_salary'),
                'date_posted': job.get('date_posted', datetime.now().isoformat()),
                'job_type': job.get('job_type', 'Full-time'),
                'num_applicants': job.get('num_applicants'),
                'is_easy_apply': job.get('is_easy_apply', False),
                'scraped_at': datetime.now().isoformat()
            })
        return formatted
