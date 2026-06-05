import os
import struct

# ⚠️ Set your USB drive letter here
DRIVE_LETTER = 'E'
CHUNK_SIZE = 64 * 1024 * 1024
OVERLAP    =  2 * 1024 * 1024

# ISO 9660: Primary Volume Descriptor starts at sector 16 (offset 32768)
# Signature bytes at offset 1 within PVD: \x01CD001\x01
ISO_PVD_SIG  = b'\x01CD001\x01'
SECTOR_SIZE  = 2048  # ISO 9660 sector size


def find_iso_size(data, pvd_idx):
    """
    The PVD is at sector 16 inside the file.
    PVD contains volume space size (in sectors) at offset 80 (both LE/BE).
    Total ISO size = volume_sectors * SECTOR_SIZE.
    pvd_idx points to the start of the PVD (the \x01 byte).
    """
    if pvd_idx + 160 > len(data):
        return -1, -1

    # Volume space size (LE) at PVD offset 80 (already relative to PVD start)
    vol_size_le = struct.unpack_from('<I', data, pvd_idx + 80)[0]
    vol_size_be = struct.unpack_from('>I', data, pvd_idx + 84)[0]

    if vol_size_le != vol_size_be or vol_size_le == 0:
        return -1, -1

    total_sectors = vol_size_le
    # The ISO starts 16 sectors before this PVD
    iso_start_offset_in_chunk = pvd_idx - (16 * SECTOR_SIZE)
    if iso_start_offset_in_chunk < 0:
        return -1, -1

    total_size = total_sectors * SECTOR_SIZE
    if total_size < SECTOR_SIZE * 18 or total_size > 50 * 1024 * 1024 * 1024:  # 50GB max
        return -1, -1

    return iso_start_offset_in_chunk, total_size


def main():
    print("1. Script Started...")
    output_dir = "Recovered_ISO"
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

    print("3. Starting ISO 9660 Disk Image Carver Scan...")
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
            while idx < len(chunk) - 160:
                pvd_idx = chunk.find(ISO_PVD_SIG, idx)
                if pvd_idx == -1 or pvd_idx >= CHUNK_SIZE - OVERLAP:
                    break

                iso_start, total_size = find_iso_size(chunk, pvd_idx)
                if iso_start != -1 and total_size != -1:
                    file_count += 1
                    fname = f"recovered_{file_count}.iso"
                    bytes_in_chunk = min(total_size, len(chunk) - iso_start)

                    with open(os.path.join(output_dir, fname), 'wb') as f:
                        f.write(chunk[iso_start:iso_start + bytes_in_chunk])
                        bytes_left = total_size - bytes_in_chunk
                        if bytes_left > 0:
                            disk.seek(offset + iso_start + bytes_in_chunk)
                            while bytes_left > 0:
                                read_len = min(bytes_left, 10 * 1024 * 1024)
                                block = disk.read(read_len)
                                if not block:
                                    break
                                f.write(block)
                                bytes_left -= len(block)

                    print(f"  [+] 🎯 Recovered {fname} ({total_size:,} bytes)", flush=True)
                    idx = pvd_idx + total_size
                else:
                    idx = pvd_idx + len(ISO_PVD_SIG)

            offset += CHUNK_SIZE - OVERLAP

    except KeyboardInterrupt:
        print("\n[*] Scan stopped by user.")
    except Exception as e:
        print(f"\n❌ Scan Error: {e}")

    print(f"\n[*] Scan complete. Recovered {file_count} ISO images.")
    disk.close()


if __name__ == '__main__':
    main()
