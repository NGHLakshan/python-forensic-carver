import os

# ⚠️ Set your USB drive letter here
DRIVE_LETTER = 'E'

def find_true_end(data, start_idx):
    """
    Mini JPEG Structure Parser:
    - Reads through APP markers and metadata (skipping embedded EXIF thumbnails)
    - Finds the true Start of Scan (FF DA) segment
    - Then finds the real FF D9 (End of Image) that follows it
    This is how Recuva/PhotoRec correctly identify genuine JPEG footers.
    """
    idx = start_idx + 2  # skip past the FF D8 header
    max_len = len(data)
    true_sos_idx = -1

    while idx < max_len - 1:
        if data[idx] == 0xFF:
            marker = data[idx + 1]

            # Skip padding bytes (FF FF ...)
            if marker == 0xFF:
                idx += 1
                continue

            # Found the real Start of Scan - this is past all thumbnails/metadata
            if marker == 0xDA:
                true_sos_idx = idx
                break

            # Standard JPEG segments with a length field - jump over them entirely
            # This is the key trick: it skips over the embedded EXIF thumbnail
            if (0xE0 <= marker <= 0xEF) or marker in (0xDB, 0xC4, 0xC0, 0xC1, 0xC2, 0xFE, 0xDD):
                if idx + 3 < max_len:
                    length = int.from_bytes(data[idx + 2:idx + 4], 'big')
                    if length < 2:
                        return -1  # corrupt segment
                    idx += 2 + length  # mathematical jump over the entire segment
                    continue
                else:
                    return -1  # not enough data
            elif marker == 0xD9:
                # Encountered an EOI before finding SOS - likely a thumbnail's end
                return -1
            else:
                idx += 2
        else:
            return -1  # structure broken, not a real JPEG here

    if true_sos_idx == -1:
        return -1  # never found a valid Start of Scan

    # Now find the real FF D9 that follows the actual image scan data
    end_idx = data.find(b'\xff\xd9', true_sos_idx + 2)
    if end_idx != -1:
        return end_idx + 2  # include the 2-byte FF D9 footer
    return -1


def main():
    print("1. Script Started...")
    output_dir = "Recovered_Photos"
    os.makedirs(output_dir, exist_ok=True)

    drive_path = chr(92) + chr(92) + '.' + chr(92) + DRIVE_LETTER + ':'
    print(f"2. Opening drive: {drive_path}")

    try:
        disk = open(drive_path, 'rb')
    except PermissionError:
        print("\n❌ PermissionError: Cannot open drive. Please run the script as Administrator!")
        return
    except Exception as e:
        print(f"\n❌ ERROR: Cannot open drive. Details: {e}")
        return

    print("3. Starting Smart JPEG Carver Scan (PhotoRec-style: structure-aware)...")
    file_count = 0

    CHUNK_SIZE = 64 * 1024 * 1024  # 64MB chunks — fewer I/O calls = faster
    OVERLAP    =  2 * 1024 * 1024  # 2MB overlap — enough to catch any cross-boundary header
    offset = 0

    try:
        while True:
            disk.seek(offset)
            chunk = disk.read(CHUNK_SIZE)

            if not chunk:
                print("\n[*] End of drive reached successfully!")
                break

            if offset % (CHUNK_SIZE * 5) == 0:
                print(f"[*] Scanning... Passed {offset / (1024 * 1024):.1f} MB...", flush=True)

            idx = 0
            while idx < len(chunk) - 2:
                # Step 1: Find the next JPEG header (FF D8)
                header_idx = chunk.find(b'\xff\xd8', idx)

                # If not found, or if header is inside the overlap region, stop this chunk
                if header_idx == -1 or header_idx >= CHUNK_SIZE - OVERLAP:
                    break

                # Step 2: Use the structure-aware parser to find the true end
                # This correctly skips embedded EXIF thumbnails (the "Recuva trick")
                end_of_file = find_true_end(chunk, header_idx)

                if end_of_file != -1:
                    extracted = chunk[header_idx:end_of_file]

                    # Filter out tiny fragments (< 10KB) that are not real photos
                    if len(extracted) > 10_000:
                        file_count += 1
                        fname = f"carved_pro_{file_count}.jpg"
                        with open(os.path.join(output_dir, fname), 'wb') as f:
                            f.write(extracted)
                        print(f"  [+] Recovered {fname} ({len(extracted):,} bytes)", flush=True)

                    # Step 3: Resume IMMEDIATELY after the footer of the saved file
                    idx = end_of_file
                else:
                    # Parser failed - skip past this header and look for the next one
                    idx = header_idx + 2

            # Advance the window, keeping the overlap so we don't miss cross-boundary files
            offset += CHUNK_SIZE - OVERLAP

    except KeyboardInterrupt:
        print("\n[*] Scan stopped manually by user.")
    except Exception as e:
        print(f"\n❌ Scan Error: {e}")

    print(f"\n[*] Scan complete. Recovered {file_count} files.")
    disk.close()


if __name__ == '__main__':
    main()