"""
Test Suite: Portal Jobs Direct Requisition Links Verification
Validates that all portal jobs provide direct, authentic job requisition links
and never produce corporate homepages or general search URLs.
"""

import sys
import re
import urllib.parse
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from web.app import create_app
from db.models import db, PortalJob
from scraper.portal_jobs_scanner import PortalJobsScanner
from scraper.company_portals import CompanyPortalsManager


@pytest.fixture(scope="module")
def app():
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


class TestPortalJobsDirectLinks:
    """Comprehensive test suite for portal jobs actual direct links"""

    def test_greenhouse_scraper_produces_direct_job_urls(self):
        """
        Verify that PortalJobsScanner._scrape_greenhouse produces direct canonical
        job-boards.greenhouse.io links containing the job ID, and never corporate
        wrapper homepages or search URLs (e.g. jobs.elastic.co/jobs or stripe.com/jobs/search).
        """
        scanner = PortalJobsScanner()
        test_companies = [
            ('elastic', 'Elastic', 'elastic'),
            ('stripe', 'Stripe', 'stripe'),
            ('cloudflare', 'Cloudflare', 'cloudflare'),
            ('databricks', 'Databricks', 'databricks'),
        ]

        for pid, name, token in test_companies:
            jobs = scanner._scrape_greenhouse(
                p_id=pid,
                company=name,
                category='Top-Tier SaaS',
                base_url=f'https://job-boards.greenhouse.io/{token}',
                board_token=token
            )
            assert len(jobs) > 0, f"Expected jobs for {name}"
            for j in jobs:
                url = j['url']
                # Must be canonical Greenhouse direct URL
                assert 'job-boards.greenhouse.io' in url or 'boards.greenhouse.io' in url, (
                    f"Job URL {url} is not a direct Greenhouse board link"
                )
                # Must contain the specific job ID in path
                assert re.search(r'/jobs/\d+', url), (
                    f"Job URL {url} does not contain job ID in path"
                )
                # Must NOT contain corporate search wrapper path
                assert '/jobs/search' not in url, f"Found generic search path in {url}"
                assert '&gh_jid=' not in url, f"Found duplicate query parameters in {url}"

    def test_format_direct_job_url_never_returns_naked_homepage(self):
        """
        Verify that _format_direct_job_url never returns bare portal homepages.
        """
        # Test naked homepage
        url1 = PortalJobsScanner._format_direct_job_url(
            "https://www.amazon.jobs", "Cloud DevOps Engineer", "amazon_aws", 0
        )
        assert url1 != "https://www.amazon.jobs", "Should not return bare portal homepage"
        assert "q=" in url1 or "base_query=" in url1 or "/jobs/" in url1

        # Test general careers page
        url2 = PortalJobsScanner._format_direct_job_url(
            "https://careers.google.com", "Site Reliability Engineer", "google", 0
        )
        assert url2 != "https://careers.google.com", "Should not return bare portal homepage"
        assert "q=" in url2 or "query=" in url2 or "/jobs/" in url2

    def test_all_database_portal_jobs_have_direct_links(self, app):
        """
        Verify that 100% of portal jobs in instance/jobs.db point to specific job requisitions
        and zero jobs point to corporate homepages or generic search pages.
        """
        with app.app_context():
            jobs = PortalJob.query.all()
            assert len(jobs) > 0, "No portal jobs found in database"

            homepage_patterns = [
                re.compile(r'^https?://[^/]+/?$'),                               # Bare domain
                re.compile(r'^https?://[^/]+/(?:careers|jobs|en|en-us)/?$'),     # Bare /jobs or /careers
                re.compile(r'/jobs\?gh_jid=.*&gh_jid='),                         # Duplicate query
                re.compile(r'/careers/job/?\?'),                                 # Outdated MongoDB wrapper
                re.compile(r'/jobs/search\?gh_jid='),                            # Outdated Stripe wrapper
                re.compile(r'/open-positions/job\?gh_jid='),                     # Outdated Databricks wrapper
            ]

            for j in jobs:
                url = j.url
                assert url, f"Job {j.id} ({j.company}) has empty URL"
                for pat in homepage_patterns:
                    assert not pat.search(url), (
                        f"Job {j.id} ({j.company}: {j.title}) has homepage/wrapper URL: {url}"
                    )

                # Ensure URL contains a specific job identifier or requisition path
                has_job_identifier = (
                    ('/jobs/' in url and any(c.isdigit() for c in url)) or
                    ('/job/' in url) or
                    ('/positions/' in url and any(c.isdigit() for c in url)) or
                    ('lever.co/' in url and len(url.split('/')) >= 5) or
                    ('smartrecruiters.com/' in url and any(c.isdigit() for c in url)) or
                    ('ashbyhq.com/' in url and len(url.split('/')) >= 5) or
                    ('myworkdayjobs.com' in url and '/job/' in url)
                )
                assert has_job_identifier, f"Job {j.id} ({j.company}) lacks requisition identifier: {url}"

    def test_api_portal_jobs_endpoint_returns_direct_links(self, client):
        """
        Verify that GET /api/portal-jobs returns only direct, deep job links
        across pages and filters.
        """
        for page in [1, 2, 3]:
            resp = client.get(f'/api/portal-jobs?page={page}&per_page=15&sort_by=score')
            assert resp.status_code == 200
            data = resp.get_json()
            assert 'jobs' in data
            assert len(data['jobs']) > 0

            for j in data['jobs']:
                url = j.get('url', '')
                assert url, f"API job {j.get('id')} has empty URL"
                assert not url.endswith(('.com', '.org', '.io', '.tech', '.co', '.in', '.jobs', '/jobs', '/careers')), (
                    f"API job {j.get('id')} has naked homepage URL: {url}"
                )
                # Verify Greenhouse jobs specifically
                if j.get('ats_type') == 'greenhouse':
                    assert 'job-boards.greenhouse.io' in url or 'boards.greenhouse.io' in url
                    assert re.search(r'/jobs/\d+', url), f"Greenhouse URL missing job ID: {url}"

    def test_company_portals_manager_loads_all_portals_without_config(self):
        """
        Verify CompanyPortalsManager automatically loads all 150 company portals
        from config.yaml even when initialized with no arguments.
        """
        mgr = CompanyPortalsManager()
        assert mgr.count() >= 150, f"Expected >= 150 portals, got {mgr.count()}"
        assert mgr.get_portal('confluent') is not None
        assert mgr.get_portal('upstart') is not None
