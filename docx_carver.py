import os

# ⚠️ Set your USB drive letter here
DRIVE_LETTER = 'E'

def find_zip_end(data: bytes, start_idx: int) -> int:
    """
    Strict ZIP Structure Parser:
    A ZIP file ends with an End of Central Directory (EOCD) record (PK\x05\x06).
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
        
        # If it doesn't match, search further
        search_pos = eocd_idx + 4


def is_valid_docx(data: bytes, start_idx: int, end_idx: int) -> bool:
    """
    Strictly verifies that this ZIP archive is specifically a DOCX file.
    DOCX files must contain 'word/document.xml'.
    We also check for '[Content_Types].xml' for extra safety.
    """
    archive_slice = data[start_idx:end_idx].lower()
    if b'word/document.xml' in archive_slice and b'[content_types].xml' in archive_slice:
        return True
    return False


def main():
    print("1. Script Started...")
    output_dir = "Recovered_DOCX"
    os.makedirs(output_dir, exist_ok=True)
    
    drive_path = chr(92) + chr(92) + '.' + chr(92) + DRIVE_LETTER + ':'
    print(f"2. Opening drive: {drive_path}")
    
    try:
        disk = open(drive_path, 'rb')
    except PermissionError:
        print("\n❌ PermissionError: Cannot open drive. Please run the script as Administrator!")
        return
    except Exception as e:
        print(f"\n❌ ERROR: Cannot open drive. Details: {e}")
        return

    print("3. Starting Strict DOCX Carver Scan...")
    
    CHUNK_SIZE = 64 * 1024 * 1024  # 64MB chunks
    OVERLAP    =  2 * 1024 * 1024  # 2MB overlap
    offset = 0
    
    file_count = 0
    
    try:
        while True:
            disk.seek(offset)
            chunk = disk.read(CHUNK_SIZE)
            
            if not chunk:
                print("\n[*] End of drive reached successfully!")
                break
                
            chunk_idx = offset // max(1, (CHUNK_SIZE - OVERLAP))
            if chunk_idx % 1 == 0:
                print(f"[*] Scanning... Passed {offset / (1024*1024):.1f} MB...", flush=True)

            idx = 0
            while idx < len(chunk) - 4:
                # 1. Find the ZIP Local File Header (PK\x03\x04)
                header_idx = chunk.find(b'PK\x03\x04', idx)
                
                if header_idx == -1 or header_idx >= CHUNK_SIZE - OVERLAP:
                    break
                    
                # 2. Use the strict ZIP structure parser to find the EOCD
                end_of_file = find_zip_end(chunk, header_idx)
                
                if end_of_file != -1:
                    extracted = chunk[header_idx : end_of_file]
                    
                    if len(extracted) > 1000: # DOCX is definitely > 1KB
                        if is_valid_docx(chunk, header_idx, end_of_file):
                            file_count += 1
                            fname = f"recovered_{file_count}.docx"
                            
                            fpath = os.path.join(output_dir, fname)
                            
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
        
    print(f"\n[*] Scan completely Done. Recovered DOCX files: {file_count}")
        
    disk.close()

if __name__ == '__main__':
    main()
