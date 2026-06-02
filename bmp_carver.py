import os

DRIVE_LETTER = 'E'
CHUNK_SIZE = 25 * 1024 * 1024
OVERLAP = 10 * 1024 * 1024

BMP_MAX_SIZE = 20 * 1024 * 1024 

def validate_bmp(data, start):
    """
    Validates and extracts a real BMP file.
    Real BMP headers have reserved bytes 6-9 set to 0x00000000.
    Returns End index or -1
    """
    if start + 14 > len(data):
        return -1
    # STRICT CHECK: reserved bytes must be exactly zero
    reserved = data[start + 6 : start + 10]
    if reserved != b'\x00\x00\x00\x00':
        return -1
    declared = int.from_bytes(data[start + 2:start + 6], 'little')
    if declared < 54 or declared > BMP_MAX_SIZE:
        return -1
    # Pixel data offset sanity check (typically 54, 66, 122)
    px_offset = int.from_bytes(data[start + 10:start + 14], 'little')
    if px_offset < 14 or px_offset > 1024:
        return -1
    end = start + declared
    if end > len(data):
        return -1
    return end

def main():
    print("1. Script Started...")
    output_dir = "Recovered_BMP"
    os.makedirs(output_dir, exist_ok=True)
    
    drive_path = f'\\\\.\\{DRIVE_LETTER}:'
    try:
        disk = open(drive_path, 'rb')
    except Exception as e:
        print(f"\n❌ ERROR: Cannot open drive. Run as Admin! Details: {e}")
        return

    print("3. Starting BMP Carver Scan...")
    offset = 0
    file_count = 0
    
    try:
        while True:
            disk.seek(offset)
            chunk = disk.read(CHUNK_SIZE)
            if not chunk: break
                
            if offset % (CHUNK_SIZE * 5) == 0:
                print(f"[*] Scanning... Passed {offset / (1024*1024):.1f} MB...", flush=True)

            idx = 0
            while idx < len(chunk) - 2:
                header_idx = chunk.find(b'BM', idx)
                if header_idx == -1 or header_idx >= CHUNK_SIZE - OVERLAP:
                    break
                    
                end_idx = validate_bmp(chunk, header_idx)
                
                if end_idx != -1:
                    extracted = chunk[header_idx:end_idx]
                    
                    file_count += 1
                    fname = f"recovered_{file_count}.bmp"
                    with open(os.path.join(output_dir, fname), 'wb') as f:
                        f.write(extracted)
                        
                    print(f"  [+] 🎯 Recovered {fname} ({len(extracted):,} bytes)", flush=True)
                    idx = end_idx
                else:
                    idx = header_idx + 2
                    
            offset += CHUNK_SIZE - OVERLAP
            
    except KeyboardInterrupt:
        pass
        
    print(f"\n[*] Scan Done. Recovered BMP files: {file_count}")
    disk.close()

if __name__ == '__main__':
    main()
