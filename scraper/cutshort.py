"""
Cutshort scraper
AI, software engineering, and tech startup job board
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class CutshortScraper:
    """Scrapes jobs from Cutshort"""

    BASE_URL = "https://cutshort.io"

    def __init__(self, config: dict):
        self.config = config
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    async def scrape(self) -> List[Dict[str, Any]]:
        """Scrape Cutshort jobs"""
        jobs = []

        try:
            for role in self.config['search']['roles'][:3]:
                logger.debug(f"Scraping Cutshort for: {role}")
                role_jobs = await self._scrape_role(role)
                jobs.extend(role_jobs)
                await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Cutshort scrape error: {e}")

        return jobs

    async def _scrape_role(self, role: str) -> List[Dict[str, Any]]:
        """Scrape jobs for a specific role"""
        jobs = []

        try:
            url = f"{self.BASE_URL}/jobs?q={role}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find job listings
            job_listings = soup.find_all('div', class_='job-item')

            for listing in job_listings:
                try:
                    job = self._parse_job_listing(listing)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Error parsing Cutshort job: {e}")
                    continue

        except requests.exceptions.RequestException as e:
            logger.error(f"Cutshort request error: {e}")

        return jobs

    def _parse_job_listing(self, listing) -> Dict[str, Any]:
        """Parse a Cutshort job listing"""
        try:
            title_elem = listing.find('h3', class_='job-title')
            company_elem = listing.find('div', class_='company-name')
            location_elem = listing.find('span', class_='location')
            link_elem = listing.find('a', class_='job-link')

            title = title_elem.text.strip() if title_elem else 'N/A'
            company = company_elem.text.strip() if company_elem else 'N/A'
            location = location_elem.text.strip() if location_elem else 'Remote'
            url = link_elem['href'] if link_elem and 'href' in link_elem.attrs else ''

            return {
                'platform': 'cutshort',
                'title': title,
                'company': company,
                'location': location,
                'url': url,
                'description': '',
                'date_posted': datetime.now().isoformat(),
                'job_type': 'Full-time',
                'num_applicants': None,
                'is_easy_apply': False,
                'scraped_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.debug(f"Error parsing Cutshort job: {e}")
            return None
