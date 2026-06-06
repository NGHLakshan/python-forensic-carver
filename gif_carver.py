import os

DRIVE_LETTER = 'E'
CHUNK_SIZE = 64 * 1024 * 1024
OVERLAP    =  2 * 1024 * 1024

def find_gif_end(data, start_idx):
    """
    Mini GIF chunk parser to find the true end (0x3B).
    Validates the structure to ensure we only extract genuine GIFs.
    """
    try:
        max_len = len(data)
        idx = start_idx + 6  # skip GIF87a/GIF89a
        if idx + 7 > max_len: return -1
        
        lsd_flags = data[idx + 4]
        idx += 7  # skip Logical Screen Descriptor
        
        # Check Global Color Table
        if lsd_flags & 0x80:
            gct_size = 2 ** ((lsd_flags & 0x07) + 1)
            idx += 3 * gct_size
            
        while idx < max_len:
            block_type = data[idx]
            
            if block_type == 0x3B:  # Trailer (End of GIF)
                return idx + 1
                
            elif block_type == 0x21:  # Extension Block
                idx += 1
                if idx >= max_len: return -1
                idx += 1 # skip extension function code
                
                # Read sub-blocks
                while idx < max_len:
                    length = data[idx]
                    idx += 1
                    if length == 0:
                        break
                    idx += length
                    
            elif block_type == 0x2C:  # Image Descriptor
                idx += 1
                if idx + 9 > max_len: return -1
                id_flags = data[idx + 8]
                idx += 9
                
                # Check Local Color Table
                if id_flags & 0x80:
                    lct_size = 2 ** ((id_flags & 0x07) + 1)
                    idx += 3 * lct_size
                    
                if idx >= max_len: return -1
                idx += 1 # skip LZW minimum code size
                
                # Read sub-blocks
                while idx < max_len:
                    length = data[idx]
                    idx += 1
                    if length == 0:
                        break
                    idx += length
            else:
                # Invalid block type / corrupt data
                return -1
                
            if idx > max_len:
                return -1
                
        return -1
    except IndexError:
        return -1

def main():
    print("1. Script Started...")
    output_dir = "Recovered_GIF"
    os.makedirs(output_dir, exist_ok=True)
    
    drive_path = chr(92) + chr(92) + '.' + chr(92) + DRIVE_LETTER + ':'
    print(f"2. Opening drive: {drive_path}")
    
    try:
        disk = open(drive_path, 'rb')
    except Exception as e:
        print(f"\n❌ ERROR: Cannot open drive. Run as Admin! Details: {e}")
        return

    print("3. Starting Smart GIF Carver Scan (Structure-Aware)...")
    offset = 0
    file_count = 0
    
    try:
        while True:
            disk.seek(offset)
            chunk = disk.read(CHUNK_SIZE)
            if not chunk:
                print("\n[*] End of drive reached successfully!")
                break
                
            chunk_idx = offset // max(1, (CHUNK_SIZE - OVERLAP))
            if chunk_idx % 1 == 0:
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
                    
                end_of_file = find_gif_end(chunk, header_idx)
                
                if end_of_file != -1:
                    extracted = chunk[header_idx:end_of_file]
                    
                    if len(extracted) > 100:
                        file_count += 1
                        fname = f"recovered_{file_count}.gif"
                        with open(os.path.join(output_dir, fname), 'wb') as f:
                            f.write(extracted)
                            
                        print(f"  [+] 🎯 Recovered {fname} ({len(extracted):,} bytes)", flush=True)
                    idx = end_of_file
                else:
                    # Parser failed or EOF not in chunk, skip to next likely header
                    idx = header_idx + 6
                    
            offset += CHUNK_SIZE - OVERLAP
            
    except KeyboardInterrupt:
        print("\n[*] Scan stopped manually by user.")
    except Exception as e:
        print(f"\n❌ Scan Error: {e}")
        
    print(f"\n[*] Scan Done. Recovered GIF files: {file_count}")
    disk.close()

if __name__ == '__main__':
    main()
