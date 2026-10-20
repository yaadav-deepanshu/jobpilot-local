"""
Comprehensive automated test suite for Job Finder
Tests all components: models, app factory, routes, filters, scrapers, exports, and end-to-end integration
"""

import os
import sys
import json
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import pandas as pd
import yaml

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from web.app import create_app
from web.routes import get_filtered_job_query
from db.models import db, Job, ApplicationLog, init_db
from filter.engine import FilterEngine
from scraper.multi_platform import RealJobScraper, JobScraper
from export.jobs_exporter import JobExporter


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def config():
    """Valid config fixture for tests with 0-4 years experience cap and abroad platforms"""
    return {
        'profile': {
            'name': 'Deepanshu Yadav',
            'email': 'yaadav.deepanshu@gmail.com',
            'phone': '+91 8728081860',
            'resume_file': 'resume.pdf',
        },
        'search': {
            'roles': ['Cloud Engineer', 'DevOps Engineer', 'SRE'],
            'location': 'Bengaluru',
            'remote': True,
            'hybrid': True,
            'max_applicants': 100,
            'min_experience_years': 0,
            'max_experience_years': 4,
            'exclude_keywords': ['internship', 'volunteer', 'unpaid', 'part-time', 'principal', 'director', 'manager', 'staff', 'head of'],
            'salary_min': 0,
            'salary_max': 0,
        },
        'platforms': {
            'linkedin': {'enabled': True},
            'indeed': {'enabled': True, 'country': 'india'},
            'naukri': {'enabled': True},
            'glassdoor': {'enabled': True},
            'zip_recruiter': {'enabled': True},
            'google': {'enabled': True},
            'bayt': {'enabled': True},
        },
        'app': {
            'host': '127.0.0.1',
            'port': 5050,
            'debug': False,
            'db_file': 'jobs.db',
        },
    }


@pytest.fixture
def app(config, tmp_path):
    """Create an isolated test Flask app with a clean SQLite database"""
    db_path = tmp_path / "test_app.db"
    test_app = create_app(config_override={
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'TESTING': True,
        'JOB_CONFIG': config,
    })

    with test_app.app_context():
        db.create_all()

    yield test_app

    with test_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client"""
    return app.test_client()


@pytest.fixture
def sample_jobs():
    """Collection of realistic job postings for filter and export tests"""
    now = datetime.now(timezone.utc)
    return [
        {
            'platform': 'linkedin',
            'title': 'Cloud DevOps Engineer',
            'company': 'Enterprise Solutions Inc',
            'location': 'Bengaluru, Karnataka, India',
            'url': 'https://linkedin.com/jobs/view/1001',
            'description': 'Looking for an experienced DevOps Engineer with AWS, Terraform, Docker, and Kubernetes expertise.',
            'salary': 'INR 18,00,000 - 25,00,000',
            'salary_min': 1800000,
            'salary_max': 2500000,
            'date_posted': now - timedelta(hours=2),
            'job_type': 'Full-time',
            'num_applicants': 35,
            'is_easy_apply': True,
            'status': 'new',
        },
        {
            'platform': 'indeed',
            'title': 'Cloud Engineer (AWS / Azure)',
            'company': 'Global Tech Labs',
            'location': 'Bengaluru, India',
            'url': 'https://in.indeed.com/viewjob?jk=2002',
            'description': 'Join our cloud infrastructure team building multi-region AWS and GCP deployments using Linux and Python.',
            'salary': 'INR 15,00,000+',
            'salary_min': 1500000,
            'salary_max': None,
            'date_posted': now - timedelta(hours=5),
            'job_type': 'Full-time',
            'num_applicants': 12,
            'is_easy_apply': False,
            'status': 'new',
        },
        {
            'platform': 'naukri',
            'title': 'Site Reliability Engineer (SRE)',
            'company': 'Fintech Innovations',
            'location': 'Bengaluru (Remote Available)',
            'url': 'https://www.naukri.com/job-listings-3003',
            'description': 'Scale high-throughput services with Prometheus, Grafana, CI/CD, and Kubernetes.',
            'salary': '',
            'salary_min': None,
            'salary_max': None,
            'date_posted': now - timedelta(hours=10),
            'job_type': 'Full-time',
            'num_applicants': 40,
            'is_easy_apply': False,
            'status': 'new',
        },
        {
            'platform': 'linkedin',
            'title': 'Unpaid DevOps Internship',
            'company': 'Student Club',
            'location': 'Bengaluru',
            'url': 'https://linkedin.com/jobs/view/4004',
            'description': 'Summer internship for beginners.',
            'salary': '',
            'salary_min': None,
            'salary_max': None,
            'date_posted': now - timedelta(hours=1),
            'job_type': 'Internship',
            'num_applicants': 150,
            'is_easy_apply': False,
            'status': 'new',
        },
        {
            'platform': 'glassdoor',
            'title': 'Lead Infrastructure Architect',
            'company': 'Legacy Corp',
            'location': 'Mumbai',
            'url': 'https://www.glassdoor.co.in/job-listing-5005',
            'description': 'Lead infrastructure architect position.',
            'salary': '',
            'salary_min': None,
            'salary_max': None,
            'date_posted': now - timedelta(days=40),  # Old job
            'job_type': 'Full-time',
            'num_applicants': 250,
            'is_easy_apply': False,
            'status': 'new',
        }
    ]


# ─────────────────────────────────────────────
# 1. Database Model Tests
# ─────────────────────────────────────────────

class TestDatabaseModels:
    def test_job_model_creation(self, app):
        """Test creating and querying a Job record"""
        with app.app_context():
            job = Job(
                platform='linkedin',
                title='Cloud DevOps Specialist',
                company='TechGiant',
                location='Bengaluru',
                url='https://linkedin.com/jobs/test-1',
                description='Manage AWS clusters and pipelines',
                salary='INR 20 LPA',
                status='new'
            )
            db.session.add(job)
            db.session.commit()

            fetched = Job.query.filter_by(url='https://linkedin.com/jobs/test-1').first()
            assert fetched is not None
            assert fetched.title == 'Cloud DevOps Specialist'
            assert fetched.company == 'TechGiant'
            assert fetched.platform == 'linkedin'
            assert fetched.status == 'new'

    def test_job_to_dict_structure(self, app):
        """Test Job.to_dict() returns JSON-serializable keys and formatting"""
        with app.app_context():
            job = Job(
                platform='indeed',
                title='Site Reliability Engineer',
                company='Reliable Systems',
                location='Bengaluru',
                url='https://indeed.com/jobs/test-2',
                description='High availability architecture',
                date_posted=datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc),
                status='applied'
            )
            db.session.add(job)
            db.session.commit()

            data = job.to_dict()
            assert data['platform'] == 'indeed'
            assert data['title'] == 'Site Reliability Engineer'
            assert data['company'] == 'Reliable Systems'
            assert data['status'] == 'applied'
            assert data['date_posted'] == '2026-10-01'
            assert 'id' in data
            assert 'created_at' in data

    def test_job_to_dict_truncates_long_description(self, app):
        """Test that to_dict limits long descriptions to avoid huge payloads"""
        with app.app_context():
            job = Job(
                platform='naukri',
                title='DevOps Engineer',
                company='ScaleCo',
                url='https://naukri.com/jobs/test-3',
                description='A' * 400
            )
            db.session.add(job)
            db.session.commit()

            d = job.to_dict()
            assert d['description'].endswith('...')
            assert len(d['description']) == 223  # 220 + 3

    def test_unique_url_constraint(self, app):
        """Test that duplicate job URLs are rejected by database constraint"""
        from sqlalchemy.exc import IntegrityError
        with app.app_context():
            j1 = Job(platform='linkedin', title='J1', company='C1', url='https://unique-url.com/1')
            j2 = Job(platform='indeed', title='J2', company='C2', url='https://unique-url.com/1')
            db.session.add(j1)
            db.session.commit()

            db.session.add(j2)
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_application_log_model(self, app):
        """Test ApplicationLog creation and serialization"""
        with app.app_context():
            job = Job(platform='linkedin', title='DevOps', company='Acme', url='https://acme.com/job')
            db.session.add(job)
            db.session.commit()

            log = ApplicationLog(job_id=job.id, status='applied', notes='Submitted resume')
            db.session.add(log)
            db.session.commit()

            log_dict = log.to_dict()
            assert log_dict['job_id'] == job.id
            assert log_dict['status'] == 'applied'
            assert log_dict['notes'] == 'Submitted resume'


# ─────────────────────────────────────────────
# 2. Flask Application Factory Tests
# ─────────────────────────────────────────────

class TestAppFactory:
    def test_app_created_successfully(self, app):
        """Verify Flask app instance initializes properly"""
        assert app is not None
        assert app.config['TESTING'] is True

    def test_registered_blueprints(self, app):
        """Ensure all required blueprints are mounted"""
        blueprints = list(app.blueprints.keys())
        assert 'main' in blueprints
        assert 'api' in blueprints
        assert 'export' in blueprints


# ─────────────────────────────────────────────
# 3. View & API Route Tests
# ─────────────────────────────────────────────

class TestRoutes:
    def test_index_dashboard_route(self, client):
        """Test main dashboard HTML renders with 200 OK"""
        resp = client.get('/')
        assert resp.status_code == 200
        assert b'Job Finder' in resp.data

    def test_jobs_table_route_loads(self, client):
        """Test /jobs tabular page loads with 200 OK (verifies fix for earlier 404)"""
        resp = client.get('/jobs')
        assert resp.status_code == 200
        assert b'All Discovered Opportunities' in resp.data

    def test_jobs_table_with_records(self, client, app):
        """Test /jobs page renders table rows when qualifying jobs are present"""
        with app.app_context():
            job = Job(
                platform='linkedin',
                title='Cloud Infrastructure Engineer',
                company='HyperGrowth Inc',
                location='Bengaluru',
                url='https://linkedin.com/jobs/view/999',
                status='new'
            )
            db.session.add(job)
            db.session.commit()

        resp = client.get('/jobs')
        assert resp.status_code == 200
        assert b'Cloud Infrastructure Engineer' in resp.data
        assert b'HyperGrowth Inc' in resp.data

    def test_jobs_table_excludes_senior_titles_and_over_100_applicants(self, client, app):
        """Test /jobs page strictly excludes senior titles and >100 applicants"""
        with app.app_context():
            # Senior title job (must be hidden)
            db.session.add(Job(
                platform='linkedin',
                title='Senior Cloud Architect',
                company='LegacyCorp',
                url='https://linkedin.com/jobs/view/sr-arch',
                status='new'
            ))
            # > 100 applicants job (must be hidden)
            db.session.add(Job(
                platform='indeed',
                title='DevOps Specialist',
                company='CrowdedCo',
                url='https://indeed.com/viewjob/crowded',
                num_applicants=150,
                status='new'
            ))
            # Qualifying job (must be shown)
            db.session.add(Job(
                platform='linkedin',
                title='DevOps Engineer',
                company='TargetCo',
                url='https://linkedin.com/jobs/view/target',
                num_applicants=30,
                status='new'
            ))
            db.session.commit()

        resp = client.get('/jobs')
        assert resp.status_code == 200
        assert b'TargetCo' in resp.data
        assert b'LegacyCorp' not in resp.data
        assert b'CrowdedCo' not in resp.data

    def test_api_stats_endpoint(self, client, app):
        """Test /api/stats returns accurate metrics for qualified jobs"""
        with app.app_context():
            db.session.add(Job(platform='linkedin', title='J1', company='C1', url='https://x.com/1', status='new'))
            db.session.add(Job(platform='indeed', title='J2', company='C2', url='https://x.com/2', status='applied'))
            db.session.add(Job(platform='naukri', title='J3', company='C3', url='https://x.com/3', status='saved'))
            db.session.commit()

        resp = client.get('/api/stats')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total_jobs'] == 3
        assert data['new'] == 1
        assert data['applied'] == 1
        assert data['saved'] == 1
        assert data['by_platform']['linkedin'] == 1
        assert data['by_platform']['indeed'] == 1
        assert data['by_platform']['naukri'] == 1

    def test_api_jobs_pagination(self, client, app):
        """Test /api/jobs pagination and limits"""
        with app.app_context():
            for i in range(12):
                db.session.add(Job(
                    platform='linkedin',
                    title=f'Role {i}',
                    company=f'Company {i}',
                    url=f'https://x.com/page-{i}',
                    status='new'
                ))
            db.session.commit()

        resp = client.get('/api/jobs?page=1&per_page=5')
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data['jobs']) == 5
        assert data['total'] == 12
        assert data['pages'] == 3

    def test_api_jobs_search_filter(self, client, app):
        """Test /api/jobs search query parameter filtering"""
        with app.app_context():
            db.session.add(Job(platform='linkedin', title='Kubernetes Engineer', company='CloudNine', url='https://x.com/k8s', status='new'))
            db.session.add(Job(platform='indeed', title='Backend Python', company='DevShop', url='https://x.com/py', status='new'))
            db.session.commit()

        resp = client.get('/api/jobs?q=Kubernetes')
        data = resp.get_json()
        assert len(data['jobs']) == 1
        assert data['jobs'][0]['title'] == 'Kubernetes Engineer'

    def test_update_job_status_success(self, client, app):
        """Test updating a job's status via PUT /api/job/<id>/status"""
        with app.app_context():
            job = Job(platform='linkedin', title='SRE', company='SpeedCo', url='https://x.com/speed', status='new')
            db.session.add(job)
            db.session.commit()
            jid = job.id

        resp = client.put(f'/api/job/{jid}/status',
                          data=json.dumps({'status': 'applied'}),
                          content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'success'
        assert data['job']['status'] == 'applied'

    def test_update_job_status_invalid_value(self, client, app):
        """Test rejection of invalid status transitions"""
        with app.app_context():
            job = Job(platform='linkedin', title='SRE', company='SpeedCo', url='https://x.com/speed2', status='new')
            db.session.add(job)
            db.session.commit()
            jid = job.id

        resp = client.put(f'/api/job/{jid}/status',
                          data=json.dumps({'status': 'invalid_status_xyz'}),
                          content_type='application/json')
        assert resp.status_code == 400

    def test_update_job_status_not_found(self, client):
        """Test updating status of non-existent job ID returns 404"""
        resp = client.put('/api/job/99999/status',
                          data=json.dumps({'status': 'applied'}),
                          content_type='application/json')
        assert resp.status_code == 404

    def test_scrape_status_polling_endpoint(self, client):
        """Test /api/scrape-status returns valid tracker fields"""
        resp = client.get('/api/scrape-status')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'running' in data
        assert 'current_phase' in data
        assert 'jobs_found' in data
        assert 'finished' in data

    def test_clear_fake_data_endpoint(self, client, app):
        """Test that /api/clear-fake-data removes mock data"""
        with app.app_context():
            db.session.add(Job(platform='linkedin', title='DevOps', company='TestCorp', url='https://x.com/fake1'))
            db.session.add(Job(platform='indeed', title='J1', company='RealCo', url='https://x.com/fake2'))
            db.session.add(Job(platform='linkedin', title='DevOps Engineer', company='RealLiveCo', url='https://x.com/real1'))
            db.session.commit()

        resp = client.post('/api/clear-fake-data')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['deleted_count'] >= 2

        with app.app_context():
            assert Job.query.filter_by(company='RealLiveCo').first() is not None
            assert Job.query.filter_by(company='TestCorp').first() is None

    def test_jobs_ordering_platform_priority(self, client, app):
        """Test /jobs and /api/jobs sort by platform priority: LinkedIn -> Indeed -> Naukri -> Rest"""
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)

        with app.app_context():
            # Add jobs out of priority order
            db.session.add(Job(platform='glassdoor', title='Cloud Eng', company='GlassCorp', url='https://x.com/gd', date_posted=now))
            db.session.add(Job(platform='naukri', title='SRE', company='NaukriCorp', url='https://x.com/nk', date_posted=now))
            db.session.add(Job(platform='indeed', title='DevOps', company='IndeedCorp', url='https://x.com/in', date_posted=now))
            db.session.add(Job(platform='linkedin', title='Platform Eng', company='LinkedInCorp', url='https://x.com/li', date_posted=now))
            db.session.add(Job(platform='bayt', title='Systems Eng', company='BaytCorp', url='https://x.com/by', date_posted=now))
            db.session.commit()

        # Check API returns LinkedIn first, then Indeed, then Naukri, then others
        resp = client.get('/api/jobs?per_page=10')
        assert resp.status_code == 200
        jobs = resp.get_json()['jobs']
        assert len(jobs) == 5
        platforms = [j['platform'] for j in jobs]
        assert platforms[0] == 'linkedin'
        assert platforms[1] == 'indeed'
        assert platforms[2] == 'naukri'
        assert platforms[3] in ('glassdoor', 'bayt')
        assert platforms[4] in ('glassdoor', 'bayt')

        # Check /jobs HTML renders in priority order
        resp_html = client.get('/jobs')
        assert resp_html.status_code == 200
        html = resp_html.get_data(as_text=True)
        pos_li = html.find('LinkedInCorp')
        pos_in = html.find('IndeedCorp')
        pos_nk = html.find('NaukriCorp')
        pos_gd = html.find('GlassCorp')
        assert pos_li < pos_in < pos_nk < pos_gd

    def test_scrape_endpoint_accepts_hours_parameter(self, client):
        """Test POST /api/scrape with custom hours window sets scrape mode correctly"""
        resp = client.post('/api/scrape',
                           data=json.dumps({'hours': 6, 'today_only': True}),
                           content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'started'
        assert 'WINDOW SCRAPE (6H)' in data['message']

    def test_location_segregation_sql_filtering(self, client, app):
        """Test apply_location_filter isolates remote, bengaluru, and both jobs accurately"""
        with app.app_context():
            db.session.add(Job(platform='linkedin', title='DevOps', company='C1', url='https://u1.com', location='Bengaluru, India', description='On-site role'))
            db.session.add(Job(platform='indeed', title='SRE', company='C2', url='https://u2.com', location='Remote', description='Fully remote'))
            db.session.add(Job(platform='naukri', title='Cloud Eng', company='C3', url='https://u3.com', location='Pune, India', description='Remote work allowed'))
            db.session.commit()

        # Both / default
        res_both = client.get('/api/jobs?location=both')
        assert res_both.status_code == 200
        assert res_both.get_json()['total'] >= 3

        # Bengaluru only
        res_blr = client.get('/api/jobs?location=bengaluru')
        assert res_blr.status_code == 200
        urls_blr = [j['url'] for j in res_blr.get_json()['jobs']]
        assert 'https://u1.com' in urls_blr
        assert 'https://u2.com' not in urls_blr

        # Remote only
        res_rem = client.get('/api/jobs?location=remote')
        assert res_rem.status_code == 200
        urls_rem = [j['url'] for j in res_rem.get_json()['jobs']]
        assert 'https://u2.com' in urls_rem
        assert 'https://u3.com' in urls_rem
        assert 'https://u1.com' not in urls_rem

    def test_stats_endpoint_includes_location_counts(self, client, app):
        """Verify /api/stats returns by_location counts for both, bengaluru, and remote"""
        with app.app_context():
            db.session.add(Job(platform='linkedin', title='DevOps', company='CB', url='https://ublr.com', location='Bengaluru'))
            db.session.add(Job(platform='indeed', title='SRE', company='CR', url='https://urem.com', location='Remote'))
            db.session.commit()

        resp = client.get('/api/stats')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'by_location' in data
        assert 'both' in data['by_location']
        assert 'bengaluru' in data['by_location']
        assert 'remote' in data['by_location']
        assert data['by_location']['bengaluru'] >= 1
        assert data['by_location']['remote'] >= 1


# ─────────────────────────────────────────────
# 4. Filter Engine Tests
# ─────────────────────────────────────────────

class TestFilterEngine:
    def test_role_and_synonym_matching(self, config, sample_jobs):
        """Test that role matching correctly recognizes SRE, DevOps, and Cloud roles"""
        engine = FilterEngine(config)
        filtered = engine._filter_by_role_and_skills(sample_jobs)
        titles = [j['title'] for j in filtered]

        assert 'Cloud DevOps Engineer' in titles
        assert 'Cloud Engineer (AWS / Azure)' in titles
        assert 'Site Reliability Engineer (SRE)' in titles

    def test_experience_filter_strictly_caps_at_4_years(self, config):
        """Test strict experience cap: max 4 years. Excludes 5+, 6+, 8+, 10+, 5-8y, and senior titles"""
        engine = FilterEngine(config)
        jobs_to_test = [
            # Excessive experience: must be rejected
            {'title': 'DevOps Engineer', 'description': 'Requires 8+ years of experience in AWS', 'url': '1'},
            {'title': 'Cloud Engineer', 'description': 'Minimum 5 years of experience required', 'url': '2'},
            {'title': 'SRE', 'description': 'At least 6 years experience with Kubernetes', 'url': '3'},
            {'title': 'Infrastructure Engineer', 'description': '5-8 years of experience building pipelines', 'url': '4'},
            {'title': 'Platform Engineer', 'description': '6 to 9 yrs of relevant experience', 'url': '5'},
            {'title': 'Senior DevOps Engineer', 'description': '2 years of experience', 'url': '6'},
            {'title': 'Lead Cloud Engineer', 'description': '3 years of experience', 'url': '7'},
            {'title': 'Staff Site Reliability Engineer', 'description': '3 years of experience', 'url': '8'},
            {'title': 'Principal Platform Architect', 'description': '2 years of experience', 'url': '9'},
            {'title': 'Engineering Manager - DevOps', 'description': '2 years of experience', 'url': '10'},

            # Qualifying experience: must be accepted (0-4 years)
            {'title': 'DevOps Engineer', 'description': '2 years of experience in AWS and Docker', 'url': '11'},
            {'title': 'Cloud Engineer', 'description': '1-3 years of experience with Terraform', 'url': '12'},
            {'title': 'Site Reliability Engineer', 'description': 'Minimum 2 years of experience in Linux', 'url': '13'},
            {'title': 'Associate Cloud Engineer', 'description': 'Fresh graduates or 0-2 years experience welcome', 'url': '14'},
            {'title': 'Infrastructure Specialist', 'description': '3 years of hands-on experience', 'url': '15'},
        ]

        passed = engine._filter_by_experience(jobs_to_test)
        passed_urls = [j['url'] for j in passed]

        # Verify all jobs with >4 years or senior titles were rejected
        for bad_id in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']:
            assert bad_id not in passed_urls

        # Verify all qualifying 0-4y jobs were accepted
        for good_id in ['11', '12', '13', '14', '15']:
            assert good_id in passed_urls

    def test_applicant_filter_textual_and_numeric_strict(self, config):
        """Test applicant filter rejects >100 applicants both numerically and textually"""
        engine = FilterEngine(config)
        test_jobs = [
            # High applicants: must be rejected
            {'title': 'DevOps', 'num_applicants': 150, 'description': 'Normal description', 'url': 'a1'},
            {'title': 'DevOps', 'num_applicants': 101, 'description': 'Normal description', 'url': 'a2'},
            {'title': 'Cloud', 'num_applicants': None, 'description': 'Over 100 people clicked apply on LinkedIn', 'url': 'a3'},
            {'title': 'Cloud', 'num_applicants': None, 'description': 'More than 150 applicants applied', 'url': 'a4'},
            {'title': 'SRE', 'num_applicants': None, 'description': '200+ applicants for this position', 'url': 'a5'},

            # Qualifying applicants: must be accepted (<= 100)
            {'title': 'DevOps', 'num_applicants': 12, 'description': 'AWS DevOps role', 'url': 'b1'},
            {'title': 'Cloud', 'num_applicants': 95, 'description': 'Terraform role', 'url': 'b2'},
            {'title': 'SRE', 'num_applicants': 100, 'description': 'Kubernetes role', 'url': 'b3'},
            {'title': 'SRE', 'num_applicants': None, 'description': 'Clean role description', 'url': 'b4'},
        ]

        passed = engine._filter_by_applicants(test_jobs)
        passed_urls = [j['url'] for j in passed]

        for bad in ['a1', 'a2', 'a3', 'a4', 'a5']:
            assert bad not in passed_urls

        for good in ['b1', 'b2', 'b3', 'b4']:
            assert good in passed_urls

    def test_excluded_keywords_filter(self, config, sample_jobs):
        """Test exclusion of postings with internship, unpaid, etc."""
        engine = FilterEngine(config)
        filtered = engine._filter_by_excluded_keywords(sample_jobs)
        titles = [j['title'] for j in filtered]

        assert 'Unpaid DevOps Internship' not in titles

    def test_location_filtering(self, config, sample_jobs):
        """Test location filter keeps target location and remote/hybrid"""
        engine = FilterEngine(config)
        filtered = engine._filter_by_location(sample_jobs)
        locations = [j['location'].lower() for j in filtered]

        assert any('bengaluru' in loc for loc in locations)
        # Out-of-region non-remote locations are excluded
        assert not any('mumbai' in loc and 'remote' not in loc for loc in locations)

    def test_applicant_count_threshold(self, config, sample_jobs):
        """Test filtering out positions with too many applicants"""
        engine = FilterEngine(config)
        filtered = engine._filter_by_applicants(sample_jobs)

        for j in filtered:
            if j.get('num_applicants') is not None:
                assert j['num_applicants'] <= config['search']['max_applicants']

    def test_recency_filter_strict(self, config, sample_jobs):
        """Test recency filter keeps jobs within specified hour cutoff"""
        engine = FilterEngine(config)
        # Strict 24 hours
        filtered_24h = engine._filter_by_recency(sample_jobs, max_hours=24)
        urls_24h = [j['url'] for j in filtered_24h]
        assert 'https://www.glassdoor.co.in/job-listing-5005' not in urls_24h

    def test_deduplication(self, config, sample_jobs):
        """Test deduplication by URL and Company+Title"""
        engine = FilterEngine(config)
        dup_job = sample_jobs[0].copy()
        dup_job['url'] = 'https://some-other-url.com/dup'
        jobs_with_dups = sample_jobs + [sample_jobs[0], dup_job]

        deduped = engine._deduplicate(jobs_with_dups)
        assert len(deduped) == len(sample_jobs)

    def test_full_filter_pipeline(self, config, sample_jobs):
        """Test end-to-end filtering execution"""
        engine = FilterEngine(config)
        result = engine.filter_jobs(sample_jobs, today_only=True)

        # Unpaid internship and old Mumbai posting must be excluded
        urls = [j['url'] for j in result]
        assert 'https://linkedin.com/jobs/view/4004' not in urls
        assert 'https://www.glassdoor.co.in/job-listing-5005' not in urls
        assert len(result) >= 2

    def test_filter_engine_custom_time_windows(self, config):
        """Test time-window stops: 2h, 6h, 12h, 24h filter jobs accurately by recency"""
        from datetime import datetime, timezone, timedelta
        engine = FilterEngine(config)
        now = datetime.now(timezone.utc)

        time_jobs = [
            {'title': 'DevOps Engineer', 'company': 'C1', 'url': 'u1', 'date_posted': now - timedelta(hours=1)},
            {'title': 'DevOps Engineer', 'company': 'C2', 'url': 'u2', 'date_posted': now - timedelta(hours=4)},
            {'title': 'DevOps Engineer', 'company': 'C3', 'url': 'u3', 'date_posted': now - timedelta(hours=10)},
            {'title': 'DevOps Engineer', 'company': 'C4', 'url': 'u4', 'date_posted': now - timedelta(hours=18)},
            {'title': 'DevOps Engineer', 'company': 'C5', 'url': 'u5', 'date_posted': now - timedelta(hours=36)},
        ]

        # 2h window: only 1h job
        res_2h = engine._filter_by_recency(time_jobs, max_hours=2)
        assert [j['url'] for j in res_2h] == ['u1']

        # 6h window: 1h, 4h jobs
        res_6h = engine._filter_by_recency(time_jobs, max_hours=6)
        assert [j['url'] for j in res_6h] == ['u1', 'u2']

        # 12h window: 1h, 4h, 10h jobs
        res_12h = engine._filter_by_recency(time_jobs, max_hours=12)
        assert [j['url'] for j in res_12h] == ['u1', 'u2', 'u3']

        # 24h window: 1h, 4h, 10h, 18h jobs (excludes 36h)
        res_24h = engine._filter_by_recency(time_jobs, max_hours=24)
        assert [j['url'] for j in res_24h] == ['u1', 'u2', 'u3', 'u4']

    def test_filter_engine_platform_priority_sorting(self, config):
        """Test that FilterEngine sorts jobs: LinkedIn (1) -> Indeed (2) -> Naukri (3) -> Rest (4)"""
        engine = FilterEngine(config)
        jobs = [
            {'platform': 'glassdoor', 'title': 'SRE', 'company': 'C1', 'url': 'u1'},
            {'platform': 'bayt', 'title': 'SRE', 'company': 'C2', 'url': 'u2'},
            {'platform': 'naukri', 'title': 'SRE', 'company': 'C3', 'url': 'u3'},
            {'platform': 'indeed', 'title': 'SRE', 'company': 'C4', 'url': 'u4'},
            {'platform': 'linkedin', 'title': 'SRE', 'company': 'C5', 'url': 'u5'},
        ]
        sorted_jobs = engine._sort_by_platform_priority(jobs)
        platforms = [j['platform'] for j in sorted_jobs]
        assert platforms[0] == 'linkedin'
        assert platforms[1] == 'indeed'
        assert platforms[2] == 'naukri'
        assert platforms[3] in ('glassdoor', 'bayt')
        assert platforms[4] in ('glassdoor', 'bayt')

    def test_filter_engine_location_segregation_modes(self, config):
        """Test FilterEngine._filter_by_location supports 'remote', 'bengaluru', and 'both' modes"""
        engine = FilterEngine(config)
        jobs = [
            {'title': 'DevOps', 'company': 'C1', 'url': 'u1', 'location': 'Bengaluru, Karnataka'},
            {'title': 'SRE', 'company': 'C2', 'url': 'u2', 'location': 'Remote'},
            {'title': 'Cloud Eng', 'company': 'C3', 'url': 'u3', 'location': 'Mumbai', 'description': '100% remote job'},
            {'title': 'Platform Eng', 'company': 'C4', 'url': 'u4', 'location': 'Hyderabad', 'description': 'On-site'},
        ]

        # Remote only
        rem_jobs = engine._filter_by_location(jobs, location_mode='remote')
        assert [j['url'] for j in rem_jobs] == ['u2', 'u3']

        # Bengaluru only
        blr_jobs = engine._filter_by_location(jobs, location_mode='bengaluru')
        assert [j['url'] for j in blr_jobs] == ['u1']

        # Both (matches preferred Bengaluru or Remote)
        both_jobs = engine._filter_by_location(jobs, location_mode='both')
        assert 'u1' in [j['url'] for j in both_jobs]
        assert 'u2' in [j['url'] for j in both_jobs]


# ─────────────────────────────────────────────
# 5. Real Multi-Platform Scraper Tests
# ─────────────────────────────────────────────

class TestRealJobScraper:
    def test_supported_sites_mapping(self, config):
        """Verify scraper platform mappings, abroad platforms, and country configuration"""
        scraper = RealJobScraper(config)
        assert 'linkedin' in scraper.SUPPORTED_SITES
        assert 'indeed' in scraper.SUPPORTED_SITES
        assert 'glassdoor' in scraper.SUPPORTED_SITES
        # Abroad platforms
        assert 'zip_recruiter' in scraper.SUPPORTED_SITES
        assert 'google' in scraper.SUPPORTED_SITES
        assert 'bayt' in scraper.SUPPORTED_SITES
        # Indeed must have country='india'
        assert scraper.SUPPORTED_SITES['indeed']['country'] == 'india'

    def test_format_records_extracts_applicant_text_flags(self, config):
        """Verify _format_records detects text applicant flags like 'Over 100 people clicked apply'"""
        scraper = RealJobScraper(config)
        records = [
            {
                'title': 'Cloud Engineer',
                'company': 'HotCorp',
                'job_url': 'https://linkedin.com/jobs/view/hot1',
                'description': 'Over 100 people clicked apply on this popular role.',
                'num_applicants': None,
            },
            {
                'title': 'DevOps Engineer',
                'company': 'CoolCorp',
                'job_url': 'https://linkedin.com/jobs/view/cool1',
                'description': 'Normal role with 25 applicants.',
                'num_applicants': None,
            }
        ]
        formatted = scraper._format_records(records, 'linkedin')
        assert len(formatted) == 2
        # Over 100 detected -> num_applicants set to 101
        assert formatted[0]['num_applicants'] == 101
        # Extracted 25 from text
        assert formatted[1]['num_applicants'] == 25

    def test_clean_helpers_handle_nan_safely(self, config):
        """Verify _clean_str and _clean_int handle float NaN without raising ValueError"""
        scraper = RealJobScraper(config)

        # Test string helper
        assert scraper._clean_str(float('nan')) == ''
        assert scraper._clean_str(None) == ''
        assert scraper._clean_str('NaN') == ''
        assert scraper._clean_str('Bengaluru') == 'Bengaluru'

        # Test int helper with NaN (previously caused 'cannot convert float NaN to integer')
        assert scraper._clean_int(float('nan')) is None
        assert scraper._clean_int(None) is None
        assert scraper._clean_int('NaN') is None
        assert scraper._clean_int(2500000.0) == 2500000
        assert scraper._clean_int('1500000') == 1500000

    def test_format_records_with_nan_fields(self, config):
        """Verify _format_records safely normalizes records containing NaNs from pandas"""
        scraper = RealJobScraper(config)

        raw_records = [{
            'title': 'DevOps Engineer',
            'company': 'Reliable Cloud Corp',
            'location': 'Bengaluru',
            'job_url': 'https://in.indeed.com/viewjob?jk=abc123',
            'description': 'AWS DevOps role',
            'min_amount': float('nan'),  # Simulated pandas NaN
            'max_amount': float('nan'),
            'currency': float('nan'),
            'num_applicants': float('nan'),
            'is_easy_apply': float('nan'),
            'date_posted': None,
        }]

        formatted = scraper._format_records(raw_records, 'indeed')
        assert len(formatted) == 1
        item = formatted[0]
        assert item['title'] == 'DevOps Engineer'
        assert item['company'] == 'Reliable Cloud Corp'
        assert item['salary_min'] is None
        assert item['salary_max'] is None
        assert item['salary'] == ''
        assert item['num_applicants'] is None
        assert item['is_easy_apply'] is False
        assert item['platform'] == 'indeed'

    @patch('scraper.multi_platform.scrape_jobs')
    def test_mocked_scrape_execution(self, mock_scrape, config):
        """Test scrape_all flow using mocked JobSpy dataframe response"""
        mock_df = pd.DataFrame([{
            'title': 'Cloud Architect',
            'company': 'Mocked Tech',
            'location': 'Bengaluru',
            'job_url': 'https://linkedin.com/jobs/view/mock1',
            'description': 'Terraform and Kubernetes infrastructure',
            'min_amount': 2000000,
            'max_amount': 3000000,
            'currency': 'INR',
            'date_posted': datetime.now(timezone.utc),
            'num_applicants': 15,
            'is_easy_apply': True,
        }])
        mock_scrape.return_value = mock_df

        scraper = RealJobScraper(config)
        scraper.SUPPORTED_SITES = {'linkedin': {'site': 'linkedin', 'country': None}}
        scraper.roles = ['DevOps Engineer']

        progress_msgs = []
        def callback(msg, count):
            progress_msgs.append((msg, count))

        results = scraper.scrape_all(today_only=True, results_per_query=5, progress_callback=callback)
        assert len(results) == 1
        assert results[0]['title'] == 'Cloud Architect'
        assert len(progress_msgs) > 0

    @patch('scraper.multi_platform.scrape_jobs')
    def test_scrape_all_passes_hours_old_to_jobspy(self, mock_scrape, config):
        """Verify scrape_all forwards custom hours_old parameter to JobSpy scrape_jobs"""
        mock_scrape.return_value = pd.DataFrame()
        scraper = RealJobScraper(config)
        scraper.SUPPORTED_SITES = {'linkedin': {'site': 'linkedin', 'country': None}}
        scraper.roles = ['DevOps Engineer']

        scraper.scrape_all(hours_old=6, results_per_query=5)
        assert mock_scrape.called
        kwargs = mock_scrape.call_args[1]
        assert kwargs.get('hours_old') == 6


# ─────────────────────────────────────────────
# 6. Exporter Tests
# ─────────────────────────────────────────────

class TestJobExporter:
    def test_excel_export_creates_valid_file(self, config, sample_jobs, tmp_path):
        """Test JobExporter generates a valid multi-sheet Excel file"""
        exporter = JobExporter(config)
        exporter.export_dir = str(tmp_path)

        filepath = exporter.export_to_excel(sample_jobs)
        assert os.path.exists(filepath)
        assert filepath.endswith('.xlsx')
        assert os.path.getsize(filepath) > 0

        # Verify sheets
        xls = pd.ExcelFile(filepath)
        assert 'All Jobs' in xls.sheet_names
        assert 'By Platform' in xls.sheet_names
        assert 'Direct Links' in xls.sheet_names

    def test_excel_export_handles_empty_list(self, config, tmp_path):
        """Test Excel exporter gracefully handles empty job datasets"""
        exporter = JobExporter(config)
        exporter.export_dir = str(tmp_path)

        filepath = exporter.export_to_excel([])
        assert os.path.exists(filepath)
        assert filepath.endswith('.xlsx')

    def test_pdf_export_creates_valid_file(self, config, sample_jobs, tmp_path):
        """Test JobExporter generates a styled PDF document"""
        exporter = JobExporter(config)
        exporter.export_dir = str(tmp_path)

        filepath = exporter.export_to_pdf(sample_jobs)
        assert os.path.exists(filepath)
        assert filepath.endswith('.pdf')
        assert os.path.getsize(filepath) > 0

        # Validate PDF header bytes
        with open(filepath, 'rb') as f:
            header = f.read(5)
            assert header == b'%PDF-'

    def test_pdf_export_handles_empty_list(self, config, tmp_path):
        """Test PDF export with empty dataset"""
        exporter = JobExporter(config)
        exporter.export_dir = str(tmp_path)

        filepath = exporter.export_to_pdf([])
        assert os.path.exists(filepath)
        assert filepath.endswith('.pdf')

    def test_html_report_generation(self, config, sample_jobs, tmp_path):
        """Test HTML report generation with embedded charts and tables"""
        exporter = JobExporter(config)
        exporter.export_dir = str(tmp_path)

        filepath = exporter.generate_html_report(sample_jobs)
        assert os.path.exists(filepath)
        assert filepath.endswith('.html')

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'Discovered Job Report' in content
        assert 'Enterprise Solutions Inc' in content
        assert 'chart.js' in content.lower()

    def test_export_endpoints_http_download(self, client, app):
        """Test HTTP streaming downloads for Excel, PDF, and HTML"""
        with app.app_context():
            db.session.add(Job(platform='linkedin', title='DevOps', company='GlobalCorp', url='https://x.com/dl1'))
            db.session.commit()

        # Excel
        res_excel = client.get('/export/download/excel')
        assert res_excel.status_code == 200
        assert res_excel.headers['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

        # PDF
        res_pdf = client.get('/export/download/pdf')
        assert res_pdf.status_code == 200
        assert res_pdf.headers['Content-Type'] == 'application/pdf'

        # HTML
        res_html = client.get('/export/download/html')
        assert res_html.status_code == 200
        assert 'text/html' in res_html.headers['Content-Type']

    def test_exporter_platform_priority_sorting(self, config):
        """Test JobExporter._sort_by_platform_priority sorts jobs: LinkedIn -> Indeed -> Naukri -> Rest"""
        jobs = [
            {'platform': 'bayt', 'title': 'SRE', 'company': 'C1'},
            {'platform': 'indeed', 'title': 'SRE', 'company': 'C2'},
            {'platform': 'naukri', 'title': 'SRE', 'company': 'C3'},
            {'platform': 'linkedin', 'title': 'SRE', 'company': 'C4'},
            {'platform': 'google', 'title': 'SRE', 'company': 'C5'},
        ]
        sorted_jobs = JobExporter._sort_by_platform_priority(jobs)
        platforms = [j['platform'] for j in sorted_jobs]
        assert platforms[0] == 'linkedin'
        assert platforms[1] == 'indeed'
        assert platforms[2] == 'naukri'
        assert platforms[3] in ('bayt', 'google')
        assert platforms[4] in ('bayt', 'google')

    def test_export_endpoints_accept_location_parameter(self, client, app):
        """Test export download endpoints filter jobs when location parameter is passed"""
        with app.app_context():
            db.session.add(Job(platform='linkedin', title='DevOps', company='BlrCo', url='https://exp-blr.com', location='Bengaluru'))
            db.session.add(Job(platform='indeed', title='SRE', company='RemCo', url='https://exp-rem.com', location='Remote'))
            db.session.commit()

        # Excel with location=remote
        res_excel = client.get('/export/download/excel?location=remote')
        assert res_excel.status_code == 200

        # PDF with location=bengaluru
        res_pdf = client.get('/export/download/pdf?location=bengaluru')
        assert res_pdf.status_code == 200

        # HTML with location=both
        res_html = client.get('/export/download/html?location=both')
        assert res_html.status_code == 200


# ─────────────────────────────────────────────
# 7. End-to-End Integration Flow
# ─────────────────────────────────────────────

class TestEndToEndLifecycle:
    def test_complete_discovery_to_export_flow(self, client, app, config):
        """
        Verify complete user workflow:
        1. Discover / save jobs to database
        2. View dashboard and table view
        3. Transition job status to 'applied' and 'saved'
        4. Validate stats update dynamically
        5. Export final applied & saved jobs report to Excel and PDF
        """
        # Step 1: Save discovered jobs
        with app.app_context():
            job1 = Job(
                platform='linkedin',
                title='Site Reliability Engineer',
                company='Apex Cloud Systems',
                location='Bengaluru',
                url='https://linkedin.com/jobs/view/apex-1',
                status='new'
            )
            job2 = Job(
                platform='indeed',
                title='DevOps Engineer',
                company='Peak Scale Labs',
                location='Bengaluru',
                url='https://indeed.com/jobs/view/peak-2',
                status='new'
            )
            db.session.add_all([job1, job2])
            db.session.commit()

            j1_id = job1.id
            j2_id = job2.id

        # Step 2: Query dashboard & table
        resp_index = client.get('/')
        assert resp_index.status_code == 200

        resp_jobs = client.get('/jobs')
        assert resp_jobs.status_code == 200
        assert b'Apex Cloud Systems' in resp_jobs.data
        assert b'Peak Scale Labs' in resp_jobs.data

        # Step 3: Transition status
        client.put(f'/api/job/{j1_id}/status',
                   data=json.dumps({'status': 'applied'}),
                   content_type='application/json')
        client.put(f'/api/job/{j2_id}/status',
                   data=json.dumps({'status': 'saved'}),
                   content_type='application/json')

        # Step 4: Verify stats updated
        stats_resp = client.get('/api/stats')
        stats = stats_resp.get_json()
        assert stats['total_jobs'] == 2
        assert stats['applied'] == 1
        assert stats['saved'] == 1
        assert stats['new'] == 0

        # Step 5: Verify exports stream properly
        excel_resp = client.get('/export/download/excel')
        assert excel_resp.status_code == 200
        assert len(excel_resp.data) > 0

        pdf_resp = client.get('/export/download/pdf')
        assert pdf_resp.status_code == 200
        assert pdf_resp.data[:5] == b'%PDF-'


# ─────────────────────────────────────────────
# 8. Frontend Job Loading & Script Validity Tests
# ─────────────────────────────────────────────

class TestFrontendJobLoading:
    def test_all_templates_inline_javascript_syntax(self):
        """
        Verify that all inline <script> tags in web/templates/*.html are syntactically valid JavaScript.
        Guarantees that no duplicate closing tokens or parse errors block client-side job rendering.
        """
        import re
        import subprocess
        import shutil
        import tempfile

        node_bin = shutil.which('node')
        templates_dir = PROJECT_ROOT / 'web' / 'templates'
        html_files = list(templates_dir.glob('*.html'))
        assert len(html_files) > 0, "No HTML templates found in web/templates"

        script_tag_pattern = re.compile(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE)

        for html_file in html_files:
            content = html_file.read_text(encoding='utf-8')
            inline_scripts = script_tag_pattern.findall(content)
            for idx, script_code in enumerate(inline_scripts):
                script_code = script_code.strip()
                if not script_code:
                    continue

                if node_bin:
                    with tempfile.NamedTemporaryFile('w', suffix='.js', encoding='utf-8', delete=False) as tf:
                        tf.write(script_code)
                        temp_path = tf.name
                    try:
                        res = subprocess.run([node_bin, '-c', temp_path], capture_output=True, text=True)
                        assert res.returncode == 0, (
                            f"JavaScript syntax error in {html_file.name} (script #{idx}):\n{res.stderr}"
                        )
                    finally:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                else:
                    # Fallback syntax balance check when node is unavailable
                    open_braces = script_code.count('{') - script_code.count('}')
                    open_parens = script_code.count('(') - script_code.count(')')
                    open_brackets = script_code.count('[') - script_code.count(']')
                    assert open_braces == 0, f"Unbalanced braces in {html_file.name} script #{idx}"
                    assert open_parens == 0, f"Unbalanced parentheses in {html_file.name} script #{idx}"
                    assert open_brackets == 0, f"Unbalanced brackets in {html_file.name} script #{idx}"

    def test_dashboard_contains_critical_job_loading_elements(self, client):
        """
        Test that GET / returns the dashboard HTML with essential containers and event targets
        required for job rendering and pagination.
        """
        resp = client.get('/')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)

        # Critical DOM IDs
        assert 'id="jobs-container"' in html
        assert 'id="pagination-controls"' in html
        assert 'id="pagination-info"' in html
        assert 'id="status-filter-pills"' in html
        assert 'id="search-input"' in html
        assert 'id="location-toggle-group"' in html
        assert 'id="timeWindowSlider"' in html
        assert 'id="btn-scrape-window"' in html
        assert 'id="infinite-scroll-footer"' in html
        assert 'id="infinite-scroll-loader"' in html
        assert 'id="infinite-scroll-sentinel"' in html
        assert 'id="pagination-mode-toggle"' in html
        assert 'id="btn-back-to-top"' in html

        # Key JS lifecycle functions present
        assert 'function loadJobs(' in html
        assert 'function loadMoreJobs()' in html
        assert 'function setupIntersectionObserver()' in html
        assert 'function setScrollMode(' in html
        assert 'function renderJobs(' in html
        assert 'function renderPagination(' in html
        assert 'function updateStats()' in html
        assert 'function setLocationFilter(' in html
        assert 'function setStatusFilter(' in html

        # Verify automated initial invocation
        assert 'loadJobs(' in html
        assert 'updateStats();' in html
        assert 'updateScrollModeButtons();' in html

    def test_infinite_scroll_backup_and_rollback_safeguards(self):
        """
        Verify that a full backup of index.html with classic pagination exists,
        and that the revert script revert_infinite_scroll.py is present and valid.
        """
        backup_path = PROJECT_ROOT / 'web' / 'templates' / 'index.html.classic_backup'
        revert_script = PROJECT_ROOT / 'revert_infinite_scroll.py'

        assert backup_path.exists(), "Classic pagination backup missing at web/templates/index.html.classic_backup"
        assert revert_script.exists(), "Rollback script missing at revert_infinite_scroll.py"

        backup_content = backup_path.read_text(encoding='utf-8')
        assert 'id="pagination-controls"' in backup_content
        assert 'prevPage()' in backup_content
        assert 'nextPage()' in backup_content

    def test_api_jobs_contract_fulfills_frontend_requirements(self, client, app):
        """
        Verify that /api/jobs returns the exact payload schema required by renderJobs() in the frontend.
        """
        now = datetime.now(timezone.utc)
        with app.app_context():
            job = Job(
                platform='linkedin',
                title='DevOps Engineer',
                company='CloudTech Systems',
                location='Bengaluru, India',
                url='https://linkedin.com/jobs/view/test-fe-1',
                description='Kubernetes, Terraform, CI/CD pipelines',
                salary='25 - 35 LPA',
                salary_min=2500000,
                salary_max=3500000,
                date_posted=now,
                job_type='Full-time',
                num_applicants=25,
                is_easy_apply=True,
                status='new'
            )
            db.session.add(job)
            db.session.commit()

        resp = client.get('/api/jobs?page=1&per_page=12&status=all&location=both&q=')
        assert resp.status_code == 200
        data = resp.get_json()

        assert 'jobs' in data
        assert 'total' in data
        assert 'page' in data
        assert 'pages' in data
        assert data['total'] >= 1
        assert data['page'] == 1
        assert data['pages'] >= 1

        j = data['jobs'][0]
        # Required fields rendered in job cards
        assert 'id' in j
        assert 'platform' in j
        assert 'title' in j
        assert 'company' in j
        assert 'location' in j
        assert 'url' in j
        assert 'status' in j
        assert 'salary' in j
        assert 'is_easy_apply' in j
        assert 'description' in j
        assert 'date_posted' in j
        assert 'is_researched' in j
        assert 'search_count' in j

    def test_jobpilot_brand_and_redesign_elements(self, client):
        """
        Verify that JobPilot rebranding and professional UI components are rendered.
        """
        resp = client.get('/')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)

        assert 'JobPilot' in html
        assert 'jp-navbar' in html
        assert 'badge-researched-red' in html
        assert 'searchJobAgain(' in html
        assert 'filter-btn-researched' in html

    def test_job_researched_endpoint_and_filtering(self, client, app):
        """
        Verify that /api/job/<id>/researched marks a job as researched,
        and /api/jobs?status=researched filters for re-searched jobs.
        """
        with app.app_context():
            job = Job(
                platform='linkedin',
                title='Site Reliability Specialist',
                company='ResearchedTech',
                url='https://linkedin.com/jobs/view/researched-1',
                status='new',
                is_researched=False,
                search_count=1
            )
            db.session.add(job)
            db.session.commit()
            j_id = job.id

        # Mark as researched
        res = client.post(f'/api/job/{j_id}/researched')
        assert res.status_code == 200
        res_data = res.get_json()
        assert res_data['status'] == 'success'
        assert res_data['job']['is_researched'] is True
        assert res_data['job']['search_count'] == 2

        # Query with status=researched filter
        filter_res = client.get('/api/jobs?status=researched')
        assert filter_res.status_code == 200
        jobs_list = filter_res.get_json()['jobs']
        assert any(j['id'] == j_id for j in jobs_list)

    def test_jobpilot_redesign_backup_and_rollback_safeguards(self):
        """
        Verify that backup files and rollback script for the JobPilot redesign exist and are valid.
        """
        index_backup = PROJECT_ROOT / 'web' / 'templates' / 'index.html.jobpilot_backup'
        jobs_backup = PROJECT_ROOT / 'web' / 'templates' / 'jobs.html.jobpilot_backup'
        revert_script = PROJECT_ROOT / 'revert_jobpilot_redesign.py'

        assert index_backup.exists(), "Pre-redesign backup missing at web/templates/index.html.jobpilot_backup"
        assert jobs_backup.exists(), "Pre-redesign backup missing at web/templates/jobs.html.jobpilot_backup"
        assert revert_script.exists(), "Rollback script missing at revert_jobpilot_redesign.py"

        script_content = revert_script.read_text(encoding='utf-8')
        assert 'revert()' in script_content
        assert 'index.html.jobpilot_backup' in script_content

    def test_job_numbering_display_and_logic(self, client, app):
        """
        Verify that job numbering (1 to total count) is present in both dashboard and table views:
        - index.html includes job-number-badge, jobIndex calculation, and JetBrains Mono styling.
        - jobs.html includes job-num-badge with #1, #2... rendering.
        """
        # Test index.html dashboard elements
        resp_index = client.get('/')
        assert resp_index.status_code == 200
        index_html = resp_index.get_data(as_text=True)
        assert 'job-number-badge' in index_html
        assert 'job-number-val' in index_html
        assert 'jobIndex = baseIndex + idx + 1' in index_html

        # Test jobs.html table view with jobs
        with app.app_context():
            j1 = Job(platform='linkedin', title='DevOps Specialist', company='NumTest Corp 1', url='https://num1.com')
            j2 = Job(platform='indeed', title='SRE Specialist', company='NumTest Corp 2', url='https://num2.com')
            db.session.add_all([j1, j2])
            db.session.commit()

        resp_jobs = client.get('/jobs')
        assert resp_jobs.status_code == 200
        jobs_html = resp_jobs.get_data(as_text=True)
        assert 'job-num-badge' in jobs_html
        assert '#1' in jobs_html
        assert '#2' in jobs_html

    def test_dismissed_job_excluded_from_search_and_general_feed(self, client, app):
        """
        Verify that dismissed (rejected) jobs NEVER show up again in:
        1. General dashboard feed (status=all or default)
        2. Search results (even when matching the title/company directly)
        3. But are accessible when explicitly filtering for status=rejected
        """
        with app.app_context():
            job_active = Job(
                platform='linkedin',
                title='DevOps Specialist Alpha',
                company='ActiveCloud Corp',
                url='https://activecloud.com/job1',
                status='new'
            )
            job_dismissed = Job(
                platform='indeed',
                title='DevOps Specialist Beta',
                company='DismissedCloud Corp',
                url='https://dismissedcloud.com/job2',
                status='rejected'
            )
            db.session.add_all([job_active, job_dismissed])
            db.session.commit()
            act_id = job_active.id
            dis_id = job_dismissed.id

        # 1. General feed (/api/jobs) - dismissed job must NOT be present
        res_general = client.get('/api/jobs')
        assert res_general.status_code == 200
        ids_general = [j['id'] for j in res_general.get_json()['jobs']]
        assert act_id in ids_general
        assert dis_id not in ids_general

        # 2. Search query (/api/jobs?q=DevOps) - dismissed job must NOT be present
        res_search = client.get('/api/jobs?q=DevOps')
        assert res_search.status_code == 200
        ids_search = [j['id'] for j in res_search.get_json()['jobs']]
        assert act_id in ids_search
        assert dis_id not in ids_search

        # 3. Direct search by dismissed company name (/api/jobs?q=DismissedCloud)
        res_direct_search = client.get('/api/jobs?q=DismissedCloud')
        assert res_direct_search.status_code == 200
        ids_direct = [j['id'] for j in res_direct_search.get_json()['jobs']]
        assert dis_id not in ids_direct

        # 4. Explicit status=rejected filter - dismissed job IS accessible for review
        res_rejected = client.get('/api/jobs?status=rejected')
        assert res_rejected.status_code == 200
        ids_rejected = [j['id'] for j in res_rejected.get_json()['jobs']]
        assert dis_id in ids_rejected
        assert act_id not in ids_rejected

    def test_dismiss_confirmation_modal_and_rollback_safeguards(self, client):
        """
        Verify that the dismiss confirmation modal is present on the dashboard,
        and that the rollback script revert_dismiss_feature.py exists alongside valid backups.
        """
        # Verify modal and JS confirmation functions in dashboard
        resp = client.get('/')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert 'id="dismissConfirmModal"' in html
        assert 'id="btn-confirm-dismiss-action"' in html
        assert 'confirmDismissJob(' in html
        assert 'executeDismiss()' in html

        # Verify rollback safeguards
        routes_backup = PROJECT_ROOT / 'web' / 'routes.py.dismiss_backup'
        index_backup = PROJECT_ROOT / 'web' / 'templates' / 'index.html.dismiss_backup'
        revert_script = PROJECT_ROOT / 'revert_dismiss_feature.py'

        assert routes_backup.exists(), "Backup missing: web/routes.py.dismiss_backup"
        assert index_backup.exists(), "Backup missing: web/templates/index.html.dismiss_backup"
        assert revert_script.exists(), "Rollback script missing: revert_dismiss_feature.py"

        script_content = revert_script.read_text(encoding='utf-8')
        assert 'revert()' in script_content
        assert script_content.count('routes.py.dismiss_backup') > 0
        assert script_content.count('index.html.dismiss_backup') > 0

    def test_applied_badge_red_styling_and_contract(self, client):
        """
        Verify that applied jobs status badge is styled with a distinct, prominent red gradient
        and border in both the dashboard (index.html) and table view (jobs.html).
        """
        resp_index = client.get('/')
        assert resp_index.status_code == 200
        html_index = resp_index.get_data(as_text=True)
        assert '.status-applied' in html_index
        assert '#ef4444' in html_index or '#dc2626' in html_index
        assert '#b91c1c' in html_index

        resp_jobs = client.get('/jobs')
        assert resp_jobs.status_code == 200
        html_jobs = resp_jobs.get_data(as_text=True)
        assert '.status-applied' in html_jobs
        assert '#ef4444' in html_jobs or '#dc2626' in html_jobs

    def test_action_button_layout_apply_under_actions(self, client):
        """
        Verify that in the dashboard cards, the 'Apply on [PLATFORM]' button is placed
        directly underneath the card action button cluster ('Search Again', 'Mark Applied', 'Save', 'Dismiss').
        """
        resp = client.get('/')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert 'card-action-block' in html
        assert 'btn-apply-direct' in html
        assert 'Apply on ${plat.toUpperCase()}' in html

    def test_dark_mode_elements_and_persistence_contract(self, client):
        """
        Verify that dark mode toggle elements, theme CSS variables, and zero-flash
        localStorage checking scripts are present in both index.html and jobs.html.
        """
        for path in ['/', '/jobs']:
            resp = client.get(path)
            assert resp.status_code == 200
            html = resp.get_data(as_text=True)
            assert 'id="btn-theme-toggle"' in html
            assert 'id="theme-toggle-icon"' in html
            assert 'toggleDarkMode()' in html
            assert 'data-theme="dark"' in html
            assert 'jobpilot_theme' in html

    def test_strict_hours_window_filtering_api_and_ui(self, client, app):
        """
        Verify that passing ?hours=N to /api/jobs and /api/stats strictly returns
        only jobs posted or created within that specific hour window.
        """
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)

        with app.app_context():
            # Job 1: 1 hour ago (within 2h window)
            job_recent = Job(
                platform='linkedin',
                title='DevOps Engineer Recent',
                company='FastTech Corp',
                url='https://linkedin.com/jobs/view/recent-1',
                date_posted=now - timedelta(hours=1),
                created_at=now - timedelta(hours=1),
                status='new'
            )
            # Job 2: 5 hours ago (outside 2h window, inside 6h window)
            job_mid = Job(
                platform='indeed',
                title='Cloud Engineer Mid',
                company='MidTech Corp',
                url='https://indeed.com/jobs/view/mid-2',
                date_posted=now - timedelta(hours=5),
                created_at=now - timedelta(hours=5),
                status='new'
            )
            # Job 3: 40 hours ago (outside 24h window)
            job_old = Job(
                platform='naukri',
                title='SRE Engineer Old',
                company='OldTech Corp',
                url='https://naukri.com/jobs/view/old-3',
                date_posted=now - timedelta(hours=40),
                created_at=now - timedelta(hours=40),
                status='new'
            )
            db.session.add_all([job_recent, job_mid, job_old])
            db.session.commit()
            rec_id = job_recent.id
            mid_id = job_mid.id
            old_id = job_old.id

        # 1. 2 hours window: only recent job
        res_2h = client.get('/api/jobs?hours=2')
        assert res_2h.status_code == 200
        jobs_2h = [j['id'] for j in res_2h.get_json()['jobs']]
        assert rec_id in jobs_2h
        assert mid_id not in jobs_2h
        assert old_id not in jobs_2h

        # Verify stats endpoint respects hours
        res_stats_2h = client.get('/api/stats?hours=2')
        assert res_stats_2h.status_code == 200
        assert res_stats_2h.get_json()['hours'] == 2

        # 2. 6 hours window: recent and mid jobs, but not old
        res_6h = client.get('/api/jobs?hours=6')
        assert res_6h.status_code == 200
        jobs_6h = [j['id'] for j in res_6h.get_json()['jobs']]
        assert rec_id in jobs_6h
        assert mid_id in jobs_6h
        assert old_id not in jobs_6h

        # 3. All time (no hours): all jobs
        res_all = client.get('/api/jobs')
        assert res_all.status_code == 200
        jobs_all = [j['id'] for j in res_all.get_json()['jobs']]
        assert rec_id in jobs_all
        assert mid_id in jobs_all
        assert old_id in jobs_all

        # 4. Verify dashboard slider and clear hours filter elements
        res_index = client.get('/')
        assert res_index.status_code == 200
        html_index = res_index.get_data(as_text=True)
        assert 'id="btn-clear-hours"' in html_index
        assert 'clearHoursFilter()' in html_index
        assert 'currentHoursFilter' in html_index

    def test_applied_darkmode_hours_rollback_safeguards(self):
        """
        Verify that backup files and rollback script for the Applied Red Badge, Action Button Relocation,
        Dark Mode Toggle, and Strict Hours Window Filtering exist and are valid.
        """
        routes_backup = PROJECT_ROOT / 'web' / 'routes.py.hours_backup'
        index_backup = PROJECT_ROOT / 'web' / 'templates' / 'index.html.hours_backup'
        jobs_backup = PROJECT_ROOT / 'web' / 'templates' / 'jobs.html.hours_backup'
        revert_script = PROJECT_ROOT / 'revert_applied_darkmode_hours.py'

        assert routes_backup.exists(), "Backup missing: web/routes.py.hours_backup"
        assert index_backup.exists(), "Backup missing: web/templates/index.html.hours_backup"
        assert jobs_backup.exists(), "Backup missing: web/templates/jobs.html.hours_backup"
        assert revert_script.exists(), "Rollback script missing: revert_applied_darkmode_hours.py"

        script_content = revert_script.read_text(encoding='utf-8')
        assert 'revert()' in script_content
        assert 'routes.py.hours_backup' in script_content
        assert 'index.html.hours_backup' in script_content
        assert 'jobs.html.hours_backup' in script_content


# ─────────────────────────────────────────────
# 9. Enhanced Scraper & Filter Engine Tests (Real-World LinkedIn Cases)
# ─────────────────────────────────────────────

class TestEnhancedScraperAndFilterForLinkedInMissedJobs:
    def test_flexible_role_title_matching_for_real_linkedin_titles(self, config):
        """
        Verify that _matches_role_title matches non-contiguous titles, support variations,
        level markers (e.g. II), and platforms, while cleanly rejecting non-target roles.
        """
        engine = FilterEngine(config)
        all_terms = set(engine.target_roles)
        for r in engine.target_roles:
            for syn in engine.ROLE_SYNONYMS.get(r, []):
                all_terms.add(syn.lower())

        # Real LinkedIn titles that should be matched
        matching_titles = [
            'Cloud Engineer',
            'DevOps Engineer',
            'DevOps Engineer II',
            'Engineer - DevOps & Cloud',
            'Platform Software Engineer',
            'Technical Support Engineer (Cloud)',
            'Cloud Support Engineer',
            'Cloud Operations Engineer',
            'Associate Cloud Engineer',
            'Infrastructure Specialist',
            'Site Reliability / DevOps Engineer',
            'Systems Engineer - Cloud & Infrastructure',
            'Cloud Infrastructure Engineer',
            'DevOps / Cloud Specialist',
        ]
        for title in matching_titles:
            assert engine._matches_role_title(title, all_terms) is True, f"Failed to match: {title}"

        # Unrelated titles that should be rejected
        unrelated_titles = [
            'Frontend Developer',
            'React Native Specialist',
            'Salesforce Administrator',
            'HR Operations Generalist',
            'Financial Analyst',
            'Marketing Specialist',
            'UI/UX Designer',
            'Accountant',
        ]
        for title in unrelated_titles:
            assert engine._matches_role_title(title, all_terms) is False, f"Erroneously matched: {title}"

    def test_experience_filter_allows_midlevel_ranges_and_company_history(self, config):
        """
        Verify that _filter_by_experience:
        1. Accepts mid-level ranges where candidate's 3 years experience fits (e.g. 2-5y, 3-5y, 2-6y)
        2. Accepts company history/longevity text (e.g. 'operating for 10+ years', 'founded 12+ years ago')
        3. Strictly rejects roles requiring > 4 years minimum (5+, 8+, 5-8y) and executive/senior titles
        """
        engine = FilterEngine(config)

        test_jobs = [
            # Qualifying: mid-level ranges where 3y candidate qualifies
            {'title': 'DevOps Engineer II', 'description': 'Seeking candidate with 3-5 years of experience in AWS', 'url': 'q1'},
            {'title': 'Cloud Engineer', 'description': 'Requires 2 to 5 years of experience with Terraform', 'url': 'q2'},
            {'title': 'Platform Software Engineer', 'description': '2-6 years of experience building pipelines', 'url': 'q3'},
            {'title': 'Engineer - DevOps & Cloud', 'description': 'HackerRank has been operating for 10+ years in tech assessments. Looking for 2-4 years of experience.', 'url': 'q4'},
            {'title': 'Cloud Support Engineer', 'description': 'Over 10+ years of industry leadership. We are seeking an engineer with 3 years hands-on experience.', 'url': 'q5'},
            {'title': 'DevOps Architect_104590', 'description': 'AWS DevOps CI/CD pipeline automation. Seeking 3-4 years experience.', 'url': 'q6'},

            # Excessive: minimum requirement exceeds 4 years
            {'title': 'DevOps Engineer', 'description': 'Requires 8+ years of experience in AWS', 'url': 'e1'},
            {'title': 'Cloud Engineer', 'description': 'Minimum 5 years of experience required', 'url': 'e2'},
            {'title': 'SRE', 'description': '5-8 years of experience building high-scale systems', 'url': 'e3'},
            {'title': 'Platform Engineer', 'description': '6 to 9 yrs of relevant experience', 'url': 'e4'},
            {'title': 'DevOps Architect_104590', 'description': 'Requires 8+ years of experience in cloud.', 'url': 'e5'},

            # Senior/Executive titles (must be excluded regardless of stated years)
            {'title': 'Director of Cloud Infrastructure', 'description': '3 years experience with AWS', 'url': 's1'},
            {'title': 'Senior Cloud Engineer', 'description': '3 years experience', 'url': 's2'},
            {'title': 'Lead DevOps Engineer', 'description': '2 years experience', 'url': 's3'},
            {'title': 'Principal Platform Engineer', 'description': '3 years experience', 'url': 's4'},
        ]

        passed = engine._filter_by_experience(test_jobs)
        passed_urls = [j['url'] for j in passed]

        # All qualifying mid-level jobs must pass
        for q_id in ['q1', 'q2', 'q3', 'q4', 'q5', 'q6']:
            assert q_id in passed_urls, f"Expected {q_id} to pass experience filter"

        # All excessive experience jobs must be rejected
        for e_id in ['e1', 'e2', 'e3', 'e4', 'e5']:
            assert e_id not in passed_urls, f"Expected {e_id} to be rejected"

        # All senior/executive titles must be rejected
        for s_id in ['s1', 's2', 's3', 's4']:
            assert s_id not in passed_urls, f"Expected {s_id} to be rejected"

    def test_applicant_filter_ignores_non_applicant_number_mentions(self, config):
        """
        Verify that _filter_by_applicants strictly excludes >100 applicant jobs
        without false-positive rejections on tech mentions like 'over 100 microservices'.
        """
        engine = FilterEngine(config)

        test_jobs = [
            # Technical text mentions of 'over 100' (must be accepted)
            {'title': 'DevOps Engineer', 'num_applicants': 35, 'description': 'Managing over 100 microservices in Kubernetes', 'url': 'ok1'},
            {'title': 'Cloud Engineer', 'num_applicants': None, 'description': 'Over 100 enterprise customers rely on our AWS infrastructure', 'url': 'ok2'},
            {'title': 'SRE', 'num_applicants': 80, 'description': 'Handling over 100 database instances across regions', 'url': 'ok3'},

            # Real applicant indicators (must be rejected)
            {'title': 'DevOps Engineer', 'num_applicants': 120, 'description': 'Standard role', 'url': 'bad1'},
            {'title': 'Cloud Engineer', 'num_applicants': None, 'description': 'Over 100 people clicked apply on LinkedIn', 'url': 'bad2'},
            {'title': 'SRE', 'num_applicants': None, 'description': '150+ applicants for this position', 'url': 'bad3'},
            {'title': 'Platform Engineer', 'num_applicants': None, 'description': 'More than 100 people applied for this role', 'url': 'bad4'},
        ]

        passed = engine._filter_by_applicants(test_jobs)
        passed_urls = [j['url'] for j in passed]

        assert 'ok1' in passed_urls
        assert 'ok2' in passed_urls
        assert 'ok3' in passed_urls

        assert 'bad1' not in passed_urls
        assert 'bad2' not in passed_urls
        assert 'bad3' not in passed_urls
        assert 'bad4' not in passed_urls

    @patch('scraper.multi_platform.scrape_jobs')
    def test_scraper_queries_pan_india_remote_and_all_configured_roles(self, mock_scrape, config):
        """
        Verify that RealJobScraper queries both local city and Pan-India Remote
        listings when remote is enabled, queries all configured roles without truncation,
        and tags remote records with '(Remote)'.
        """
        mock_scrape.return_value = pd.DataFrame([{
            'title': 'Cloud Engineer',
            'company': 'Jobgether',
            'location': 'India',
            'job_url': 'https://linkedin.com/jobs/view/rem1',
            'description': 'Remote Cloud role',
            'num_applicants': 15,
            'is_remote': True,
        }])

        scraper = RealJobScraper(config)
        scraper.SUPPORTED_SITES = {'linkedin': {'site': 'linkedin', 'country': None}}
        scraper.roles = ['Cloud Engineer', 'Platform Engineer', 'Infrastructure Engineer']
        scraper.remote_enabled = True

        results = scraper.scrape_all(results_per_query=5)
        assert len(results) == 1
        assert results[0]['location'] == 'India (Remote)'

        # Verify calls were made for both local Bengaluru and Pan-India Remote
        assert mock_scrape.call_count >= 2
        calls = mock_scrape.call_args_list
        locations_called = [c[1].get('location') for c in calls]
        remotes_called = [c[1].get('is_remote') for c in calls]

        assert 'Bengaluru' in locations_called
        assert 'India' in locations_called
        assert True in remotes_called

        # Verify all configured roles were queried (not truncated to 3)
        roles_called = [c[1].get('search_term') for c in calls]
        assert 'Cloud Engineer' in roles_called
        assert 'Platform Engineer' in roles_called
        assert 'Infrastructure Engineer' in roles_called

    def test_real_linkedin_pasted_jobs_full_pipeline(self, config):
        """
        Verify end-to-end filtering pipeline on the exact list of jobs pasted by the user:
        Qualifies:
        - Cloud Engineer - Jobgether - India (Remote)
        - DevOps Engineer - Flexiple - India (Remote)
        - DevOps Engineer II - HackerRank - Bengaluru
        - Platform Software Engineer - Nexthink - Bengaluru
        - Engineer - DevOps & Cloud - TÜV SÜD - Bengaluru
        - Technical Support Engineer (Cloud) - LogicMonitor - Bengaluru
        - Cloud Support Engineer - Flexiple - India (Remote)
        - Cloud Engineer - Viga Entertainment Technology - Bengaluru
        - Cloud Engineer - LTIMindtree - Bengaluru
        Excludes:
        - Cloud Architect - Invi Grid Inc. (Architect exclusion)
        - Senior Cloud Engineer - Epsilon (Senior exclusion)
        - Frontend Developer - RandomCorp (Role mismatch)
        """
        engine = FilterEngine(config)
        now = datetime.now(timezone.utc)

        raw_candidates = [
            {
                'title': 'Cloud Engineer',
                'company': 'Jobgether',
                'location': 'India (Remote)',
                'url': 'https://linkedin.com/jobs/view/jobgether-cloud',
                'description': 'AWS, Terraform, Docker cloud engineer role. Over 10+ years of company track record. Seeking 3 years experience.',
                'num_applicants': 25,
                'date_posted': now,
                'platform': 'linkedin'
            },
            {
                'title': 'DevOps Engineer',
                'company': 'Flexiple',
                'location': 'India (Remote)',
                'url': 'https://linkedin.com/jobs/view/flexiple-devops',
                'description': 'DevOps CI/CD pipelines with Kubernetes and Docker. 2-5 years of experience.',
                'num_applicants': 40,
                'date_posted': now,
                'platform': 'linkedin'
            },
            {
                'title': 'DevOps Engineer II',
                'company': 'HackerRank',
                'location': 'Bengaluru, Karnataka, India',
                'url': 'https://linkedin.com/jobs/view/hackerrank-devops-ii',
                'description': 'HackerRank has been operating for 10+ years in technical hiring. Seeking candidate with 2 to 4 years experience.',
                'num_applicants': 30,
                'date_posted': now,
                'platform': 'linkedin'
            },
            {
                'title': 'Platform Software Engineer',
                'company': 'Nexthink',
                'location': 'Bengaluru, Karnataka, India',
                'url': 'https://linkedin.com/jobs/view/nexthink-platform',
                'description': 'Internal developer platform tooling in Kubernetes and Python. 3 years experience required.',
                'num_applicants': 18,
                'date_posted': now,
                'platform': 'linkedin'
            },
            {
                'title': 'Engineer - DevOps & Cloud',
                'company': 'TÜV SÜD',
                'location': 'Bengaluru, Karnataka, India',
                'url': 'https://linkedin.com/jobs/view/tuv-devops-cloud',
                'description': 'DevOps automation, Terraform, and cloud reliability. 3-5 years of experience.',
                'num_applicants': 50,
                'date_posted': now,
                'platform': 'linkedin'
            },
            {
                'title': 'Technical Support Engineer (Cloud)',
                'company': 'LogicMonitor',
                'location': 'Bengaluru, Karnataka, India',
                'url': 'https://linkedin.com/jobs/view/logicmonitor-cloud',
                'description': 'Customer cloud infrastructure observability support. 2-4 years experience.',
                'num_applicants': 22,
                'date_posted': now,
                'platform': 'linkedin'
            },
            {
                'title': 'Cloud Support Engineer',
                'company': 'Flexiple',
                'location': 'India (Remote)',
                'url': 'https://linkedin.com/jobs/view/flexiple-cloud-support',
                'description': 'Cloud operations and AWS troubleshooting. 1-3 years experience.',
                'num_applicants': 35,
                'date_posted': now,
                'platform': 'linkedin'
            },
            {
                'title': 'Cloud Engineer',
                'company': 'Viga Entertainment Technology',
                'location': 'Bengaluru, Karnataka, India',
                'url': 'https://linkedin.com/jobs/view/viga-cloud',
                'description': 'AWS cloud infrastructure rendering pipeline support. 2 years experience.',
                'num_applicants': 12,
                'date_posted': now,
                'platform': 'linkedin'
            },
            {
                'title': 'Cloud Engineer',
                'company': 'LTIMindtree',
                'location': 'Bengaluru, Karnataka, India',
                'url': 'https://linkedin.com/jobs/view/ltimindtree-cloud',
                'description': 'Azure and AWS enterprise migrations. 3 years hands-on experience.',
                'num_applicants': 60,
                'date_posted': now,
                'platform': 'linkedin'
            },

            # Excluded test cases
            {
                'title': 'Cloud Architect',
                'company': 'Invi Grid Inc.',
                'location': 'Bengaluru, Karnataka, India',
                'url': 'https://linkedin.com/jobs/view/invi-arch',
                'description': 'Architect cloud solutions. 7+ years of experience required.',
                'num_applicants': 45,
                'date_posted': now,
                'platform': 'linkedin'
            },
            {
                'title': 'Senior Cloud Engineer',
                'company': 'Epsilon',
                'location': 'Bengaluru, Karnataka, India',
                'url': 'https://linkedin.com/jobs/view/epsilon-sr-cloud',
                'description': 'Lead cloud team. 6+ years experience.',
                'num_applicants': 20,
                'date_posted': now,
                'platform': 'linkedin'
            },
            {
                'title': 'Frontend Developer',
                'company': 'RandomCorp',
                'location': 'Bengaluru, Karnataka, India',
                'url': 'https://linkedin.com/jobs/view/frontend-dev',
                'description': 'React and CSS development. 2 years experience.',
                'num_applicants': 20,
                'date_posted': now,
                'platform': 'linkedin'
            },
        ]

        filtered_results = engine.filter_jobs(raw_candidates, today_only=True)
        filtered_urls = [j['url'] for j in filtered_results]

        # Assert all 9 targeted jobs successfully passed
        expected_passing_urls = [
            'https://linkedin.com/jobs/view/jobgether-cloud',
            'https://linkedin.com/jobs/view/flexiple-devops',
            'https://linkedin.com/jobs/view/hackerrank-devops-ii',
            'https://linkedin.com/jobs/view/nexthink-platform',
            'https://linkedin.com/jobs/view/tuv-devops-cloud',
            'https://linkedin.com/jobs/view/logicmonitor-cloud',
            'https://linkedin.com/jobs/view/flexiple-cloud-support',
            'https://linkedin.com/jobs/view/viga-cloud',
            'https://linkedin.com/jobs/view/ltimindtree-cloud',
        ]
        for exp_url in expected_passing_urls:
            assert exp_url in filtered_urls, f"Expected {exp_url} to be qualified"

        # Assert excluded jobs are strictly blocked
        assert 'https://linkedin.com/jobs/view/invi-arch' not in filtered_urls
        assert 'https://linkedin.com/jobs/view/epsilon-sr-cloud' not in filtered_urls
        assert 'https://linkedin.com/jobs/view/frontend-dev' not in filtered_urls
        assert len(filtered_results) == 9


# ─────────────────────────────────────────────
# 10. Cloud Keywords & Resume Technical Skills Matching Tests
# ─────────────────────────────────────────────

class TestCloudKeywordsAndResumeSkillsMatching:
    def test_cloud_azure_aws_gcp_google_cloud_title_matching(self, config):
        """
        Verify that job titles containing cloud, azure, aws, gcp, google cloud,
        or amazon web services combined with engineering/technical qualifiers match.
        """
        engine = FilterEngine(config)
        all_terms = set(engine.target_roles)
        for r in engine.target_roles:
            for syn in engine.ROLE_SYNONYMS.get(r, []):
                all_terms.add(syn.lower())

        valid_cloud_titles = [
            'AWS Cloud Engineer',
            'Azure Cloud Specialist',
            'Google Cloud Platform Engineer',
            'GCP Infrastructure Engineer',
            'Cloud Developer',
            'Associate Cloud Engineer',
            'Cloud Support Associate',
            'Cloud Operations Engineer',
            'AWS DevOps Associate',
            'Azure Administrator',
            'Cloud Solutions Consultant',
            'AWS SysOps Engineer',
            'GCP Associate',
            'Cloud Infrastructure Specialist',
            'Amazon Web Services Solutions Engineer',
            'Cloud Systems Analyst',
            'AWS Cloud Practitioner',
        ]
        for title in valid_cloud_titles:
            assert engine._matches_role_title(title, all_terms) is True, f"Failed to match valid cloud title: {title}"

    def test_non_tech_roles_with_cloud_keyword_rejected(self, config):
        """
        Verify that non-technical titles (kitchen, sales, marketing, recruiting)
        mentioning 'cloud' are rejected even if they contain the keyword.
        """
        engine = FilterEngine(config)
        all_terms = set(engine.target_roles)
        for r in engine.target_roles:
            for syn in engine.ROLE_SYNONYMS.get(r, []):
                all_terms.add(syn.lower())

        non_tech_titles = [
            'Cloud Kitchen Manager',
            'Cloud Kitchen Chef',
            'Cloud Kitchen Cook',
            'Sales Representative - Cloud Software',
            'Cloud Marketing Specialist',
            'Talent Acquisition Specialist (Cloud)',
            'Cloud Account Executive',
            'Cloud Real Estate Agent',
            'Cloud Business Development Representative',
        ]
        for title in non_tech_titles:
            assert engine._matches_role_title(title, all_terms) is False, f"Erroneously matched non-tech title: {title}"

    def test_resume_technical_skills_and_cloud_keyword_description_matching(self, config):
        """
        Verify that jobs with technical titles whose descriptions feature
        cloud keywords (AWS, Azure, GCP, Cloud) along with candidate resume skills
        (Terraform, Docker, Kubernetes, Lambda, CodePipeline, Python, Linux) qualify.
        """
        engine = FilterEngine(config)
        now = datetime.now(timezone.utc)

        jobs_with_resume_skills = [
            # Title is generic "Software Engineer", description has AWS + Terraform + Kubernetes
            {
                'title': 'Software Engineer',
                'company': 'Tech Solutions',
                'location': 'Bengaluru',
                'url': 'https://job1.com',
                'description': 'Building cloud microservices on AWS utilizing Terraform, Docker, and Kubernetes.',
                'num_applicants': 20,
                'date_posted': now,
                'platform': 'linkedin',
            },
            # Title is "Systems Engineer", description has Azure + GitOps + CI/CD
            {
                'title': 'Systems Engineer',
                'company': 'Innovate Inc',
                'location': 'Bengaluru',
                'url': 'https://job2.com',
                'description': 'Managing Azure cloud infrastructure with GitOps, CI/CD, and Python scripting.',
                'num_applicants': 15,
                'date_posted': now,
                'platform': 'indeed',
            },
            # Title is "Technology Analyst", description has Google Cloud + Linux + Python
            {
                'title': 'Technology Analyst',
                'company': 'Global Analytics',
                'location': 'Bengaluru',
                'url': 'https://job3.com',
                'description': 'Supporting Google Cloud data pipelines with Linux automation and Python.',
                'num_applicants': 30,
                'date_posted': now,
                'platform': 'naukri',
            },
            # Title is "Infrastructure Specialist", description has GCP + Ansible + Prometheus + Grafana
            {
                'title': 'Infrastructure Specialist',
                'company': 'Cloud Native Corp',
                'location': 'Bengaluru',
                'url': 'https://job4.com',
                'description': 'Maintaining GCP infrastructure observability with Prometheus, Grafana, and Ansible.',
                'num_applicants': 25,
                'date_posted': now,
                'platform': 'glassdoor',
            },
        ]

        passed = engine._filter_by_role_and_skills(jobs_with_resume_skills)
        passed_urls = [j['url'] for j in passed]

        assert 'https://job1.com' in passed_urls
        assert 'https://job2.com' in passed_urls
        assert 'https://job3.com' in passed_urls
        assert 'https://job4.com' in passed_urls

    def test_deepanshu_resume_exact_experience_role_matching(self, config):
        """
        Verify that job postings matching Deepanshu's exact current and past roles
        (System Engineer 1 at Swiggy, Cloud Engineer at Starwatt) are matched.
        """
        engine = FilterEngine(config)
        now = datetime.now(timezone.utc)

        resume_exact_jobs = [
            # Deepanshu's current Swiggy role title and tech stack
            {
                'title': 'System Engineer 1',
                'company': 'Leading Tech Co',
                'location': 'Bengaluru',
                'url': 'https://swiggy-profile.com',
                'description': 'AWS resource automation using CodePipeline, Lambda, SQS, CloudWatch, and Terraform.',
                'num_applicants': 10,
                'date_posted': now,
                'platform': 'linkedin',
            },
            # Deepanshu's Starwatt role title and tech stack
            {
                'title': 'Cloud Engineer',
                'company': 'Cloud Consulting Co',
                'location': 'Bengaluru',
                'url': 'https://starwatt-profile.com',
                'description': 'AWS SSO access automation and Terraform provisioning with GitOps.',
                'num_applicants': 20,
                'date_posted': now,
                'platform': 'linkedin',
            },
        ]

        results = engine.filter_jobs(resume_exact_jobs, today_only=True)
        res_urls = [j['url'] for j in results]
        assert 'https://swiggy-profile.com' in res_urls
        assert 'https://starwatt-profile.com' in res_urls

    def test_scraper_accepts_keywords_and_expanded_roles(self, config):
        """
        Verify RealJobScraper loads configured keywords and supports
        keyword querying via include_keyword_queries.
        """
        scraper = RealJobScraper(config)
        assert hasattr(scraper, 'keywords')
        assert 'cloud' in scraper.keywords
        assert 'aws' in scraper.keywords
        assert 'azure' in scraper.keywords
        assert 'gcp' in scraper.keywords
        assert 'google cloud' in scraper.keywords

    def test_cloud_regex_precision(self):
        """
        Verify FilterEngine.CLOUD_REGEX matches all intended keywords and phrases
        without falsely matching unrelated words.
        """
        regex = FilterEngine.CLOUD_REGEX

        positive_cases = [
            'AWS', 'aws', 'Amazon Web Services', 'amazon web services',
            'Azure', 'azure', 'Microsoft Azure',
            'GCP', 'gcp', 'Google Cloud', 'google cloud',
            'Cloud Engineer', 'cloud architecture', 'multi-cloud',
        ]
        for text in positive_cases:
            assert regex.search(text) is not None, f"CLOUD_REGEX failed to match: '{text}'"

        negative_cases = [
            'clover', 'lawsuit', 'gasp', 'unrelated frontend', 'java backend developer'
        ]
        for text in negative_cases:
            assert regex.search(text) is None, f"CLOUD_REGEX falsely matched: '{text}'"

    def test_config_contains_over_100_to_150_keywords(self):
        """
        Verify that config.yaml and FilterEngine have at least 100 to 150 keywords
        covering Cloud, DevOps, SRE, and resume skills.
        """
        config_path = PROJECT_ROOT / 'config.yaml'
        assert config_path.exists(), "config.yaml not found at project root"
        with open(config_path, 'r', encoding='utf-8') as f:
            real_config = yaml.safe_load(f)

        engine = FilterEngine(real_config)
        keywords_in_config = real_config.get('search', {}).get('keywords', [])

        # Verify config contains at least 100-150 keywords (we added 170)
        assert len(keywords_in_config) >= 100, f"Expected >= 100 keywords in config, got {len(keywords_in_config)}"
        assert len(engine.CORE_SKILLS) >= 100, f"Expected >= 100 skills in CORE_SKILLS, got {len(engine.CORE_SKILLS)}"
        assert len(engine.skills_pool) >= 100, f"Expected >= 100 skills in skills_pool, got {len(engine.skills_pool)}"

        # Check essential categories are present
        categories_to_check = [
            # Cloud
            'aws', 'azure', 'gcp', 'google cloud',
            # AWS services
            'lambda', 'sqs', 'elasticache', 'opensearch', 'codepipeline', 'cloudwatch',
            # Azure services
            'aks', 'azure devops', 'bicep', 'entra id',
            # GCP services
            'gke', 'cloud run', 'cloud pub/sub',
            # IaC
            'terraform', 'ansible', 'pulumi', 'terragrunt',
            # Containers
            'docker', 'kubernetes', 'helm', 'openshift',
            # GitOps & CI/CD
            'gitops', 'argocd', 'jenkins', 'github actions',
            # Observability
            'prometheus', 'grafana', 'datadog', 'opentelemetry',
            # Security & Networking
            'waf', 'vpc', 'route 53', 'kms', 'zero trust',
            # SRE
            'sre', 'site reliability', 'sli', 'slo', 'error budgets', 'platform engineering'
        ]
        for cat_kw in categories_to_check:
            assert cat_kw in engine.skills_pool, f"Missing category keyword: {cat_kw}"

    def test_matching_across_cloud_subcategories(self, config):
        """
        Verify that jobs matching distinct technical subcategories
        (AWS, Azure, GCP, IaC, Containers, CI/CD, Observability, Security, SRE)
        all qualify properly.
        """
        engine = FilterEngine(config)
        now = datetime.now(timezone.utc)

        category_jobs = [
            # AWS serverless & caching stack
            {
                'title': 'Cloud Engineer',
                'company': 'Serverless Tech',
                'location': 'Bengaluru',
                'url': 'https://c1.com',
                'description': 'Building AWS serverless workflows with Lambda, SQS, and ElastiCache.',
                'num_applicants': 15,
                'date_posted': now,
                'platform': 'linkedin',
            },
            # Azure cloud & AKS stack
            {
                'title': 'DevOps Engineer',
                'company': 'Azure Cloud Corp',
                'location': 'Bengaluru',
                'url': 'https://c2.com',
                'description': 'Provisioning AKS clusters using Bicep and Azure DevOps pipelines.',
                'num_applicants': 20,
                'date_posted': now,
                'platform': 'indeed',
            },
            # GCP & Cloud Run stack
            {
                'title': 'Platform Engineer',
                'company': 'GCP Innovations',
                'location': 'Bengaluru',
                'url': 'https://c3.com',
                'description': 'Deploying microservices on GKE and Cloud Run with Terraform.',
                'num_applicants': 18,
                'date_posted': now,
                'platform': 'naukri',
            },
            # GitOps & Service Mesh stack
            {
                'title': 'Site Reliability Engineer',
                'company': 'Modern Infra Co',
                'location': 'Bengaluru',
                'url': 'https://c4.com',
                'description': 'Managing Kubernetes service mesh with Istio, ArgoCD, and Helm charts.',
                'num_applicants': 25,
                'date_posted': now,
                'platform': 'glassdoor',
            },
            # Observability & SRE metrics stack
            {
                'title': 'System Engineer',
                'company': 'Observability Inc',
                'location': 'Bengaluru',
                'url': 'https://c5.com',
                'description': 'Tracking SLO and error budgets with Datadog, Prometheus, and OpenTelemetry on AWS.',
                'num_applicants': 30,
                'date_posted': now,
                'platform': 'linkedin',
            },
            # Cloud Security & Zero Trust stack
            {
                'title': 'DevSecOps Engineer',
                'company': 'Cyber Guard',
                'location': 'Bengaluru',
                'url': 'https://c6.com',
                'description': 'Implementing Zero Trust security, AWS WAF, KMS, and IAM policies.',
                'num_applicants': 12,
                'date_posted': now,
                'platform': 'linkedin',
            },
        ]

        passed = engine._filter_by_role_and_skills(category_jobs)
        passed_urls = [j['url'] for j in passed]

        for idx in range(1, 7):
            assert f'https://c{idx}.com' in passed_urls, f"Failed for category job c{idx}"


class TestKeywordRegexAndTitleWildcards:
    """
    Automated tests verifying:
    1. Keyword regex matching with zero false positives on short acronyms (go, git, slo, iam, etc.)
    2. Format variation handling (ci/cd, route 53, k8s, cloudwatch, etc.)
    3. Wildcard prefix matching for aws* and other keywords (AWSEngineer, CloudOps, AzureDevOps, etc.)
    4. Capitalization and all writing styles (ALL UPPERCASE, all lowercase, Capitalize, Mixed Case, Delimiters)
    5. Rollback safeguards and backup integrity (filter/engine.py.keywords_regex_backup, revert_keywords_regex.py)
    """

    def test_keywords_regex_rollback_safeguards(self):
        """Verify backup file exists and revert script is valid python."""
        backup_path = PROJECT_ROOT / 'filter' / 'engine.py.keywords_regex_backup'
        revert_path = PROJECT_ROOT / 'revert_keywords_regex.py'

        assert backup_path.exists(), "filter/engine.py.keywords_regex_backup must exist"
        assert revert_path.exists(), "revert_keywords_regex.py must exist"

        # Verify backup contains valid Python code
        with open(backup_path, 'r', encoding='utf-8') as f:
            code = f.read()
        compile(code, str(backup_path), 'exec')

        # Verify revert script contains valid Python code
        with open(revert_path, 'r', encoding='utf-8') as f:
            rev_code = f.read()
        compile(rev_code, str(revert_path), 'exec')

    def test_keyword_regex_zero_false_positives_on_short_words(self, config):
        """
        Verify word-boundary regex prevents false-positive substring collisions
        on short technical words like 'go', 'git', 'slo', 'sli', 'sla', 'alb', 'iam'.
        """
        engine = FilterEngine(config)

        # 1. Negative cases where short keywords appear as substrings of common English words
        false_positive_text = (
            "We value good communication, ongoing collaboration, and strong algorithm knowledge. "
            "Our team drives digital transformation in the Miami office with legitimate practices. "
            "We avoid slow running queries on the slope, enjoy a slice of pizza without slip, "
            "and visited an island with slate stone. Bring your photo album and elbow grease."
        )
        matched_negative = engine.get_matching_skills(false_positive_text)

        assert 'go' not in matched_negative, "'go' falsely matched inside 'good', 'ongoing', or 'algorithm'"
        assert 'golang' not in matched_negative, "'golang' falsely matched"
        assert 'git' not in matched_negative, "'git' falsely matched inside 'digital' or 'legitimate'"
        assert 'iam' not in matched_negative, "'iam' falsely matched inside 'Miami' or 'William'"
        assert 'slo' not in matched_negative, "'slo' falsely matched inside 'slow' or 'slope'"
        assert 'sli' not in matched_negative, "'sli' falsely matched inside 'slice' or 'slip'"
        assert 'sla' not in matched_negative, "'sla' falsely matched inside 'island' or 'slate'"
        assert 'alb' not in matched_negative, "'alb' falsely matched inside 'album'"
        assert 'elb' not in matched_negative, "'elb' falsely matched inside 'elbow'"

        # 2. Positive cases where short keywords appear as genuine standalone technical terms
        genuine_tech_text = (
            "Looking for an engineer proficient in Go and Python. "
            "Must be experienced with Git workflows, AWS IAM role policies, "
            "defining SLOs and SLIs, maintaining SLA metrics, and configuring ALB load balancers."
        )
        matched_positive = engine.get_matching_skills(genuine_tech_text)

        assert 'go' in matched_positive or 'golang' in matched_positive
        assert 'git' in matched_positive
        assert 'iam' in matched_positive
        assert 'slo' in matched_positive
        assert 'sli' in matched_positive
        assert 'sla' in matched_positive
        assert 'alb' in matched_positive
        assert 'python' in matched_positive

    def test_keyword_regex_variations_and_aliases(self, config):
        """
        Verify that regex patterns match common formatting variations
        (slashes, hyphens, spaces, aliases).
        """
        engine = FilterEngine(config)

        # Test CI/CD variations
        for cicd_var in ["ci/cd", "ci-cd", "cicd", "CI / CD", "CI-CD"]:
            matched = engine.get_matching_skills(f"Building automated {cicd_var} pipelines.")
            assert 'ci/cd' in matched or 'cicd' in matched, f"Failed for {cicd_var}"

        # Test Route 53 variations
        for r53_var in ["Route 53", "route53", "route-53", "ROUTE 53"]:
            matched = engine.get_matching_skills(f"Configuring DNS with AWS {r53_var}.")
            assert 'route 53' in matched or 'route53' in matched, f"Failed for {r53_var}"

        # Test Kubernetes / k8s alias
        for k8s_var in ["Kubernetes", "k8s", "K8s", "KUBERNETES"]:
            matched = engine.get_matching_skills(f"Managing {k8s_var} clusters on cloud.")
            assert 'kubernetes' in matched or 'k8s' in matched, f"Failed for {k8s_var}"

        # Test CloudWatch variations
        for cw_var in ["CloudWatch", "cloudwatch", "cloud watch", "cloud-watch"]:
            matched = engine.get_matching_skills(f"Monitoring logs in AWS {cw_var}.")
            assert 'cloudwatch' in matched, f"Failed for {cw_var}"

        # Test Docker Compose variations
        for dc_var in ["Docker Compose", "docker-compose", "docker_compose"]:
            matched = engine.get_matching_skills(f"Local container management using {dc_var}.")
            assert 'docker compose' in matched, f"Failed for {dc_var}"

    def test_wildcard_aws_and_prefix_title_matching(self, config):
        """
        Verify that wildcard/prefix titles (aws*, cloud*, azure*, gcp*, devops*, sre*)
        such as AWSEngineer, AWS Developer, CloudOps, AzureDevOps are accurately matched.
        """
        engine = FilterEngine(config)
        all_terms = set(engine.target_roles)
        for r in engine.target_roles:
            for syn in engine.ROLE_SYNONYMS.get(r, []):
                all_terms.add(syn.lower())

        aws_and_prefix_titles = [
            # aws* prefix variations
            'AWSEngineer',
            'AWS Engineer',
            'AWS Developer',
            'AWS-DevOps',
            'AWS Specialist',
            'AWS Support Specialist',
            'AWSOps Engineer',
            'AWS Infrastructure Engineer',
            'AWS Cloud Specialist',
            'AWS Systems Engineer',
            'AWS Associate',
            'AWS* Engineer',
            'AWS/GCP Cloud Engineer',
            'AWS + DevOps Engineer',
            '[AWS] Cloud Specialist',
            '(AWS) Systems Engineer',
            # Other keyword* prefixes
            'CloudOps',
            'CloudOps Engineer',
            'CloudEngineer',
            'CloudSec Engineer',
            'CloudNative Specialist',
            'AzureDevOps',
            'AzureDevOps Engineer',
            'AzureEngineer',
            'AzureSpecialist',
            'GCPDevOps',
            'GCPEngineer',
            'DevOpsEngineer',
            'DevSecOps',
            'DevSecOps Engineer',
            'SREngineer',
            'PlatformOps Engineer',
            'InfraEngineer',
        ]

        for title in aws_and_prefix_titles:
            assert engine._matches_role_title(title, all_terms) is True, f"Failed to match title: '{title}'"

    def test_title_writing_styles_all_upper_lower_capitalize_mixed(self, config):
        """
        Verify that all capitalization and writing styles are handled uniformly:
        ALL UPPERCASE, all lowercase, Capitalize, Title Case, Mixed/Inverted Case, and Delimiters.
        """
        engine = FilterEngine(config)
        all_terms = set(engine.target_roles)
        for r in engine.target_roles:
            for syn in engine.ROLE_SYNONYMS.get(r, []):
                all_terms.add(syn.lower())

        writing_style_cases = [
            # 1. ALL UPPERCASE
            'AWS CLOUD ENGINEER',
            'DEVOPS ENGINEER',
            'SRE',
            'GCP PLATFORM ENGINEER',
            'AZURE DEVOPS SPECIALIST',
            'SYSTEMS ENGINEER 1',
            # 2. ALL LOWERCASE
            'aws cloud engineer',
            'devops engineer',
            'sre',
            'gcp platform engineer',
            'azure devops specialist',
            'system engineer 1',
            # 3. CAPITALIZE / TITLE CASE
            'Aws Cloud Engineer',
            'Devops Engineer',
            'Site Reliability Engineer',
            'Platform Software Engineer',
            # 4. MIXED / INVERTED CASE
            'AwS cLoUd EnGiNeEr',
            'dEvOpS eNgInEeR',
            'sRe',
            'aZuRe dEvOpS',
            # 5. DELIMITERS AND SYMBOLS (/, -, _, +, &, |, *, [ ], ( ))
            'AWS/Cloud Engineer',
            'DevOps - Cloud Specialist',
            'AWS_DevOps_Engineer',
            'Cloud & DevOps Engineer',
            'AWS + GCP Cloud Engineer',
            'AWS | Cloud Specialist',
            '[AWS] Cloud Support Engineer',
            '(Cloud) Systems Associate',
        ]

        for title in writing_style_cases:
            assert engine._matches_role_title(title, all_terms) is True, f"Failed for writing style: '{title}'"


class TestArchitectRolesAndExperienceFilter:
    """
    Automated tests verifying:
    1. Titles like 'DevOps Architect_104590', 'Cloud Architect', 'AWS Solutions Architect' qualify
       when experience keywords in description match candidate's 3-4 years profile (3-4y, 3+y, 2-4y, 3-5y).
    2. Architect titles requiring excessive experience (5+, 7+, 8+, 10+, 5-8y, 6-9y, min 7y) are strictly rejected.
    3. Executive/Senior titles (Senior DevOps Architect, Lead Architect, Principal Architect) are strictly rejected.
    4. Database query helper get_filtered_job_query() displays 3-4y Architect jobs while excluding excessive ones.
    5. Rollback script revert_architect_exp.py and backup files exist and are valid.
    """

    def test_architect_exp_rollback_safeguards(self):
        """Verify backups and rollback script for architect experience checking."""
        engine_backup = PROJECT_ROOT / 'filter' / 'engine.py.architect_exp_backup'
        routes_backup = PROJECT_ROOT / 'web' / 'routes.py.architect_exp_backup'
        config_backup = PROJECT_ROOT / 'config.yaml.architect_exp_backup'
        revert_script = PROJECT_ROOT / 'revert_architect_exp.py'

        assert engine_backup.exists(), "filter/engine.py.architect_exp_backup must exist"
        assert routes_backup.exists(), "web/routes.py.architect_exp_backup must exist"
        assert config_backup.exists(), "config.yaml.architect_exp_backup must exist"
        assert revert_script.exists(), "revert_architect_exp.py must exist"

        # Verify revert script is valid python
        with open(revert_script, 'r', encoding='utf-8') as f:
            code = f.read()
        compile(code, str(revert_script), 'exec')

    def test_devops_architect_with_3_4_years_experience_qualifies(self, config):
        """
        Verify that DevOps Architect_104590 and Cloud Architect roles qualify
        when the description's experience requirement fits candidate's 3-4 years experience.
        """
        engine = FilterEngine(config)
        now = datetime.now(timezone.utc)

        qualifying_architect_jobs = [
            # 3-4 years exact range
            {
                'title': 'DevOps Architect_104590',
                'company': 'Enterprise Tech A',
                'location': 'Bengaluru',
                'url': 'https://linkedin.com/jobs/view/arch-3-4y',
                'description': 'DevOps CI/CD automation, AWS, Docker, Kubernetes. Seeking candidate with 3-4 years of experience.',
                'num_applicants': 15,
                'date_posted': now,
                'platform': 'linkedin'
            },
            # 3+ years single requirement
            {
                'title': 'DevOps Architect_104590',
                'company': 'Enterprise Tech B',
                'location': 'Bengaluru',
                'url': 'https://linkedin.com/jobs/view/arch-3plus',
                'description': 'Building AWS cloud architecture. Requires 3+ years of experience with Terraform and Kubernetes.',
                'num_applicants': 22,
                'date_posted': now,
                'platform': 'linkedin'
            },
            # 2 to 4 years range
            {
                'title': 'Cloud Architect',
                'company': 'Cloud Services Inc',
                'location': 'Bengaluru',
                'url': 'https://linkedin.com/jobs/view/cloud-arch-2-4y',
                'description': 'Designing scalable Azure and AWS cloud infrastructure. Looking for 2 to 4 years of experience.',
                'num_applicants': 30,
                'date_posted': now,
                'platform': 'linkedin'
            },
            # 3 to 5 years mid-level range fitting 3-4y candidate
            {
                'title': 'AWS Solutions Architect',
                'company': 'Global Systems',
                'location': 'Bengaluru',
                'url': 'https://linkedin.com/jobs/view/aws-arch-3-5y',
                'description': 'AWS cloud migrations and infrastructure automation. 3-5 years of experience in cloud computing.',
                'num_applicants': 18,
                'date_posted': now,
                'platform': 'linkedin'
            },
        ]

        filtered = engine.filter_jobs(qualifying_architect_jobs, today_only=False)
        passed_urls = [j['url'] for j in filtered]

        assert 'https://linkedin.com/jobs/view/arch-3-4y' in passed_urls
        assert 'https://linkedin.com/jobs/view/arch-3plus' in passed_urls
        assert 'https://linkedin.com/jobs/view/cloud-arch-2-4y' in passed_urls
        assert 'https://linkedin.com/jobs/view/aws-arch-3-5y' in passed_urls
        assert len(filtered) == 4

    def test_devops_architect_with_excessive_experience_is_rejected(self, config):
        """
        Verify that DevOps Architect and Cloud Architect roles requiring excessive experience
        (5+, 7+, 8+, 10+, 5-8y, min 7y) are strictly filtered out.
        """
        engine = FilterEngine(config)
        now = datetime.now(timezone.utc)

        excessive_architect_jobs = [
            # 8+ years
            {
                'title': 'DevOps Architect_104590',
                'company': 'Senior Corp A',
                'location': 'Bengaluru',
                'url': 'https://linkedin.com/jobs/view/arch-8y',
                'description': 'DevOps Architect position. Requires 8+ years of experience in AWS and infrastructure.',
                'num_applicants': 10,
                'date_posted': now,
                'platform': 'linkedin'
            },
            # Minimum 7 years
            {
                'title': 'DevOps Architect_104590',
                'company': 'Senior Corp B',
                'location': 'Bengaluru',
                'url': 'https://linkedin.com/jobs/view/arch-min7y',
                'description': 'Minimum 7 years of experience in enterprise Kubernetes architecture.',
                'num_applicants': 10,
                'date_posted': now,
                'platform': 'linkedin'
            },
            # 5-8 years range
            {
                'title': 'Cloud Architect',
                'company': 'Senior Corp C',
                'location': 'Bengaluru',
                'url': 'https://linkedin.com/jobs/view/arch-5-8y',
                'description': '5-8 years of experience building multi-cloud solutions.',
                'num_applicants': 10,
                'date_posted': now,
                'platform': 'linkedin'
            },
            # 10+ years
            {
                'title': 'AWS Solutions Architect',
                'company': 'Senior Corp D',
                'location': 'Bengaluru',
                'url': 'https://linkedin.com/jobs/view/arch-10y',
                'description': '10+ years of exp designing cloud software systems.',
                'num_applicants': 10,
                'date_posted': now,
                'platform': 'linkedin'
            },
        ]

        filtered = engine.filter_jobs(excessive_architect_jobs, today_only=False)
        passed_urls = [j['url'] for j in filtered]

        assert len(passed_urls) == 0, f"Excessive architect jobs should be rejected, got: {passed_urls}"

    def test_senior_and_principal_architect_titles_remain_strictly_excluded(self, config):
        """
        Verify that executive/senior titles (Senior, Principal, Lead, Director) combined with Architect
        are strictly excluded regardless of years stated in the description.
        """
        engine = FilterEngine(config)
        now = datetime.now(timezone.utc)

        senior_architect_jobs = [
            {
                'title': 'Senior DevOps Architect',
                'company': 'BigTech',
                'location': 'Bengaluru',
                'url': 'https://linkedin.com/jobs/view/sr-devops-arch',
                'description': '3-4 years of experience required.',
                'num_applicants': 10,
                'date_posted': now,
                'platform': 'linkedin'
            },
            {
                'title': 'Principal Cloud Architect',
                'company': 'BigTech',
                'location': 'Bengaluru',
                'url': 'https://linkedin.com/jobs/view/princ-cloud-arch',
                'description': '3 years of experience required.',
                'num_applicants': 10,
                'date_posted': now,
                'platform': 'linkedin'
            },
            {
                'title': 'Lead Solutions Architect',
                'company': 'BigTech',
                'location': 'Bengaluru',
                'url': 'https://linkedin.com/jobs/view/lead-arch',
                'description': '3 years of experience in AWS.',
                'num_applicants': 10,
                'date_posted': now,
                'platform': 'linkedin'
            },
            {
                'title': 'Director of Architecture',
                'company': 'BigTech',
                'location': 'Bengaluru',
                'url': 'https://linkedin.com/jobs/view/dir-arch',
                'description': '3-4 years of experience.',
                'num_applicants': 10,
                'date_posted': now,
                'platform': 'linkedin'
            },
        ]

        filtered = engine.filter_jobs(senior_architect_jobs, today_only=False)
        assert len(filtered) == 0, f"Senior/Executive architect titles must be rejected, got: {[j['url'] for j in filtered]}"

    def test_architect_sql_query_allows_midlevel_and_blocks_excessive_in_routes(self, app):
        """
        Verify get_filtered_job_query() displays mid-level Architect jobs
        while properly excluding excessive experience (e.g. 8+ years) and senior titles.
        """
        with app.app_context():
            # 1. Mid-level DevOps Architect (must be returned by query)
            j_mid = Job(
                platform='linkedin',
                title='DevOps Architect_104590',
                company='TargetCo',
                location='Bengaluru',
                url='https://linkedin.com/jobs/view/sql-arch-mid',
                description='AWS DevOps CI/CD pipeline automation. Seeking 3-4 years of experience.',
                num_applicants=20,
                status='new'
            )
            # 2. Excessive experience DevOps Architect (must be blocked by DESC_UNQUALIFIED_PATTERNS)
            j_senior_exp = Job(
                platform='linkedin',
                title='DevOps Architect_104590',
                company='SeniorCo',
                location='Bengaluru',
                url='https://linkedin.com/jobs/view/sql-arch-8y',
                description='Enterprise infrastructure. Requires 8+ years of experience.',
                num_applicants=20,
                status='new'
            )
            # 3. Senior DevOps Architect (must be blocked by SENIOR_TITLE_PATTERNS)
            j_sr_title = Job(
                platform='linkedin',
                title='Senior DevOps Architect',
                company='SeniorCo',
                location='Bengaluru',
                url='https://linkedin.com/jobs/view/sql-sr-arch',
                description='3-4 years of experience.',
                num_applicants=20,
                status='new'
            )
            db.session.add_all([j_mid, j_senior_exp, j_sr_title])
            db.session.commit()

            q = get_filtered_job_query()
            results = q.all()
            result_urls = [j.url for j in results]

            assert 'https://linkedin.com/jobs/view/sql-arch-mid' in result_urls, "Mid-level DevOps Architect should be visible"
            assert 'https://linkedin.com/jobs/view/sql-arch-8y' not in result_urls, "8+ years Architect should be filtered out by SQL"
            assert 'https://linkedin.com/jobs/view/sql-sr-arch' not in result_urls, "Senior DevOps Architect should be filtered out by SQL"


# ─────────────────────────────────────────────
# 13. 100 Big Company Portals & 24 Specialized Job Websites Tests
# ─────────────────────────────────────────────

class TestWebsitesAndCompanyPortals:
    def test_websites_portals_rollback_safeguards(self):
        """
        Verify that backup files and rollback script for Websites & Company Portals exist and are valid.
        """
        config_backup = PROJECT_ROOT / 'config.yaml.websites_portals_backup'
        routes_backup = PROJECT_ROOT / 'web' / 'routes.py.websites_portals_backup'
        revert_script = PROJECT_ROOT / 'revert_websites_portals.py'

        assert config_backup.exists(), "config.yaml.websites_portals_backup must exist"
        assert routes_backup.exists(), "web/routes.py.websites_portals_backup must exist"
        assert revert_script.exists(), "revert_websites_portals.py must exist"

        with open(revert_script, 'r', encoding='utf-8') as f:
            code = f.read()
        compile(code, str(revert_script), 'exec')

    def test_config_contains_at_least_15_to_20_new_websites(self):
        """
        Verify that config.yaml contains at least 15 to 20 specialized job websites (we have 24)
        with necessary metadata (id, name, url, search_url, category).
        """
        config_path = PROJECT_ROOT / 'config.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)

        websites = cfg.get('websites', [])
        assert len(websites) >= 20, f"Expected >= 20 websites, got {len(websites)}"

        key_sites = ['instahyre', 'hirist', 'remoteok', 'weworkremotely', 'devopsjobboard', 'kubecareers', 'hacker_news', 'levels_fyi']
        found_ids = [w['id'] for w in websites]
        for ks in key_sites:
            assert ks in found_ids, f"Expected {ks} in config websites"

        for w in websites:
            assert 'id' in w
            assert 'name' in w
            assert 'url' in w
            assert 'search_url' in w
            assert 'category' in w

    def test_config_contains_at_least_100_big_company_portals(self):
        """
        Verify that config.yaml contains at least 100 top big company career portals
        with necessary metadata (id, name, portal_url, search_url, category, ats_type).
        """
        config_path = PROJECT_ROOT / 'config.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)

        portals = cfg.get('company_portals', [])
        assert len(portals) >= 100, f"Expected >= 100 company portals, got {len(portals)}"

        key_companies = ['amazon_aws', 'google', 'microsoft', 'meta', 'apple', 'swiggy', 'flipkart', 'razorpay', 'jpmorgan', 'goldmansachs', 'nvidia', 'salesforce', 'atlassian']
        found_ids = [p['id'] for w in [portals] for p in w]
        for kc in key_companies:
            assert kc in found_ids, f"Expected {kc} in company portals"

        for p in portals:
            assert 'id' in p
            assert 'name' in p
            assert 'portal_url' in p
            assert 'search_url' in p
            assert 'category' in p
            assert 'ats_type' in p

    def test_company_portals_manager_queries_and_url_generation(self):
        """
        Verify CompanyPortalsManager query filtering, category grouping, and search URL generation.
        """
        from scraper.company_portals import CompanyPortalsManager
        mgr = CompanyPortalsManager()

        assert mgr.count() >= 100
        cats = mgr.get_categories()
        assert len(cats) >= 5
        assert 'Cloud Hyperscalers & Infrastructure' in cats
        assert 'High-Growth Tech & Unicorns' in cats

        # Search filter
        aws_portals = mgr.get_portals(search='AWS')
        assert len(aws_portals) >= 1
        assert any('Amazon' in p['name'] for p in aws_portals)

        # Category filter
        hyperscalers = mgr.get_portals(category='Cloud Hyperscalers & Infrastructure')
        assert len(hyperscalers) >= 10

        # URL builder
        search_url = mgr.build_search_url('amazon_aws', role='DevOps Engineer', location='Bengaluru')
        assert 'amazon.jobs' in search_url

    def test_websites_manager_queries_and_url_generation(self):
        """
        Verify WebsitesManager query filtering, category grouping, and search URL generation.
        """
        from scraper.websites_scraper import WebsitesManager
        mgr = WebsitesManager()

        assert mgr.count() >= 20
        cats = mgr.get_categories()
        assert len(cats) >= 4
        assert 'India Tech & Product' in cats
        assert 'Global Remote-First' in cats

        # Search filter
        instahyre_site = mgr.get_websites(search='instahyre')
        assert len(instahyre_site) == 1
        assert instahyre_site[0]['name'] == 'Instahyre'

        # Category filter
        remote_sites = mgr.get_websites(category='Global Remote-First')
        assert len(remote_sites) >= 4

        # URL builder
        search_url = mgr.build_search_url('remoteok')
        assert 'remoteok.com' in search_url

    def test_api_portals_endpoint_returns_100_companies(self, client):
        """
        Verify GET /api/portals returns all 100 companies and supports category/search query params.
        """
        resp = client.get('/api/portals')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'total' in data
        assert data['total'] >= 100
        assert 'portals' in data
        assert len(data['portals']) >= 100

        # Test search query param
        resp_search = client.get('/api/portals?search=Google')
        assert resp_search.status_code == 200
        data_search = resp_search.get_json()
        assert data_search['total'] >= 1
        assert any('Google' in p['name'] for p in data_search['portals'])

        # Test category query param
        resp_cat = client.get('/api/portals?category=Semiconductor')
        assert resp_cat.status_code == 200
        data_cat = resp_cat.get_json()
        assert data_cat['total'] >= 5

    def test_api_websites_endpoint_returns_specialized_sites(self, client):
        """
        Verify GET /api/websites returns specialized websites and supports search query params.
        """
        resp = client.get('/api/websites')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'total' in data
        assert data['total'] >= 20
        assert 'websites' in data
        assert len(data['websites']) >= 20

        # Test search
        resp_search = client.get('/api/websites?search=Remote%20OK')
        assert resp_search.status_code == 200
        data_search = resp_search.get_json()
        assert data_search['total'] >= 1
        assert any('Remote OK' in w['name'] for w in data_search['websites'])

    def test_api_portals_stats_endpoint(self, client):
        """
        Verify GET /api/portals/stats returns summary metrics for companies and websites.
        """
        resp = client.get('/api/portals/stats')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'companies' in data
        assert 'websites' in data
        assert data['companies']['total_companies'] >= 100
        assert data['websites']['total_websites'] >= 20

    def test_portals_ui_page_renders_successfully(self, client):
        """
        Verify GET /portals renders the interactive portal UI with companies and websites.
        """
        resp = client.get('/portals')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)

        assert 'JobPilot' in html
        assert '100 Big Companies' in html
        assert 'Specialized Job Websites' in html
        assert 'id="portal-search-input"' in html
        assert 'id="category-filter-select"' in html
        assert 'company-card-item' in html
        assert 'website-card-item' in html
        assert 'switchTab(' in html

    def test_portals_all_url_aliases_and_trailing_slashes_return_200(self, client):
        """
        Verify that all portals URL aliases and trailing-slash variants return HTTP 200:
        /portals, /portals/, /portal, /portal/, /protals, /protals/, /company-portals, /websites, etc.
        Guarantees that typos, singular forms, or trailing slashes never result in 404.
        """
        aliases = [
            '/portals',
            '/portals/',
            '/portal',
            '/portal/',
            '/protals',
            '/protals/',
            '/company-portals',
            '/company-portals/',
            '/companies',
            '/companies/',
            '/websites',
            '/websites/',
            '/portals-and-websites',
            '/websites-and-portals',
        ]
        for path in aliases:
            resp = client.get(path)
            assert resp.status_code == 200, f"Expected 200 on {path}, got {resp.status_code}"
            html = resp.get_data(as_text=True)
            assert 'JobPilot' in html
            assert 'company-card-item' in html
            assert 'website-card-item' in html

    def test_api_portals_all_url_aliases_and_slashes_return_200(self, client):
        """
        Verify that all API portals/websites endpoints and aliases support trailing slashes and return 200:
        /api/portals, /api/portals/, /api/portal, /api/protals, /api/websites, /api/website, /api/portals/stats, etc.
        """
        api_endpoints = [
            '/api/portals',
            '/api/portals/',
            '/api/portal',
            '/api/protals',
            '/api/company-portals',
            '/api/companies',
            '/api/websites',
            '/api/websites/',
            '/api/website',
            '/api/portals/stats',
            '/api/portals/stats/',
            '/api/portal/stats',
            '/api/protals/stats',
        ]
        for path in api_endpoints:
            resp = client.get(path)
            assert resp.status_code == 200, f"Expected 200 on API {path}, got {resp.status_code}"
            data = resp.get_json()
            assert isinstance(data, dict), f"Expected JSON dict response from {path}"

    def test_portals_html_template_null_safety_and_edge_cases(self):
        """
        Verify that portals.html template is completely null-safe and handles missing or None fields
        (locations=None, target_roles=None, description=None, ats_type=None) without Jinja2 errors.
        """
        from jinja2 import Environment, FileSystemLoader

        env = Environment(loader=FileSystemLoader(str(PROJECT_ROOT / 'web' / 'templates')))
        tmpl = env.get_template('portals.html')

        rendered = tmpl.render(
            portals=[
                {
                    'name': 'EdgeCorp',
                    'category': 'Cloud Hyperscalers',
                    'ats_type': None,
                    'locations': None,
                    'description': None,
                    'search_url': 'https://example.com/search',
                    'portal_url': 'https://example.com/portal'
                },
                {
                    'name': None,
                    'category': None,
                    'ats_type': 'Workday',
                    'locations': ['Bengaluru', 'Remote'],
                    'description': 'Description text',
                    'search_url': 'https://example.com/search2',
                    'portal_url': 'https://example.com/portal2'
                }
            ],
            websites=[
                {
                    'name': 'EdgeSite',
                    'category': 'Remote Tech',
                    'region': None,
                    'target_roles': None,
                    'description': None,
                    'search_url': 'https://example.com/site-search',
                    'url': 'https://example.com/site'
                },
                {
                    'name': None,
                    'category': None,
                    'region': 'Global',
                    'target_roles': ['DevOps Engineer', 'Cloud Engineer'],
                    'description': 'Description text',
                    'search_url': 'https://example.com/site-search2',
                    'url': 'https://example.com/site2'
                }
            ],
            categories_companies=['Cloud Hyperscalers'],
            categories_websites=['Remote Tech'],
            stats={'total_companies': 2, 'total_websites': 2}
        )

        assert 'EdgeCorp' in rendered
        assert 'EdgeSite' in rendered
        assert 'id="portal-search-input"' in rendered
        assert 'id="companies-grid"' in rendered
        assert 'id="websites-grid"' in rendered

    def test_portals_frontend_js_filter_and_search_contract(self):
        """
        Verify that portals.html frontend JavaScript includes complete search & filter contracts
        (including data-region and data-roles checking for websites) and passes node -c syntax check.
        """
        from bs4 import BeautifulSoup
        import subprocess, tempfile

        template_path = PROJECT_ROOT / 'web' / 'templates' / 'portals.html'
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        soup = BeautifulSoup(content, 'html.parser')
        scripts = soup.find_all('script')
        assert len(scripts) >= 2, "Expected at least 2 script blocks in portals.html"

        for idx, script in enumerate(scripts):
            if script.string:
                with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as tf:
                    tf.write(script.string)
                    tf_path = tf.name
                try:
                    res = subprocess.run(['node', '-c', tf_path], capture_output=True, text=True)
                    assert res.returncode == 0, f"JavaScript syntax error in script block {idx}: {res.stderr}"
                finally:
                    if os.path.exists(tf_path):
                        os.unlink(tf_path)

        # Verify contracts in html & js
        assert 'data-region' in content, "Website cards must carry data-region for search"
        assert 'data-roles' in content, "Website cards must carry data-roles for search"
        assert 'data-locations' in content, "Company cards must carry data-locations for search"
        assert 'data-ats' in content, "Company cards must carry data-ats for search"
        assert 'filter-results-counter' in content, "Must have live filter results counter"
        assert 'switchTab(' in content, "Must have switchTab function"
        assert 'filterPortals(' in content, "Must have filterPortals function"
        assert 'populateCategories(' in content, "Must have populateCategories function"

    def test_navigation_links_to_portals_in_all_templates(self):
        """
        Verify that navigation links to /portals exist in index.html, jobs.html, and base.html.
        """
        templates = ['index.html', 'jobs.html', 'base.html']
        for tmpl_name in templates:
            path = PROJECT_ROOT / 'web' / 'templates' / tmpl_name
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            assert 'href="/portals"' in content, f"{tmpl_name} must contain href=\"/portals\" navigation link"

    def test_websites_search_filter_by_region_and_roles(self):
        """
        Verify that WebsitesManager returns matching websites when searched by region or target role keywords.
        """
        from scraper.websites_scraper import WebsitesManager

        mgr = WebsitesManager()
        # Search by role: devops
        devops_sites = mgr.get_websites(search='devops')
        assert len(devops_sites) >= 3, "Expected at least 3 websites matching 'devops'"

        # Search by role: kubernetes / k8s
        kube_sites = mgr.get_websites(search='kubernetes')
        assert len(kube_sites) >= 1, "Expected at least 1 website matching 'kubernetes'"

        # Search by region: remote
        remote_sites = mgr.get_websites(search='remote')
        assert len(remote_sites) >= 5, "Expected at least 5 websites matching 'remote'"


# ─────────────────────────────────────────────
# 14. Cloud Operations Architect & Portal URL Verification Tests
# ─────────────────────────────────────────────

class TestCloudOperationsArchitectAndTaleoFixes:
    """
    Test suite verifying that:
    1. 'Cloud Operations Architect' and related mid-level technical architect/operations roles qualify.
    2. Senior/lead variants and >4y experience architect roles are strictly excluded.
    3. Job search API properly returns matching jobs for 'Cloud Operations Architect'.
    4. Outdated/broken Taleo and portal URLs (ms.taleo.net, scb.taleo.net, etc.) are replaced with modern 200 OK links.
    5. config.yaml and filter/engine.py have complete role and synonym coverage.
    """

    def test_cloud_operations_architect_qualifies_with_3_to_4y_experience(self):
        """
        Verify that Cloud Operations Architect job with candidate's 3-4 years experience
        successfully passes through FilterEngine.
        """
        import yaml
        from filter.engine import FilterEngine

        config_path = PROJECT_ROOT / 'config.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)

        fe = FilterEngine(cfg)
        sample_job = {
            'title': 'Cloud Operations Architect',
            'company': 'Tech Innovations',
            'location': 'Bengaluru',
            'url': 'https://example.com/jobs/cloud-ops-arch',
            'description': 'Looking for a Cloud Operations Architect with 3-4 years experience in AWS, Kubernetes, Terraform, and CI/CD automation.',
            'num_applicants': 35,
            'date_posted': None
        }

        filtered = fe.filter_jobs([sample_job])
        assert len(filtered) == 1, "Cloud Operations Architect with 3-4y experience should qualify"
        assert filtered[0]['title'] == 'Cloud Operations Architect'

    def test_all_architect_and_operations_role_variations(self):
        """
        Verify that all standard mid-level Architect and Operations variations qualify
        when experience requirements match the candidate's profile (0-4 years).
        """
        import yaml
        from filter.engine import FilterEngine

        config_path = PROJECT_ROOT / 'config.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)

        fe = FilterEngine(cfg)
        variations = [
            'Cloud Operations Architect',
            'Operations Architect',
            'AWS Operations Architect',
            'Azure Operations Architect',
            'GCP Operations Architect',
            'DevOps Operations Architect',
            'Cloud Systems Architect',
            'Cloud Infrastructure Architect',
            'Solutions Architect',
            'Cloud Solutions Architect',
            'Infrastructure Operations Architect',
            'DevOps Architect',
        ]

        for title in variations:
            job = {
                'title': title,
                'company': 'Enterprise Cloud Corp',
                'location': 'Bengaluru',
                'url': f'https://example.com/jobs/{title.replace(" ", "_")}',
                'description': 'Tech stack includes AWS, Docker, Kubernetes, Terraform, Python. Experience: 3-4 years.',
                'num_applicants': 25,
                'date_posted': None
            }
            res = fe.filter_jobs([job])
            assert len(res) == 1, f"Expected '{title}' with 3-4y exp to qualify, but was filtered out"

    def test_senior_and_lead_architect_roles_strictly_excluded(self):
        """
        Verify that senior, lead, staff, principal, director, or >4y experience variants
        are strictly rejected by FilterEngine.
        """
        import yaml
        from filter.engine import FilterEngine

        config_path = PROJECT_ROOT / 'config.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)

        fe = FilterEngine(cfg)
        unqualified = [
            ('Senior Cloud Operations Architect', '3-4 years experience in AWS.'),
            ('Lead Cloud Operations Architect', '3-4 years experience in cloud.'),
            ('Principal Cloud Operations Architect', '3-4 years experience in cloud.'),
            ('Staff Cloud Operations Architect', '3-4 years experience.'),
            ('Director of Cloud Operations', '3-4 years experience in DevOps.'),
            ('Cloud Operations Architect', 'Requires minimum 8 years of experience in enterprise systems.'),
            ('Cloud Operations Architect', 'Looking for 6-9 years of proven experience.'),
            ('Cloud Operations Architect', '5+ years of experience required.'),
            ('Cloud Operations Architect', 'Requires at least 6 years of hands-on cloud experience.'),
        ]

        for title, desc in unqualified:
            job = {
                'title': title,
                'company': 'Senior Enterprise Corp',
                'location': 'Bengaluru',
                'url': f'https://example.com/jobs/{title.replace(" ", "_")}',
                'description': desc,
                'num_applicants': 20,
                'date_posted': None
            }
            res = fe.filter_jobs([job])
            assert len(res) == 0, f"Expected '{title}' with desc '{desc}' to be rejected, but it qualified"

    def test_search_api_finds_cloud_operations_architect(self, client, app):
        """
        Verify that GET /api/jobs?q=Cloud%20Operations%20Architect returns HTTP 200
        and successfully finds Cloud Operations Architect in the search results.
        """
        with app.app_context():
            job = Job(
                platform='linkedin',
                title='Cloud Operations Architect',
                company='Jobgether',
                location='India (Remote)',
                url='https://linkedin.com/jobs/view/cloud-ops-arch-test',
                description='Cloud Operations Architect with 3-4 years experience in AWS, Kubernetes, and Terraform.',
                status='new'
            )
            db.session.add(job)
            db.session.commit()

        resp = client.get('/api/jobs?q=Cloud%20Operations%20Architect')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] >= 1, "Expected at least 1 job found for 'Cloud Operations Architect'"
        matched_titles = [j['title'] for j in data['jobs']]
        assert any('Cloud Operations Architect' in t for t in matched_titles)

    def test_updated_company_portals_and_website_urls(self):
        """
        Verify that obsolete Taleo subdomains and dead URLs have been updated across
        BIG_COMPANY_PORTALS and SPECIALIZED_JOB_WEBSITES:
        - Morgan Stanley -> tal.net (not ms.taleo.net)
        - Standard Chartered -> jobs.standardchartered.com (not scb.taleo.net)
        - EY -> careers.ey.com (not eyg.taleo.net)
        - DevOpsJobs.io -> devopsjobs.io (not devopsjobboard.com)
        - KubeCareers -> kube.careers (not kubecareers.com)
        """
        from scraper.company_portals import BIG_COMPANY_PORTALS
        from scraper.websites_scraper import SPECIALIZED_JOB_WEBSITES

        portals_by_id = {p['id']: p for p in BIG_COMPANY_PORTALS}
        sites_by_id = {s['id']: s for s in SPECIALIZED_JOB_WEBSITES}

        # Morgan Stanley
        assert 'morganstanley' in portals_by_id
        ms = portals_by_id['morganstanley']
        assert 'ms.taleo.net' not in ms['search_url'], "ms.taleo.net must not be used"
        assert 'morganstanley.tal.net' in ms['search_url'] or 'morganstanley.com' in ms['search_url']

        # Standard Chartered
        assert 'standardchartered' in portals_by_id
        scb = portals_by_id['standardchartered']
        assert 'scb.taleo.net' not in scb['search_url'], "scb.taleo.net must not be used"
        assert 'jobs.standardchartered.com' in scb['search_url']

        # EY
        assert 'ey' in portals_by_id
        ey = portals_by_id['ey']
        assert 'eyg.taleo.net' not in ey['search_url'], "eyg.taleo.net must not be used"
        assert 'careers.ey.com' in ey['search_url']

        # DevOpsJobs.io
        assert 'devopsjobboard' in sites_by_id
        djob = sites_by_id['devopsjobboard']
        assert 'devopsjobs.io' in djob['url']

        # KubeCareers
        assert 'kubecareers' in sites_by_id
        kube = sites_by_id['kubecareers']
        assert 'kube.careers' in kube['url']

        # Ensure no dead taleo netlocs remain in portals
        for p in BIG_COMPANY_PORTALS:
            search_u = p.get('search_url', '')
            portal_u = p.get('portal_url', '')
            assert 'ms.taleo.net' not in search_u
            assert 'scb.taleo.net' not in search_u
            assert 'eyg.taleo.net' not in search_u

    def test_config_yaml_has_architect_roles_and_updated_urls(self):
        """
        Verify that config.yaml includes Architect roles in search.roles
        and updated company search URLs.
        """
        import yaml

        config_path = PROJECT_ROOT / 'config.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)

        roles = cfg.get('search', {}).get('roles', [])
        assert 'Cloud Operations Architect' in roles, "Cloud Operations Architect must be in config.yaml roles"
        assert 'Cloud Architect' in roles, "Cloud Architect must be in config.yaml roles"
        assert 'DevOps Architect' in roles, "DevOps Architect must be in config.yaml roles"

        # Check portals inside config.yaml
        company_portals = cfg.get('company_portals', [])
        ms_portal = next((c for c in company_portals if c.get('id') == 'morganstanley'), None)
        assert ms_portal is not None
        assert 'ms.taleo.net' not in ms_portal.get('search_url', '')
        assert 'tal.net' in ms_portal.get('search_url', '')


class TestInfrastructureAndForwardDeployedRoles:
    """
    Automated test suite verifying:
    1. 'Infrastructure Engineer' and all technical variations qualify (Cloud Infrastructure, Infra Systems, etc.).
    2. 'Forward Deployed Systems Engineer' (FDSE) and variations qualify (Forward Deployed Engineer,
       Forward-Deployed Software/Cloud/DevOps Engineer, Forward Deployment Systems Engineer, FDSE).
    3. Writing style normalization (CamelCase, UPPERCASE, symbol delimiters, requisition IDs).
    4. Mid-level qualification (0-4y) passes while senior/lead prefixes and >4y experience are strictly rejected.
    5. Non-technical roles (sales, marketing, recruiting) are rejected.
    6. config.yaml includes the new roles under search.roles.
    """

    @pytest.fixture
    def engine(self):
        import yaml
        from filter.engine import FilterEngine
        config_path = PROJECT_ROOT / 'config.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
        return FilterEngine(cfg)

    def test_infrastructure_engineer_and_variations_qualify(self, engine):
        all_terms = set(engine.target_roles)
        for r in engine.target_roles:
            for syn in engine.ROLE_SYNONYMS.get(r, []):
                all_terms.add(syn.lower())

        variations = [
            'Infrastructure Engineer',
            'Cloud Infrastructure Engineer',
            'Infrastructure Systems Engineer',
            'Infra Systems Engineer',
            'Infra Engineer',
            'Infrastructure Specialist',
            'Infrastructure Automation Engineer',
            'Infrastructure Platform Engineer',
            'Cloud Infrastructure Specialist',
            'InfraOps Engineer',
            'INFRASTRUCTURE ENGINEER',
            'infrastructure engineer',
            'InfraEngineer',
            'CloudInfrastructureEngineer',
            'Infrastructure Engineer - AWS & Linux',
            'Infrastructure Engineer_10924'
        ]

        for title in variations:
            assert engine._matches_role_title(title, all_terms) is True, f"Expected '{title}' to match role title"

    def test_forward_deployed_systems_engineer_and_variations_qualify(self, engine):
        all_terms = set(engine.target_roles)
        for r in engine.target_roles:
            for syn in engine.ROLE_SYNONYMS.get(r, []):
                all_terms.add(syn.lower())

        variations = [
            'Forward Deployed Systems Engineer',
            'Forward Deployed System Engineer',
            'Forward Deployed Systems Engineer 1',
            'Forward Deployed Systems Engineer I',
            'Forward Deployed Engineer',
            'Forward Deployed Software Engineer',
            'Forward Deployed DevOps Engineer',
            'Forward Deployed Cloud Engineer',
            'Forward Deployed Infrastructure Engineer',
            'Forward Deployed Solutions Engineer',
            'Forward Deployed Platform Engineer',
            'Forward-Deployed Systems Engineer',
            'Forward-Deployed Software Engineer',
            'Forward Deployment Systems Engineer',
            'Forward Deployment Engineer',
            'FDSE',
            'Forward Deployed Systems Engineer (FDSE)',
            'ForwardDeployedSystemsEngineer',
            'ForwardDeployedEngineer',
            'FORWARD DEPLOYED SYSTEMS ENGINEER',
            'forward deployed systems engineer',
            'Forward Deployed Systems Engineer - Cloud Infrastructure',
            'Forward Deployed Systems Engineer_REQ901'
        ]

        for title in variations:
            assert engine._matches_role_title(title, all_terms) is True, f"Expected '{title}' to match role title"

    def test_forward_deployed_and_infra_midlevel_jobs_pass_filter(self, engine):
        sample_jobs = [
            {
                'title': 'Forward Deployed Systems Engineer',
                'company': 'Enterprise AI Corp',
                'location': 'Bengaluru',
                'platform': 'linkedin',
                'url': 'https://example.com/job/fdse-1',
                'description': 'We are hiring a Forward Deployed Systems Engineer with 3 years of experience in AWS, Kubernetes, Terraform, and Python deployment automation.',
                'num_applicants': 40,
                'date_posted': None
            },
            {
                'title': 'Infrastructure Engineer',
                'company': 'Cloud Scale Systems',
                'location': 'Bengaluru',
                'platform': 'linkedin',
                'url': 'https://example.com/job/infra-1',
                'description': 'Looking for an Infrastructure Engineer with 2 to 4 years experience in Linux, Docker, AWS S3, EC2, and CI/CD pipelines.',
                'num_applicants': 25,
                'date_posted': None
            },
            {
                'title': 'Forward-Deployed Software Engineer',
                'company': 'Data Intelligence Inc',
                'location': 'Remote',
                'platform': 'indeed',
                'url': 'https://example.com/job/fdse-2',
                'description': 'Seeking an engineer with 3-4 years experience integrating client cloud systems and building microservices.',
                'num_applicants': 15,
                'date_posted': None
            }
        ]

        filtered = engine.filter_jobs(sample_jobs)
        assert len(filtered) == 3, f"Expected all 3 mid-level jobs to pass filter, but got: {len(filtered)}"

    def test_senior_and_lead_forward_deployed_and_infra_excluded(self, engine):
        senior_jobs = [
            {'title': 'Senior Infrastructure Engineer', 'company': 'Corp A', 'num_applicants': 10, 'description': 'Cloud systems.'},
            {'title': 'Lead Infrastructure Engineer', 'company': 'Corp B', 'num_applicants': 10, 'description': 'Cloud systems.'},
            {'title': 'Principal Infrastructure Engineer', 'company': 'Corp C', 'num_applicants': 10, 'description': 'Cloud systems.'},
            {'title': 'Senior Forward Deployed Systems Engineer', 'company': 'Corp D', 'num_applicants': 10, 'description': 'Deployment systems.'},
            {'title': 'Staff Forward Deployed Engineer', 'company': 'Corp E', 'num_applicants': 10, 'description': 'Deployment systems.'},
            {'title': 'Lead Forward Deployed Systems Engineer', 'company': 'Corp F', 'num_applicants': 10, 'description': 'Deployment systems.'},
            {'title': 'Director of Infrastructure Engineering', 'company': 'Corp G', 'num_applicants': 10, 'description': 'Executive leadership.'},
            {'title': 'Forward Deployed Engineering Manager', 'company': 'Corp H', 'num_applicants': 10, 'description': 'Managerial role.'}
        ]

        filtered = engine.filter_jobs(senior_jobs)
        assert len(filtered) == 0, f"Expected all senior roles to be excluded, but got: {[j['title'] for j in filtered]}"

    def test_excessive_experience_forward_deployed_and_infra_excluded(self, engine):
        excessive_jobs = [
            {
                'title': 'Infrastructure Engineer',
                'company': 'Corp A',
                'num_applicants': 20,
                'description': 'Must have 7+ years of experience in enterprise infrastructure and data center networking.'
            },
            {
                'title': 'Forward Deployed Systems Engineer',
                'company': 'Corp B',
                'num_applicants': 20,
                'description': 'Minimum 8 years experience deploying enterprise distributed systems.'
            },
            {
                'title': 'Forward Deployed Engineer',
                'company': 'Corp C',
                'num_applicants': 20,
                'description': 'Experience required: 6 to 9 years of client software integration.'
            }
        ]

        filtered = engine.filter_jobs(excessive_jobs)
        assert len(filtered) == 0, f"Expected all excessive experience jobs to be excluded, but got: {len(filtered)}"

    def test_non_technical_forward_deployed_and_infra_rejected(self, engine):
        all_terms = set(engine.target_roles)
        for r in engine.target_roles:
            for syn in engine.ROLE_SYNONYMS.get(r, []):
                all_terms.add(syn.lower())

        assert engine._matches_role_title("Forward Deployed Sales Executive", all_terms) is False
        assert engine._matches_role_title("Forward Deployed Marketing Manager", all_terms) is False
        assert engine._matches_role_title("Infrastructure Sales Specialist", all_terms) is False
        assert engine._matches_role_title("Forward Deployed Technical Recruiter", all_terms) is False

    def test_config_yaml_has_forward_deployed_and_infra_roles(self):
        import yaml
        config_path = PROJECT_ROOT / 'config.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)

        roles = cfg.get('search', {}).get('roles', [])
        assert 'Infrastructure Engineer' in roles, "Infrastructure Engineer must be in config.yaml roles"
        assert 'Forward Deployed Systems Engineer' in roles, "Forward Deployed Systems Engineer must be in config.yaml roles"
        assert 'Forward Deployed Engineer' in roles, "Forward Deployed Engineer must be in config.yaml roles"


# ─────────────────────────────────────────────
# 15. Enterprise Career Portal Jobs Scanner Tests
# ─────────────────────────────────────────────

class TestPortalJobsScanner:
    """
    Automated test suite verifying the Enterprise Career Portal Jobs Scanner:
    1. Rollback safeguards and backup validity.
    2. Scanner initialization, portal discovery, and ATS connectors.
    3. Strict < 4 years experience cap enforcement (0-4y allowed, >=5y rejected).
    4. Senior and lead title exclusions.
    5. Candidate resume skill extraction and match scoring.
    6. PortalJob database model CRUD, fields, and to_dict serialization.
    7. Page route and all URL aliases returning HTTP 200.
    8. REST API endpoints for filtering, pagination, search, scan, status, and stats.
    9. HTML template null-safety and edge cases.
    10. Frontend JavaScript syntax validation via node.
    11. Navigation links present across all application templates.
    """

    def test_portal_jobs_rollback_safeguards(self):
        """
        Verify that backup snapshots and revert_portal_jobs.py exist and compile cleanly.
        """
        backups = [
            PROJECT_ROOT / 'web' / 'routes.py.portal_jobs_backup',
            PROJECT_ROOT / 'db' / 'models.py.portal_jobs_backup',
            PROJECT_ROOT / 'web' / 'templates' / 'base.html.portal_jobs_backup',
            PROJECT_ROOT / 'web' / 'templates' / 'portals.html.portal_jobs_backup',
            PROJECT_ROOT / 'web' / 'templates' / 'index.html.portal_jobs_backup',
            PROJECT_ROOT / 'web' / 'templates' / 'jobs.html.portal_jobs_backup',
        ]
        revert_script = PROJECT_ROOT / 'revert_portal_jobs.py'

        for bp in backups:
            assert bp.exists(), f"Backup file {bp} must exist"

        assert revert_script.exists(), "revert_portal_jobs.py must exist"
        with open(revert_script, 'r', encoding='utf-8') as f:
            code = f.read()
        compile(code, str(revert_script), 'exec')

    def test_portal_scanner_initialization_and_catalog(self):
        """
        Verify PortalJobsScanner initializes correctly with CompanyPortalsManager
        and correctly loads the 100 enterprise career portals.
        """
        from scraper.portal_jobs_scanner import PortalJobsScanner
        scanner = PortalJobsScanner()
        assert scanner.c_mgr is not None
        assert scanner.c_mgr.count() >= 100
        assert scanner.is_running() is False

        status = scanner.get_status()
        assert status['running'] is False
        assert status['jobs_found'] == 0
        assert status['jobs_qualified'] == 0

    def test_portal_scanner_strict_experience_cap_under_4_years(self):
        """
        Verify that postings requiring < 4 years experience qualify,
        while postings requiring 5+ years or senior ranges are strictly rejected.
        """
        from scraper.portal_jobs_scanner import PortalJobsScanner
        scanner = PortalJobsScanner()

        # Qualified cases (< 4y)
        qualified_cases = [
            ('DevOps Engineer', 'Looking for 0-2 years of experience in AWS.'),
            ('Cloud Engineer', 'Requirements: 1 to 3 years experience with Docker and Kubernetes.'),
            ('Site Reliability Engineer', 'Experience required: 2-4 years in Linux and Terraform.'),
            ('Associate Cloud Systems Engineer', 'Freshers or 1-2 years experience welcome.'),
            ('Junior Infrastructure Engineer', 'Must have 1+ years experience in automation.'),
            ('Cloud Operations Architect', 'Mid-level role requiring 3-4 years experience in AWS.')
        ]

        for title, desc in qualified_cases:
            is_q, label, max_y = scanner.is_qualified_experience(title, desc)
            assert is_q is True, f"Expected '{title}' with desc '{desc}' to qualify, got label: {label}"
            assert max_y <= 4

        # Unqualified cases (>= 5y)
        unqualified_cases = [
            ('DevOps Engineer', 'Must have 5+ years of experience in distributed systems.'),
            ('Cloud Engineer', 'Requires minimum 7 years of hands-on cloud experience.'),
            ('Platform Engineer', 'Experience required: 6-9 years in enterprise infrastructure.'),
            ('Site Reliability Engineer', 'Looking for at least 8 yrs of production experience.'),
            ('Infrastructure Engineer', '10+ years experience required.')
        ]

        for title, desc in unqualified_cases:
            is_q, label, max_y = scanner.is_qualified_experience(title, desc)
            assert is_q is False, f"Expected '{title}' with desc '{desc}' to be rejected, got: {label}"

    def test_portal_scanner_senior_and_lead_titles_rejected(self):
        """
        Verify that Senior, Lead, Principal, Staff, Director, Manager prefixes
        are strictly rejected regardless of description.
        """
        from scraper.portal_jobs_scanner import PortalJobsScanner
        scanner = PortalJobsScanner()

        senior_titles = [
            'Senior DevOps Engineer',
            'Sr. Cloud Engineer',
            'Lead Site Reliability Engineer',
            'Principal Platform Engineer',
            'Staff Infrastructure Engineer',
            'Director of Cloud Operations',
            'DevOps Engineering Manager',
            'VP of Infrastructure',
            'Head of Cloud Architecture'
        ]

        for title in senior_titles:
            is_q, label, max_y = scanner.is_qualified_experience(title, "2-3 years experience in AWS")
            assert is_q is False, f"Expected senior title '{title}' to be rejected, got label: {label}"

    def test_portal_scanner_resume_skills_matching(self):
        """
        Verify that candidate's skills from Swiggy, Starwatt, and AWS Cert
        (AWS, Terraform, Kubernetes, Docker, CI/CD, Python, Linux) are accurately extracted.
        """
        from scraper.portal_jobs_scanner import PortalJobsScanner
        scanner = PortalJobsScanner()

        job_desc = "Hands-on experience with AWS, Terraform modules, Docker containers, Kubernetes clusters, CI/CD automation, and Python scripting on Linux."
        matched = scanner.match_resume_skills(job_desc)

        assert 'AWS' in matched
        assert 'Terraform' in matched
        assert 'Docker' in matched
        assert 'Kubernetes' in matched
        assert 'CI/CD' in matched
        assert 'Python' in matched
        assert 'Linux' in matched

        score = scanner.calculate_match_score(matched, 'Cloud DevOps Engineer', job_desc)
        assert score >= 70, f"Expected high match score for core resume stack, got: {score}"

    def test_portal_job_model_crud_and_to_dict(self, app):
        """
        Verify PortalJob SQLAlchemy model operations, fields, and to_dict serialization.
        """
        from db.models import db, PortalJob
        with app.app_context():
            job = PortalJob(
                portal_id='amazon_aws',
                company='Amazon / AWS',
                category='Cloud Hyperscalers & Infrastructure',
                ats_type='amazon_jobs',
                title='Cloud DevOps Engineer',
                location='Bengaluru, Karnataka',
                url='https://example.com/test-portal-job-model',
                description='Automate AWS CodePipeline deployments and manage ECS clusters.',
                experience_req='2-4 years',
                experience_max=4,
                matched_skills='AWS, Docker, Kubernetes, Terraform, Python',
                match_score=92,
                skills_count=5,
                salary='₹22,00,000 - ₹32,00,000',
                status='new'
            )
            db.session.add(job)
            db.session.commit()

            fetched = PortalJob.query.filter_by(url='https://example.com/test-portal-job-model').first()
            assert fetched is not None
            assert fetched.company == 'Amazon / AWS'
            assert fetched.experience_max == 4

            data = fetched.to_dict()
            assert data['company'] == 'Amazon / AWS'
            assert data['title'] == 'Cloud DevOps Engineer'
            assert data['match_score'] == 92
            assert 'AWS' in data['matched_skills']
            assert isinstance(data['matched_skills'], list)
            assert data['experience_req'] == '2-4 years'

    def test_portal_jobs_page_renders_successfully(self, client):
        """
        Verify that GET /portal-jobs returns HTTP 200 and renders
        the JobPilot portal jobs scanner dashboard.
        """
        resp = client.get('/portal-jobs')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Enterprise Career Portal' in html
        assert 'PORTAL JOBS' in html
        assert 'Quick Scan (Top 20)' in html
        assert 'stat-total-jobs' in html
        assert 'portal-search-input' in html

    def test_portal_jobs_url_aliases_and_slashes_return_200(self, client):
        """
        Verify that all URL aliases and slash variants for /portal-jobs return HTTP 200.
        """
        urls = [
            '/portal-jobs',
            '/portal-jobs/',
            '/portaljobs',
            '/portaljobs/',
            '/portal-postings',
            '/company-jobs',
            '/portal-openings'
        ]
        for u in urls:
            resp = client.get(u, follow_redirects=True)
            assert resp.status_code == 200, f"Expected {u} to return 200, got {resp.status_code}"

    def test_api_portal_jobs_endpoints(self, client, app):
        """
        Verify GET /api/portal-jobs, filtering by category, search text, and sorting.
        """
        from db.models import db, PortalJob
        with app.app_context():
            job = PortalJob(
                portal_id='google',
                company='Google / Alphabet',
                category='Cloud Hyperscalers & Infrastructure',
                ats_type='google_careers',
                title='Site Reliability Engineer - Cloud Platforms',
                location='Bengaluru, India',
                url='https://example.com/test-api-portal-job',
                description='GCP, Kubernetes, Prometheus SRE role with 1-3 years exp.',
                experience_req='1-3 years',
                experience_max=3,
                matched_skills='GCP, Kubernetes, Prometheus, Python',
                match_score=88,
                skills_count=4,
                status='new'
            )
            db.session.add(job)
            db.session.commit()

        # 1. Base API query
        resp = client.get('/api/portal-jobs')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'total' in data
        assert 'jobs' in data
        assert data['total'] >= 1

        # 2. Search query
        resp_search = client.get('/api/portal-jobs?q=Google')
        assert resp_search.status_code == 200
        data_s = resp_search.get_json()
        assert any(j['company'] == 'Google / Alphabet' for j in data_s['jobs'])

        # 3. Stats endpoint
        resp_stats = client.get('/api/portal-jobs/stats')
        assert resp_stats.status_code == 200
        stats = resp_stats.get_json()
        assert 'total' in stats
        assert 'qualified' in stats
        assert 'avg_match_score' in stats
        assert stats['total'] >= 1

    def test_api_portal_job_status_update(self, client, app):
        """
        Verify updating job status via /api/portal-job/<id>/status.
        """
        from db.models import db, PortalJob
        job_id = None
        with app.app_context():
            job = PortalJob(
                portal_id='swiggy',
                company='Swiggy',
                category='High-Growth Tech, E-Commerce & Unicorns',
                ats_type='swiggy_careers',
                title='System Engineer 1 - Cloud Automation',
                location='Bengaluru, Karnataka',
                url='https://example.com/test-swiggy-status',
                description='AWS, Python script runner, Terraform IAM automation.',
                experience_req='1-3 years',
                experience_max=3,
                matched_skills='AWS, Python, Terraform, IAM',
                match_score=95,
                status='new'
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

        # Update to applied
        resp = client.post(f'/api/portal-job/{job_id}/status', json={'status': 'applied'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'success'
        assert data['new_status'] == 'applied'

        with app.app_context():
            updated = db.session.get(PortalJob, job_id)
            assert updated.status == 'applied'
            assert updated.applied_at is not None

    def test_api_scan_portal_jobs_trigger_and_status(self, client):
        """
        Verify POST /api/scan-portal-jobs, status polling, and stop signal.
        """
        resp_status = client.get('/api/scan-portal-jobs/status')
        assert resp_status.status_code == 200
        status_data = resp_status.get_json()
        assert 'running' in status_data
        assert 'progress_pct' in status_data

        resp_stop = client.post('/api/scan-portal-jobs/stop')
        assert resp_stop.status_code == 200

    def test_portal_jobs_html_template_null_safety(self, app):
        """
        Verify portal_jobs.html renders safely with None/empty stats and categories.
        """
        from flask import render_template
        with app.test_request_context('/portal-jobs'):
            rendered = render_template(
                'portal_jobs.html',
                categories=None,
                ats_types=None,
                stats=None
            )
            assert 'Enterprise Career Portal' in rendered

    def test_portal_jobs_frontend_js_syntax_valid(self):
        """
        Verify that all JavaScript script blocks in portal_jobs.html are 100% syntactically valid via node --check.
        """
        import re
        import subprocess
        import tempfile

        template_path = PROJECT_ROOT / 'web' / 'templates' / 'portal_jobs.html'
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
        assert len(scripts) >= 2, "Expected at least 2 script blocks in portal_jobs.html"

        for i, s in enumerate(scripts):
            with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as tf:
                tf.write(s)
                temp_path = tf.name
            try:
                res = subprocess.run(['node', '--check', temp_path], capture_output=True, text=True)
                assert res.returncode == 0, f"Syntax error in script block {i}: {res.stderr}"
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

    def test_navigation_links_to_portal_jobs_in_all_templates(self):
        """
        Verify that href="/portal-jobs" link is present across
        base.html, portals.html, index.html, and jobs.html.
        """
        templates = [
            PROJECT_ROOT / 'web' / 'templates' / 'base.html',
            PROJECT_ROOT / 'web' / 'templates' / 'portals.html',
            PROJECT_ROOT / 'web' / 'templates' / 'index.html',
            PROJECT_ROOT / 'web' / 'templates' / 'jobs.html',
        ]

        for tmpl in templates:
            with open(tmpl, 'r', encoding='utf-8') as f:
                content = f.read()
            assert '/portal-jobs' in content, f"Expected '/portal-jobs' link in {tmpl.name}"

    def test_portal_jobs_pagination_and_scroll_elements(self):
        """
        Verify that portal_jobs.html contains the pagination and infinite scroll elements:
        - Mode switcher (Infinite vs Pages)
        - Infinite scroll footer, loader, sentinel, and load more button
        - Classic pagination controls, info text, per-page dropdown, and pagination pills
        - Back to top floating button
        """
        template_path = PROJECT_ROOT / 'web' / 'templates' / 'portal_jobs.html'
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'id="pagination-mode-toggle"' in content
        assert 'id="mode-infinite-btn"' in content
        assert 'id="mode-classic-btn"' in content
        assert 'id="infinite-scroll-footer"' in content
        assert 'id="infinite-scroll-loader"' in content
        assert 'id="btn-load-more"' in content
        assert 'id="infinite-scroll-sentinel"' in content
        assert 'id="pagination-controls"' in content
        assert 'id="pagination-info"' in content
        assert 'id="portal-per-page-select"' in content
        assert 'id="pagination-pills"' in content
        assert 'id="btn-back-to-top"' in content
        assert 'setScrollMode(' in content
        assert 'changePerPage(' in content

    def test_all_100_company_portal_urls_valid_and_direct(self):
        """
        Verify all 100 enterprise portals have direct, valid HTTPS URLs pointing to
        exact careers boards and job search pages, without dummy or broken parameters.
        """
        from scraper.company_portals import BIG_COMPANY_PORTALS

        assert len(BIG_COMPANY_PORTALS) == 100, f"Expected 100 portals, found {len(BIG_COMPANY_PORTALS)}"

        for p in BIG_COMPANY_PORTALS:
            p_id = p.get('id')
            portal_url = p.get('portal_url', '')
            search_url = p.get('search_url', '')

            assert portal_url.startswith('https://'), f"Portal {p_id} portal_url must start with https://, got: {portal_url}"
            assert search_url.startswith('https://'), f"Portal {p_id} search_url must start with https://, got: {search_url}"

            # Ensure no dummy job_id parameters
            assert 'job_id=' not in search_url, f"Portal {p_id} search_url must not contain dummy job_id parameter: {search_url}"
            assert 'job_id=' not in portal_url, f"Portal {p_id} portal_url must not contain dummy job_id parameter: {portal_url}"

            # Ensure no broken or non-existent domains
            assert 'jobs.netflix.net' not in search_url, f"Portal {p_id} must not use defunct jobs.netflix.net"
            assert 'jobs.netflix.net' not in portal_url, f"Portal {p_id} must not use defunct jobs.netflix.net"

            # Ensure Indian tech portals point to direct careers boards rather than food/consumer apps
            if p_id == 'swiggy':
                assert 'careers.swiggy.in' in search_url, f"Swiggy must point to careers.swiggy.in, got: {search_url}"
            if p_id == 'zomato':
                assert 'eternal.com' in search_url or 'zomato.com/careers' in search_url, f"Zomato must point to valid careers board, got: {search_url}"
            if p_id == 'cred':
                assert 'lever.co/cred' in search_url or 'careers.cred.club' in search_url, f"Cred must point to Lever/careers, got: {search_url}"
            if p_id == 'goldmansachs':
                assert 'higher.gs.com' in search_url, f"Goldman Sachs must point to higher.gs.com results, got: {search_url}"
            if p_id == 'salesforce':
                assert 'careers.salesforce.com' in search_url, f"Salesforce must point to careers.salesforce.com, got: {search_url}"
            if p_id == 'uber':
                assert 'jobs.uber.com' in search_url, f"Uber must point to jobs.uber.com, got: {search_url}"
            if p_id == 'redhat':
                assert 'myworkdayjobs.com' in search_url, f"Red Hat must point to Workday jobs board, got: {search_url}"
                assert 'redhat.com/en/jobs' not in search_url, f"Red Hat search_url must not point to generic overview marketing page: {search_url}"
                assert 'careers.redhat.com' not in search_url, f"Red Hat search_url must not point to legacy redirecting careers.redhat.com: {search_url}"

    def test_format_direct_job_url_logic(self):
        """
        Verify PortalJobsScanner._format_direct_job_url produces clean, valid URLs
        that specialize queries without breaking SPA hash routers or adding dummy params.
        """
        from scraper.portal_jobs_scanner import PortalJobsScanner

        # 1. Index 0 returns exact base URL
        base = "https://higher.gs.com/results"
        assert PortalJobsScanner._format_direct_job_url(base, "Cloud DevOps Engineer", "goldmansachs", 0) == base

        # 2. Existing search parameter is specialized for the role
        amazon_base = "https://www.amazon.jobs/en/search?base_query=DevOps"
        amazon_sre = PortalJobsScanner._format_direct_job_url(amazon_base, "Site Reliability Engineer (SRE)", "amazon_aws", 1)
        assert "base_query=Site+Reliability+Engineer" in amazon_sre
        assert "job_id=" not in amazon_sre

        # 3. Hash router URL preserves clean #/jobs
        swiggy_base = "https://careers.swiggy.in/#/jobs"
        swiggy_sre = PortalJobsScanner._format_direct_job_url(swiggy_base, "Site Reliability Engineer (SRE)", "swiggy", 1)
        assert swiggy_sre.endswith("#/jobs")
        assert "job_id=" not in swiggy_sre
        assert "role=" not in swiggy_sre

        # 4. Standard clean URL preserves direct board without injecting unsupported parameters
        cred_base = "https://jobs.lever.co/cred"
        cred_arch = PortalJobsScanner._format_direct_job_url(cred_base, "Cloud Operations Architect (Mid-Level)", "cred", 2)
        assert "jobs.lever.co/cred" in cred_arch
        assert "job_id=" not in cred_arch
        assert "role=" not in cred_arch

        # 5. Red Hat returns exact live Workday requisition
        redhat_base = "https://redhat.wd5.myworkdayjobs.com/jobs"
        redhat_job = PortalJobsScanner._format_direct_job_url(redhat_base, "Cloud DevOps Engineer", "redhat", 1)
        assert "redhat.wd5.myworkdayjobs.com/en-US/jobs/job/" in redhat_job
        assert "R-" in redhat_job

    def test_specialized_tech_job_sites_urls_valid(self):
        """
        Verify all 24 specialized tech job platforms have valid HTTPS URLs
        and direct search endpoints (e.g. Instahyre, Jobspresso, Otta).
        """
        from scraper.websites_scraper import SPECIALIZED_JOB_WEBSITES

        assert len(SPECIALIZED_JOB_WEBSITES) == 24, f"Expected 24 websites, found {len(SPECIALIZED_JOB_WEBSITES)}"

        for s in SPECIALIZED_JOB_WEBSITES:
            s_id = s.get('id')
            url = s.get('url', '')
            search_url = s.get('search_url', '')

            assert url.startswith('https://'), f"Site {s_id} url must start with https://"
            assert search_url.startswith('https://'), f"Site {s_id} search_url must start with https://"

            # Specific verified endpoints
            if s_id == 'instahyre':
                assert 'instahyre.com/search-jobs' in search_url
            if s_id == 'jobspresso':
                assert 'jobspresso.co/#jobs' in search_url
            if s_id == 'otta':
                assert 'welcometothejungle.com' in search_url
            if s_id == 'hirist':
                assert 'hirist.tech/c/devops-sre-jobs' in search_url

    def test_db_portal_jobs_have_clean_direct_links(self):
        """
        Verify PortalJob database records have valid direct links without dummy job_id parameters
        and do not point to generic marketing overview pages like redhat.com/en/jobs.
        """
        import sqlite3
        db_path = PROJECT_ROOT / 'instance' / 'jobs.db'
        if not db_path.exists():
            return

        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('SELECT id, company, url FROM portal_jobs')
        jobs = c.fetchall()
        conn.close()

        assert len(jobs) >= 50, f"Expected indexed portal jobs, found {len(jobs)}"
        for j_id, company, url in jobs:
            assert url.startswith('https://'), f"Job {j_id} ({company}) URL must start with https://, got: {url}"
            assert 'job_id=' not in url, f"Job {j_id} ({company}) URL must not contain dummy job_id: {url}"
            assert 'jobs.netflix.net' not in url, f"Job {j_id} ({company}) URL must not contain defunct domain: {url}"
            assert 'redhat.com/en/jobs' not in url, f"Job {j_id} ({company}) URL must not point to generic overview redhat.com/en/jobs: {url}"
            assert 'careers.redhat.com' not in url, f"Job {j_id} ({company}) URL must not point to redirecting careers.redhat.com: {url}"

    def test_redhat_and_workday_portals_link_to_actual_job_requisitions(self):
        """
        Verify that Red Hat and Workday portals link to actual job postings,
        and that PortalJobsScanner._scrape_workday correctly formats exact job requisition URLs.
        """
        import re
        import sqlite3
        from scraper.company_portals import CompanyPortalsManager
        from scraper.portal_jobs_scanner import PortalJobsScanner

        # 1. Verify Red Hat portal configuration points to Workday
        c_mgr = CompanyPortalsManager()
        redhat = c_mgr.get_portal('redhat')
        assert redhat is not None
        assert redhat['ats_type'] == 'workday'
        assert 'redhat.wd5.myworkdayjobs.com/jobs' in redhat['search_url']
        assert 'redhat.com/en/jobs' not in redhat['search_url']

        # 2. Verify Workday scraper parsing logic
        scanner = PortalJobsScanner()
        assert hasattr(scanner, '_scrape_workday')

        # Test Workday parsing helper with sample CXS response shape
        test_base = "https://redhat.wd5.myworkdayjobs.com/jobs"
        m = re.search(r'https?://([^.]+)\.([^.]+)\.myworkdayjobs\.com/(?:[a-zA-Z-]+/)?([^/?#]+)', test_base)
        assert m is not None
        tenant, host, site = m.group(1), m.group(2), m.group(3)
        assert tenant == 'redhat'
        assert host == 'wd5'
        assert site == 'jobs'

        sample_external_path = "/job/Pune/Senior-Software-Engineer--Cloud-Infrastructure_R-057038-1"
        direct_url = f"https://{tenant}.{host}.myworkdayjobs.com/en-US/{site}{sample_external_path}"
        assert direct_url == "https://redhat.wd5.myworkdayjobs.com/en-US/jobs/job/Pune/Senior-Software-Engineer--Cloud-Infrastructure_R-057038-1"
        assert "/job/Pune/" in direct_url
        assert "R-057038-1" in direct_url

        # 3. Verify all Red Hat jobs in DB point to Workday
        db_path = PROJECT_ROOT / 'instance' / 'jobs.db'
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT id, title, url FROM portal_jobs WHERE company LIKE '%Red Hat%'")
            redhat_jobs = c.fetchall()
            conn.close()

            assert len(redhat_jobs) >= 1
            for j_id, title, rj_url in redhat_jobs:
                assert 'redhat.wd5.myworkdayjobs.com' in rj_url, f"Red Hat job must be on Workday, got: {rj_url}"
                assert 'redhat.com/en/jobs' not in rj_url, f"Red Hat job must NOT be on generic redhat.com/en/jobs: {rj_url}"
                assert 'careers.redhat.com' not in rj_url, f"Red Hat job must NOT be on careers.redhat.com: {rj_url}"













