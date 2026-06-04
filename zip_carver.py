import os

# ⚠️ Set your USB drive letter here
DRIVE_LETTER = 'E'

def find_zip_end(data: bytes, start_idx: int) -> int:
    """
    Strict ZIP Structure Parser:
    A ZIP file ends with an End of Central Directory (EOCD) record (PK\x05\x06).
    Fake EOCD boundaries cause corrupted extractions. We validate it by checking:
    EOCD Offset 12: Size of Central Directory (4 bytes)
    EOCD Offset 16: Offset of CD relative to start (4 bytes)
    If Offset of CD + Size of CD == Distance from start to EOCD, it's 100% valid.
    """
    search_pos = start_idx + 4
    
    while True:
        eocd_idx = data.find(b'PK\x05\x06', search_pos)
        
        if eocd_idx == -1:
            return -1  
            
        if eocd_idx + 22 > len(data):
            return -1 
            
        # Parse EOCD fields (Little Endian)
        cd_size   = int.from_bytes(data[eocd_idx + 12 : eocd_idx + 16], 'little')
        cd_offset = int.from_bytes(data[eocd_idx + 16 : eocd_idx + 20], 'little')
        
        rel_eocd = eocd_idx - start_idx
        
        # Mathematical Validation: Does the Central Directory perfectly connect the start to the EOCD?
        if cd_offset + cd_size == rel_eocd:
            # Valid EOCD found! Calculate the total length including the comment.
            comment_len = int.from_bytes(data[eocd_idx + 20 : eocd_idx + 22], 'little')
            true_end = eocd_idx + 22 + comment_len
            
            if true_end > len(data):
                return -1
            return true_end
        
        # If it doesn't match, this is a false positive PK\x05\x06 (or belongs to another file).
        # We continue searching further down.
        search_pos = eocd_idx + 4


def get_office_extension(data: bytes, start_idx: int, end_idx: int) -> str:
    """
    Peek inside the ZIP contents to guess if it's a regular ZIP, or an MS Office document.
    MS Office files are just ZIP archives containing specific folders (like 'word/', 'xl/', 'ppt/').
    """
    archive_slice = data[start_idx:end_idx].lower()
    
    if b'word/' in archive_slice:
        return 'docx'
    elif b'xl/' in archive_slice:
        return 'xlsx'
    elif b'ppt/' in archive_slice:
        return 'pptx'
    elif b'androidmanifest.xml' in archive_slice:
        return 'apk'
    else:
        return 'zip'


def main():
    print("1. Script Started...")
    output_dir = "Recovered_ZIP_Office"
    os.makedirs(output_dir, exist_ok=True)
    
    drive_path = f'\\\\.\\{DRIVE_LETTER}:'
    print(f"2. Opening drive: {drive_path}")
    
    try:
        disk = open(drive_path, 'rb')
    except PermissionError:
        print("\n❌ PermissionError: Cannot open drive. Please run the script as Administrator!")
        return
    except Exception as e:
        print(f"\n❌ ERROR: Cannot open drive. Details: {e}")
        return

    print("3. Starting Strict ZIP/DOCX/XLSX Carver Scan...")
    
    CHUNK_SIZE = 64 * 1024 * 1024  # 64MB chunks
    OVERLAP    =  2 * 1024 * 1024  # 2MB overlap
    offset = 0
    
    counters = {}
    
    try:
        while True:
            disk.seek(offset)
            chunk = disk.read(CHUNK_SIZE)
            
            if not chunk:
                print("\n[*] End of drive reached successfully!")
                break
                
            if offset % (CHUNK_SIZE * 5) == 0:
                print(f"[*] Scanning... Passed {offset / (1024*1024):.1f} MB...", flush=True)

            idx = 0
            while idx < len(chunk) - 4:
                # 1. Find the ZIP Local File Header (PK\x03\x04)
                header_idx = chunk.find(b'PK\x03\x04', idx)
                
                if header_idx == -1 or header_idx >= CHUNK_SIZE - OVERLAP:
                    break
                    
                # 2. Use the strict ZIP structure parser to find the End of Central Directory
                end_of_file = find_zip_end(chunk, header_idx)
                
                if end_of_file != -1:
                    extracted = chunk[header_idx : end_of_file]
                    
                    if len(extracted) > 100: # Filter out ultra-small corrupted fragments
                        # Determine actual extension
                        ext = get_office_extension(chunk, header_idx, end_of_file)
                        
                        counters[ext] = counters.get(ext, 0) + 1
                        fname = f"recovered_{counters[ext]}.{ext}"
                        
                        # Save inside subfolder based on extracted type
                        type_dir = os.path.join(output_dir, ext.upper())
                        os.makedirs(type_dir, exist_ok=True)
                        fpath = os.path.join(type_dir, fname)
                        
                        with open(fpath, 'wb') as f:
                            f.write(extracted)
                            
                        print(f"  [+] 🎯 Recovered {fname} ({len(extracted):,} bytes)", flush=True)
                        
                    # 3. Resume scanning immediately after the recovered archive
                    idx = end_of_file
                else:
                    # Parser failed to find EOCD, so move past this header
                    idx = header_idx + 4
                    
            offset += CHUNK_SIZE - OVERLAP
            
    except KeyboardInterrupt:
        print("\n[*] Scan stopped manually by user.")
    except Exception as e:
        print(f"\n❌ Scan Error: {e}")
        
    print(f"\n[*] Scan completely Done. Recovered files breakdown:")
    for ext, count in counters.items():
        print(f"  - {ext.upper()}: {count} files")
        
    disk.close()

if __name__ == '__main__':
    main()
