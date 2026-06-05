import os
import struct

DRIVE_LETTER = 'E'
CHUNK_SIZE = 64 * 1024 * 1024
OVERLAP    =  2 * 1024 * 1024

def get_sqlite_size(data, idx):
    if idx + 32 > len(data):
        return -1
    # Page size is at offset 16 (2 bytes, big endian)
    page_size = struct.unpack_from('>H', data, idx + 16)[0]
    if page_size == 1:
        page_size = 65536
    elif page_size < 512 or (page_size & (page_size - 1)) != 0:
        return -1
        
    # Database size in pages is at offset 28 (4 bytes, big endian)
    size_in_pages = struct.unpack_from('>I', data, idx + 28)[0]
    if size_in_pages == 0:
        return -1
        
    total_size = page_size * size_in_pages
    # Sanity check: SQLite DBs are usually reasonable size, cap at 5GB for safety
    if total_size > 5 * 1024 * 1024 * 1024:
        return -1
        
    return total_size

def main():
    print("1. Script Started...")
    output_dir = "Recovered_SQLite"
    os.makedirs(output_dir, exist_ok=True)
    
    drive_path = chr(92) + chr(92) + '.' + chr(92) + DRIVE_LETTER + ':'
    try:
        disk = open(drive_path, 'rb')
    except Exception as e:
        print(f"\n❌ ERROR: Cannot open drive. Run as Admin! Details: {e}")
        return

    print("3. Starting Smart SQLite Database Carver Scan...")
    offset = 0
    file_count = 0
    header_sig = b'SQLite format 3\0'
    
    try:
        while True:
            disk.seek(offset)
            chunk = disk.read(CHUNK_SIZE)
            if not chunk: break
                
            if offset % (CHUNK_SIZE * 2) == 0:
                print(f"[*] Scanning... Passed {offset / (1024*1024):.1f} MB...", flush=True)

            idx = 0
            while idx < len(chunk) - 32:
                header_idx = chunk.find(header_sig, idx)
                if header_idx == -1 or header_idx >= CHUNK_SIZE - OVERLAP:
                    break
                    
                total_size = get_sqlite_size(chunk, header_idx)
                
                if total_size != -1:
                    file_count += 1
                    fname = f"recovered_{file_count}.sqlite"
                    
                    # Safe extraction dealing with raw sector sizes
                    bytes_in_chunk = min(total_size, len(chunk) - header_idx)
                    
                    with open(os.path.join(output_dir, fname), 'wb') as f:
                        f.write(chunk[header_idx:header_idx + bytes_in_chunk])
                        
                        bytes_left = total_size - bytes_in_chunk
                        if bytes_left > 0:
                            disk_pos = disk.tell() 
                            # Safe aligned seek to the end of the current chunk
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
                            
                    print(f"  [+] 🎯 Recovered {fname} ({total_size:,} bytes)", flush=True)
                    
                    jump = min(total_size, CHUNK_SIZE - idx - 1)
                    idx = header_idx + jump
                else:
                    idx = header_idx + 16
                
            offset += CHUNK_SIZE - OVERLAP
            
    except KeyboardInterrupt:
        pass
        
    print(f"\n[*] Scan Done. Recovered SQLite DBs: {file_count}")
    disk.close()

if __name__ == '__main__':
    main()
