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
        self.roles = self.search_config.get('roles', ['Cloud Engineer', 'DevOps Engineer', 'SRE', 'Platform Engineer', 'Infrastructure Engineer', 'Forward Deployed Systems Engineer'])
        self.keywords = self.search_config.get('keywords', ['cloud', 'azure', 'aws', 'gcp', 'google cloud'])
        self.location = self.search_config.get('location', 'Bengaluru')
        self.remote_enabled = self.search_config.get('remote', True)

    def scrape_all(
        self,
        today_only: bool = False,
        hours_old: Optional[int] = None,
        results_per_query: int = 15,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        roles: Optional[List[str]] = None,
        include_remote: Optional[bool] = None,
        keywords: Optional[List[str]] = None,
        include_keyword_queries: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Scrape jobs across enabled platforms.
        hours_old: Specific time window in hours (e.g. 2, 6, 12, 24).
        progress_callback(message, count_found) is called to report live status.
        roles: Optional list of roles to override self.roles.
        include_remote: Optional boolean to explicitly enable/disable remote job queries.
        keywords: Optional list of search keywords (e.g. cloud, azure, aws, gcp, google cloud).
        include_keyword_queries: If True, also executes direct queries for configured search keywords.
        """
        all_jobs = []
        enabled_platforms = self._get_enabled_platforms()

        # Deduplicate and clean roles list while preserving order
        target_roles = roles if roles is not None else self.roles
        clean_roles = []
        seen = set()
        for r in target_roles:
            r_str = str(r).strip()
            if r_str and r_str.lower() not in seen:
                seen.add(r_str.lower())
                clean_roles.append(r_str)

        # Support searching additional search keywords if provided or requested
        target_keywords = keywords if keywords is not None else (self.keywords if include_keyword_queries else [])
        if target_keywords:
            for kw in target_keywords:
                kw_str = str(kw).strip()
                if kw_str and kw_str.lower() not in seen:
                    seen.add(kw_str.lower())
                    clean_roles.append(kw_str)

        if not clean_roles:
            clean_roles = ['Cloud Engineer', 'DevOps Engineer', 'SRE']

        do_remote = self.remote_enabled if include_remote is None else include_remote

        # Calculate total queries accurately
        total_queries = 0
        for platform_key in enabled_platforms:
            has_remote_query = do_remote and platform_key in ('linkedin', 'indeed', 'naukri', 'glassdoor', 'google')
            loc_count = 2 if has_remote_query else 1
            total_queries += len(clean_roles) * loc_count

        completed_queries = 0
        logger.info(f"🚀 Starting scrape across {len(enabled_platforms)} platforms ({len(clean_roles)} roles, remote={do_remote}): {list(enabled_platforms.keys())}")

        for platform_key, site_info in enabled_platforms.items():
            site_name = site_info['site']
            country = site_info['country']

            # Determine query locations for this platform
            loc_queries = [{'location': self.location, 'is_remote': False}]
            if do_remote and platform_key in ('linkedin', 'indeed', 'naukri', 'glassdoor', 'google'):
                # Add Pan-India Remote query to capture "India (Remote)" postings
                loc_queries.append({'location': 'India', 'is_remote': True})

            for loc_info in loc_queries:
                query_location = loc_info['location']
                query_remote = loc_info['is_remote']
                loc_label = f"{query_location} (Remote)" if query_remote else query_location

                for role in clean_roles:
                    completed_queries += 1
                    msg = f"Scraping {platform_key.capitalize()} for '{role}' in {loc_label}..."
                    logger.info(f"[{completed_queries}/{total_queries}] {msg}")

                    if progress_callback:
                        progress_callback(msg, len(all_jobs))

                    try:
                        kwargs = {
                            'site_name': [site_name],
                            'search_term': role,
                            'location': query_location,
                            'is_remote': query_remote,
                            'results_wanted': results_per_query,
                            'fetch_description': True,
                        }

                        if country:
                            kwargs['country_indeed'] = country

                        if hours_old is not None:
                            # JobSpy expects int for hours_old
                            kwargs['hours_old'] = int(hours_old)
                        elif today_only:
                            kwargs['hours_old'] = 24

                        df = scrape_jobs(**kwargs)

                        if df is not None and len(df) > 0:
                            records = df.to_dict('records')
                            formatted = self._format_records(records, platform_key, query_is_remote=query_remote)
                            all_jobs.extend(formatted)
                            logger.info(f"  ✓ {platform_key}: Found {len(formatted)} jobs for '{role}' ({loc_label})")
                        else:
                            logger.info(f"  - {platform_key}: No jobs returned for '{role}' ({loc_label})")

                    except Exception as e:
                        logger.warning(f"  ✗ {platform_key} scrape error for '{role}' ({loc_label}): {e}")

                    # Polite delay between requests to avoid rate limits
                    time.sleep(0.5)

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

    def _format_records(self, records: List[Dict], platform: str, query_is_remote: bool = False) -> List[Dict[str, Any]]:
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
            is_remote_val = r.get('is_remote')
            is_remote_flag = query_is_remote or (bool(is_remote_val) if (is_remote_val is not None and not pd.isna(is_remote_val)) else False)
            if is_remote_flag and 'remote' not in loc.lower() and 'wfh' not in loc.lower():
                loc = f"{loc} (Remote)" if loc else "India (Remote)"

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

