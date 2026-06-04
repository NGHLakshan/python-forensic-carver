import os
import re

DRIVE_LETTER = 'E'
CHUNK_SIZE = 64 * 1024 * 1024  
OVERLAP    =  2 * 1024 * 1024
MP3_MAX_SIZE = 15 * 1024 * 1024  # 15MB cap for MP3 (most songs are 3-8MB)

# Pre-compile the regex to search for MP3 headers rapidly
MP3_SIGNATURE_PATTERN = re.compile(b'ID3|\xff[\xfa\xfb\xf2\xf3]')

MPEG1_BITRATES = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
MPEG1_SAMPLERATES = [44100, 48000, 32000, 0]
MPEG2_BITRATES = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]
MPEG2_SAMPLERATES = [22050, 24000, 16000, 0]

def get_mp3_frame_size(header_bytes):
    if len(header_bytes) < 4: return -1
    if header_bytes[0] != 0xFF: return -1
    b2 = header_bytes[1]
    if b2 not in (0xFA, 0xFB, 0xF2, 0xF3): return -1
    
    version = (b2 >> 3) & 0x03
    bitrate_idx = (header_bytes[2] >> 4) & 0x0F
    sr_idx = (header_bytes[2] >> 2) & 0x03
    padding = (header_bytes[2] >> 1) & 0x01
    
    if bitrate_idx == 0 or bitrate_idx == 15 or sr_idx == 3: return -1

    if version == 3: # MPEG-1
        br = MPEG1_BITRATES[bitrate_idx] * 1000
        sr = MPEG1_SAMPLERATES[sr_idx]
        return int(144 * br / sr) + padding
    elif version == 2: # MPEG-2
        br = MPEG2_BITRATES[bitrate_idx] * 1000
        sr = MPEG2_SAMPLERATES[sr_idx]
        return int(72 * br / sr) + padding
    return -1

def check_consecutive_frames(data, start_idx, num_frames=3):
    idx = start_idx
    for _ in range(num_frames):
        if idx + 4 > len(data): return False
        size = get_mp3_frame_size(data[idx:idx+4])
        if size == -1: return False
        idx += size
    return True

def get_id3_size(data, idx):
    if data[idx:idx+3] != b'ID3': return -1
    version = data[idx+3]
    if version not in (2, 3, 4): return -1
    for i in range(6, 10):
        if data[idx+i] >= 0x80: return -1
    size = (data[idx+6] << 21) | (data[idx+7] << 14) | (data[idx+8] << 7) | data[idx+9]
    return size + 10

def main():
    print("1. Script Started...")
    output_dir = "Recovered_MP3"
    os.makedirs(output_dir, exist_ok=True)
    
    drive_path = f'\\\\.\\{DRIVE_LETTER}:'
    try:
        disk = open(drive_path, 'rb')
    except Exception as e:
        print(f"\n❌ ERROR: Cannot open drive. Run as Admin! Details: {e}")
        return

    print("3. Starting DEEP MP3 Carver Scan (PhotoRec Engine)...")
    offset = 0
    file_count = 0
    
    try:
        while True:
            disk.seek(offset)
            chunk = disk.read(CHUNK_SIZE)
            if not chunk: break
                
            if offset % (CHUNK_SIZE * 2) == 0:
                print(f"[*] Scanning... Passed {offset / (1024*1024):.1f} MB...", flush=True)

            idx = 0
            # Use regex finditer for highly optimized O(N) scanning instead of O(N^2) byte-by-byte scanning
            for match in MP3_SIGNATURE_PATTERN.finditer(chunk):
                target = match.start()
                
                if target < idx:
                    continue  # Skip bytes if we already extracted a chunk here
                    
                if target >= CHUNK_SIZE - OVERLAP:
                    break
                
                is_valid = False
                start_extract = target

                # If it's ID3
                if chunk[target:target+3] == b'ID3':
                    size = get_id3_size(chunk, target)
                    if size != -1 and target + size + 4 < len(chunk):
                        # Verify that immediately after ID3 is a valid audio frame
                        if check_consecutive_frames(chunk, target + size, num_frames=2):
                            is_valid = True
                else:
                    # It's an audio frame
                    if check_consecutive_frames(chunk, target, num_frames=3):
                        is_valid = True
                        
                if is_valid:
                    end_idx = min(start_extract + MP3_MAX_SIZE, len(chunk))
                    extracted = chunk[start_extract:end_idx]
                    
                    if len(extracted) > 1000:
                        file_count += 1
                        fname = f"recovered_{file_count}.mp3"
                        with open(os.path.join(output_dir, fname), 'wb') as f:
                            f.write(extracted)
                            
                        print(f"  [+] 🎯 Recovered {fname} ({len(extracted):,} bytes)", flush=True)
                        
                    idx = start_extract + MP3_MAX_SIZE
                
            offset += CHUNK_SIZE - OVERLAP
            
    except KeyboardInterrupt:
        pass
        
    print(f"\n[*] Scan Done. Recovered MP3 files: {file_count}")
    disk.close()

if __name__ == '__main__':
    main()
