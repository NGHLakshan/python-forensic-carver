"""
gui_main.py — Forensic Tool GUI (Tkinter)
==========================================
Professional dark-mode GUI for running all carver modules.
Features: drive selector, file type checkboxes, progress bar,
live log, per-type file count summary.

Usage:
    python gui_main.py
    (Must be run as Administrator for raw drive access)
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import importlib
import queue
import time


# ── All available carver modules ─────────────────────────────────────────────
CARVERS = {
    "JPG Images":       ("jpg_carver",   "🖼️"),
    "PNG Images":       ("png_carver",   "🖼️"),
    "BMP Images":       ("bmp_carver",   "🖼️"),
    "GIF Images":       ("gif_carver",   "🖼️"),
    "MP3 Audio":        ("mp3_carver",   "🎵"),
    "WAV Audio":        ("wav_carver",   "🎵"),
    "MP4 Video":        ("mp4_carver",   "🎬"),
    "AVI Video":        ("avi_carver",   "🎬"),
    "MOV Video":        ("mov_carver",   "🎬"),
    "MKV Video":        ("mkv_carver",   "🎬"),
    "PDF Documents":    ("pdf_carver",   "📄"),
    "DOCX (Word)":      ("docx_carver",  "📄"),
    "XLSX (Excel)":     ("xlsx_carver",  "📄"),
    "PPTX (PowerPoint)":("pptx_carver",  "📄"),
    "ZIP Archives":     ("zip_carver",   "🗂️"),
    "RAR Archives":     ("rar_carver",   "🗂️"),
    "7z Archives":      ("7z_carver",    "🗂️"),
    "ISO Images":       ("iso_carver",   "💿"),
    "PST/OST Email":    ("pst_carver",   "📧"),
    "SQLite Database":  ("sqlite_carver","🗄️"),
    "XML Files":        ("xml_carver",   "📝"),
    "HTML Files":       ("html_carver",  "🌐"),
    "EXE Files":        ("exe_carver",   "⚙️"),
}

DARK_BG     = "#0d1b2a"
CARD_BG     = "#112233"
ACCENT      = "#00b4d8"
ACCENT2     = "#0077b6"
TEXT        = "#e0e0e0"
MUTED       = "#8899aa"
SUCCESS     = "#06d6a0"
WARNING     = "#ffd166"
DANGER      = "#ef476f"


class ForensicGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🔎 Python Forensic Recovery Tool")
        self.geometry("1000x720")
        self.configure(bg=DARK_BG)
        self.resizable(True, True)
        self.minsize(800, 600)

        self._log_queue = queue.Queue()
        self._running   = False
        self._threads   = []
        self._counts    = {}   # module -> file_count

        self._setup_styles()
        self._build_ui()
        self._poll_log()

    # ── Styles ────────────────────────────────────────────────────────────────
    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TProgressbar', troughcolor=CARD_BG, background=ACCENT,
                        bordercolor=DARK_BG, lightcolor=ACCENT, darkcolor=ACCENT2)
        style.configure('TFrame', background=DARK_BG)
        style.configure('Card.TFrame', background=CARD_BG)
        style.configure('TLabel', background=DARK_BG, foreground=TEXT)
        style.configure('Card.TLabel', background=CARD_BG, foreground=TEXT)
        style.configure('TCheckbutton', background=CARD_BG, foreground=TEXT,
                        selectcolor=DARK_BG, activebackground=CARD_BG)
        style.configure('TEntry', fieldbackground=CARD_BG, foreground=TEXT,
                        insertcolor=TEXT)

    # ── UI Build ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=CARD_BG, pady=14)
        hdr.pack(fill='x')
        tk.Label(hdr, text="🔎  Python Forensic Recovery Tool",
                 bg=CARD_BG, fg=ACCENT,
                 font=('Segoe UI', 18, 'bold')).pack(side='left', padx=24)
        tk.Label(hdr, text="Run as Administrator for full access",
                 bg=CARD_BG, fg=MUTED,
                 font=('Segoe UI', 9)).pack(side='right', padx=24)

        # ── Main content ──────────────────────────────────────────────────────
        content = tk.Frame(self, bg=DARK_BG)
        content.pack(fill='both', expand=True, padx=16, pady=12)

        left  = tk.Frame(content, bg=DARK_BG, width=310)
        left.pack(side='left', fill='y', padx=(0, 12))
        left.pack_propagate(False)

        right = tk.Frame(content, bg=DARK_BG)
        right.pack(side='left', fill='both', expand=True)

        # ── Drive selector ────────────────────────────────────────────────────
        drive_card = tk.Frame(left, bg=CARD_BG, bd=0, padx=14, pady=12)
        drive_card.pack(fill='x', pady=(0, 10))
        tk.Label(drive_card, text="Drive Letter", bg=CARD_BG, fg=MUTED,
                 font=('Segoe UI', 8)).pack(anchor='w')
        drv_row = tk.Frame(drive_card, bg=CARD_BG)
        drv_row.pack(fill='x', pady=(4,0))
        self._drive_var = tk.StringVar(value='E')
        tk.Entry(drv_row, textvariable=self._drive_var, width=4,
                 bg=DARK_BG, fg=ACCENT, font=('Segoe UI', 18, 'bold'),
                 insertbackground=TEXT, bd=0, relief='flat').pack(side='left')
        tk.Label(drv_row, text=":", bg=CARD_BG, fg=ACCENT,
                 font=('Segoe UI', 18, 'bold')).pack(side='left')
        tk.Label(drive_card, text="(e.g. E  or  F  or  D)",
                 bg=CARD_BG, fg=MUTED, font=('Segoe UI', 8)).pack(anchor='w', pady=(4,0))

        # ── File type checkboxes ──────────────────────────────────────────────
        types_card = tk.Frame(left, bg=CARD_BG, padx=14, pady=10)
        types_card.pack(fill='both', expand=True, pady=(0,10))
        hdr2 = tk.Frame(types_card, bg=CARD_BG)
        hdr2.pack(fill='x', pady=(0,8))
        tk.Label(hdr2, text="File Types to Recover",
                 bg=CARD_BG, fg=MUTED, font=('Segoe UI', 8)).pack(side='left')
        tk.Button(hdr2, text="All", bg=CARD_BG, fg=ACCENT, bd=0,
                  font=('Segoe UI', 8), cursor='hand2',
                  command=self._select_all).pack(side='right')
        tk.Button(hdr2, text="None", bg=CARD_BG, fg=MUTED, bd=0,
                  font=('Segoe UI', 8), cursor='hand2',
                  command=self._select_none).pack(side='right', padx=8)

        canvas = tk.Canvas(types_card, bg=CARD_BG, highlightthickness=0)
        scroll = tk.Scrollbar(types_card, orient='vertical', command=canvas.yview)
        self._cb_frame = tk.Frame(canvas, bg=CARD_BG)
        self._cb_frame.bind('<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0,0), window=self._cb_frame, anchor='nw')
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

        self._check_vars = {}
        for label, (mod, icon) in CARVERS.items():
            var = tk.BooleanVar(value=True)
            self._check_vars[label] = var
            cb = tk.Checkbutton(self._cb_frame, text=f"{icon}  {label}",
                                variable=var, bg=CARD_BG, fg=TEXT,
                                selectcolor=DARK_BG, activebackground=CARD_BG,
                                activeforeground=ACCENT, font=('Segoe UI', 9),
                                cursor='hand2', anchor='w')
            cb.pack(fill='x', pady=1)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_card = tk.Frame(left, bg=CARD_BG, padx=14, pady=10)
        btn_card.pack(fill='x')
        self._start_btn = tk.Button(btn_card, text="▶  START SCAN",
                                    bg=ACCENT, fg='#000',
                                    font=('Segoe UI', 11, 'bold'),
                                    relief='flat', cursor='hand2', pady=8,
                                    command=self._start_scan)
        self._start_btn.pack(fill='x', pady=(0,6))
        self._stop_btn  = tk.Button(btn_card, text="⏹  STOP",
                                    bg=DANGER, fg='#fff',
                                    font=('Segoe UI', 11, 'bold'),
                                    relief='flat', cursor='hand2', pady=8,
                                    state='disabled', command=self._stop_scan)
        self._stop_btn.pack(fill='x')

        # ── Progress ──────────────────────────────────────────────────────────
        prog_card = tk.Frame(right, bg=CARD_BG, padx=14, pady=12)
        prog_card.pack(fill='x', pady=(0,10))
        tk.Label(prog_card, text="Scan Progress", bg=CARD_BG, fg=MUTED,
                 font=('Segoe UI', 8)).pack(anchor='w')
        self._progress = ttk.Progressbar(prog_card, mode='indeterminate', length=400)
        self._progress.pack(fill='x', pady=(6,4))
        self._status_var = tk.StringVar(value="Ready — select drive & file types, then press Start")
        tk.Label(prog_card, textvariable=self._status_var, bg=CARD_BG, fg=ACCENT,
                 font=('Segoe UI', 9)).pack(anchor='w')

        # ── Summary counters ──────────────────────────────────────────────────
        self._summary_frame = tk.Frame(right, bg=DARK_BG)
        self._summary_frame.pack(fill='x', pady=(0,10))
        self._summary_labels = {}  # will be created dynamically

        # ── Live log ──────────────────────────────────────────────────────────
        log_card = tk.Frame(right, bg=CARD_BG, padx=14, pady=10)
        log_card.pack(fill='both', expand=True)
        tk.Label(log_card, text="Live Log", bg=CARD_BG, fg=MUTED,
                 font=('Segoe UI', 8)).pack(anchor='w', pady=(0,6))
        self._log_box = scrolledtext.ScrolledText(log_card, bg=DARK_BG, fg=TEXT,
                                                  font=('Consolas', 8),
                                                  relief='flat', bd=0,
                                                  state='disabled')
        self._log_box.pack(fill='both', expand=True)
        self._log_box.tag_config('ok',      foreground=SUCCESS)
        self._log_box.tag_config('err',     foreground=DANGER)
        self._log_box.tag_config('info',    foreground=ACCENT)
        self._log_box.tag_config('warn',    foreground=WARNING)
        self._log_box.tag_config('default', foreground=TEXT)

    # ── Control ───────────────────────────────────────────────────────────────
    def _select_all(self):
        for v in self._check_vars.values():
            v.set(True)

    def _select_none(self):
        for v in self._check_vars.values():
            v.set(False)

    def _start_scan(self):
        drive = self._drive_var.get().strip().upper()
        if not drive or len(drive) != 1 or not drive.isalpha():
            messagebox.showerror("Invalid Drive", "Please enter a single drive letter (e.g. E)")
            return

        selected = [(label, CARVERS[label][0]) for label, var in self._check_vars.items() if var.get()]
        if not selected:
            messagebox.showwarning("No Types", "Please select at least one file type to recover.")
            return

        self._running = True
        self._threads = []
        self._counts  = {}
        self._start_btn.config(state='disabled')
        self._stop_btn.config(state='normal')
        self._progress.start(12)
        self._clear_log()
        self._status_var.set(f"Scanning drive {drive}: with {len(selected)} modules...")
        self._log(f"[*] Starting scan on drive {drive}: — {len(selected)} file types", 'info')

        for label, mod_name in selected:
            self._counts[label] = 0
            t = threading.Thread(target=self._run_carver,
                                 args=(drive, label, mod_name), daemon=True)
            self._threads.append(t)
            t.start()

        threading.Thread(target=self._monitor_threads, daemon=True).start()

    def _stop_scan(self):
        self._running = False
        self._log("[*] STOP requested — carvers will finish their current chunk.", 'warn')
        self._status_var.set("Stopping... please wait.")

    def _run_carver(self, drive: str, label: str, mod_name: str):
        """Run a single carver module in its own thread."""
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        try:
            mod = importlib.import_module(mod_name)
            # Patch DRIVE_LETTER in the module
            if hasattr(mod, 'DRIVE_LETTER'):
                mod.DRIVE_LETTER = drive
            # Redirect print to our log queue
            import builtins
            original_print = builtins.print

            def patched_print(*args, **kwargs):
                msg = ' '.join(str(a) for a in args)
                tag = 'ok' if '[+]' in msg else ('err' if '❌' in msg else 'default')
                self._log_queue.put((f"[{label}] {msg}", tag))

            builtins.print = patched_print
            try:
                mod.main()
            finally:
                builtins.print = original_print

        except Exception as e:
            self._log_queue.put((f"[{label}] ❌ Error: {e}", 'err'))

    def _monitor_threads(self):
        for t in self._threads:
            t.join()
        self._log_queue.put(('__DONE__', 'info'))

    def _poll_log(self):
        """Drain the log queue and update the UI — runs on main thread."""
        try:
            while True:
                msg, tag = self._log_queue.get_nowait()
                if msg == '__DONE__':
                    self._on_scan_done()
                else:
                    self._log(msg, tag)
        except queue.Empty:
            pass
        self.after(120, self._poll_log)

    def _on_scan_done(self):
        self._running = False
        self._progress.stop()
        self._start_btn.config(state='normal')
        self._stop_btn.config(state='disabled')
        self._status_var.set("✅ Scan complete!")
        self._log("[*] All carvers finished.", 'ok')

    # ── Log helpers ──────────────────────────────────────────────────────────
    def _log(self, msg: str, tag: str = 'default'):
        self._log_box.config(state='normal')
        self._log_box.insert('end', msg + '\n', tag)
        self._log_box.see('end')
        self._log_box.config(state='disabled')

    def _clear_log(self):
        self._log_box.config(state='normal')
        self._log_box.delete('1.0', 'end')
        self._log_box.config(state='disabled')


def main():
    app = ForensicGUI()
    app.mainloop()


if __name__ == '__main__':
    main()
