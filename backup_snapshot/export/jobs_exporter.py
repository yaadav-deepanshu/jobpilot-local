"""
Export system for Job Finder
Exports jobs to Excel (.xlsx), PDF (.pdf), and interactive HTML (.html)
"""

import os
import logging
from typing import List, Dict, Any
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

class JobExporter:
    """Generate professional exports for discovered jobs"""

    def __init__(self, config: dict):
        self.config = config
        self.export_dir = os.path.join(os.getcwd(), 'exports')
        os.makedirs(self.export_dir, exist_ok=True)

    @staticmethod
    def _sort_by_platform_priority(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort jobs: LinkedIn (1) -> Indeed (2) -> Naukri (3) -> Rest (4), then date_posted desc"""
        priority_map = {'linkedin': 1, 'indeed': 2, 'naukri': 3}
        def get_sort_key(j):
            p = priority_map.get((j.get('platform') or '').lower(), 4)
            dt = j.get('date_posted')
            ts = 0.0
            if dt:
                if hasattr(dt, 'timestamp'):
                    try:
                        ts = dt.timestamp()
                    except Exception:
                        ts = 0.0
                elif isinstance(dt, str):
                    try:
                        ts = datetime.fromisoformat(dt.replace('Z', '+00:00')).timestamp()
                    except Exception:
                        ts = 0.0
            return (p, -ts)
        return sorted(jobs, key=get_sort_key)

    def export_to_excel(self, jobs: List[Dict[str, Any]], filename: str = None) -> str:
        """Export to multi-tab formatted Excel sheet in platform priority order"""
        jobs = self._sort_by_platform_priority(jobs)
        if not filename:
            filename = f"job_finder_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        filepath = os.path.join(self.export_dir, filename)

        df = pd.DataFrame(jobs) if jobs else pd.DataFrame()

        # Ensure standard columns
        default_columns = ['platform', 'title', 'company', 'location', 'url', 'salary', 'date_posted', 'status', 'description']
        for col in default_columns:
            if col not in df.columns:
                df[col] = ''

        # Reorder columns
        ordered_cols = [c for c in default_columns if c in df.columns]
        extra_cols = [c for c in df.columns if c not in default_columns]
        df = df[ordered_cols + extra_cols]

        # Strip timezones for Excel compatibility (openpyxl rejects timezone-aware datetimes)
        for col in df.columns:
            def strip_tz(val):
                if isinstance(val, datetime) and val.tzinfo is not None:
                    return val.replace(tzinfo=None)
                if hasattr(val, 'tz_localize'):
                    try:
                        return val.tz_localize(None)
                    except Exception:
                        return str(val)
                return val
            df[col] = df[col].apply(strip_tz)

        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # 1. All Jobs
            df.to_excel(writer, sheet_name='All Jobs', index=False)

            # 2. Platform Breakdown
            if len(df) > 0 and 'platform' in df.columns:
                summary = df.groupby('platform').size().reset_index(name='Total Jobs')
                summary.to_excel(writer, sheet_name='By Platform', index=False)
            else:
                pd.DataFrame(columns=['Platform', 'Total Jobs']).to_excel(writer, sheet_name='By Platform', index=False)

            # 3. Direct Application Links
            links_df = df[['platform', 'title', 'company', 'location', 'url', 'status']].copy()
            links_df.to_excel(writer, sheet_name='Direct Links', index=False)

            # Format column widths
            for sheetname in writer.book.sheetnames:
                ws = writer.sheets[sheetname]
                for col in ws.columns:
                    col_letter = col[0].column_letter
                    max_len = max(len(str(cell.value or '')) for cell in col)
                    ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

        logger.info(f"✓ Excel exported: {filepath}")
        return filepath

    def export_to_pdf(self, jobs: List[Dict[str, Any]], filename: str = None) -> str:
        """Export formatted PDF report in platform priority order"""
        jobs = self._sort_by_platform_priority(jobs)
        if not filename:
            filename = f"job_finder_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        filepath = os.path.join(self.export_dir, filename)

        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER

        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        story = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            'Header',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#4f46e5'),
            alignment=TA_CENTER,
            spaceAfter=15
        )
        story.append(Paragraph("🎯 Job Finder — Discovered Opportunities", title_style))
        story.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))

        # Stats Table
        applied_cnt = sum(1 for j in jobs if j.get('status') == 'applied')
        saved_cnt = sum(1 for j in jobs if j.get('status') == 'saved')
        new_cnt = sum(1 for j in jobs if j.get('status') == 'new')

        summary_data = [
            ['Total Jobs Found', 'New / Unreviewed', 'Applied', 'Saved'],
            [str(len(jobs)), str(new_cnt), str(applied_cnt), str(saved_cnt)],
        ]
        stat_table = Table(summary_data, colWidths=[1.8 * inch, 1.8 * inch, 1.8 * inch, 1.8 * inch])
        stat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f8fafc')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ]))
        story.append(stat_table)
        story.append(Spacer(1, 0.3 * inch))

        # Jobs Listing
        story.append(Paragraph("Job Listings", styles['Heading2']))
        story.append(Spacer(1, 0.1 * inch))

        # List up to 80 jobs
        for i, j in enumerate(jobs[:80], 1):
            url = j.get('url', '#')
            title = j.get('title', 'N/A')
            comp = j.get('company', 'N/A')
            loc = j.get('location', 'N/A')
            plat = (j.get('platform') or 'N/A').upper()
            status = j.get('status', 'new').upper()

            job_p = f"""
            <b>{i}. {title}</b> — <font color="#4f46e5"><b>{comp}</b></font><br/>
            📍 Location: {loc} &nbsp;|&nbsp; 🌐 Platform: <b>{plat}</b> &nbsp;|&nbsp; Status: <b>{status}</b><br/>
            🔗 Link: <a href="{url}" color="#2563eb">{url[:60]}...</a>
            """
            story.append(Paragraph(job_p, styles['Normal']))
            story.append(Spacer(1, 0.1 * inch))

        doc.build(story)
        logger.info(f"✓ PDF exported: {filepath}")
        return filepath

    def generate_html_report(self, jobs: List[Dict[str, Any]], filename: str = None) -> str:
        """Generate interactive HTML dashboard report in platform priority order"""
        jobs = self._sort_by_platform_priority(jobs)
        if not filename:
            filename = f"job_finder_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

        filepath = os.path.join(self.export_dir, filename)

        df = pd.DataFrame(jobs) if jobs else pd.DataFrame()
        platform_counts = {}
        if len(df) > 0 and 'platform' in df.columns:
            platform_counts = df['platform'].value_counts().to_dict()

        status_counts = {}
        if len(df) > 0 and 'status' in df.columns:
            status_counts = df['status'].value_counts().to_dict()

        table_rows = []
        for i, j in enumerate(jobs, 1):
            plat = (j.get('platform') or 'unknown').lower()
            status = (j.get('status') or 'new').lower()
            url = j.get('url') or '#'
            title = j.get('title') or 'N/A'
            company = j.get('company') or 'N/A'
            loc = j.get('location') or 'N/A'
            posted = j.get('date_posted') or ''
            if hasattr(posted, 'strftime'):
                posted = posted.strftime('%Y-%m-%d')
            else:
                posted = str(posted)[:10]

            row_html = f"""
            <tr>
                <td>{i}</td>
                <td><span class="badge badge-{plat}">{plat}</span></td>
                <td><strong>{title}</strong></td>
                <td>{company}</td>
                <td>{loc}</td>
                <td>{posted}</td>
                <td><span class="status status-{status}">{status}</span></td>
                <td><a href="{url}" target="_blank" class="btn-link">Apply →</a></td>
            </tr>
            """
            table_rows.append(row_html)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Discovery Report — {datetime.now().strftime('%Y-%m-%d')}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: #f1f5f9;
            color: #0f172a;
            padding: 30px 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.06);
            padding: 32px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 20px;
            margin-bottom: 24px;
        }}
        h1 {{ color: #4338ca; font-size: 26px; }}
        .timestamp {{ color: #64748b; font-size: 14px; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%);
            color: #ffffff;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        .stat-card.stat-green {{ background: linear-gradient(135deg, #059669 0%, #10b981 100%); }}
        .stat-card.stat-amber {{ background: linear-gradient(135deg, #d97706 0%, #f59e0b 100%); }}
        .stat-card.stat-purple {{ background: linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%); }}
        .stat-card .val {{ font-size: 32px; font-weight: 700; margin-top: 6px; }}
        .charts-row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .chart-box {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 20px;
        }}
        .chart-box h3 {{ font-size: 16px; margin-bottom: 12px; color: #334155; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
            margin-top: 15px;
        }}
        th {{
            background: #4338ca;
            color: white;
            text-align: left;
            padding: 12px 14px;
            font-weight: 600;
        }}
        td {{
            padding: 12px 14px;
            border-bottom: 1px solid #e2e8f0;
        }}
        tr:hover td {{ background: #f8fafc; }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            color: white;
        }}
        .badge-linkedin {{ background: #0a66c2; }}
        .badge-indeed {{ background: #003da5; }}
        .badge-naukri {{ background: #ff6600; }}
        .badge-glassdoor {{ background: #0caa41; }}
        .badge-unknown {{ background: #64748b; }}
        .status {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .status-new {{ background: #e0e7ff; color: #3730a3; }}
        .status-applied {{ background: #dcfce7; color: #166534; }}
        .status-saved {{ background: #fef3c7; color: #92400e; }}
        .status-rejected {{ background: #fee2e2; color: #991b1b; }}
        .btn-link {{
            color: #4338ca;
            text-decoration: none;
            font-weight: 600;
        }}
        .btn-link:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>🎯 Discovered Job Report</h1>
                <div class="timestamp">Exported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div>Total Jobs</div>
                <div class="val">{len(jobs)}</div>
            </div>
            <div class="stat-card stat-purple">
                <div>Platforms</div>
                <div class="val">{len(platform_counts)}</div>
            </div>
            <div class="stat-card stat-green">
                <div>Applied</div>
                <div class="val">{sum(1 for j in jobs if j.get('status') == 'applied')}</div>
            </div>
            <div class="stat-card stat-amber">
                <div>Saved</div>
                <div class="val">{sum(1 for j in jobs if j.get('status') == 'saved')}</div>
            </div>
        </div>

        <div class="charts-row">
            <div class="chart-box">
                <h3>Jobs by Platform</h3>
                <canvas id="platChart" height="200"></canvas>
            </div>
            <div class="chart-box">
                <h3>Jobs by Status</h3>
                <canvas id="statChart" height="200"></canvas>
            </div>
        </div>

        <h3>All Job Listings ({len(jobs)})</h3>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Platform</th>
                    <th>Role Title</th>
                    <th>Company</th>
                    <th>Location</th>
                    <th>Posted</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {''.join(table_rows) if table_rows else '<tr><td colspan="8" style="text-align:center;">No jobs to show</td></tr>'}
            </tbody>
        </table>
    </div>

    <script>
        const platData = {list(platform_counts.values())};
        const platLabels = {list(platform_counts.keys())};
        new Chart(document.getElementById('platChart'), {{
            type: 'doughnut',
            data: {{
                labels: platLabels.length ? platLabels : ['None'],
                datasets: [{{
                    data: platData.length ? platData : [1],
                    backgroundColor: ['#0a66c2', '#003da5', '#ff6600', '#0caa41', '#64748b']
                }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false }}
        }});

        const statData = {list(status_counts.values())};
        const statLabels = {list(status_counts.keys())};
        new Chart(document.getElementById('statChart'), {{
            type: 'pie',
            data: {{
                labels: statLabels.length ? statLabels : ['None'],
                datasets: [{{
                    data: statData.length ? statData : [1],
                    backgroundColor: ['#4f46e5', '#10b981', '#f59e0b', '#ef4444']
                }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false }}
        }});
    </script>
</body>
</html>
"""

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"✓ HTML report exported: {filepath}")
        return filepath
