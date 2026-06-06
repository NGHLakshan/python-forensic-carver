import os
import struct

DRIVE_LETTER = 'E'
CHUNK_SIZE = 64 * 1024 * 1024
OVERLAP    =  2 * 1024 * 1024
MP4_MAX_SIZE = 250 * 1024 * 1024 # extract up to 250MB for video files

def is_valid_mp4(data, idx):
    # MP4 header 'ftyp' is usually preceded by a 4-byte box size.
    # Therefore, the file starts at idx - 4.
    if idx < 4 or idx + 8 > len(data): 
        return False
        
    box_size = struct.unpack_from('>I', data, idx - 4)[0]
    if box_size < 8 or box_size > 1024: 
        return False
        
    # We also check if it contains common MP4 boxes like mdat or moov nearby
    search_limit = min(idx + 1024 * 1024 * 5, len(data)) # search first 5MB
    search_area = data[idx:search_limit]
    if b'mdat' in search_area or b'moov' in search_area:
        return True
        
    return False

def main():
    print("1. Script Started...")
    output_dir = "Recovered_MP4"
    os.makedirs(output_dir, exist_ok=True)
    
    drive_path = chr(92) + chr(92) + '.' + chr(92) + DRIVE_LETTER + ':'
    try:
        disk = open(drive_path, 'rb')
    except Exception as e:
        print(f"\n❌ ERROR: Cannot open drive. Run as Admin! Details: {e}")
        return

    print("3. Starting Smart MP4 Video Carver Scan...")
    offset = 0
    file_count = 0
    header_sig = b'ftyp'
    
    try:
        while True:
            disk.seek(offset)
            chunk = disk.read(CHUNK_SIZE)
            if not chunk: break
                
            chunk_idx = offset // max(1, (CHUNK_SIZE - OVERLAP))
            if chunk_idx % 1 == 0:
                print(f"[*] Scanning... Passed {offset / (1024*1024):.1f} MB...", flush=True)

            idx = 4
            while idx < len(chunk) - 8:
                header_idx = chunk.find(header_sig, idx)
                if header_idx == -1 or header_idx >= CHUNK_SIZE - OVERLAP:
                    break
                    
                if is_valid_mp4(chunk, header_idx):
                    file_count += 1
                    fname = f"recovered_{file_count}.mp4"
                    
                    # File actually begins 4 bytes before 'ftyp' (where the size of ftyp box is declared)
                    file_start_idx = header_idx - 4
                    total_size = MP4_MAX_SIZE # Video files are dynamic, standard max size 250MB extraction
                    
                    # Safe extraction dealing with raw sector sizes
                    bytes_in_chunk = min(total_size, len(chunk) - file_start_idx)
                    
                    with open(os.path.join(output_dir, fname), 'wb') as f:
                        f.write(chunk[file_start_idx:file_start_idx + bytes_in_chunk])
                        
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
                            
                    print(f"  [+] 🎯 Recovered {fname} (Extracted 250 MB max chunk)", flush=True)
                    
                    # Jump forward to avoid extracting overlapping MP4 components
                    idx = header_idx + min(bytes_in_chunk, 50 * 1024 * 1024)
                else:
                    idx = header_idx + 4
                
            offset += CHUNK_SIZE - OVERLAP
            
    except KeyboardInterrupt:
        pass
        
    print(f"\n[*] Scan Done. Recovered MP4 Videos: {file_count}")
    disk.close()

if __name__ == '__main__':
    main()
