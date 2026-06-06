import os

DRIVE_LETTER = 'E'
CHUNK_SIZE = 64 * 1024 * 1024
OVERLAP    =  2 * 1024 * 1024
RAR_MAX_SIZE = 500 * 1024 * 1024 # Extract up to 500MB

def main():
    print("1. Script Started...")
    output_dir = "Recovered_RAR"
    os.makedirs(output_dir, exist_ok=True)
    
    drive_path = chr(92) + chr(92) + '.' + chr(92) + DRIVE_LETTER + ':'
    try:
        disk = open(drive_path, 'rb')
    except Exception as e:
        print(f"\n❌ ERROR: Cannot open drive. Run as Admin! Details: {e}")
        return

    print("3. Starting Smart RAR Archive Carver Scan...")
    offset = 0
    file_count = 0
    header_sig = b'Rar!\x1a\x07'
    
    try:
        while True:
            disk.seek(offset)
            chunk = disk.read(CHUNK_SIZE)
            if not chunk: break
                
            chunk_idx = offset // max(1, (CHUNK_SIZE - OVERLAP))
            if chunk_idx % 1 == 0:
                print(f"[*] Scanning... Passed {offset / (1024*1024):.1f} MB...", flush=True)

            idx = 0
            while idx < len(chunk) - 8:
                header_idx = chunk.find(header_sig, idx)
                if header_idx == -1 or header_idx >= CHUNK_SIZE - OVERLAP:
                    break
                    
                is_valid = False
                if chunk[header_idx:header_idx+7] == b'Rar!\x1a\x07\x00' or chunk[header_idx:header_idx+8] == b'Rar!\x1a\x07\x01\x00':
                    is_valid = True
                    
                if is_valid:
                    file_count += 1
                    fname = f"recovered_{file_count}.rar"
                    
                    total_size = RAR_MAX_SIZE
                    bytes_in_chunk = min(total_size, len(chunk) - header_idx)
                    
                    with open(os.path.join(output_dir, fname), 'wb') as f:
                        f.write(chunk[header_idx:header_idx + bytes_in_chunk])
                        
                        bytes_left = total_size - bytes_in_chunk
                        if bytes_left > 0:
                            disk_pos = disk.tell() 
                            disk.seek(offset + len(chunk))
                            
                            while bytes_left > 0:
                                read_len = min(bytes_left, 1024 * 1024 * 5)
                                aligned_read = ((read_len + 511) // 512) * 512
                                
                                block = disk.read(aligned_read)
                                if not block: break
                                
                                to_write = min(bytes_left, len(block))
                                f.write(block[:to_write])
                                bytes_left -= to_write
                                
                            disk.seek(disk_pos)
                            
                    print(f"  [+] 🎯 Recovered {fname} (Extracted 500 MB max chunk)", flush=True)
                    
                    # Jump a smaller amount forward safely
                    idx = header_idx + min(bytes_in_chunk, 50 * 1024 * 1024)
                else:
                    idx = header_idx + 6
                
            offset += CHUNK_SIZE - OVERLAP
            
    except KeyboardInterrupt:
        pass
        
    print(f"\n[*] Scan Done. Recovered RAR Archives: {file_count}")
    disk.close()

if __name__ == '__main__':
    main()
