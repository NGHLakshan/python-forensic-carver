import os

DRIVE_LETTER = 'E'
CHUNK_SIZE = 64 * 1024 * 1024
OVERLAP    =  2 * 1024 * 1024
MAX_SIZE = 5 * 1024 * 1024  # 5MB cap for XML

def main():
    print("1. Script Started...")
    output_dir = "Recovered_XML"
    os.makedirs(output_dir, exist_ok=True)
    
    drive_path = chr(92) + chr(92) + '.' + chr(92) + DRIVE_LETTER + ':'
    try:
        disk = open(drive_path, 'rb')
    except Exception as e:
        print(f"\n❌ ERROR: Cannot open drive. Run as Admin! Details: {e}")
        return

    print("3. Starting XML Carver Scan...")
    offset = 0
    file_count = 0
    header_sig = b'<?xml version'
    
    try:
        while True:
            disk.seek(offset)
            chunk = disk.read(CHUNK_SIZE)
            if not chunk: break
                
            if offset % (CHUNK_SIZE * 5) == 0:
                print(f"[*] Scanning... Passed {offset / (1024*1024):.1f} MB...", flush=True)

            idx = 0
            while idx < len(chunk) - len(header_sig):
                header_idx = chunk.find(header_sig, idx)
                if header_idx == -1 or header_idx >= CHUNK_SIZE - OVERLAP:
                    break
                    
                end_idx = min(header_idx + MAX_SIZE, len(chunk))
                extracted = chunk[header_idx:end_idx]
                
                if len(extracted) > 100: 
                    file_count += 1
                    fname = f"recovered_{file_count}.xml"
                    with open(os.path.join(output_dir, fname), 'wb') as f:
                        f.write(extracted)
                        
                    print(f"  [+] 🎯 Recovered {fname} ({len(extracted):,} bytes)", flush=True)
                    
                idx = end_idx
                
            offset += CHUNK_SIZE - OVERLAP
            
    except KeyboardInterrupt:
        pass
        
    print(f"\n[*] Scan Done. Recovered XML files: {file_count}")
    disk.close()

if __name__ == '__main__':
    main()
