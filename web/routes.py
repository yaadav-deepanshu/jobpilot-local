"""
Web and API routes for Job Finder
Handles dashboard rendering, real-time job scraping, status updates, and stats
"""

import logging
import threading
from datetime import datetime, timezone, timedelta
from flask import Blueprint, jsonify, render_template, request, abort, current_app
from sqlalchemy import case, func
from db.models import db, Job, PortalJob
from scraper.multi_platform import RealJobScraper
from scraper.company_portals import CompanyPortalsManager
from scraper.websites_scraper import WebsitesManager
from scraper.portal_jobs_scanner import PortalJobsScanner
from filter.engine import FilterEngine
import yaml
import os

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__)

# --- Scraper status tracker ---
_status_lock = threading.Lock()
_scrape_state = {
    'running': False,
    'mode': 'idle',
    'started_at': None,
    'current_phase': 'Idle',
    'jobs_found': 0,
    'jobs_saved': 0,
    'finished': False,
    'error': None,
}

def _set_scrape_started(mode: str):
    with _status_lock:
        _scrape_state.update({
            'running': True,
            'mode': mode,
            'started_at': datetime.now(timezone.utc).isoformat(),
            'current_phase': 'Starting scrape engine...',
            'jobs_found': 0,
            'jobs_saved': 0,
            'finished': False,
            'error': None,
        })


def get_live_job_config() -> dict:
    """Retrieve active configuration with automatic hot-reload from config.yaml"""
    from pathlib import Path
    try:
        config_path = Path(current_app.root_path).parent / 'config.yaml'
        mtime = os.path.getmtime(config_path) if config_path.exists() else 0
        last_mtime = getattr(current_app, '_config_mtime', 0)
        cached = current_app.config.get('JOB_CONFIG') or {}
        # Hot-reload if file timestamp changed or if cached portals < 1000
        if not cached or mtime > last_mtime or len(cached.get('company_portals', [])) < 1000:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    new_cfg = yaml.safe_load(f) or {}
                current_app.config['JOB_CONFIG'] = new_cfg
                current_app._config_mtime = mtime
                return new_cfg
    except Exception as e:
        logger.debug(f"Live config check note: {e}")
    return current_app.config.get('JOB_CONFIG', {})

def _set_scrape_progress(phase: str, count: int):
    with _status_lock:
        _scrape_state['current_phase'] = phase
        _scrape_state['jobs_found'] = count

def _set_scrape_finished(saved_count: int, error: str = None):
    with _status_lock:
        _scrape_state.update({
            'running': False,
            'finished': True,
            'jobs_saved': saved_count,
            'current_phase': 'Complete' if not error else 'Failed',
            'error': error,
        })


# --- Filtered Query Helper & Cleanup Utilities ---

SENIOR_TITLE_PATTERNS = [
    '%senior%', '%sr.%', '%sr %', '%lead%', '%principal%',
    '%staff%', '%director%', '%manager%', '%head of%', '%vp%', '%vice president%'
]

DESC_UNQUALIFIED_PATTERNS = [
    '%over 100 people%', '%over 100 applicants%', '%over 100 clicked%', '%100+ applicants%',
    '%5+ years%', '%6+ years%', '%7+ years%', '%8+ years%', '%9+ years%', '%10+ years%',
    '%5+ yrs%', '%6+ yrs%', '%7+ yrs%', '%8+ yrs%', '%10+ yrs%',
    '%minimum 5 years%', '%minimum 6 years%', '%minimum 7 years%', '%minimum 8 years%', '%minimum 10 years%',
    '%at least 5 years%', '%at least 6 years%', '%at least 8 years%',
    '%5-8 years%', '%6-9 years%', '%5-9 years%', '%6-8 years%', '%8-10 years%'
]

PLATFORM_SORT_ORDER = case(
    (Job.platform == 'linkedin', 1),
    (Job.platform == 'indeed', 2),
    (Job.platform == 'naukri', 3),
    else_=4
)

def get_filtered_job_query(base_query=None):
    """
    Apply strict constraints:
    1. Maximum 4 years experience: Exclude senior/lead/architect/manager titles and explicit 5+ year patterns.
    2. Maximum 100 applicants: num_applicants <= 100 and no 'over 100' in description.
    Safely handles NULL values in title/description/num_applicants.
    """
    q = base_query if base_query is not None else Job.query

    # Title exclusions
    for pat in SENIOR_TITLE_PATTERNS:
        q = q.filter((Job.title.is_(None)) | (~Job.title.ilike(pat)))

    # Applicant count limit (max 100)
    q = q.filter((Job.num_applicants.is_(None)) | (Job.num_applicants <= 100))

    # Description exclusions (excessive experience and over 100 applicants)
    for pat in DESC_UNQUALIFIED_PATTERNS:
        q = q.filter((Job.description.is_(None)) | (~Job.description.ilike(pat)))

    return q

def get_sorted_job_query(base_query=None):
    """
    Returns filtered jobs sorted by platform priority:
    1. LinkedIn on top
    2. Indeed second
    3. Naukri third
    4. Rest (Glassdoor, ZipRecruiter, Google, Bayt, etc.)
    Within each platform group, sorted by date_posted desc, created_at desc.
    """
    q = get_filtered_job_query(base_query)
    return q.order_by(PLATFORM_SORT_ORDER.asc(), Job.date_posted.desc(), Job.created_at.desc())

def apply_location_filter(query, location_mode='both'):
    """
    Segregate jobs by location:
    - 'remote': Only Remote jobs (matches remote/wfh in location, title, description, or job_type)
    - 'bengaluru': Only Bengaluru / Bangalore jobs (matches in location)
    - 'both' / 'all': Both Bengaluru and Remote jobs (or all qualified jobs)
    """
    if not location_mode or location_mode in ('both', 'all'):
        return query

    location_mode = str(location_mode).lower().strip()
    if location_mode == 'remote':
        return query.filter(
            (Job.location.ilike('%remote%')) |
            (Job.location.ilike('%work from home%')) |
            (Job.location.ilike('%wfh%')) |
            (Job.title.ilike('%remote%')) |
            (Job.description.ilike('%remote%')) |
            (Job.job_type.ilike('%remote%'))
        )
    elif location_mode == 'bengaluru':
        return query.filter(
            (Job.location.ilike('%bengaluru%')) |
            (Job.location.ilike('%bangalore%'))
        )
    return query

def apply_hours_filter(query, hours):
    """
    Filter jobs to those posted or uploaded/created within the last `hours` window.
    Strictly checks both date_posted and created_at against the cutoff.
    """
    if not hours:
        return query
    try:
        hours = int(hours)
        if hours <= 0:
            return query
    except (ValueError, TypeError):
        return query

    cutoff_utc = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_naive = cutoff_utc.replace(tzinfo=None)
    return query.filter(
        (Job.date_posted >= cutoff_utc) | (Job.date_posted >= cutoff_naive) |
        (Job.created_at >= cutoff_utc) | (Job.created_at >= cutoff_naive)
    )

def purge_unqualified_jobs():
    """
    Permanently purge any legacy jobs that violate:
    - 0-4 years experience cap
    - senior/lead/architect/manager titles
    - > 100 applicants or text saying 'over 100'
    """
    deleted = 0
    # Senior / Lead titles
    for pat in SENIOR_TITLE_PATTERNS:
        deleted += Job.query.filter(Job.title.ilike(pat)).delete(synchronize_session='fetch')

    # Over 100 applicants
    deleted += Job.query.filter(Job.num_applicants > 100).delete(synchronize_session='fetch')

    # Excessive experience or over 100 text
    for pat in DESC_UNQUALIFIED_PATTERNS:
        deleted += Job.query.filter(Job.description.ilike(pat)).delete(synchronize_session='fetch')

    db.session.commit()
    logger.info(f"✓ Purged {deleted} unqualified/legacy jobs from database.")
    return deleted


# --- View Routes ---

@main_bp.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@main_bp.route('/jobs')
def page_jobs():
    """All Jobs tabular view with strict 0-4y experience, <=100 applicant filtering, location segregation, and platform priority ordering"""
    status_filter = request.args.get('status', 'all')
    platform_filter = request.args.get('platform', 'all')
    location_filter = request.args.get('location', request.args.get('location_type', 'both')).lower().strip()
    search_query = request.args.get('q', '').strip()
    hours_filter = request.args.get('hours', None, type=int)

    query = Job.query

    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    else:
        # Exclude dismissed/rejected jobs from general view
        query = query.filter((Job.status.is_(None)) | (Job.status != 'rejected'))

    if platform_filter != 'all':
        query = query.filter_by(platform=platform_filter)
    query = apply_location_filter(query, location_filter)
    query = apply_hours_filter(query, hours_filter)
    if search_query:
        like_pattern = f"%{search_query}%"
        query = query.filter(
            (Job.title.ilike(like_pattern)) |
            (Job.company.ilike(like_pattern)) |
            (Job.location.ilike(like_pattern))
        )
        if status_filter != 'rejected':
            query = query.filter((Job.status.is_(None)) | (Job.status != 'rejected'))

    jobs = get_sorted_job_query(query).all()
    return render_template(
        'jobs.html',
        jobs=jobs,
        status_filter=status_filter,
        platform_filter=platform_filter,
        location_filter=location_filter,
        search_query=search_query,
        hours_filter=hours_filter
    )

@main_bp.route('/portals', strict_slashes=False)
@main_bp.route('/portal', strict_slashes=False)
@main_bp.route('/protals', strict_slashes=False)
@main_bp.route('/company-portals', strict_slashes=False)
@main_bp.route('/companies', strict_slashes=False)
@main_bp.route('/websites', strict_slashes=False)
@main_bp.route('/portals-and-websites', strict_slashes=False)
@main_bp.route('/websites-and-portals', strict_slashes=False)
def page_portals():
    """100 Big Companies Portals & 24 Specialized Job Websites Directory"""
    config = get_live_job_config()
    c_mgr = CompanyPortalsManager(config)
    w_mgr = WebsitesManager(config)

    portals = c_mgr.get_portals()
    websites = w_mgr.get_websites()
    categories_companies = c_mgr.get_categories()
    categories_websites = w_mgr.get_categories()
    stats = {
        'total_companies': c_mgr.count(),
        'total_websites': w_mgr.count(),
        'company_categories': c_mgr.get_stats()['by_category'],
        'website_categories': w_mgr.get_stats()['by_category'],
    }
    return render_template(
        'portals.html',
        portals=portals,
        websites=websites,
        categories_companies=categories_companies,
        categories_websites=categories_websites,
        stats=stats
    )

@main_bp.route('/portal-jobs', strict_slashes=False)
@main_bp.route('/portaljobs', strict_slashes=False)
@main_bp.route('/portal-postings', strict_slashes=False)
@main_bp.route('/company-jobs', strict_slashes=False)
@main_bp.route('/portal-openings', strict_slashes=False)
def page_portal_jobs():
    """
    Direct Career Portals Job Postings Page
    Scans & lists jobs from 1,400+ Top Company Portals and 24 Tech Websites
    filtered for < 4 years experience and scored against Deepanshu Yadav's resume skills.
    """
    config = get_live_job_config()
    c_mgr = CompanyPortalsManager(config)
    categories = c_mgr.get_categories()
    standard_ats = ['greenhouse', 'lever', 'ashby', 'smartrecruiters', 'workday', 'amazon_jobs', 'jobvite', 'taleo', 'successfactors', 'custom']
    try:
        db_ats = [row[0] for row in db.session.query(PortalJob.ats_type).distinct().all() if row[0]]
    except Exception:
        db_ats = []
    ats_types = []
    for a in standard_ats + sorted(db_ats):
        if a and a not in ats_types:
            ats_types.append(a)

    # Auto-seed initial top-company postings if table is empty so user gets instant value
    total_count = PortalJob.query.count()
    if total_count == 0:
        scanner = PortalJobsScanner(config)
        quick_jobs = scanner.scan(mode='quick', max_jobs_per_company=3)
        scanner.save_jobs_to_db(quick_jobs, app=current_app._get_current_object())
        total_count = PortalJob.query.count()

    qualified_count = PortalJob.query.filter(PortalJob.experience_max <= 4).count()
    avg_score_raw = db.session.query(func.avg(PortalJob.match_score)).scalar()
    avg_score = int(round(avg_score_raw)) if avg_score_raw else 0
    companies_count = db.session.query(func.count(func.distinct(PortalJob.company))).scalar() or 0

    stats = {
        'total_jobs': total_count,
        'qualified_jobs': qualified_count,
        'avg_match_score': avg_score,
        'companies_discovered': companies_count,
    }

    return render_template(
        'portal_jobs.html',
        categories=categories,
        ats_types=ats_types,
        stats=stats
    )


# --- API Routes ---

@api_bp.route('/scrape-status', methods=['GET'])
def get_scrape_status():
    """Poll live scraping progress"""
    with _status_lock:
        return jsonify(dict(_scrape_state))

@api_bp.route('/scrape', methods=['POST'])
@api_bp.route('/flexible-scrape', methods=['POST'])
@api_bp.route('/bulk-scrape', methods=['POST'])
def trigger_scrape():
    """Trigger background scrape (supports flexible 24h, bulk all-time, or general)"""
    with _status_lock:
        if _scrape_state['running']:
            return jsonify({
                'status': 'already_running',
                'message': 'Scraping is already in progress.'
            }), 409

    data = request.get_json(silent=True) or {}
    endpoint = request.path
    hours = data.get('hours') or data.get('hours_old')
    if hours is not None:
        try:
            hours = int(hours)
        except (ValueError, TypeError):
            hours = None

    if 'flexible-scrape' in endpoint:
        today_only = True
        mode_name = '🔥 FLEXIBLE SCRAPE (TODAY)'
    elif 'bulk-scrape' in endpoint:
        today_only = False
        mode_name = '📦 BULK SCRAPE (ALL TIME)'
    elif hours:
        today_only = True
        mode_name = f'⏱️ WINDOW SCRAPE ({hours}H)'
    else:
        today_only = bool(data.get('today_only', False))
        mode_name = '🔥 FLEXIBLE SCRAPE (TODAY)' if today_only else '📦 BULK SCRAPE (ALL TIME)'

    # Get application instance for background context
    app = current_app._get_current_object()

    config = {}
    if os.path.exists('config.yaml'):
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f) or {}

    _set_scrape_started(mode_name)

    def background_worker():
        try:
            scraper = RealJobScraper(config)
            filter_engine = FilterEngine(config)

            def progress_callback(phase_text, current_count):
                _set_scrape_progress(phase_text, current_count)

            # 1. Scrape real jobs from enabled platforms
            raw_jobs = scraper.scrape_all(
                today_only=today_only,
                hours_old=hours,
                results_per_query=15,
                progress_callback=progress_callback
            )

            # 2. Filter jobs
            _set_scrape_progress(f"Filtering {len(raw_jobs)} discovered jobs...", len(raw_jobs))
            matched_jobs = filter_engine.filter_jobs(raw_jobs, today_only=today_only, max_hours=hours)

            # 3. Save to database within Flask app context
            _set_scrape_progress(f"Saving {len(matched_jobs)} matching jobs to database...", len(matched_jobs))
            new_saved = 0

            with app.app_context():
                for j_data in matched_jobs:
                    url = j_data.get('url', '').strip()
                    if not url:
                        continue

                    # Check if already exists by URL
                    existing = Job.query.filter_by(url=url).first()
                    if not existing:
                        job = Job(
                            platform=j_data['platform'],
                            title=j_data['title'],
                            company=j_data['company'],
                            location=j_data.get('location', ''),
                            url=url,
                            description=j_data.get('description', ''),
                            salary=j_data.get('salary', ''),
                            salary_min=j_data.get('salary_min'),
                            salary_max=j_data.get('salary_max'),
                            date_posted=j_data.get('date_posted'),
                            job_type=j_data.get('job_type', 'Full-time'),
                            num_applicants=j_data.get('num_applicants'),
                            is_easy_apply=j_data.get('is_easy_apply', False),
                            status='new',
                            is_researched=False,
                            search_count=1,
                        )
                        db.session.add(job)
                        new_saved += 1
                    else:
                        # Job discovered again in subsequent search/scrape
                        existing.is_researched = True
                        existing.search_count = (existing.search_count or 1) + 1
                        existing.updated_at = datetime.now(timezone.utc)

                db.session.commit()
                logger.info(f"✓ Background scrape finished. Added {new_saved} new jobs to DB.")

            _set_scrape_finished(new_saved)

        except Exception as e:
            logger.error(f"Scraper error in background worker: {e}", exc_info=True)
            _set_scrape_finished(0, error=str(e))

    thread = threading.Thread(target=background_worker, daemon=True)
    thread.start()

    return jsonify({
        'status': 'started',
        'message': f'Scrape started ({mode_name}). Live progress will update automatically.'
    })

@api_bp.route('/stats', methods=['GET'])
def get_stats():
    """Return dashboard stats strictly respecting 0-4y experience and <=100 applicant limits, plus location segregation counts"""
    hours_filter = request.args.get('hours', None, type=int)
    base_q = apply_hours_filter(get_filtered_job_query(), hours_filter)
    total = base_q.count()
    new_count = apply_hours_filter(get_filtered_job_query(), hours_filter).filter_by(status='new').count()
    applied_count = apply_hours_filter(get_filtered_job_query(), hours_filter).filter_by(status='applied').count()
    saved_count = apply_hours_filter(get_filtered_job_query(), hours_filter).filter_by(status='saved').count()
    rejected_count = apply_hours_filter(get_filtered_job_query(), hours_filter).filter_by(status='rejected').count()
    researched_count = apply_hours_filter(get_filtered_job_query(), hours_filter).filter((Job.is_researched.is_(True)) | (Job.search_count > 1)).count()

    # Platforms breakdown from filtered jobs
    platforms = {}
    rows = base_q.with_entities(Job.platform, db.func.count(Job.id)).group_by(Job.platform).all()
    for plat, cnt in rows:
        platforms[plat] = cnt

    # Location breakdown from filtered jobs
    blr_count = apply_location_filter(base_q, 'bengaluru').count()
    rem_count = apply_location_filter(base_q, 'remote').count()

    return jsonify({
        'total_jobs': total,
        'new': new_count,
        'applied': applied_count,
        'saved': saved_count,
        'rejected': rejected_count,
        'researched': researched_count,
        'by_platform': platforms,
        'by_location': {
            'both': total,
            'bengaluru': blr_count,
            'remote': rem_count,
        },
        'hours': hours_filter,
    })

@api_bp.route('/jobs', methods=['GET'])
def get_jobs():
    """Paginated list of jobs as JSON with 0-4y experience, <=100 applicants, location segregation, and platform priority ordering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    status_filter = request.args.get('status', 'all')
    platform_filter = request.args.get('platform', 'all')
    location_filter = request.args.get('location', request.args.get('location_type', 'both')).lower().strip()
    search_q = request.args.get('q', '').strip()
    hours_filter = request.args.get('hours', None, type=int)

    query = Job.query

    if status_filter != 'all':
        if status_filter == 'researched':
            query = query.filter((Job.is_researched.is_(True)) | (Job.search_count > 1))
            query = query.filter((Job.status.is_(None)) | (Job.status != 'rejected'))
        else:
            query = query.filter_by(status=status_filter)
    else:
        # Exclude dismissed/rejected jobs from general feed
        query = query.filter((Job.status.is_(None)) | (Job.status != 'rejected'))

    if platform_filter != 'all':
        query = query.filter_by(platform=platform_filter)
    query = apply_location_filter(query, location_filter)
    query = apply_hours_filter(query, hours_filter)
    if search_q:
        pattern = f"%{search_q}%"
        query = query.filter(
            (Job.title.ilike(pattern)) |
            (Job.company.ilike(pattern)) |
            (Job.location.ilike(pattern))
        )
        # Dismissed jobs never show up during search unless viewing rejected
        if status_filter != 'rejected':
            query = query.filter((Job.status.is_(None)) | (Job.status != 'rejected'))

    pagination = get_sorted_job_query(query).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'jobs': [j.to_dict() for j in pagination.items],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages,
        'hours': hours_filter,
    })

@api_bp.route('/job/<int:job_id>/researched', methods=['POST', 'PUT'])
def mark_job_researched(job_id):
    """Mark a job as re-searched / searched again"""
    job = db.session.get(Job, job_id)
    if not job:
        abort(404)

    job.is_researched = True
    job.search_count = (job.search_count or 1) + 1
    job.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({
        'status': 'success',
        'job': job.to_dict()
    })

@api_bp.route('/job/<int:job_id>/status', methods=['PUT'])
def update_job_status(job_id):
    """Update status of a job (new, applied, saved, rejected)"""
    job = db.session.get(Job, job_id)
    if not job:
        abort(404)

    data = request.get_json(silent=True) or {}
    new_status = data.get('status')
    valid_statuses = ['new', 'applied', 'saved', 'rejected', 'pending']

    if new_status not in valid_statuses:
        return jsonify({'error': f'Invalid status. Must be one of {valid_statuses}'}), 400

    job.status = new_status
    if new_status == 'applied':
        job.applied_at = datetime.now(timezone.utc)

    db.session.commit()
    return jsonify({
        'status': 'success',
        'job': job.to_dict()
    })

@api_bp.route('/clear-fake-data', methods=['POST'])
def clear_fake_data():
    """Delete any mock/test jobs and purge legacy unqualified jobs"""
    fake_patterns = ['TestCorp', 'Co 0', 'Co 1', 'Co 2', 'C1', 'C2', 'C3', 'ExportCo', 'IntegrationTestCo']
    deleted = 0
    for pat in fake_patterns:
        count = Job.query.filter(Job.company.ilike(f"%{pat}%")).delete(synchronize_session='fetch')
        deleted += count

    # Also clean any jobs with title 'J1', 'J2', 'J3'
    count = Job.query.filter(Job.title.in_(['J1', 'J2', 'J3', 'Export Test'])).delete(synchronize_session='fetch')
    deleted += count

    # Also purge any legacy jobs violating experience (>4y) or applicant (>100) constraints
    deleted += purge_unqualified_jobs()

    db.session.commit()
    return jsonify({'status': 'success', 'deleted_count': deleted})

@api_bp.route('/purge-unqualified', methods=['POST'])
def api_purge_unqualified():
    """Explicit endpoint to purge any jobs exceeding 4 years experience or 100 applicants"""
    purged_count = purge_unqualified_jobs()
    return jsonify({'status': 'success', 'purged_count': purged_count})

@api_bp.route('/portals', methods=['GET'], strict_slashes=False)
@api_bp.route('/portal', methods=['GET'], strict_slashes=False)
@api_bp.route('/protals', methods=['GET'], strict_slashes=False)
@api_bp.route('/company-portals', methods=['GET'], strict_slashes=False)
@api_bp.route('/companies', methods=['GET'], strict_slashes=False)
def get_portals():
    """Return 100 Big Companies Job Portals with optional filtering"""
    config = get_live_job_config()
    mgr = CompanyPortalsManager(config)
    category = request.args.get('category')
    search = request.args.get('search') or request.args.get('q')
    ats = request.args.get('ats')
    portals = mgr.get_portals(category=category, search=search, ats_type=ats)
    return jsonify({
        'total': len(portals),
        'portals': portals,
        'categories': mgr.get_categories()
    })

@api_bp.route('/websites', methods=['GET'], strict_slashes=False)
@api_bp.route('/website', methods=['GET'], strict_slashes=False)
def get_websites():
    """Return 24 Specialized Tech & DevOps Job Websites with optional filtering"""
    config = get_live_job_config()
    mgr = WebsitesManager(config)
    category = request.args.get('category')
    search = request.args.get('search') or request.args.get('q')
    websites = mgr.get_websites(category=category, search=search)
    return jsonify({
        'total': len(websites),
        'websites': websites,
        'categories': mgr.get_categories()
    })

@api_bp.route('/portals/stats', methods=['GET'], strict_slashes=False)
@api_bp.route('/portal/stats', methods=['GET'], strict_slashes=False)
@api_bp.route('/protals/stats', methods=['GET'], strict_slashes=False)
def get_portals_stats():
    """Return summary metrics for company portals and specialized websites"""
    config = get_live_job_config()
    c_mgr = CompanyPortalsManager(config)
    w_mgr = WebsitesManager(config)
    return jsonify({
        'companies': c_mgr.get_stats(),
        'websites': w_mgr.get_stats(),
    })


# --- Portal Jobs Scanner API Routes ---

_portal_scanner_lock = threading.Lock()
_portal_scanner_obj = None

def get_portal_scanner(config=None):
    global _portal_scanner_obj
    with _portal_scanner_lock:
        if _portal_scanner_obj is None:
            cfg = config or get_live_job_config()
            _portal_scanner_obj = PortalJobsScanner(cfg)
        return _portal_scanner_obj

@api_bp.route('/portal-jobs', methods=['GET'], strict_slashes=False)
@api_bp.route('/portaljobs', methods=['GET'], strict_slashes=False)
@api_bp.route('/company-jobs', methods=['GET'], strict_slashes=False)
def get_portal_jobs():
    """Return paginated, filtered, and scored portal jobs"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 15, type=int), 100)
    q = request.args.get('q', '').strip()
    category = request.args.get('category', 'all').strip()
    ats = request.args.get('ats', request.args.get('ats_type', 'all')).strip()
    status = request.args.get('status', 'all').strip()
    min_score = request.args.get('min_score', 0, type=int)
    max_exp = request.args.get('max_exp', 4, type=int)
    sort_by = request.args.get('sort_by', 'score').strip().lower()

    query = PortalJob.query

    # Filter: Sector / Category
    if category and category.lower() != 'all':
        query = query.filter(PortalJob.category.ilike(f"%{category}%"))

    # Filter: ATS Type
    if ats and ats.lower() != 'all':
        query = query.filter(PortalJob.ats_type.ilike(f"%{ats}%"))

    # Filter: Status (exclude rejected by default unless requested)
    if status and status.lower() != 'all':
        query = query.filter(PortalJob.status == status.lower())
    else:
        query = query.filter((PortalJob.status.is_(None)) | (PortalJob.status != 'rejected'))

    # Filter: Experience cap (< 4 years)
    if max_exp and max_exp > 0:
        query = query.filter(PortalJob.experience_max <= max_exp)
    else:
        query = query.filter(PortalJob.experience_max <= 4)

    # Filter: Minimum match score
    if min_score and min_score > 0:
        query = query.filter(PortalJob.match_score >= min_score)

    # Filter: Text search (supports multi-term matching across title, company, location, skills)
    if q:
        terms = [t.strip() for t in q.split() if t.strip()]
        for t in terms:
            term = f"%{t}%"
            query = query.filter(
                (PortalJob.title.ilike(term)) |
                (PortalJob.company.ilike(term)) |
                (PortalJob.location.ilike(term)) |
                (PortalJob.matched_skills.ilike(term)) |
                (PortalJob.description.ilike(term))
            )

    # Sorting
    if sort_by == 'newest':
        query = query.order_by(PortalJob.date_posted.desc(), PortalJob.id.desc())
    elif sort_by == 'company':
        query = query.order_by(PortalJob.company.asc(), PortalJob.match_score.desc())
    elif sort_by == 'skills':
        query = query.order_by(PortalJob.skills_count.desc(), PortalJob.match_score.desc())
    else:  # 'score' (default)
        query = query.order_by(PortalJob.match_score.desc(), PortalJob.skills_count.desc(), PortalJob.date_posted.desc())

    total = query.count()
    jobs_page = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': max(1, (total + per_page - 1) // per_page),
        'pages': max(1, (total + per_page - 1) // per_page),
        'jobs': [j.to_dict() for j in jobs_page]
    })

@api_bp.route('/scan-portal-jobs', methods=['POST'], strict_slashes=False)
def trigger_portal_scan():
    """Trigger background scanning across company portals and specialized sites"""
    scanner = get_portal_scanner()
    if scanner.is_running():
        return jsonify({
            'status': 'already_running',
            'message': 'Portal scanning is already active in background.'
        }), 409

    data = request.get_json(silent=True) or {}
    mode = data.get('mode', 'all')
    category = data.get('category')
    portal_ids = data.get('portal_ids')
    raw_query = data.get('query') or data.get('q') or request.args.get('q') or request.args.get('query')
    query = raw_query.strip() if raw_query else None

    app_obj = current_app._get_current_object()

    def _run_scan_thread():
        with app_obj.app_context():
            try:
                results = scanner.scan(
                    mode=mode,
                    category=category,
                    portal_ids=portal_ids,
                    query=query
                )
                scanner.save_jobs_to_db(results, app=app_obj)
                logger.info(f"✓ Background portal scan complete: saved {len(results)} jobs.")
            except Exception as e:
                logger.error(f"Portal scan thread error: {e}", exc_info=True)

    thread = threading.Thread(target=_run_scan_thread, daemon=True)
    thread.start()

    msg = f"Started portal scan for '{query}' across company portals." if query else f"Started portal scan in mode '{mode}'."
    return jsonify({
        'status': 'started',
        'mode': mode,
        'query': query,
        'message': msg
    })

@api_bp.route('/scan-portal-jobs/status', methods=['GET'], strict_slashes=False)
def get_portal_scan_status():
    """Get live progress status of the portal scanner"""
    scanner = get_portal_scanner()
    return jsonify(scanner.get_status())

@api_bp.route('/scan-portal-jobs/stop', methods=['POST'], strict_slashes=False)
def stop_portal_scan():
    """Stop active portal scan immediately"""
    scanner = get_portal_scanner()
    scanner.stop()
    return jsonify({'status': 'stopping', 'message': 'Stop signal sent to scanner.'})

@api_bp.route('/portal-job/<int:job_id>/status', methods=['PUT', 'POST'], strict_slashes=False)
def update_portal_job_status(job_id: int):
    """Update status of a portal job (new, applied, saved, rejected)"""
    job = db.session.get(PortalJob, job_id)
    if not job:
        return jsonify({'error': 'Portal job not found'}), 404

    data = request.get_json(silent=True) or {}
    new_status = data.get('status', '').lower().strip()
    if new_status not in ('new', 'applied', 'saved', 'rejected'):
        return jsonify({'error': 'Invalid status'}), 400

    job.status = new_status
    if new_status == 'applied':
        job.applied_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({'status': 'success', 'job_id': job_id, 'new_status': new_status})

@api_bp.route('/portal-jobs/stats', methods=['GET'], strict_slashes=False)
def get_portal_jobs_stats():
    """Return aggregated metrics for portal jobs"""
    total = PortalJob.query.count()
    qualified = PortalJob.query.filter(PortalJob.experience_max <= 4).count()

    by_status = {
        'new': PortalJob.query.filter_by(status='new').count(),
        'applied': PortalJob.query.filter_by(status='applied').count(),
        'saved': PortalJob.query.filter_by(status='saved').count(),
        'rejected': PortalJob.query.filter_by(status='rejected').count(),
    }

    avg_score_raw = db.session.query(func.avg(PortalJob.match_score)).scalar()
    avg_score = int(round(avg_score_raw)) if avg_score_raw else 0

    companies_count = db.session.query(func.count(func.distinct(PortalJob.company))).scalar() or 0

    return jsonify({
        'total': total,
        'qualified': qualified,
        'by_status': by_status,
        'avg_match_score': avg_score,
        'companies_count': companies_count
    })

@api_bp.route('/portal-jobs/clear', methods=['DELETE', 'POST'], strict_slashes=False)
def clear_portal_jobs():
    """Clear all portal jobs"""
    count = PortalJob.query.delete()
    db.session.commit()
    return jsonify({'status': 'cleared', 'count': count})

@api_bp.route('/portal-jobs/seed', methods=['POST', 'GET'], strict_slashes=False)
def seed_portal_jobs():
    """Seed or refresh qualified portal jobs from top companies"""
    config = current_app.config.get('JOB_CONFIG', {})
    scanner = get_portal_scanner(config)
    mode = request.args.get('mode', 'quick')
    jobs = scanner.scan(mode=mode)
    saved = scanner.save_jobs_to_db(jobs, app=current_app._get_current_object())
    return jsonify({'status': 'success', 'saved_count': saved, 'total': PortalJob.query.count()})


