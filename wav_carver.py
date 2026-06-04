import os

DRIVE_LETTER = 'E'
CHUNK_SIZE = 64 * 1024 * 1024
OVERLAP    =  2 * 1024 * 1024  

def get_riff_size(data, idx):
    if idx + 12 > len(data): return -1
    size_bytes = data[idx+4:idx+8]
    declared_size = int.from_bytes(size_bytes, 'little')
    if declared_size < 36 or declared_size > 2 * 1024 * 1024 * 1024:  # up to 2GB
        return -1
    return declared_size + 8  # Total file size = 8 bytes (RIFF+size) + declared_size

def main():
    print("1. Script Started...")
    output_dir_wav = "Recovered_WAV"
    output_dir_avi = "Recovered_AVI"
    os.makedirs(output_dir_wav, exist_ok=True)
    os.makedirs(output_dir_avi, exist_ok=True)
    
    drive_path = f'\\\\.\\{DRIVE_LETTER}:'
    try:
        disk = open(drive_path, 'rb')
    except Exception as e:
        print(f"\n❌ ERROR: Cannot open drive. Run as Admin! Details: {e}")
        return

    print("3. Starting Smart WAV/AVI Carver Scan...")
    offset = 0
    counters = {'wav': 0, 'avi': 0}
    header_sig = b'RIFF'
    
    try:
        while True:
            disk.seek(offset)
            chunk = disk.read(CHUNK_SIZE)
            if not chunk: break
                
            if offset % (CHUNK_SIZE * 2) == 0:
                print(f"[*] Scanning... Passed {offset / (1024*1024):.1f} MB...", flush=True)

            idx = 0
            while idx < len(chunk) - 12:
                header_idx = chunk.find(header_sig, idx)
                if header_idx == -1 or header_idx >= CHUNK_SIZE - OVERLAP:
                    break
                    
                total_size = get_riff_size(chunk, header_idx)
                
                if total_size != -1:
                    ext = 'wav'
                    if chunk[header_idx+8:header_idx+12] == b'AVI ':
                        ext = 'avi'
                        
                    counters[ext] += 1
                    fname = f"recovered_{counters[ext]}.{ext}"
                    out_dir = output_dir_wav if ext == 'wav' else output_dir_avi
                    
                    # Safe extraction dealing with raw sector sizes (512-byte aligned)
                    bytes_in_chunk = min(total_size, len(chunk) - header_idx)
                    
                    with open(os.path.join(out_dir, fname), 'wb') as f:
                        # Write the part of the file we already have in the 50MB chunk
                        f.write(chunk[header_idx:header_idx + bytes_in_chunk])
                        
                        bytes_left = total_size - bytes_in_chunk
                        if bytes_left > 0:
                            disk_pos = disk.tell() 
                            # Safe aligned seek to the end of the current chunk
                            disk.seek(offset + len(chunk))
                            
                            while bytes_left > 0:
                                # Ensure read buffer size is a multiple of 512 for raw disks
                                read_len = min(bytes_left, 1024 * 1024 * 5)
                                aligned_read = ((read_len + 511) // 512) * 512
                                
                                block = disk.read(aligned_read)
                                if not block:
                                    break
                                
                                to_write = min(bytes_left, len(block))
                                f.write(block[:to_write])
                                bytes_left -= to_write
                                
                            disk.seek(disk_pos) # Restore position
                    print(f"  [+] 🎯 Recovered {fname} ({total_size:,} bytes)", flush=True)
                    
                    jump = min(total_size, CHUNK_SIZE - idx - 1)
                    idx = header_idx + jump
                else:
                    idx = header_idx + 4
                
            offset += CHUNK_SIZE - OVERLAP
            
    except KeyboardInterrupt:
        pass
        
    print(f"\n[*] Scan Done. Recovered:")
    print(f"  - WAV: {counters['wav']}")
    print(f"  - AVI: {counters['avi']}")
    disk.close()

if __name__ == '__main__':
    main()
