import os
import struct

# ⚠️ Set your USB drive letter here
DRIVE_LETTER = 'E'
CHUNK_SIZE = 64 * 1024 * 1024   # 64MB chunks
OVERLAP    =  2 * 1024 * 1024   # 2MB overlap
AVI_MAX_SIZE = 2 * 1024 * 1024 * 1024  # 2GB cap


def get_avi_size(data, idx):
    """
    AVI structure: RIFF <4-byte LE size> AVI<space>
    The RIFF chunk size includes everything after the first 8 bytes,
    so total file size = 8 + chunk_size.
    """
    if idx + 12 > len(data):
        return -1
    if data[idx:idx+4] != b'RIFF':
        return -1
    if data[idx+8:idx+12] != b'AVI ':
        return -1
    chunk_size = struct.unpack_from('<I', data, idx + 4)[0]
    total_size = 8 + chunk_size
    if total_size < 1024 or total_size > AVI_MAX_SIZE:
        return -1
    return total_size


def main():
    print("1. Script Started...")
    output_dir = "Recovered_AVI"
    os.makedirs(output_dir, exist_ok=True)

    drive_path = chr(92) + chr(92) + '.' + chr(92) + DRIVE_LETTER + ':'
    print(f"2. Opening drive: {drive_path}")
    try:
        disk = open(drive_path, 'rb')
    except PermissionError:
        print("\n❌ PermissionError: Run the script as Administrator!")
        return
    except Exception as e:
        print(f"\n❌ ERROR: Cannot open drive. Details: {e}")
        return

    print("3. Starting AVI Video Carver Scan...")
    offset = 0
    file_count = 0
    HEADER_SIG = b'RIFF'

    try:
        while True:
            disk.seek(offset)
            chunk = disk.read(CHUNK_SIZE)
            if not chunk:
                print("\n[*] End of drive reached.")
                break

            chunk_idx = offset // max(1, (CHUNK_SIZE - OVERLAP))
            if chunk_idx % 1 == 0:
                print(f"[*] Scanning... Passed {offset / (1024*1024):.1f} MB...", flush=True)

            idx = 0
            while idx < len(chunk) - 12:
                header_idx = chunk.find(HEADER_SIG, idx)
                if header_idx == -1 or header_idx >= CHUNK_SIZE - OVERLAP:
                    break

                total_size = get_avi_size(chunk, header_idx)
                if total_size != -1:
                    file_count += 1
                    fname = f"recovered_{file_count}.avi"

                    bytes_in_chunk = min(total_size, len(chunk) - header_idx)
                    with open(os.path.join(output_dir, fname), 'wb') as f:
                        f.write(chunk[header_idx:header_idx + bytes_in_chunk])
                        bytes_left = total_size - bytes_in_chunk
                        if bytes_left > 0:
                            disk.seek(offset + header_idx + bytes_in_chunk)
                            while bytes_left > 0:
                                read_len = min(bytes_left, 5 * 1024 * 1024)
                                block = disk.read(read_len)
                                if not block:
                                    break
                                f.write(block)
                                bytes_left -= len(block)

                    print(f"  [+] 🎯 Recovered {fname} ({total_size:,} bytes)", flush=True)
                    idx = header_idx + total_size
                else:
                    idx = header_idx + 4

            offset += CHUNK_SIZE - OVERLAP

    except KeyboardInterrupt:
        print("\n[*] Scan stopped by user.")
    except Exception as e:
        print(f"\n❌ Scan Error: {e}")

    print(f"\n[*] Scan complete. Recovered {file_count} AVI files.")
    disk.close()


if __name__ == '__main__':
    main()
