"""
Database models for Job Finder
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

def utcnow():
    """Current UTC datetime"""
    return datetime.now(timezone.utc)

class Job(db.Model):
    """Represents a discovered job posting"""
    __tablename__ = 'jobs'

    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)   # linkedin, indeed, naukri, glassdoor
    title = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255))
    url = db.Column(db.Text, unique=True, nullable=False)
    description = db.Column(db.Text)
    salary = db.Column(db.String(100))
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    date_posted = db.Column(db.DateTime)
    job_type = db.Column(db.String(50))                  # Full-time, Contract, etc.
    num_applicants = db.Column(db.Integer)
    is_easy_apply = db.Column(db.Boolean, default=False)

    # Tracking fields
    status = db.Column(db.String(20), default='new')     # new, applied, saved, rejected
    applied_at = db.Column(db.DateTime)
    tailored_resume = db.Column(db.Text)
    notes = db.Column(db.Text)
    is_researched = db.Column(db.Boolean, default=False) # True when discovered again in re-searches
    search_count = db.Column(db.Integer, default=1)      # Count of times discovered / searched

    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    def to_dict(self):
        """Serialize job to JSON-compatible dictionary"""
        date_str = ''
        if self.date_posted:
            try:
                date_str = self.date_posted.strftime('%Y-%m-%d')
            except Exception:
                date_str = str(self.date_posted)

        created_str = ''
        if self.created_at:
            try:
                created_str = self.created_at.strftime('%Y-%m-%d %H:%M')
            except Exception:
                created_str = str(self.created_at)

        applied_str = None
        if self.applied_at:
            try:
                applied_str = self.applied_at.strftime('%Y-%m-%d %H:%M')
            except Exception:
                applied_str = str(self.applied_at)

        desc_short = ''
        if self.description:
            desc_short = self.description[:220] + ('...' if len(self.description) > 220 else '')

        return {
            'id': self.id,
            'platform': self.platform,
            'title': self.title,
            'company': self.company,
            'location': self.location or 'Not specified',
            'url': self.url,
            'description': desc_short,
            'salary': self.salary or '',
            'salary_min': self.salary_min,
            'salary_max': self.salary_max,
            'date_posted': date_str,
            'job_type': self.job_type or 'Full-time',
            'num_applicants': self.num_applicants,
            'is_easy_apply': bool(self.is_easy_apply),
            'status': self.status or 'new',
            'is_researched': bool(self.is_researched or (self.search_count and self.search_count > 1)),
            'search_count': self.search_count or 1,
            'applied_at': applied_str,
            'created_at': created_str,
            'notes': self.notes or '',
        }

class ApplicationLog(db.Model):
    """Log of applications submitted or tracked"""
    __tablename__ = 'application_logs'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=True)
    status = db.Column(db.String(50), default='applied')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'job_id': self.job_id,
            'status': self.status,
            'notes': self.notes or '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else ''
        }

class PortalJob(db.Model):
    """Represents a job discovered directly from company career portals and specialized sites"""
    __tablename__ = 'portal_jobs'

    id = db.Column(db.Integer, primary_key=True)
    portal_id = db.Column(db.String(100), nullable=False)   # amazon_aws, google, swiggy, etc.
    company = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100))                    # Cloud Hyperscalers, SaaS, FinTech, etc.
    ats_type = db.Column(db.String(50))                     # greenhouse, lever, workday, etc.
    title = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255))
    url = db.Column(db.Text, unique=True, nullable=False)
    description = db.Column(db.Text)
    experience_req = db.Column(db.String(100), default='0-4 years')  # 0-4y, 2-4y, 1-3y
    experience_max = db.Column(db.Integer, default=4)       # strictly <= 4 years
    matched_skills = db.Column(db.Text)                     # comma-separated matched skills
    match_score = db.Column(db.Integer, default=0)          # 0-100%
    skills_count = db.Column(db.Integer, default=0)
    salary = db.Column(db.String(100))
    date_posted = db.Column(db.DateTime)
    job_type = db.Column(db.String(50), default='Full-time')
    is_easy_apply = db.Column(db.Boolean, default=False)

    # Tracking fields
    status = db.Column(db.String(20), default='new')        # new, applied, saved, rejected
    applied_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    def to_dict(self):
        """Serialize portal job to JSON-compatible dictionary"""
        date_str = ''
        if self.date_posted:
            try:
                date_str = self.date_posted.strftime('%Y-%m-%d')
            except Exception:
                date_str = str(self.date_posted)

        created_str = ''
        if self.created_at:
            try:
                created_str = self.created_at.strftime('%Y-%m-%d %H:%M')
            except Exception:
                created_str = str(self.created_at)

        applied_str = None
        if self.applied_at:
            try:
                applied_str = self.applied_at.strftime('%Y-%m-%d %H:%M')
            except Exception:
                applied_str = str(self.applied_at)

        desc_short = ''
        if self.description:
            desc_short = self.description[:260] + ('...' if len(self.description) > 260 else '')

        # Parse matched skills to list
        skills_list = []
        if self.matched_skills:
            skills_list = [s.strip() for s in self.matched_skills.split(',') if s.strip()]

        return {
            'id': self.id,
            'portal_id': self.portal_id,
            'company': self.company,
            'category': self.category or 'General Tech',
            'ats_type': self.ats_type or 'portal',
            'title': self.title,
            'location': self.location or 'Bengaluru / Remote',
            'url': self.url,
            'description': desc_short,
            'description_full': self.description or '',
            'experience_req': self.experience_req or '< 4 years',
            'experience_max': self.experience_max or 4,
            'matched_skills': skills_list,
            'skills_count': self.skills_count or len(skills_list),
            'match_score': self.match_score or 0,
            'salary': self.salary or '',
            'date_posted': date_str,
            'job_type': self.job_type or 'Full-time',
            'status': self.status or 'new',
            'applied_at': applied_str,
            'created_at': created_str,
            'notes': self.notes or '',
        }

def _migrate_sqlite_columns(app=None):
    """Ensure newly added columns exist in SQLite database if it already exists."""
    import os, sqlite3
    db_path = None
    if app and 'SQLALCHEMY_DATABASE_URI' in app.config:
        uri = app.config['SQLALCHEMY_DATABASE_URI']
        if uri.startswith('sqlite:///'):
            db_path = uri.replace('sqlite:///', '')
    if not db_path:
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'jobs.db')

    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("PRAGMA table_info(jobs)")
            cols = [row[1] for row in c.fetchall()]
            if cols and 'is_researched' not in cols:
                c.execute("ALTER TABLE jobs ADD COLUMN is_researched BOOLEAN DEFAULT 0")
            if cols and 'search_count' not in cols:
                c.execute("ALTER TABLE jobs ADD COLUMN search_count INTEGER DEFAULT 1")
            conn.commit()
            conn.close()
        except Exception:
            pass

def init_db(app=None):
    """Initialize database tables"""
    if app:
        with app.app_context():
            db.create_all()
            _migrate_sqlite_columns(app)
    else:
        db.create_all()
        _migrate_sqlite_columns()
