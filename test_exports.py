"""Test export endpoints directly"""
import sys
sys.path.insert(0, r"G:\Geonix\vscode\ai\job-finder")

from web.app import create_app
from db.models import db, Job

app = create_app()

with app.app_context():
    # Get jobs from database
    jobs = Job.query.all()
    print(f"Total jobs in DB: {len(jobs)}")

    if jobs:
        # Test export with actual job data
        from export.jobs_exporter import JobExporter
        import yaml

        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        exporter = JobExporter(config)

        # Convert jobs to dict format
        job_dicts = [job.to_dict() for job in jobs]
        print(f"Sample job keys: {list(job_dicts[0].keys()) if job_dicts else 'none'}")

        # Test Excel export
        try:
            result = exporter.export_to_excel(job_dicts)
            print(f"Excel export OK: {result}")
        except Exception as e:
            import traceback
            print(f"Excel error: {e}")
            traceback.print_exc()

        # Test HTML export
        try:
            result = exporter.generate_html_report(job_dicts)
            print(f"HTML export OK: {result}")
        except Exception as e:
            import traceback
            print(f"HTML error: {e}")
            traceback.print_exc()
    else:
        print("No jobs in database to test with")