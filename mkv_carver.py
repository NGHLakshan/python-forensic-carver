import os

# ⚠️ Set your USB drive letter here
DRIVE_LETTER = 'E'
CHUNK_SIZE = 50 * 1024 * 1024
OVERLAP    = 10 * 1024 * 1024
MKV_MAX_SIZE = 2 * 1024 * 1024 * 1024  # 2GB cap

# EBML header magic
EBML_HEADER = b'\x1A\x45\xDF\xA3'
MATROSKA_DOCTYPE = b'matroska'
WEBM_DOCTYPE     = b'webm'


def decode_vint(data, pos):
    """Decode EBML variable-length integer. Returns (value, bytes_consumed)."""
    if pos >= len(data):
        return -1, 0
    b = data[pos]
    if b == 0:
        return -1, 0
    # Count leading zeros to find width
    width = 1
    mask = 0x80
    while not (b & mask):
        width += 1
        mask >>= 1
        if width > 8:
            return -1, 0
    value = b & (mask - 1)
    for i in range(1, width):
        if pos + i >= len(data):
            return -1, 0
        value = (value << 8) | data[pos + i]
    return value, width


def validate_mkv(data, idx):
    """
    Check that the EBML header contains DocType = 'matroska' or 'webm'.
    Returns total estimated file size or -1.
    """
    if data[idx:idx+4] != EBML_HEADER:
        return -1

    # Skip to element size (vint after the 4-byte ID)
    size_val, size_bytes = decode_vint(data, idx + 4)
    if size_val == -1 or size_bytes == 0:
        return -1

    header_end = idx + 4 + size_bytes + size_val
    header_content = data[idx + 4 + size_bytes: header_end]

    # Check for doctype
    if MATROSKA_DOCTYPE not in header_content and WEBM_DOCTYPE not in header_content:
        return -1

    # Determine extension
    ext = 'webm' if WEBM_DOCTYPE in header_content else 'mkv'
    return ext


def main():
    print("1. Script Started...")
    output_dir = "Recovered_MKV"
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

    print("3. Starting Matroska MKV/WebM Carver Scan...")
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
                header_idx = chunk.find(EBML_HEADER, idx)
                if header_idx == -1 or header_idx >= CHUNK_SIZE - OVERLAP:
                    break

                result = validate_mkv(chunk, header_idx)
                if result != -1:
                    ext = result
                    # Use max size cap since MKV doesn't embed total size reliably
                    extract_size = min(MKV_MAX_SIZE, len(chunk) - header_idx)
                    file_count += 1
                    fname = f"recovered_{file_count}.{ext}"

                    bytes_in_chunk = extract_size
                    with open(os.path.join(output_dir, fname), 'wb') as f:
                        f.write(chunk[header_idx:header_idx + bytes_in_chunk])
                        # Continue reading from disk up to MKV_MAX_SIZE
                        bytes_left = MKV_MAX_SIZE - bytes_in_chunk
                        if bytes_left > 0:
                            disk.seek(offset + header_idx + bytes_in_chunk)
                            while bytes_left > 0:
                                read_len = min(bytes_left, 5 * 1024 * 1024)
                                block = disk.read(read_len)
                                if not block:
                                    break
                                # Stop at first all-zero 512-byte block (likely end of file)
                                if block == b'\x00' * len(block):
                                    break
                                f.write(block)
                                bytes_left -= len(block)

                    actual_size = os.path.getsize(os.path.join(output_dir, fname))
                    print(f"  [+] 🎯 Recovered {fname} ({actual_size:,} bytes)", flush=True)
                    idx = header_idx + 4
                else:
                    idx = header_idx + 4

            offset += CHUNK_SIZE - OVERLAP

    except KeyboardInterrupt:
        print("\n[*] Scan stopped by user.")
    except Exception as e:
        print(f"\n❌ Scan Error: {e}")

    print(f"\n[*] Scan complete. Recovered {file_count} MKV/WebM files.")
    disk.close()


if __name__ == '__main__':
    main()
