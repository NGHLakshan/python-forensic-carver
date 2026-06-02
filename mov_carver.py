import os
import struct

# ⚠️ Set your USB drive letter here
DRIVE_LETTER = 'E'
CHUNK_SIZE = 50 * 1024 * 1024
OVERLAP    = 10 * 1024 * 1024
MOV_MAX_SIZE = 4 * 1024 * 1024 * 1024  # 4GB cap

# QuickTime/MP4 ftyp brands that indicate a MOV file
MOV_BRANDS = {b'qt  ', b'MSNV', b'mp42', b'mp41', b'isom', b'M4V ', b'M4A ', b'f4v ', b'mov '}

# Known top-level atoms that start a valid QuickTime file
VALID_START_ATOMS = {b'ftyp', b'moov', b'mdat', b'free', b'skip', b'wide', b'pnot'}


def get_mov_size(data, idx):
    """
    QuickTime atom structure: <4-byte BE size><4-byte type>[data...]
    We find an ftyp atom and sum all top-level atoms until moov is encountered.
    Falls back to a max-size cap if moov is fragmented.
    """
    if idx + 8 > len(data):
        return -1

    atom_size = struct.unpack_from('>I', data, idx)[0]
    atom_type = data[idx+4:idx+8]

    if atom_type not in VALID_START_ATOMS:
        return -1

    # Extended size: atom_size == 1 means next 8 bytes hold 64-bit size
    if atom_size == 1:
        if idx + 16 > len(data):
            return -1
        atom_size = struct.unpack_from('>Q', data, idx + 8)[0]

    if atom_size < 8 or atom_size > MOV_MAX_SIZE:
        return -1

    # Validate ftyp brand if this is an ftyp atom
    if atom_type == b'ftyp':
        brand = data[idx+8:idx+12]
        if brand not in MOV_BRANDS:
            return -1

    # Walk subsequent atoms to find total size
    pos = idx
    total = 0
    found_moov = False
    for _ in range(50):  # max 50 top-level atoms
        if pos + 8 > len(data):
            break
        sz = struct.unpack_from('>I', data, pos)[0]
        tp = data[pos+4:pos+8]
        if sz == 1:
            if pos + 16 > len(data):
                break
            sz = struct.unpack_from('>Q', data, pos + 8)[0]
        if sz < 8:
            break
        total += sz
        if tp == b'moov':
            found_moov = True
            break
        pos += sz
        if total > MOV_MAX_SIZE:
            return -1

    if not found_moov:
        # Accept anyway with size of first atom if it is moov directly
        return atom_size if atom_type == b'moov' else -1

    return total


def main():
    print("1. Script Started...")
    output_dir = "Recovered_MOV"
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

    print("3. Starting QuickTime MOV Carver Scan...")
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
            while idx < len(chunk) - 8:
                # Search for ftyp atom (most reliable MOV/MP4 start marker)
                sig_idx = chunk.find(b'ftyp', idx)
                if sig_idx < 4:
                    idx = sig_idx + 4 if sig_idx != -1 else len(chunk)
                    continue
                if sig_idx >= CHUNK_SIZE - OVERLAP:
                    break

                # The atom starts 4 bytes before 'ftyp'
                atom_start = sig_idx - 4
                total_size = get_mov_size(chunk, atom_start)

                if total_size != -1 and total_size > 1024:
                    file_count += 1
                    fname = f"recovered_{file_count}.mov"
                    bytes_in_chunk = min(total_size, len(chunk) - atom_start)

                    with open(os.path.join(output_dir, fname), 'wb') as f:
                        f.write(chunk[atom_start:atom_start + bytes_in_chunk])
                        bytes_left = total_size - bytes_in_chunk
                        if bytes_left > 0:
                            disk.seek(offset + atom_start + bytes_in_chunk)
                            while bytes_left > 0:
                                read_len = min(bytes_left, 5 * 1024 * 1024)
                                block = disk.read(read_len)
                                if not block:
                                    break
                                f.write(block)
                                bytes_left -= len(block)

                    print(f"  [+] 🎯 Recovered {fname} ({total_size:,} bytes)", flush=True)
                    idx = sig_idx + total_size
                else:
                    idx = sig_idx + 4

            offset += CHUNK_SIZE - OVERLAP

    except KeyboardInterrupt:
        print("\n[*] Scan stopped by user.")
    except Exception as e:
        print(f"\n❌ Scan Error: {e}")

    print(f"\n[*] Scan complete. Recovered {file_count} MOV files.")
    disk.close()


if __name__ == '__main__':
    main()
