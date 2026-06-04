import os

DRIVE_LETTER = 'E'
CHUNK_SIZE = 64 * 1024 * 1024
OVERLAP    =  2 * 1024 * 1024

def main():
    print("1. Script Started...")
    output_dir = "Recovered_GIF"
    os.makedirs(output_dir, exist_ok=True)
    
    drive_path = f'\\\\.\\{DRIVE_LETTER}:'
    try:
        disk = open(drive_path, 'rb')
    except Exception as e:
        print(f"\n❌ ERROR: Cannot open drive. Run as Admin! Details: {e}")
        return

    print("3. Starting GIF Carver Scan...")
    offset = 0
    file_count = 0
    footer_sig = b'\x00\x3b'
    
    try:
        while True:
            disk.seek(offset)
            chunk = disk.read(CHUNK_SIZE)
            if not chunk: break
                
            if offset % (CHUNK_SIZE * 5) == 0:
                print(f"[*] Scanning... Passed {offset / (1024*1024):.1f} MB...", flush=True)

            idx = 0
            while idx < len(chunk) - 6:
                header_idx87 = chunk.find(b'GIF87a', idx)
                header_idx89 = chunk.find(b'GIF89a', idx)
                
                # Pick the earliest occurring header
                headers = [h for h in (header_idx87, header_idx89) if h != -1]
                if not headers:
                    break
                    
                header_idx = min(headers)
                
                if header_idx >= CHUNK_SIZE - OVERLAP:
                    break
                    
                footer_idx = chunk.find(footer_sig, header_idx + 6)
                if footer_idx != -1:
                    end_idx = footer_idx + 2
                    extracted = chunk[header_idx:end_idx]
                    
                    if len(extracted) > 100:
                        file_count += 1
                        fname = f"recovered_{file_count}.gif"
                        with open(os.path.join(output_dir, fname), 'wb') as f:
                            f.write(extracted)
                            
                        print(f"  [+] 🎯 Recovered {fname} ({len(extracted):,} bytes)", flush=True)
                    idx = end_idx
                else:
                    idx = header_idx + 6
                    
            offset += CHUNK_SIZE - OVERLAP
            
    except KeyboardInterrupt:
        pass
        
    print(f"\n[*] Scan Done. Recovered GIF files: {file_count}")
    disk.close()

if __name__ == '__main__':
    main()
