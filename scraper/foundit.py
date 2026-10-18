"""
foundit (formerly Monster India) scraper
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class FounditScraper:
    """Scrapes jobs from foundit.in"""

    BASE_URL = "https://www.foundit.in"

    def __init__(self, config: dict):
        self.config = config
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    async def scrape(self) -> List[Dict[str, Any]]:
        """Scrape foundit jobs"""
        jobs = []

        try:
            for role in self.config['search']['roles'][:3]:
                logger.debug(f"Scraping foundit for: {role}")
                role_jobs = await self._scrape_role(role)
                jobs.extend(role_jobs)
                await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"foundit scrape error: {e}")

        return jobs

    async def _scrape_role(self, role: str) -> List[Dict[str, Any]]:
        """Scrape jobs for a specific role"""
        jobs = []

        try:
            location = self.config['search']['location'].replace(' ', '%20')
            url = f"{self.BASE_URL}/jobs?searchType=browse_sr&query={role}&location={location}"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find job postings
            job_postings = soup.find_all('div', class_='srp-jobcard-container')

            for posting in job_postings:
                try:
                    job = self._parse_job_posting(posting)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Error parsing foundit job: {e}")
                    continue

        except requests.exceptions.RequestException as e:
            logger.error(f"foundit request error: {e}")

        return jobs

    def _parse_job_posting(self, posting) -> Dict[str, Any]:
        """Parse a foundit job posting"""
        try:
            title_elem = posting.find('h2', class_='job-title')
            company_elem = posting.find('h3', class_='company-name')
            location_elem = posting.find('span', class_='location')
            link_elem = posting.find('a', class_='job-posting-link')
            salary_elem = posting.find('span', class_='salary')

            title = title_elem.text.strip() if title_elem else 'N/A'
            company = company_elem.text.strip() if company_elem else 'N/A'
            location = location_elem.text.strip() if location_elem else 'N/A'
            salary = salary_elem.text.strip() if salary_elem else 'N/A'
            url = link_elem['href'] if link_elem and 'href' in link_elem.attrs else ''

            return {
                'platform': 'foundit',
                'title': title,
                'company': company,
                'location': location,
                'salary': salary,
                'url': url,
                'description': '',
                'date_posted': datetime.now().isoformat(),
                'job_type': 'Full-time',
                'num_applicants': None,
                'is_easy_apply': False,
                'scraped_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.debug(f"Error parsing foundit job: {e}")
            return None
