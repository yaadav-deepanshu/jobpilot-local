"""
Real Multi-Platform Job Scraper
Collects real jobs from LinkedIn, Indeed, Naukri, and Glassdoor using JobSpy
"""

import logging
import time
import math
import pandas as pd
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime, timezone, timedelta
from jobspy import scrape_jobs

logger = logging.getLogger(__name__)

class RealJobScraper:
    """Robust multi-platform job scraper using JobSpy"""

    # Mapping of platforms to JobSpy site names and country kwargs (including abroad platforms)
    SUPPORTED_SITES = {
        'linkedin': {'site': 'linkedin', 'country': None},
        'indeed': {'site': 'indeed', 'country': 'india'},
        'naukri': {'site': 'naukri', 'country': None},
        'glassdoor': {'site': 'glassdoor', 'country': None},
        'zip_recruiter': {'site': 'zip_recruiter', 'country': None},
        'google': {'site': 'google', 'country': None},
        'bayt': {'site': 'bayt', 'country': None},
    }

    def __init__(self, config: dict):
        self.config = config
        self.search_config = config.get('search', {})
        self.roles = self.search_config.get('roles', ['DevOps Engineer', 'Cloud Engineer', 'SRE'])
        self.location = self.search_config.get('location', 'Bengaluru')

    def scrape_all(
        self,
        today_only: bool = False,
        hours_old: Optional[int] = None,
        results_per_query: int = 15,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape jobs across enabled platforms.
        hours_old: Specific time window in hours (e.g. 2, 6, 12, 24).
        progress_callback(message, count_found) is called to report live status.
        """
        all_jobs = []
        enabled_platforms = self._get_enabled_platforms()

        total_queries = len(enabled_platforms) * min(len(self.roles), 3)
        completed_queries = 0

        logger.info(f"🚀 Starting scrape across {len(enabled_platforms)} platforms: {list(enabled_platforms.keys())}")

        for platform_key, site_info in enabled_platforms.items():
            site_name = site_info['site']
            country = site_info['country']

            # Use top roles to avoid excessive requests
            search_roles = self.roles[:3]

            for role in search_roles:
                completed_queries += 1
                msg = f"Scraping {platform_key.capitalize()} for '{role}' in {self.location}..."
                logger.info(f"[{completed_queries}/{total_queries}] {msg}")

                if progress_callback:
                    progress_callback(msg, len(all_jobs))

                try:
                    kwargs = {
                        'site_name': [site_name],
                        'search_term': role,
                        'location': self.location,
                        'results_wanted': results_per_query,
                        'fetch_description': True,
                    }

                    if country:
                        kwargs['country_indeed'] = country

                    if hours_old is not None:
                        kwargs['hours_old'] = hours_old
                    elif today_only:
                        # JobSpy supports hours_old
                        kwargs['hours_old'] = 24

                    df = scrape_jobs(**kwargs)

                    if df is not None and len(df) > 0:
                        records = df.to_dict('records')
                        formatted = self._format_records(records, platform_key)
                        all_jobs.extend(formatted)
                        logger.info(f"  ✓ {platform_key}: Found {len(formatted)} jobs for '{role}'")
                    else:
                        logger.info(f"  - {platform_key}: No jobs returned for '{role}'")

                except Exception as e:
                    logger.warning(f"  ✗ {platform_key} scrape error for '{role}': {e}")

                # Polite delay between requests to avoid rate limits
                time.sleep(1)

        # Deduplicate by URL
        unique_jobs = self._deduplicate(all_jobs)
        logger.info(f"✓ Scraping complete: {len(all_jobs)} raw → {len(unique_jobs)} unique jobs")

        if progress_callback:
            progress_callback(f"Scraping complete! Found {len(unique_jobs)} unique jobs.", len(unique_jobs))

        return unique_jobs

    def _get_enabled_platforms(self) -> Dict[str, dict]:
        """Return dict of enabled platforms configured in config.yaml"""
        platforms_cfg = self.config.get('platforms', {})
        enabled = {}

        for key, info in self.SUPPORTED_SITES.items():
            if platforms_cfg.get(key, {}).get('enabled', True):
                enabled[key] = info

        # Fallback to at least linkedin and indeed if nothing configured
        if not enabled:
            enabled = {
                'linkedin': self.SUPPORTED_SITES['linkedin'],
                'indeed': self.SUPPORTED_SITES['indeed'],
            }

        return enabled

    def _clean_str(self, val: Any, default: str = '') -> str:
        """Safely clean a string value and ignore NaN/None"""
        if val is None or pd.isna(val):
            return default
        s = str(val).strip()
        return default if s.lower() in ('nan', 'none', 'null') else s

    def _clean_int(self, val: Any) -> Optional[int]:
        """Safely convert a value to int and ignore NaN/None"""
        if val is None or pd.isna(val):
            return None
        try:
            if isinstance(val, (int, float)):
                if math.isnan(val) or math.isinf(val):
                    return None
                return int(val)
            s = str(val).strip()
            if not s or s.lower() in ('nan', 'none', 'null'):
                return None
            return int(float(s))
        except Exception:
            return None

    def _format_records(self, records: List[Dict], platform: str) -> List[Dict[str, Any]]:
        """Normalize raw JobSpy records to our Job schema safely without NaN errors"""
        formatted = []
        now_dt = datetime.now(timezone.utc)

        for r in records:
            url = self._clean_str(r.get('job_url') or r.get('url'))
            title = self._clean_str(r.get('title'))
            company = self._clean_str(r.get('company'), 'Unknown Company')

            if not url or not title:
                continue

            # Parse date_posted
            date_posted = None
            raw_date = r.get('date_posted')
            if raw_date and not pd.isna(raw_date):
                if isinstance(raw_date, datetime):
                    date_posted = raw_date
                elif hasattr(raw_date, 'to_pydatetime'):  # pandas Timestamp
                    date_posted = raw_date.to_pydatetime()
                elif isinstance(raw_date, str):
                    try:
                        date_posted = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
                    except Exception:
                        pass

            if not date_posted:
                date_posted = now_dt

            # Format salary safely
            min_sal = self._clean_int(r.get('min_amount') or r.get('min_salary'))
            max_sal = self._clean_int(r.get('max_amount') or r.get('max_salary'))
            currency = self._clean_str(r.get('currency'), '')

            salary_str = ''
            if min_sal and max_sal:
                salary_str = f"{currency} {min_sal:,.0f} - {max_sal:,.0f}".strip()
            elif min_sal:
                salary_str = f"{currency} {min_sal:,.0f}+".strip()
            elif max_sal:
                salary_str = f"{currency} up to {max_sal:,.0f}".strip()

            # Clean location
            loc = self._clean_str(r.get('location'), self.location)

            # Clean easy apply
            easy_apply_val = r.get('is_easy_apply')
            is_easy = bool(easy_apply_val) if (easy_apply_val is not None and not pd.isna(easy_apply_val)) else False

            desc_text = self._clean_str(r.get('description'))
            num_apps = self._clean_int(r.get('num_applicants'))
            if num_apps is None and desc_text:
                import re
                if any(kw in desc_text.lower() for kw in ['over 100 people', 'over 100 applicants', 'over 100 clicked', '100+ applicants', '100+ people', 'more than 100']):
                    num_apps = 101
                else:
                    app_m = re.search(r'(\d+)\s*(?:\+|plus)?\s*(?:people\s+clicked\s+apply|applicants|people\s+applied|applied)', desc_text, re.IGNORECASE)
                    if app_m:
                        try:
                            num_apps = int(app_m.group(1))
                        except Exception:
                            pass

            formatted.append({
                'platform': platform,
                'title': title,
                'company': company,
                'location': loc,
                'url': url,
                'description': desc_text,
                'salary': salary_str,
                'salary_min': min_sal,
                'salary_max': max_sal,
                'date_posted': date_posted,
                'job_type': self._clean_str(r.get('job_type'), 'Full-time').capitalize(),
                'num_applicants': num_apps,
                'is_easy_apply': is_easy,
                'status': 'new',
            })

        return formatted

    def _deduplicate(self, jobs: List[Dict]) -> List[Dict]:
        """Remove duplicates by URL or Company+Title"""
        seen_urls = set()
        seen_titles = set()
        unique = []

        for j in jobs:
            url = j.get('url', '').strip()
            title_key = f"{j.get('company', '').lower()}|{j.get('title', '').lower()}"

            if url and url not in seen_urls and title_key not in seen_titles:
                seen_urls.add(url)
                seen_titles.add(title_key)
                unique.append(j)

        return unique

# Backward-compatibility alias
JobScraper = RealJobScraper

