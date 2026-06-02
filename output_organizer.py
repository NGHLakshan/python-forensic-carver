"""
output_organizer.py — Smart Output Organizer
============================================
Scans all Recovered_* folders, moves files into
Organized_Recovery/<FileType>/ subfolders, renames them
with a timestamp prefix, and skips exact MD5 duplicates.

Usage:
    python output_organizer.py
"""

import os
import shutil
import hashlib
import datetime


# Map file extensions to readable category names
CATEGORY_MAP = {
    '.jpg':    'Images_JPG',
    '.jpeg':   'Images_JPG',
    '.png':    'Images_PNG',
    '.bmp':    'Images_BMP',
    '.gif':    'Images_GIF',
    '.mp3':    'Audio_MP3',
    '.wav':    'Audio_WAV',
    '.mp4':    'Video_MP4',
    '.avi':    'Video_AVI',
    '.mov':    'Video_MOV',
    '.mkv':    'Video_MKV',
    '.pdf':    'Documents_PDF',
    '.docx':   'Documents_Word',
    '.doc':    'Documents_Word',
    '.xlsx':   'Documents_Excel',
    '.xls':    'Documents_Excel',
    '.pptx':   'Documents_PowerPoint',
    '.ppt':    'Documents_PowerPoint',
    '.zip':    'Archives_ZIP',
    '.rar':    'Archives_RAR',
    '.7z':     'Archives_7z',
    '.iso':    'DiskImages_ISO',
    '.pst':    'Email_PST',
    '.ost':    'Email_OST',
    '.sqlite': 'Databases_SQLite',
    '.db':     'Databases_SQLite',
    '.xml':    'Data_XML',
    '.html':   'Data_HTML',
    '.htm':    'Data_HTML',
    '.exe':    'Executables_EXE',
    '.mkv':    'Video_MKV',
}


def _md5_file(path: str) -> str:
    """Compute MD5 hash of a file for duplicate detection."""
    h = hashlib.md5()
    try:
        with open(path, 'rb') as f:
            for block in iter(lambda: f.read(65536), b''):
                h.update(block)
        return h.hexdigest()
    except Exception:
        return None


def main():
    print("\n╔═══════════════════════════════════════════╗")
    print("║       Smart Output Organizer v1.0         ║")
    print("╚═══════════════════════════════════════════╝\n")

    base_output = "Organized_Recovery"
    os.makedirs(base_output, exist_ok=True)

    # Collect source directories
    source_dirs = [d for d in os.listdir('.') if d.startswith('Recovered_') and os.path.isdir(d)]
    if not source_dirs:
        print("❌ No Recovered_* folders found. Run a carver first!")
        return

    timestamp_prefix = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    seen_hashes = {}   # md5 -> destination path
    moved = skipped_dup = skipped_err = 0

    for folder in source_dirs:
        for root, _, files in os.walk(folder):
            for fname in files:
                src_path = os.path.join(root, fname)
                ext = os.path.splitext(fname)[1].lower()
                category = CATEGORY_MAP.get(ext, 'Other')

                # Compute MD5 for dedup
                file_md5 = _md5_file(src_path)
                if file_md5 and file_md5 in seen_hashes:
                    print(f"  [SKIP-DUP] {fname} (duplicate of {os.path.basename(seen_hashes[file_md5])})")
                    skipped_dup += 1
                    continue

                # Create category subfolder
                dest_dir = os.path.join(base_output, category)
                os.makedirs(dest_dir, exist_ok=True)

                # New filename: timestamp_originalname
                new_name = f"{timestamp_prefix}_{fname}"
                dest_path = os.path.join(dest_dir, new_name)

                # Handle name collisions
                counter = 1
                while os.path.exists(dest_path):
                    base, ext2 = os.path.splitext(new_name)
                    dest_path = os.path.join(dest_dir, f"{base}_{counter}{ext2}")
                    counter += 1

                try:
                    shutil.copy2(src_path, dest_path)
                    if file_md5:
                        seen_hashes[file_md5] = dest_path
                    size = os.path.getsize(dest_path)
                    print(f"  [OK] {fname:40s} → {category}/{os.path.basename(dest_path)}  ({size:,} B)")
                    moved += 1
                except Exception as e:
                    print(f"  [ERR] {fname}: {e}")
                    skipped_err += 1

    print(f"\n✅ Done! {moved} files organized | {skipped_dup} duplicates skipped | {skipped_err} errors")
    print(f"   Output folder: {os.path.abspath(base_output)}")


if __name__ == '__main__':
    main()
