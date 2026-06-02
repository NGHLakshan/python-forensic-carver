import os

# ⚠️ Set your USB drive letter here
DRIVE_LETTER = 'E'

def find_zip_end(data: bytes, start_idx: int) -> int:
    """
    Strict ZIP Structure Parser.
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
        
        # Mathematical Validation
        if cd_offset + cd_size == rel_eocd:
            comment_len = int.from_bytes(data[eocd_idx + 20 : eocd_idx + 22], 'little')
            true_end = eocd_idx + 22 + comment_len
            
            if true_end > len(data):
                return -1
            return true_end
        
        search_pos = eocd_idx + 4


def is_valid_pptx(data: bytes, start_idx: int, end_idx: int) -> bool:
    """
    Strictly verifies that this ZIP archive is specifically a PPTX file.
    PPTX files must contain 'ppt/presentation.xml'.
    We also check for '[Content_Types].xml'.
    """
    archive_slice = data[start_idx:end_idx].lower()
    if b'ppt/presentation.xml' in archive_slice and b'[content_types].xml' in archive_slice:
        return True
    return False


def main():
    print("1. Script Started...")
    output_dir = "Recovered_PPTX"
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

    print("3. Starting Strict PPTX Carver Scan...")
    
    CHUNK_SIZE = 15 * 1024 * 1024  # 15MB chunks
    OVERLAP = 5 * 1024 * 1024      # 5MB Overlap
    offset = 0
    
    file_count = 0
    
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
                header_idx = chunk.find(b'PK\x03\x04', idx)
                
                if header_idx == -1 or header_idx >= CHUNK_SIZE - OVERLAP:
                    break
                    
                end_of_file = find_zip_end(chunk, header_idx)
                
                if end_of_file != -1:
                    extracted = chunk[header_idx : end_of_file]
                    
                    if len(extracted) > 1000:
                        if is_valid_pptx(chunk, header_idx, end_of_file):
                            file_count += 1
                            fname = f"recovered_{file_count}.pptx"
                            
                            fpath = os.path.join(output_dir, fname)
                            
                            with open(fpath, 'wb') as f:
                                f.write(extracted)
                                
                            print(f"  [+] 🎯 Recovered {fname} ({len(extracted):,} bytes)", flush=True)
                        
                    idx = end_of_file
                else:
                    idx = header_idx + 4
                    
            offset += CHUNK_SIZE - OVERLAP
            
    except KeyboardInterrupt:
        print("\n[*] Scan stopped manually by user.")
    except Exception as e:
        print(f"\n❌ Scan Error: {e}")
        
    print(f"\n[*] Scan completely Done. Recovered PPTX files: {file_count}")
        
    disk.close()

if __name__ == '__main__':
    main()
