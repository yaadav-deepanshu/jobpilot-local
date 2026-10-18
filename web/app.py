"""
Updated Flask app with export routes
"""

import os
import logging
from flask import Flask, render_template, jsonify, request
from datetime import datetime
from db.models import db, Job, ApplicationLog
import yaml

logger = logging.getLogger(__name__)

def create_app(config_override=None):
    """Create and configure Flask app"""
    app = Flask(__name__)

    # Configuration defaults
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jobs.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'job-finder-secret-key'
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max for exports
    app.config['TEMPLATES_AUTO_RELOAD'] = True

    # Apply any overrides before initializing extensions
    if config_override:
        app.config.update(config_override)

    # Initialize database
    db.init_app(app)

    # Load config
    with app.app_context():
        if os.path.exists('config.yaml'):
            with open('config.yaml', 'r') as f:
                app.config['JOB_CONFIG'] = yaml.safe_load(f)

    # Register blueprints
    from web.routes import main_bp, api_bp
    from export.routes import export_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(export_bp, url_prefix='/export')

    return app
