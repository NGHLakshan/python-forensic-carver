"""
report_generator.py — HTML Recovery Report Generator
======================================================
After a carving session, generates a professional HTML report
with: session info, file-type breakdown, per-file hashes.

Usage:
    python report_generator.py            (auto-scans Recovered_* folders)
or:
    from report_generator import generate_report
    generate_report(session_data)
"""

import os
import hashlib
import datetime
import json


def _md5(path):
    h = hashlib.md5()
    try:
        with open(path, 'rb') as f:
            for b in iter(lambda: f.read(65536), b''):
                h.update(b)
        return h.hexdigest()
    except Exception:
        return 'ERROR'


def _sha256(path):
    h = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            for b in iter(lambda: f.read(65536), b''):
                h.update(b)
        return h.hexdigest()
    except Exception:
        return 'ERROR'


def _scan_recovered_folders():
    """Auto-discover files in Recovered_* folders."""
    data = {}   # category -> list of {name, path, size}
    for d in os.listdir('.'):
        if d.startswith('Recovered_') and os.path.isdir(d):
            category = d.replace('Recovered_', '')
            files = []
            for root, _, fnames in os.walk(d):
                for f in fnames:
                    fpath = os.path.join(root, f)
                    files.append({'name': f, 'path': fpath, 'size': os.path.getsize(fpath)})
            if files:
                data[category] = files
    return data


def generate_report(session_data: dict = None, drive_letter: str = 'E', output_dir: str = '.'):
    """
    Generate a self-contained HTML report.
    session_data: {category: [{name, path, size}, ...]}
    """
    if session_data is None:
        session_data = _scan_recovered_folders()

    if not session_data:
        print("❌ No recovered files found. Run a carver first!")
        return

    now = datetime.datetime.now()
    timestamp = now.strftime('%Y%m%d_%H%M%S')
    report_path = os.path.join(output_dir, f"Recovery_Report_{timestamp}.html")

    # Tally totals
    totals = {}
    all_files = []
    grand_total_size = 0
    for cat, files in session_data.items():
        totals[cat] = {'count': len(files), 'size': sum(f['size'] for f in files)}
        grand_total_size += totals[cat]['size']
        for f in files:
            all_files.append((cat, f))

    # Build bar chart data
    max_count = max((v['count'] for v in totals.values()), default=1)
    bar_rows = ''
    for cat, stats in sorted(totals.items(), key=lambda x: -x[1]['count']):
        pct = int((stats['count'] / max_count) * 100)
        size_mb = stats['size'] / (1024 * 1024)
        bar_rows += f'''
        <tr>
          <td>{cat}</td>
          <td>{stats['count']}</td>
          <td>{size_mb:.2f} MB</td>
          <td><div class="bar" style="width:{pct}%"></div></td>
        </tr>'''

    # Build file table rows with hashes
    file_rows = ''
    print("\n[Report] Computing hashes for all files...")
    for i, (cat, f) in enumerate(all_files, 1):
        md5  = _md5(f['path'])
        sha  = _sha256(f['path'])
        size_kb = f['size'] / 1024
        print(f"  [{i}/{len(all_files)}] {f['name']}", flush=True)
        file_rows += f'''
        <tr>
          <td>{i}</td>
          <td><span class="badge">{cat}</span></td>
          <td>{f['name']}</td>
          <td>{size_kb:.1f} KB</td>
          <td class="hash">{md5}</td>
          <td class="hash">{sha[:32]}...</td>
        </tr>'''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Forensic Recovery Report — {now.strftime("%Y-%m-%d %H:%M")}</title>
<style>
  :root {{--accent:#00b4d8;--dark:#0d1b2a;--card:#112233;--text:#e0e0e0;--muted:#8899aa}}
  * {{box-sizing:border-box;margin:0;padding:0}}
  body {{font-family:'Segoe UI',system-ui,sans-serif;background:var(--dark);color:var(--text);padding:40px 20px}}
  h1 {{color:var(--accent);font-size:2rem;margin-bottom:4px}}
  .sub {{color:var(--muted);margin-bottom:30px;font-size:.9rem}}
  .cards {{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:30px}}
  .card {{background:var(--card);border-radius:10px;padding:20px 28px;flex:1;min-width:160px;border-left:3px solid var(--accent)}}
  .card h3 {{font-size:2rem;color:var(--accent)}}
  .card p  {{font-size:.8rem;color:var(--muted);margin-top:4px}}
  h2 {{color:var(--accent);font-size:1.2rem;margin:28px 0 12px}}
  table {{width:100%;border-collapse:collapse;font-size:.85rem}}
  th {{background:var(--accent);color:#000;padding:10px 12px;text-align:left}}
  td {{padding:9px 12px;border-bottom:1px solid #1e3050}}
  tr:hover td {{background:#1a2d42}}
  .bar {{height:14px;background:var(--accent);border-radius:4px;opacity:.8}}
  .badge {{background:var(--accent);color:#000;border-radius:4px;padding:2px 8px;font-size:.75rem;font-weight:700}}
  .hash {{font-family:monospace;font-size:.75rem;color:var(--muted)}}
  .footer {{margin-top:40px;color:var(--muted);font-size:.8rem;text-align:center}}
</style>
</head>
<body>
<h1>🔎 Forensic Recovery Report</h1>
<p class="sub">Generated: {now.strftime("%Y-%m-%d %H:%M:%S")} &nbsp;|&nbsp; Drive: {drive_letter}:</p>

<div class="cards">
  <div class="card"><h3>{sum(v['count'] for v in totals.values())}</h3><p>Total Files Recovered</p></div>
  <div class="card"><h3>{len(totals)}</h3><p>File Type Categories</p></div>
  <div class="card"><h3>{grand_total_size / (1024*1024):.1f} MB</h3><p>Total Data Recovered</p></div>
  <div class="card"><h3>{now.strftime("%H:%M")}</h3><p>Report Generated At</p></div>
</div>

<h2>📊 Recovery Breakdown</h2>
<table>
  <tr><th>Category</th><th>Files</th><th>Size</th><th>Volume</th></tr>
  {bar_rows}
</table>

<h2>📁 Recovered File Manifest</h2>
<table>
  <tr><th>#</th><th>Type</th><th>Filename</th><th>Size</th><th>MD5</th><th>SHA-256 (preview)</th></tr>
  {file_rows}
</table>

<div class="footer">
  Python Forensic Tool — Auto-generated report &nbsp;|&nbsp; For investigative use only
</div>
</body>
</html>'''

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n✅ Report saved: {os.path.abspath(report_path)}")
    print("   Open this file in any web browser to view.")
    return report_path


def main():
    drive = input("Enter drive letter (e.g. E) [for report header]: ").strip().upper() or 'E'
    generate_report(drive_letter=drive)


if __name__ == '__main__':
    main()
