"""
chain_of_custody.py — Forensic Evidence Chain of Custody Logger
================================================================
Creates a timestamped, tamper-evident log of every recovery session.
Records: drive identifier, recovered files, hashes, byte offsets.

Usage:
    from chain_of_custody import CustodyLog
    log = CustodyLog(drive_letter='E')
    log.start()
    log.log_file("carved_1.jpg", size=204800, offset=32768)
    log.finish(total_files=1)
"""

import os
import hashlib
import datetime
import time


def _sha256_file(path: str) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return "ERROR"


def _md5_file(path: str) -> str:
    """Compute MD5 hash of a file."""
    h = hashlib.md5()
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return "ERROR"


def _drive_fingerprint(drive_letter: str) -> str:
    """
    Read the first 512 bytes (MBR) of the drive and compute its SHA-256.
    This serves as a unique drive identifier for evidence linking.
    """
    try:
        drive_path = f'\\\\.\\{drive_letter}:'
        with open(drive_path, 'rb') as d:
            mbr = d.read(512)
        return hashlib.sha256(mbr).hexdigest()
    except Exception as e:
        return f"UNAVAILABLE ({e})"


class CustodyLog:
    def __init__(self, drive_letter: str = 'E', output_dir: str = '.'):
        self.drive_letter = drive_letter.upper()
        self.output_dir   = output_dir
        self.timestamp    = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_path     = os.path.join(output_dir, f"custody_log_{self.timestamp}.txt")
        self._lines       = []
        self._start_time  = None

    def _write(self, line: str = ''):
        self._lines.append(line)

    def start(self):
        """Call this at the beginning of a carving session."""
        self._start_time = time.time()
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        drive_fp = _drive_fingerprint(self.drive_letter)

        self._write("=" * 72)
        self._write("           FORENSIC CHAIN OF CUSTODY LOG")
        self._write("=" * 72)
        self._write(f"  Session Start  : {now}")
        self._write(f"  Drive Letter   : {self.drive_letter}:")
        self._write(f"  Drive SHA-256  : {drive_fp}")
        self._write(f"  Log File       : {self.log_path}")
        self._write("=" * 72)
        self._write("")
        self._write(f"{'#':<6} {'Filename':<40} {'Size (B)':>12}  {'Offset':>14}  {'MD5'}")
        self._write("-" * 120)
        self._flush()
        print(f"[Custody] Log started: {self.log_path}")

    def log_file(self, filepath: str, size: int = None, offset: int = None):
        """Log a single recovered file entry."""
        fname = os.path.basename(filepath)
        if size is None:
            try:
                size = os.path.getsize(filepath)
            except Exception:
                size = 0
        md5  = _md5_file(filepath)
        sha  = _sha256_file(filepath)
        off_str = f"{offset:,}" if offset is not None else "N/A"

        count = len([l for l in self._lines if l and l[0].isdigit()])
        entry_num = count + 1

        self._write(f"{entry_num:<6} {fname:<40} {size:>12,}  {off_str:>14}  {md5}")
        self._write(f"{'':6} SHA-256: {sha}")
        self._flush()

    def finish(self, total_files: int = 0, notes: str = ''):
        """Call this at the end of a carving session."""
        elapsed = time.time() - self._start_time if self._start_time else 0
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self._write("")
        self._write("=" * 72)
        self._write(f"  Session End    : {now}")
        self._write(f"  Total Files    : {total_files}")
        self._write(f"  Elapsed Time   : {elapsed:.1f} seconds")
        if notes:
            self._write(f"  Notes          : {notes}")
        self._write("=" * 72)
        self._flush()
        print(f"[Custody] Log complete: {self.log_path} ({total_files} files logged)")

    def _flush(self):
        """Write all buffered lines to the log file."""
        with open(self.log_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self._lines))


# ── Standalone: Hash all files in Recovered_* folders ────────────────────────

def main():
    print("\n╔═══════════════════════════════════════════════╗")
    print("║    Chain of Custody Logger — Standalone Mode  ║")
    print("╚═══════════════════════════════════════════════╝\n")

    drive_letter = input("Enter drive letter to fingerprint (e.g. E): ").strip().upper() or 'E'
    log = CustodyLog(drive_letter=drive_letter)
    log.start()

    recovered_dirs = [d for d in os.listdir('.') if d.startswith('Recovered_') and os.path.isdir(d)]
    if not recovered_dirs:
        print("❌ No Recovered_* folders found.")
        log.finish(total_files=0, notes="No recovered files found.")
        return

    total = 0
    for folder in recovered_dirs:
        for root, _, files in os.walk(folder):
            for fname in files:
                fpath = os.path.join(root, fname)
                print(f"  [*] Hashing {fname}...", flush=True)
                log.log_file(fpath)
                total += 1

    log.finish(total_files=total)
    print(f"\n✅ Done. {total} files logged.")


if __name__ == '__main__':
    main()
