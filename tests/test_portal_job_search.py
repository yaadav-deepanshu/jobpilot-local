"""
Test suite for Job Search and Live Targeted ATS Scanning across 1,400+ Enterprise Portals.
Verifies keyword searching, multi-token skill filtering, targeted scan API triggers,
and UI quick-search pill integration.
"""

import pytest
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from web.app import create_app
from db.models import db, PortalJob
from scraper.portal_jobs_scanner import PortalJobsScanner


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


class TestPortalJobSearch:

    def test_search_portal_jobs_by_skill_and_keyword(self, client):
        """
        Verify GET /api/portal-jobs?q=<skill> accurately filters stored portal jobs
        by skill keywords (e.g. AWS, Kubernetes, Golang, Terraform).
        """
        # 1. Search for AWS
        resp_aws = client.get('/api/portal-jobs?q=aws')
        assert resp_aws.status_code == 200
        data_aws = resp_aws.get_json()
        assert data_aws['total'] > 0
        for job in data_aws['jobs']:
            combined = f"{job['title']} {job['company']} {job.get('matched_skills', [])} {job.get('description', '')}".lower()
            assert 'aws' in combined, f"Job {job['title']} missing AWS match"

        # 2. Search for Golang
        resp_go = client.get('/api/portal-jobs?q=golang')
        assert resp_go.status_code == 200
        data_go = resp_go.get_json()
        assert data_go['total'] > 0

        # 3. Multi-word search
        resp_multi = client.get('/api/portal-jobs?q=cloud+engineer')
        assert resp_multi.status_code == 200
        data_multi = resp_multi.get_json()
        assert 'jobs' in data_multi

    def test_search_portal_jobs_by_company(self, client):
        """
        Verify searching by company name filters results where company or content contains that keyword.
        """
        resp_notion = client.get('/api/portal-jobs?q=Notion')
        assert resp_notion.status_code == 200
        data_notion = resp_notion.get_json()
        assert data_notion['total'] > 0
        for j in data_notion['jobs']:
            combined = f"{j['company']} {j['title']} {j.get('description_full', j.get('description', ''))} {j.get('matched_skills', [])}".lower()
            assert 'notion' in combined

    def test_trigger_scan_with_targeted_query(self, client):
        """
        Verify POST /api/scan-portal-jobs accepts a custom search query
        and returns status started with query included in response.
        """
        payload = {
            'mode': 'quick',
            'query': 'Kubernetes'
        }
        resp = client.post('/api/scan-portal-jobs', json=payload)
        # 200 (started) or 409 (if previous scan still finishing)
        assert resp.status_code in [200, 409]
        data = resp.get_json()
        if resp.status_code == 200:
            assert data['status'] == 'started'
            assert data.get('query') == 'Kubernetes'
            assert 'Kubernetes' in data['message']

    def test_scanner_targeted_query_propagation(self):
        """
        Verify PortalJobsScanner accepts query and propagates it to ATS scraping methods.
        """
        scanner = PortalJobsScanner()
        # Verify scanner._discover_portal_jobs accepts query argument
        portal = {
            'id': 'notion',
            'name': 'Notion',
            'category': 'Enterprise SaaS & Productivity',
            'ats_type': 'ashby',
            'board_token': 'notion'
        }
        jobs = scanner._discover_portal_jobs(portal, max_jobs=3, query='Engineer')
        assert isinstance(jobs, list)
        for j in jobs:
            assert 'engineer' in j['title'].lower() or 'engineer' in j.get('description', '').lower()

    def test_portal_jobs_ui_renders_search_pills_and_query_banner(self, client):
        """
        Verify GET /portal-jobs renders quick search pills, active query banner,
        and targeted scan button.
        """
        resp = client.get('/portal-jobs')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'quick-search-pill' in html
        assert 'setQuickSearch(' in html
        assert 'search-active-banner' in html
        assert 'btn-scan-current-query' in html
        assert 'Scan 1,400 Portals for this Query' in html
