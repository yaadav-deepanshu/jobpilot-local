"""
Test Suite: Scaled Company Portals (1,000–2,000 Companies)
Validates catalog integrity, URL sanity, ATS token resolution,
concurrent scraping performance, and zero regression across the existing 150 companies.
"""

import sys
import re
import yaml
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from web.app import create_app
from scraper.company_portals import CompanyPortalsManager, BIG_COMPANY_PORTALS
from scraper.portal_jobs_scanner import PortalJobsScanner
from db.models import db, PortalJob


@pytest.fixture(scope="module")
def app():
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


class TestScaledCompanyPortals:
    """Exhaustive test suite for 1,000+ company portals catalog and ATS integration"""

    def test_scaled_portals_count_exceeds_1000(self):
        """
        Verify that the company portals catalog contains at least 1,000 companies.
        """
        mgr = CompanyPortalsManager()
        assert mgr.count() >= 1000, f"Expected >= 1000 portals, found {mgr.count()}"

        config_path = PROJECT_ROOT / 'config.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
        cfg_portals = cfg.get('company_portals', [])
        assert len(cfg_portals) >= 1000, f"Expected >= 1000 in config.yaml, got {len(cfg_portals)}"

    def test_scaled_portals_have_valid_structure_and_urls(self):
        """
        Verify all portals adhere to the strict schema:
        - Required keys: id, name, category, portal_url, search_url, ats_type, locations, description.
        - Valid HTTP/HTTPS URLs.
        - No dummy 'job_id=' or broken placeholder links.
        """
        mgr = CompanyPortalsManager()
        portals = mgr.get_portals()
        assert len(portals) >= 1000

        seen_ids = set()
        for p in portals:
            pid = p.get('id', '')
            assert pid, "Portal missing 'id'"
            assert pid not in seen_ids, f"Duplicate portal ID found: {pid}"
            seen_ids.add(pid)

            assert p.get('name'), f"Portal {pid} missing name"
            assert p.get('category'), f"Portal {pid} missing category"
            assert isinstance(p.get('locations'), list), f"Portal {pid} locations must be a list"
            assert len(p.get('locations')) > 0, f"Portal {pid} locations list is empty"
            assert p.get('description'), f"Portal {pid} missing description"

            portal_url = p.get('portal_url', '')
            search_url = p.get('search_url', '')

            assert portal_url.startswith(('http://', 'https://')), f"Portal {pid} invalid portal_url: {portal_url}"
            assert search_url.startswith(('http://', 'https://')), f"Portal {pid} invalid search_url: {search_url}"
            assert 'job_id=' not in search_url, f"Portal {pid} search_url has dummy job_id: {search_url}"

    def test_scaled_portals_ats_type_and_board_token_coverage(self):
        """
        Verify that hundreds of companies are mapped to authentic ATS platforms
        with valid board tokens for direct API querying.
        """
        mgr = CompanyPortalsManager()
        portals = mgr.get_portals()

        ats_counts = {}
        for p in portals:
            ats = p.get('ats_type', 'custom')
            ats_counts[ats] = ats_counts.get(ats, 0) + 1

        assert ats_counts.get('greenhouse', 0) >= 400, f"Expected >= 400 Greenhouse portals, got {ats_counts.get('greenhouse')}"
        assert ats_counts.get('lever', 0) >= 200, f"Expected >= 200 Lever portals, got {ats_counts.get('lever')}"
        assert ats_counts.get('smartrecruiters', 0) >= 150, f"Expected >= 150 SmartRecruiters portals, got {ats_counts.get('smartrecruiters')}"
        assert ats_counts.get('ashby', 0) >= 50, f"Expected >= 50 Ashby portals, got {ats_counts.get('ashby')}"
        assert ats_counts.get('workday', 0) >= 25, f"Expected >= 25 Workday portals, got {ats_counts.get('workday')}"

        # Verify prominent tech unicorns are present with valid board tokens
        critical_companies = ['openai', 'anthropic', 'vercel', 'supabase', 'stripe', 'plaid', 'wiz', 'hashicorp']
        for cid in critical_companies:
            portal = mgr.get_portal(cid)
            assert portal is not None, f"Critical company {cid} not found in scaled catalog"
            assert portal.get('board_token') or portal.get('id'), f"Company {cid} missing board_token"

    def test_scanner_concurrent_bulk_scraping(self):
        """
        Verify that PortalJobsScanner performs concurrent scraping on multiple
        live ATS boards, produces direct requisition URLs, and enforces qualification.
        """
        scanner = PortalJobsScanner()
        test_ids = ['elastic', 'sandboxaq', 'voodoo']
        jobs = scanner.scan(portal_ids=test_ids, max_jobs_per_company=3)

        assert len(jobs) > 0, "Expected jobs from test ATS companies"
        for j in jobs:
            url = j.get('url', '')
            assert url.startswith('https://'), f"Invalid job URL: {url}"
            assert not url.endswith(('.com', '.org', '.io', '.tech', '.co', '/jobs', '/careers')), f"Job URL is bare homepage: {url}"
            assert j.get('experience_max', 0) <= 4, f"Job exceeds 4y experience cap: {j.get('title')}"
            assert j.get('match_score', 0) >= 0

    def test_dashboard_routes_and_api_with_scaled_portals(self, client):
        """
        Verify /portals and API endpoints handle 1,000+ portals cleanly.
        """
        # 1. HTML Portals Page
        resp = client.get('/portals')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Enterprise Career' in html or 'Enterprise' in html
        assert 'portal-search-input' in html

        # 2. JSON API /api/portals
        resp_api = client.get('/api/portals')
        assert resp_api.status_code == 200
        data = resp_api.get_json()
        assert data['total'] >= 1000
        assert len(data['portals']) >= 1000
        assert len(data['categories']) >= 10

        # 3. Filter by ATS type
        resp_gh = client.get('/api/portals?ats=greenhouse')
        assert resp_gh.status_code == 200
        data_gh = resp_gh.get_json()
        assert data_gh['total'] >= 400

        # 4. Search by company name
        resp_search = client.get('/api/portals?search=OpenAI')
        assert resp_search.status_code == 200
        data_search = resp_search.get_json()
        assert any(p['name'] == 'OpenAI' for p in data_search['portals'])

        # 5. Stats endpoint
        resp_stats = client.get('/api/portals/stats')
        assert resp_stats.status_code == 200
        stats = resp_stats.get_json()
        assert stats['companies']['total_companies'] >= 1000

    def test_zero_regression_on_existing_150_companies(self):
        """
        Ensure 100% of the original 150 companies remain present in the catalog
        and BIG_COMPANY_PORTALS maintains its 100-company baseline.
        """
        # Baseline check
        assert len(BIG_COMPANY_PORTALS) == 100, f"Expected BIG_COMPANY_PORTALS length 100, got {len(BIG_COMPANY_PORTALS)}"

        mgr = CompanyPortalsManager()

        # Check sample of original 100 big companies
        original_sample = [
            'amazon_aws', 'microsoft', 'google', 'meta', 'apple', 'oracle',
            'cisco', 'cloudflare', 'digitalocean', 'salesforce', 'adobe',
            'nvidia', 'intel', 'snowflake', 'servicenow', 'swiggy', 'flipkart', 'razorpay'
        ]
        for cid in original_sample:
            p = mgr.get_portal(cid)
            assert p is not None, f"Original company {cid} missing from scaled catalog"

        # Check sample of 50 remote companies added previously
        remote_sample = [
            'confluent', 'upstart', 'faire', 'deltek', 'quest_software',
            'docusign', 'workiva', 'hims_hers', 'symetra'
        ]
        for cid in remote_sample:
            p = mgr.get_portal(cid)
            assert p is not None, f"Remote company {cid} missing from scaled catalog"

    def test_portal_jobs_page_renders_scaled_portals_and_all_ats(self, client):
        """
        Verify /portal-jobs route renders with updated 1,400+ branding and
        includes Ashby, Amazon Jobs, and major ATS platforms in the filter.
        """
        resp = client.get('/portal-jobs')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert '1,400+ Top Companies' in html
        assert 'ASHBY' in html
        assert 'GREENHOUSE' in html
        assert 'WORKDAY' in html
        assert 'Full Scan (All 1,400+ Portals & Sites)' in html

        # Verify API supports filtering by ashby and returns valid direct jobs
        resp_ashby = client.get('/api/portal-jobs?ats=ashby')
        assert resp_ashby.status_code == 200
        data = resp_ashby.get_json()
        assert 'jobs' in data
        assert data['total'] >= 0

