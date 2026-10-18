"""
Export API routes
"""

import logging
from flask import Blueprint, jsonify, send_file, request
from db.models import Job
from export.jobs_exporter import JobExporter
from web.routes import get_filtered_job_query, get_sorted_job_query, apply_location_filter
import yaml
import os

logger = logging.getLogger(__name__)

export_bp = Blueprint('export', __name__)

def _get_config():
    if os.path.exists('config.yaml'):
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f) or {}
    return {}

@export_bp.route('/download/excel', methods=['GET'])
def download_excel():
    """Download jobs as formatted Excel spreadsheet in platform priority order, optionally filtered by location"""
    try:
        config = _get_config()
        loc_filter = request.args.get('location', request.args.get('location_type', 'both')).lower().strip()
        q = apply_location_filter(get_sorted_job_query(), loc_filter)
        jobs = [j.to_dict() for j in q.all()]
        exporter = JobExporter(config)
        filepath = exporter.export_to_excel(jobs)

        return send_file(
            filepath,
            as_attachment=True,
            download_name=os.path.basename(filepath),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.error(f"Excel export error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@export_bp.route('/download/pdf', methods=['GET'])
def download_pdf():
    """Download jobs as formatted PDF report in platform priority order, optionally filtered by location"""
    try:
        config = _get_config()
        loc_filter = request.args.get('location', request.args.get('location_type', 'both')).lower().strip()
        q = apply_location_filter(get_sorted_job_query(), loc_filter)
        jobs = [j.to_dict() for j in q.all()]
        exporter = JobExporter(config)
        filepath = exporter.export_to_pdf(jobs)

        return send_file(
            filepath,
            as_attachment=True,
            download_name=os.path.basename(filepath),
            mimetype='application/pdf'
        )
    except Exception as e:
        logger.error(f"PDF export error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@export_bp.route('/download/html', methods=['GET'])
def download_html():
    """Download jobs as interactive HTML report in platform priority order, optionally filtered by location"""
    try:
        config = _get_config()
        loc_filter = request.args.get('location', request.args.get('location_type', 'both')).lower().strip()
        q = apply_location_filter(get_sorted_job_query(), loc_filter)
        jobs = [j.to_dict() for j in q.all()]
        exporter = JobExporter(config)
        filepath = exporter.generate_html_report(jobs)

        return send_file(
            filepath,
            as_attachment=True,
            download_name=os.path.basename(filepath),
            mimetype='text/html'
        )
    except Exception as e:
        logger.error(f"HTML export error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
