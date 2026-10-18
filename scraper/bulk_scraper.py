"""
Bulk job scraper
Maximizes job collection across all platforms
"""

import logging
import asyncio
from typing import List, Dict, Any
from datetime import datetime
from jobspy import scrape_jobs
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class BulkJobScraper:
    """Scraper optimized to collect maximum jobs"""

    def __init__(self, config: dict):
        self.config = config
        self.search_config = config['search']
        self.jobs = []

    async def scrape_maximum(self) -> List[Dict[str, Any]]:
        """Scrape maximum jobs across all platforms"""
        logger.info("🔥 BULK SCRAPE — Maximizing job collection...")

        all_jobs = []

        # Generate multiple search variations
        search_terms = self._generate_search_variations()

        # LinkedIn, Indeed, Glassdoor via JobSpy
        logger.info(f"📍 Scraping LinkedIn, Indeed, Glassdoor ({len(search_terms)} variations each)...")
        for platform in ['linkedin', 'indeed', 'glassdoor']:
            for search_term in search_terms:
                try:
                    logger.debug(f"  Scraping {platform} for: {search_term}")
                    jobs = scrape_jobs(
                        site_name=[platform],
                        search_term=search_term,
                        location=self.search_config['location'],
                        results_wanted=100,  # Max results per search
                        hours_old=168,  # 1 week old (more results)
                        country_indeed="IN"
                    )
                    formatted = self._format_jobs(jobs.to_dict('records'), platform)
                    all_jobs.extend(formatted)
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.warning(f"Error scraping {platform}: {e}")

        # Naukri (India focused — likely highest volume)
        logger.info("📍 Scraping Naukri (India's largest job board)...")
        try:
            naukri_jobs = await self._scrape_naukri_bulk()
            all_jobs.extend(naukri_jobs)
        except Exception as e:
            logger.warning(f"Naukri error: {e}")

        # Cutshort (Tech/AI jobs)
        logger.info("📍 Scraping Cutshort (Tech jobs)...")
        try:
            cutshort_jobs = await self._scrape_cutshort_bulk()
            all_jobs.extend(cutshort_jobs)
        except Exception as e:
            logger.warning(f"Cutshort error: {e}")

        logger.info(f"✓ Total jobs scraped: {len(all_jobs)}")
        return all_jobs

    def _generate_search_variations(self) -> List[str]:
        """Generate multiple search term variations"""
        base_roles = self.search_config['roles']

        # Variations to maximize results
        variations = []
        for role in base_roles:
            variations.extend([
                role,
                role.replace(' ', ''),  # Remove spaces
                role.split()[0],  # First word only
            ])

        # Add generic terms for broader results
        variations.extend([
            'engineer',
            'developer',
            'infrastructure',
            'automation',
            'cloud',
        ])

        return list(set(variations))  # Remove duplicates

    async def _scrape_naukri_bulk(self) -> List[Dict[str, Any]]:
        """Scrape maximum jobs from Naukri"""
        jobs = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            for role in self.search_config['roles']:
                for page in range(1, 6):  # Pages 1-5 (max results)
                    try:
                        location = self.search_config['location'].replace(' ', '-').lower()
                        role_formatted = role.replace(' ', '-').lower()

                        url = f"https://www.naukri.com/jobs-{role_formatted}-in-{location}-{page}"

                        response = requests.get(url, headers=headers, timeout=10)
                        response.raise_for_status()

                        soup = BeautifulSoup(response.content, 'html.parser')
                        job_cards = soup.find_all('article', class_='jobTuple')

                        for card in job_cards:
                            try:
                                job = self._parse_naukri_job(card)
                                if job:
                                    jobs.append(job)
                            except:
                                continue

                        await asyncio.sleep(0.5)

                    except Exception as e:
                        logger.debug(f"Naukri page {page} error: {e}")
                        continue

        except Exception as e:
            logger.warning(f"Naukri bulk error: {e}")

        return jobs

    async def _scrape_cutshort_bulk(self) -> List[Dict[str, Any]]:
        """Scrape maximum jobs from Cutshort"""
        jobs = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            for role in self.search_config['roles']:
                try:
                    url = f"https://cutshort.io/jobs?q={role}&l={self.search_config['location']}"

                    response = requests.get(url, headers=headers, timeout=10)
                    response.raise_for_status()

                    soup = BeautifulSoup(response.content, 'html.parser')
                    job_listings = soup.find_all('div', class_='job-item')

                    for listing in job_listings:
                        try:
                            job = self._parse_cutshort_job(listing)
                            if job:
                                jobs.append(job)
                        except:
                            continue

                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.debug(f"Cutshort error for {role}: {e}")

        except Exception as e:
            logger.warning(f"Cutshort bulk error: {e}")

        return jobs

    def _parse_naukri_job(self, card) -> Dict[str, Any]:
        """Parse Naukri job card"""
        try:
            title_elem = card.find('a', class_='jobTitle')
            company_elem = card.find('a', class_='companyName')
            location_elem = card.find('span', class_='location')

            if not title_elem:
                return None

            return {
                'platform': 'naukri',
                'title': title_elem.text.strip(),
                'company': company_elem.text.strip() if company_elem else 'N/A',
                'location': location_elem.text.strip() if location_elem else 'N/A',
                'url': title_elem.get('href', ''),
                'description': '',
                'date_posted': datetime.now().isoformat(),
                'job_type': 'Full-time',
                'num_applicants': None,
                'is_easy_apply': False,
                'scraped_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.debug(f"Parse Naukri job error: {e}")
            return None

    def _parse_cutshort_job(self, listing) -> Dict[str, Any]:
        """Parse Cutshort job listing"""
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
                'url': listing.find('a', class_='job-link').get('href', '') if listing.find('a', class_='job-link') else '',
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
