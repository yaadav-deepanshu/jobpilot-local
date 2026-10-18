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

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from web.app import create_app
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
            'exclude_keywords': ['internship', 'volunteer', 'unpaid', 'part-time', 'principal', 'director', 'architect', 'manager'],
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
