"""
Naukri.com scraper
India's largest job board
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class NaukriScraper:
    """Scrapes jobs from Naukri.com"""

    BASE_URL = "https://www.naukri.com/jobs"

    def __init__(self, config: dict):
        self.config = config
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    async def scrape(self) -> List[Dict[str, Any]]:
        """Scrape Naukri jobs"""
        jobs = []

        try:
            for role in self.config['search']['roles'][:3]:  # Limit to 3 roles
                url = self._build_url(role)
                logger.debug(f"Scraping: {url}")

                role_jobs = await self._scrape_page(url)
                jobs.extend(role_jobs)

                # Rate limiting
                await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Naukri scrape error: {e}")

        return jobs

    def _build_url(self, role: str) -> str:
        """Build Naukri search URL"""
        location = self.config['search']['location'].replace(' ', '-').lower()
        role_formatted = role.replace(' ', '-').lower()
        return f"{self.BASE_URL}-{role_formatted}-in-{location}"

    async def _scrape_page(self, url: str) -> List[Dict[str, Any]]:
        """Scrape a single Naukri page"""
        jobs = []

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find job cards (Naukri uses specific class names)
            job_cards = soup.find_all('article', class_='jobTuple')

            for card in job_cards:
                try:
                    job = self._parse_job_card(card)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Error parsing Naukri job card: {e}")
                    continue

        except requests.exceptions.RequestException as e:
            logger.error(f"Naukri request error: {e}")

        return jobs

    def _parse_job_card(self, card) -> Dict[str, Any]:
        """Parse a Naukri job card"""
        try:
            # Extract job details from card
            title_elem = card.find('a', class_='jobTitle')
            company_elem = card.find('a', class_='companyName')
            location_elem = card.find('span', class_='location')
            salary_elem = card.find('span', class_='salary')

            title = title_elem.text.strip() if title_elem else 'N/A'
            company = company_elem.text.strip() if company_elem else 'N/A'
            location = location_elem.text.strip() if location_elem else 'N/A'
            salary = salary_elem.text.strip() if salary_elem else 'N/A'
            url = title_elem['href'] if title_elem and 'href' in title_elem.attrs else ''

            return {
                'platform': 'naukri',
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
            logger.debug(f"Error parsing job card: {e}")
            return None
