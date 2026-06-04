"""
api_server.py — Forensic Tool  (SECURE - NATIVE WINDOW)
========================================================
Security hardening:
  • Binds to 127.0.0.1 ONLY  (no remote/network access)
  • One-time secret token on every request
  • Opens in a native desktop window (pywebview / Edge WebView2)
    — NO browser address bar, NO history, NO extensions
  • No external resource loading
"""

import os
import sys
import threading
import importlib
import queue
import json
import builtins
import time
import secrets

# Force UTF-8 output so Windows cp1252 never causes UnicodeEncodeError
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from flask import Flask, jsonify, request, Response, abort

# ── Paths ─────────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
    run_dir  = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    run_dir  = base_dir

sys.path.insert(0, run_dir)
if run_dir != base_dir:
    sys.path.insert(0, base_dir)

web_ui_path = os.path.join(base_dir, "web_ui")

# ── One-time secret token ─────────────────────────────────────────────────────
_SECRET_TOKEN = secrets.token_hex(32)

app = Flask(__name__, static_folder=web_ui_path)

# ── Security middleware ───────────────────────────────────────────────────────
@app.before_request
def verify_token():
    token = request.args.get("token") or request.headers.get("X-Forensic-Token")
    if token != _SECRET_TOKEN:
        abort(403)

# ── Carver registry ───────────────────────────────────────────────────────────
CARVERS = {
    "JPG Images":        {"module": "jpg_carver",    "icon": "🖼️",  "category": "Images"},
    "PNG Images":        {"module": "png_carver",    "icon": "🖼️",  "category": "Images"},
    "BMP Images":        {"module": "bmp_carver",    "icon": "🖼️",  "category": "Images"},
    "GIF Images":        {"module": "gif_carver",    "icon": "🖼️",  "category": "Images"},
    "MP3 Audio":         {"module": "mp3_carver",    "icon": "🎵",  "category": "Audio"},
    "WAV Audio":         {"module": "wav_carver",    "icon": "🎵",  "category": "Audio"},
    "MP4 Video":         {"module": "mp4_carver",    "icon": "🎬",  "category": "Video"},
    "AVI Video":         {"module": "avi_carver",    "icon": "🎬",  "category": "Video"},
    "MOV Video":         {"module": "mov_carver",    "icon": "🎬",  "category": "Video"},
    "MKV Video":         {"module": "mkv_carver",    "icon": "🎬",  "category": "Video"},
    "PDF Documents":     {"module": "pdf_carver",    "icon": "📄",  "category": "Documents"},
    "DOCX (Word)":       {"module": "docx_carver",   "icon": "📄",  "category": "Documents"},
    "XLSX (Excel)":      {"module": "xlsx_carver",   "icon": "📄",  "category": "Documents"},
    "PPTX (PowerPoint)": {"module": "pptx_carver",   "icon": "📄",  "category": "Documents"},
    "ZIP Archives":      {"module": "zip_carver",    "icon": "🗂️",  "category": "Archives"},
    "RAR Archives":      {"module": "rar_carver",    "icon": "🗂️",  "category": "Archives"},
    "7z Archives":       {"module": "7z_carver",     "icon": "🗂️",  "category": "Archives"},
    "ISO Images":        {"module": "iso_carver",    "icon": "💿",  "category": "Archives"},
    "PST/OST Email":     {"module": "pst_carver",    "icon": "📧",  "category": "Other"},
    "SQLite Database":   {"module": "sqlite_carver", "icon": "🗄️",  "category": "Other"},
    "XML Files":         {"module": "xml_carver",    "icon": "📝",  "category": "Documents"},
    "HTML Files":        {"module": "html_carver",   "icon": "🌐",  "category": "Documents"},
    "EXE Files":         {"module": "exe_carver",    "icon": "⚙️",  "category": "Other"},
}

# ── Global scan state ─────────────────────────────────────────────────────────
_scan_state = {
    "running": False,
    "drive": None,
    "selected": [],
    "log_queue": queue.Queue(),
    "counts": {},
    "threads": [],
}

_clients: list[queue.Queue] = []

# ══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    html_path = os.path.join(web_ui_path, "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("__SESSION_TOKEN__", _SECRET_TOKEN)
    response = Response(html, mimetype="text/html")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/api/carvers", methods=["GET"])
def get_carvers():
    return jsonify({
        "carvers": [
            {"label": lbl, "module": info["module"],
             "icon": info["icon"], "category": info["category"]}
            for lbl, info in CARVERS.items()
        ]
    })


@app.route("/api/select_folder", methods=["POST"])
def select_folder():
    import webview
    try:
        if not webview.windows:
            raise Exception("No active webview window found.")
        window = webview.windows[0]
        folders = window.create_file_dialog(webview.FOLDER_DIALOG)
        
        dest_folder = folders[0] if folders and len(folders) > 0 else ""
        return jsonify({"folder": dest_folder})
    except Exception as e:
        _push_log(f"[!] Target folder selection error: {e}", "err")
        return jsonify({"error": str(e)}), 500


@app.route("/api/scan/start", methods=["POST"])
def start_scan():
    if _scan_state["running"]:
        return jsonify({"error": "Scan already running"}), 409
        
    data = request.get_json(force=True)
    drive = data.get("drive", "").strip().upper()
    output_folder = data.get("output_folder", "").strip()
    selected_labels = data.get("selected", [])
    
    if not drive or len(drive) != 1 or not drive.isalpha():
        return jsonify({"error": "Invalid drive letter"}), 400
    if not selected_labels:
        return jsonify({"error": "No file types selected"}), 400
        
    selected = [(lbl, CARVERS[lbl]["module"]) for lbl in selected_labels if lbl in CARVERS]
    
    # ── Override Working Directory before starting scripts ──
    if output_folder and os.path.exists(output_folder):
        os.chdir(output_folder)
        _push_log(f"[*] Output directory set to: {output_folder}", "info")
    else:
        # Revert to standard app directory if empty/invalid
        os.chdir(base_dir)
        if output_folder:
            _push_log(f"[!] Warning: Folder {output_folder} invalid. Using default.", "warn")

    _scan_state.update({
        "running": True, "drive": drive, "selected": selected,
        "counts": {lbl: 0 for lbl, _ in selected}, "threads": []
    })
    while not _scan_state["log_queue"].empty():
        _scan_state["log_queue"].get_nowait()
    _push_log(f"[*] Starting scan on drive {drive}: — {len(selected)} file types", "info")
    for label, mod_name in selected:
        t = threading.Thread(target=_run_carver, args=(drive, label, mod_name), daemon=True)
        _scan_state["threads"].append(t)
        t.start()
    threading.Thread(target=_monitor_threads, daemon=True).start()
    return jsonify({"status": "started", "drive": drive, "modules": len(selected)})


@app.route("/api/scan/stop", methods=["POST"])
def stop_scan():
    if not _scan_state["running"]:
        return jsonify({"error": "No scan running"}), 409
    _scan_state["running"] = False
    _push_log("[!] STOP requested — carvers will finish their current chunk.", "warn")
    return jsonify({"status": "stopping"})


@app.route("/api/scan/status", methods=["GET"])
def scan_status():
    return jsonify({"running": _scan_state["running"],
                    "drive": _scan_state["drive"],
                    "counts": _scan_state["counts"]})


@app.route("/api/scan/logs", methods=["GET"])
def stream_logs():
    def event_stream():
        client_q = queue.Queue()
        _clients.append(client_q)
        try:
            while True:
                try:
                    msg = client_q.get(timeout=20)
                    yield f"data: {json.dumps(msg)}\n\n"
                except queue.Empty:
                    yield ": ping\n\n"
        finally:
            _clients.remove(client_q)
    return Response(event_stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── Helpers ──────────────────────────────────────────────────────────────────
def _push_log(message: str, tag: str = "default"):
    payload = {"msg": message, "tag": tag, "ts": time.strftime("%H:%M:%S")}
    _scan_state["log_queue"].put(payload)
    for cq in list(_clients):
        cq.put(payload)


def _run_carver(drive: str, label: str, mod_name: str):
    original_print = builtins.print
    try:
        mod = importlib.import_module(mod_name)
        if hasattr(mod, "DRIVE_LETTER"):
            mod.DRIVE_LETTER = drive

        def patched_print(*args, **kwargs):
            msg = " ".join(str(a) for a in args)
            tag = "ok" if "[+]" in msg else ("err" if "❌" in msg or "[!]" in msg else "default")
            _push_log(f"[{label}] {msg}", tag)
            if "[+]" in msg:
                _scan_state["counts"][label] = _scan_state["counts"].get(label, 0) + 1

        builtins.print = patched_print
        try:
            mod.main()
        finally:
            builtins.print = original_print
    except Exception as e:
        builtins.print = original_print
        _push_log(f"[{label}] ❌ Error: {e}", "err")


def _monitor_threads():
    for t in _scan_state["threads"]:
        t.join()
    _scan_state["running"] = False
    _push_log("[✔] All carvers finished.", "ok")
    _push_log("__DONE__", "done")


# ── Flask server thread ───────────────────────────────────────────────────────
def _start_flask():
    """Run Flask silently on 127.0.0.1 only."""
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host="127.0.0.1", port=5000, threaded=True, debug=False, use_reloader=False)


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import webview

    url = f"http://127.0.0.1:5000/?token={_SECRET_TOKEN}&v={time.time()}"

    # Start Flask in background thread
    flask_thread = threading.Thread(target=_start_flask, daemon=True)
    flask_thread.start()

    # Wait briefly for Flask to be ready
    time.sleep(1.5)

    # Create native window — no address bar, no browser chrome
    window = webview.create_window(
        title="🔎 Python Forensic Recovery Tool",
        url=url,
        width=1280,
        height=800,
        min_size=(900, 600),
        resizable=True,
        shadow=True,
    )

    # Start the webview event loop (this blocks until window is closed)
    webview.start(debug=False)
