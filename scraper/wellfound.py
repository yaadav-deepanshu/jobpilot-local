"""
Wellfound (formerly AngelList) scraper
Startup and tech job board
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class WellfoundScraper:
    """Scrapes jobs from Wellfound"""

    BASE_URL = "https://wellfound.com"
    API_URL = "https://api.wellfound.com/graphql"

    def __init__(self, config: dict):
        self.config = config
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    async def scrape(self) -> List[Dict[str, Any]]:
        """Scrape Wellfound jobs"""
        jobs = []

        try:
            for role in self.config['search']['roles'][:3]:
                logger.debug(f"Scraping Wellfound for: {role}")
                role_jobs = await self._scrape_role(role)
                jobs.extend(role_jobs)
                await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Wellfound scrape error: {e}")

        return jobs

    async def _scrape_role(self, role: str) -> List[Dict[str, Any]]:
        """Scrape jobs for a specific role"""
        jobs = []

        try:
            # Wellfound doesn't have great public API, so we scrape the search page
            url = f"{self.BASE_URL}/jobs?title={role}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find job listings
            job_items = soup.find_all('div', class_='job-card')

            for item in job_items:
                try:
                    job = self._parse_job_item(item)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Error parsing Wellfound job: {e}")
                    continue

        except requests.exceptions.RequestException as e:
            logger.error(f"Wellfound request error: {e}")

        return jobs

    def _parse_job_item(self, item) -> Dict[str, Any]:
        """Parse a Wellfound job item"""
        try:
            title_elem = item.find('h2', class_='job-title')
            company_elem = item.find('h3', class_='company-name')
            location_elem = item.find('span', class_='location')
            link_elem = item.find('a', class_='job-link')

            title = title_elem.text.strip() if title_elem else 'N/A'
            company = company_elem.text.strip() if company_elem else 'N/A'
            location = location_elem.text.strip() if location_elem else 'Remote'
            url = link_elem['href'] if link_elem and 'href' in link_elem.attrs else ''

            return {
                'platform': 'wellfound',
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
            logger.debug(f"Error parsing Wellfound job: {e}")
            return None
