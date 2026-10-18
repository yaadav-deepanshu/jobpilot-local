"""
Web and API routes for Job Finder
Handles dashboard rendering, real-time job scraping, status updates, and stats
"""

import logging
import threading
from datetime import datetime, timezone
from flask import Blueprint, jsonify, render_template, request, abort, current_app
from sqlalchemy import case
from db.models import db, Job
from scraper.multi_platform import RealJobScraper
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
    '%staff%', '%architect%', '%director%', '%manager%', '%head of%', '%vp%', '%vice president%'
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

    query = Job.query

    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    if platform_filter != 'all':
        query = query.filter_by(platform=platform_filter)
    query = apply_location_filter(query, location_filter)
    if search_query:
        like_pattern = f"%{search_query}%"
        query = query.filter(
            (Job.title.ilike(like_pattern)) |
            (Job.company.ilike(like_pattern)) |
            (Job.location.ilike(like_pattern))
        )

    jobs = get_sorted_job_query(query).all()
    return render_template(
        'jobs.html',
        jobs=jobs,
        status_filter=status_filter,
        platform_filter=platform_filter,
        location_filter=location_filter,
        search_query=search_query
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
                        )
                        db.session.add(job)
                        new_saved += 1

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
    base_q = get_filtered_job_query()
    total = base_q.count()
    new_count = get_filtered_job_query().filter_by(status='new').count()
    applied_count = get_filtered_job_query().filter_by(status='applied').count()
    saved_count = get_filtered_job_query().filter_by(status='saved').count()
    rejected_count = get_filtered_job_query().filter_by(status='rejected').count()

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
        'by_platform': platforms,
        'by_location': {
            'both': total,
            'bengaluru': blr_count,
            'remote': rem_count,
        }
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

    query = Job.query

    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    if platform_filter != 'all':
        query = query.filter_by(platform=platform_filter)
    query = apply_location_filter(query, location_filter)
    if search_q:
        pattern = f"%{search_q}%"
        query = query.filter(
            (Job.title.ilike(pattern)) |
            (Job.company.ilike(pattern)) |
            (Job.location.ilike(pattern))
        )

    pagination = get_sorted_job_query(query).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'jobs': [j.to_dict() for j in pagination.items],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages,
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
