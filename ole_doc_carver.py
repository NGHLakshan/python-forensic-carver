import os

DRIVE_LETTER = 'E'
CHUNK_SIZE = 50 * 1024 * 1024
OVERLAP = 15 * 1024 * 1024
OLE_MAX_SIZE = 100 * 1024 * 1024 # extract up to 100MB 

def main():
    print("1. Script Started...")
    output_dir = "Recovered_Old_Office"
    os.makedirs(output_dir, exist_ok=True)
    
    drive_path = f'\\\\.\\{DRIVE_LETTER}:'
    try:
        disk = open(drive_path, 'rb')
    except Exception as e:
        print(f"\n❌ ERROR: Cannot open drive. Run as Admin! Details: {e}")
        return

    print("3. Starting Legacy Office (DOC/XLS/PPT) Carver Scan...")
    offset = 0
    file_count = 0
    header_sig = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
    
    try:
        while True:
            disk.seek(offset)
            chunk = disk.read(CHUNK_SIZE)
            if not chunk: break
                
            if offset % (CHUNK_SIZE * 2) == 0:
                print(f"[*] Scanning... Passed {offset / (1024*1024):.1f} MB...", flush=True)

            idx = 0
            while idx < len(chunk) - 8:
                header_idx = chunk.find(header_sig, idx)
                if header_idx == -1 or header_idx >= CHUNK_SIZE - OVERLAP:
                    break
                    
                file_count += 1
                fname = f"recovered_{file_count}.doc"  # Or .xls/.ppt
                
                total_size = OLE_MAX_SIZE
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
                        
                print(f"  [+] 🎯 Recovered {fname} (Extracted 100 MB max chunk)", flush=True)
                
                idx = header_idx + min(bytes_in_chunk, 20 * 1024 * 1024)
                
            offset += CHUNK_SIZE - OVERLAP
            
    except KeyboardInterrupt:
        pass
        
    print(f"\n[*] Scan Done. Recovered Legacy Office Files: {file_count}")
    disk.close()

if __name__ == '__main__':
    main()
