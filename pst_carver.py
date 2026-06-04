import os
import struct

# ⚠️ Set your USB drive letter here
DRIVE_LETTER = 'E'
CHUNK_SIZE = 64 * 1024 * 1024
OVERLAP    =  2 * 1024 * 1024
PST_MAX_SIZE = 50 * 1024 * 1024 * 1024  # 50GB cap (PST files can be huge)

# PST/OST magic bytes
PST_MAGIC = b'\x21\x42\x44\x4E'  # "!BDN"

# PST file types
PST_TYPES = {
    0x00: 'pst_32bit',   # ANSI (32-bit) PST
    0x0E: 'ost',         # OST file
    0x0F: 'ost',         # OST file (alt)
    0x14: 'pst_64bit',   # Unicode (64-bit) PST
    0x15: 'pst_64bit',   # Unicode (64-bit) PST (4K)
}


def validate_pst(data, idx):
    """
    PST/OST header layout:
    - 4 bytes: Magic (!BDN)
    - 4 bytes: CRC partial (ignored)
    - 2 bytes: file type (0x00=PST-ANSI, 0x0E/0x0F=OST, 0x14/0x15=PST-Unicode)
    - 2 bytes: file format version
    - 2 bytes: client version
    Returns: (extension, estimated_size) or (-1, -1)
    """
    if idx + 512 > len(data):
        return -1, -1
    if data[idx:idx+4] != PST_MAGIC:
        return -1, -1

    file_type_word = struct.unpack_from('<H', data, idx + 8)[0]
    file_type = file_type_word & 0xFF

    if file_type not in PST_TYPES:
        return -1, -1

    type_name = PST_TYPES[file_type]
    ext = 'ost' if 'ost' in type_name else 'pst'

    # PST/OST don't have a clear total size in the first 512 bytes
    # We use a reasonable cap per type: ANSI PST max 2GB, Unicode PST max 50GB
    estimated_size = 2 * 1024 * 1024 * 1024 if '32bit' in type_name else PST_MAX_SIZE

    return ext, estimated_size


def main():
    print("1. Script Started...")
    output_dir = "Recovered_PST"
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

    print("3. Starting Outlook PST/OST Email Archive Carver Scan...")
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
            while idx < len(chunk) - 512:
                header_idx = chunk.find(PST_MAGIC, idx)
                if header_idx == -1 or header_idx >= CHUNK_SIZE - OVERLAP:
                    break

                ext, max_size = validate_pst(chunk, header_idx)
                if ext != -1:
                    file_count += 1
                    fname = f"recovered_{file_count}.{ext}"
                    bytes_in_chunk = min(max_size, len(chunk) - header_idx)

                    print(f"  [*] Found {ext.upper()} signature at offset {offset + header_idx:,} — extracting...", flush=True)

                    with open(os.path.join(output_dir, fname), 'wb') as f:
                        f.write(chunk[header_idx:header_idx + bytes_in_chunk])
                        bytes_left = max_size - bytes_in_chunk
                        if bytes_left > 0:
                            disk.seek(offset + header_idx + bytes_in_chunk)
                            while bytes_left > 0:
                                read_len = min(bytes_left, 10 * 1024 * 1024)
                                block = disk.read(read_len)
                                if not block:
                                    break
                                # Stop if we hit a long run of zeros (end of PST likely)
                                if block.count(b'\x00') == len(block):
                                    break
                                f.write(block)
                                bytes_left -= len(block)

                    actual = os.path.getsize(os.path.join(output_dir, fname))
                    print(f"  [+] 🎯 Recovered {fname} ({actual:,} bytes)", flush=True)
                    idx = header_idx + 4
                else:
                    idx = header_idx + 4

            offset += CHUNK_SIZE - OVERLAP

    except KeyboardInterrupt:
        print("\n[*] Scan stopped by user.")
    except Exception as e:
        print(f"\n❌ Scan Error: {e}")

    print(f"\n[*] Scan complete. Recovered {file_count} PST/OST files.")
    disk.close()


if __name__ == '__main__':
    main()
