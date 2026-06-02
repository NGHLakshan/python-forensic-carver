"""
file_validator.py — Post-Recovery File Integrity Validator
============================================================
Scans all Recovered_* folders and validates each file.
Results:  VALID | CORRUPT | PARTIAL

Usage:
    python file_validator.py
or import and call:
    from file_validator import validate_file
    status = validate_file("path/to/file.jpg")
"""

import os
import zipfile
import struct

# Try importing PIL — optional
try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ── Validators ──────────────────────────────────────────────────────────────

def _validate_jpg(path):
    if not PIL_AVAILABLE:
        # Fallback: check footer
        with open(path, 'rb') as f:
            f.seek(-2, 2)
            return "VALID" if f.read(2) == b'\xff\xd9' else "PARTIAL"
    try:
        with open(path, 'rb') as f:
            data = f.read()
        img = Image.open(io.BytesIO(data))
        img.verify()
        return "VALID"
    except Exception:
        return "CORRUPT"


def _validate_png(path):
    if not PIL_AVAILABLE:
        with open(path, 'rb') as f:
            header = f.read(8)
            f.seek(-8, 2)
            footer = f.read(8)
        return "VALID" if header == b'\x89PNG\r\n\x1a\n' and b'IEND' in footer else "PARTIAL"
    try:
        with open(path, 'rb') as f:
            data = f.read()
        img = Image.open(io.BytesIO(data))
        img.verify()
        return "VALID"
    except Exception:
        return "CORRUPT"


def _validate_zip_family(path):
    try:
        with zipfile.ZipFile(path, 'r') as z:
            result = z.testzip()
            return "VALID" if result is None else "CORRUPT"
    except zipfile.BadZipFile:
        return "CORRUPT"
    except Exception:
        return "PARTIAL"


def _validate_pdf(path):
    try:
        with open(path, 'rb') as f:
            header = f.read(5)
            if header != b'%PDF-':
                return "CORRUPT"
            f.seek(-1024, 2)
            tail = f.read()
        return "VALID" if b'%%EOF' in tail else "PARTIAL"
    except Exception:
        return "CORRUPT"


def _validate_mp3(path):
    """Check first 3 consecutive valid MP3 frames."""
    MPEG1_BITRATES = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
    MPEG1_SR       = [44100, 48000, 32000, 0]
    try:
        with open(path, 'rb') as f:
            data = f.read(65536)
        idx = 0
        # Skip ID3 tag
        if data[:3] == b'ID3':
            size = (data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9]
            idx = size + 10
        frames = 0
        for _ in range(3):
            if idx + 4 > len(data):
                break
            b0, b1, b2 = data[idx], data[idx + 1], data[idx + 2]
            if b0 != 0xFF or b1 not in (0xFA, 0xFB, 0xF2, 0xF3):
                return "CORRUPT"
            br_idx = (b2 >> 4) & 0x0F
            sr_idx = (b2 >> 2) & 0x03
            if br_idx in (0, 15) or sr_idx == 3:
                return "CORRUPT"
            padding = (b2 >> 1) & 0x01
            br = MPEG1_BITRATES[br_idx] * 1000
            sr = MPEG1_SR[sr_idx]
            frame_size = int(144 * br / sr) + padding
            if frame_size <= 0:
                return "CORRUPT"
            idx += frame_size
            frames += 1
        return "VALID" if frames >= 3 else "PARTIAL"
    except Exception:
        return "CORRUPT"


def _validate_wav(path):
    try:
        with open(path, 'rb') as f:
            header = f.read(44)
        if len(header) < 44:
            return "PARTIAL"
        if header[:4] != b'RIFF' or header[8:12] != b'WAVE':
            return "CORRUPT"
        fmt_size = struct.unpack_from('<I', header, 16)[0]
        if fmt_size not in (16, 18, 40):
            return "CORRUPT"
        audio_fmt = struct.unpack_from('<H', header, 20)[0]
        if audio_fmt not in (1, 3, 6, 7, 0xFFFE):  # PCM, Float, ALAW, ULAW, Extensible
            return "CORRUPT"
        return "VALID"
    except Exception:
        return "CORRUPT"


def _validate_avi(path):
    try:
        with open(path, 'rb') as f:
            header = f.read(12)
        if header[:4] == b'RIFF' and header[8:12] == b'AVI ':
            return "VALID"
        return "CORRUPT"
    except Exception:
        return "CORRUPT"


def _validate_sqlite(path):
    try:
        with open(path, 'rb') as f:
            header = f.read(16)
        return "VALID" if header == b'SQLite format 3\x00' else "CORRUPT"
    except Exception:
        return "CORRUPT"


def _validate_generic(path):
    """Fallback: file exists and is non-zero."""
    try:
        return "VALID" if os.path.getsize(path) > 0 else "CORRUPT"
    except Exception:
        return "CORRUPT"


# ── Extension Dispatch ───────────────────────────────────────────────────────

VALIDATORS = {
    '.jpg':   _validate_jpg,
    '.jpeg':  _validate_jpg,
    '.png':   _validate_png,
    '.pdf':   _validate_pdf,
    '.mp3':   _validate_mp3,
    '.wav':   _validate_wav,
    '.avi':   _validate_avi,
    '.sqlite': _validate_sqlite,
    '.db':    _validate_sqlite,
    '.zip':   _validate_zip_family,
    '.docx':  _validate_zip_family,
    '.xlsx':  _validate_zip_family,
    '.pptx':  _validate_zip_family,
    '.rar':   _validate_generic,
    '.7z':    _validate_generic,
    '.mp4':   _validate_generic,
    '.mov':   _validate_generic,
    '.mkv':   _validate_generic,
}


def validate_file(path: str) -> str:
    """
    Validate a single recovered file.
    Returns: 'VALID', 'CORRUPT', or 'PARTIAL'
    """
    ext = os.path.splitext(path)[1].lower()
    validator = VALIDATORS.get(ext, _validate_generic)
    try:
        return validator(path)
    except Exception:
        return "CORRUPT"


# ── Main: Scan all Recovered_* folders ───────────────────────────────────────

def main():
    print("\n╔══════════════════════════════════════════╗")
    print("║       File Integrity Validator v1.0      ║")
    print("╚══════════════════════════════════════════╝\n")

    # Find all Recovered_* directories
    recovered_dirs = [d for d in os.listdir('.') if d.startswith('Recovered_') and os.path.isdir(d)]
    # Also check Organized_Recovery
    if os.path.isdir('Organized_Recovery'):
        for sub in os.listdir('Organized_Recovery'):
            sub_path = os.path.join('Organized_Recovery', sub)
            if os.path.isdir(sub_path):
                recovered_dirs.append(sub_path)

    if not recovered_dirs:
        print("❌ No Recovered_* folders found. Run a carver first!")
        return

    total = valid = corrupt = partial = 0
    results = []

    for folder in recovered_dirs:
        for root, _, files in os.walk(folder):
            for fname in files:
                fpath = os.path.join(root, fname)
                status = validate_file(fpath)
                size   = os.path.getsize(fpath)
                results.append((status, fname, size, fpath))
                total   += 1
                if status == "VALID":   valid   += 1
                elif status == "CORRUPT": corrupt += 1
                else:                     partial += 1

    # Print table
    print(f"{'Status':<10} {'File':<40} {'Size':>12}")
    print("-" * 66)
    for status, fname, size, _ in sorted(results, key=lambda x: x[0]):
        icon = "✅" if status == "VALID" else ("❌" if status == "CORRUPT" else "⚠️ ")
        print(f"{icon} {status:<8} {fname:<40} {size:>10,} B")

    print("-" * 66)
    print(f"\n📊 Summary: {total} files | ✅ {valid} VALID | ⚠️  {partial} PARTIAL | ❌ {corrupt} CORRUPT")

    if not PIL_AVAILABLE:
        print("\n⚠️  Tip: Install Pillow for better image validation: pip install Pillow")


if __name__ == '__main__':
    main()
