import os
import struct

# ⚠️ Set your USB drive letter here
DRIVE_LETTER = 'E'
CHUNK_SIZE = 64 * 1024 * 1024
OVERLAP    =  2 * 1024 * 1024
SEVENZ_MAX_SIZE = 4 * 1024 * 1024 * 1024  # 4GB cap

# 7-Zip signature: "7z" + 4 magic bytes
SEVENZ_SIG = b'\x37\x7A\xBC\xAF\x27\x1C'


def get_7z_size(data, idx):
    """
    7z header layout (after 6-byte signature):
    - 2 bytes: version major/minor
    - 4 bytes: CRC of StartHeader
    - 8 bytes: NextHeaderOffset (LE)
    - 8 bytes: NextHeaderSize (LE)
    - 4 bytes: NextHeaderCRC
    Total header = 32 bytes.
    File size = 32 + NextHeaderOffset + NextHeaderSize
    """
    if idx + 32 > len(data):
        return -1

    try:
        next_header_offset = struct.unpack_from('<Q', data, idx + 12)[0]
        next_header_size   = struct.unpack_from('<Q', data, idx + 20)[0]
    except struct.error:
        return -1

    total_size = 32 + next_header_offset + next_header_size
    if total_size < 32 or total_size > SEVENZ_MAX_SIZE:
        return -1
    return total_size


def main():
    print("1. Script Started...")
    output_dir = "Recovered_7z"
    os.makedirs(output_dir, exist_ok=True)

    drive_path = f'\\\\.\\{DRIVE_LETTER}:'
    print(f"2. Opening drive: {drive_path}")
    try:
        disk = open(drive_path, 'rb')
    except PermissionError:
        print("\n❌ PermissionError: Run the script as Administrator!")
        return
    except Exception as e:
        print(f"\n❌ ERROR: Cannot open drive. Details: {e}")
        return

    print("3. Starting 7-Zip Archive Carver Scan...")
    offset = 0
    file_count = 0

    try:
        while True:
            disk.seek(offset)
            chunk = disk.read(CHUNK_SIZE)
            if not chunk:
                print("\n[*] End of drive reached.")
                break

            if offset % (CHUNK_SIZE * 2) == 0:
                print(f"[*] Scanning... Passed {offset / (1024*1024):.1f} MB...", flush=True)

            idx = 0
            while idx < len(chunk) - 32:
                header_idx = chunk.find(SEVENZ_SIG, idx)
                if header_idx == -1 or header_idx >= CHUNK_SIZE - OVERLAP:
                    break

                total_size = get_7z_size(chunk, header_idx)
                if total_size != -1:
                    file_count += 1
                    fname = f"recovered_{file_count}.7z"
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
                    idx = header_idx + max(total_size, 6)
                else:
                    idx = header_idx + 6

            offset += CHUNK_SIZE - OVERLAP

    except KeyboardInterrupt:
        print("\n[*] Scan stopped by user.")
    except Exception as e:
        print(f"\n❌ Scan Error: {e}")

    print(f"\n[*] Scan complete. Recovered {file_count} 7z archives.")
    disk.close()


if __name__ == '__main__':
    main()
