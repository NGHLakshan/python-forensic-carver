import os

DRIVE_LETTER = 'E'
CHUNK_SIZE = 64 * 1024 * 1024
OVERLAP    =  2 * 1024 * 1024

def main():
    print("1. Script Started...")
    output_dir = "Recovered_PNG"
    os.makedirs(output_dir, exist_ok=True)
    
    drive_path = chr(92) + chr(92) + '.' + chr(92) + DRIVE_LETTER + ':'
    try:
        disk = open(drive_path, 'rb')
    except Exception as e:
        print(f"\n❌ ERROR: Cannot open drive. Run as Admin! Details: {e}")
        return

    print("3. Starting PNG Carver Scan...")
    offset = 0
    file_count = 0
    header_sig = b'\x89PNG\r\n\x1a\n'
    footer_sig = b'\x49\x45\x4e\x44\xae\x42\x60\x82'
    
    try:
        while True:
            disk.seek(offset)
            chunk = disk.read(CHUNK_SIZE)
            if not chunk: break
                
            chunk_idx = offset // max(1, (CHUNK_SIZE - OVERLAP))
            if chunk_idx % 1 == 0:
                print(f"[*] Scanning... Passed {offset / (1024*1024):.1f} MB...", flush=True)

            idx = 0
            while idx < len(chunk) - len(header_sig):
                header_idx = chunk.find(header_sig, idx)
                if header_idx == -1 or header_idx >= CHUNK_SIZE - OVERLAP:
                    break
                    
                footer_idx = chunk.find(footer_sig, header_idx + len(header_sig))
                if footer_idx != -1:
                    end_idx = footer_idx + len(footer_sig)
                    extracted = chunk[header_idx:end_idx]
                    
                    file_count += 1
                    fname = f"recovered_{file_count}.png"
                    with open(os.path.join(output_dir, fname), 'wb') as f:
                        f.write(extracted)
                        
                    print(f"  [+] 🎯 Recovered {fname} ({len(extracted):,} bytes)", flush=True)
                    idx = end_idx
                else:
                    idx = header_idx + len(header_sig)
                    
            offset += CHUNK_SIZE - OVERLAP
            
    except KeyboardInterrupt:
        pass
        
    print(f"\n[*] Scan Done. Recovered PNG files: {file_count}")
    disk.close()

if __name__ == '__main__':
    main()
