"""
FAT32 Deleted File Parser
=========================
Reads a FAT32-formatted drive natively via raw sector I/O and lists
all deleted directory entries (marker byte 0xE5).

Run this script as Administrator so that the raw drive handle can be opened.
"""

import struct

# ─── Configuration ────────────────────────────────────────────────────────────
DRIVE_LETTER = 'E'
# ──────────────────────────────────────────────────────────────────────────────

BYTES_PER_SECTOR = 512          # default; overwritten after boot-sector parse
DELETED_MARKER   = 0xE5         # FAT32 "deleted entry" signature

# Attribute flag – entries with VOLUME_LABEL or LFN bits are skipped
ATTR_VOLUME_LABEL = 0x08
ATTR_LFN          = 0x0F
ATTR_DIRECTORY    = 0x10


# ── 1. Low-level sector reader ────────────────────────────────────────────────

def read_sector(drive_path: str, sector_number: int, sector_size: int = 512) -> bytes:
    """Return exactly `sector_size` bytes from `sector_number` on the raw drive."""
    with open(drive_path, 'rb') as fh:
        fh.seek(sector_number * sector_size)
        data = fh.read(sector_size)
    if len(data) < sector_size:
        raise IOError(
            f"Short read at sector {sector_number}: "
            f"expected {sector_size} bytes, got {len(data)}."
        )
    return data


# ── 2. Boot-sector / BPB parser ───────────────────────────────────────────────

def parse_boot_sector(drive_path: str) -> dict:
    """
    Parse the FAT32 BIOS Parameter Block (BPB) from sector 0.

    Returns a dict with the geometry fields and the calculated
    data_area_start (first sector of cluster 2).
    """
    raw = read_sector(drive_path, 0)

    # Unpack the standard BPB fields
    bytes_per_sector   = struct.unpack_from('<H', raw, 11)[0]
    sectors_per_cluster= struct.unpack_from('<B', raw, 13)[0]
    reserved_sectors   = struct.unpack_from('<H', raw, 14)[0]
    num_fats           = struct.unpack_from('<B', raw, 16)[0]
    # FAT32: the 16-bit "sectors per FAT" field at offset 22 is 0; real value is at 36
    sectors_per_fat_16 = struct.unpack_from('<H', raw, 22)[0]
    sectors_per_fat_32 = struct.unpack_from('<I', raw, 36)[0]
    sectors_per_fat    = sectors_per_fat_32 if sectors_per_fat_16 == 0 else sectors_per_fat_16
    root_cluster       = struct.unpack_from('<I', raw, 44)[0]

    # First data sector = reserved + (num_fats × sectors_per_fat)
    data_area_start = reserved_sectors + (num_fats * sectors_per_fat)

    geometry = {
        'bytes_per_sector'   : bytes_per_sector,
        'sectors_per_cluster': sectors_per_cluster,
        'reserved_sectors'   : reserved_sectors,
        'num_fats'           : num_fats,
        'sectors_per_fat'    : sectors_per_fat,
        'root_cluster'       : root_cluster,
        'data_area_start'    : data_area_start,
    }
    return geometry


# ── 3. FAT chain reader ───────────────────────────────────────────────────────

def read_fat_entry(drive_path: str, cluster: int, geo: dict) -> int:
    """Return the FAT32 value for `cluster` (next cluster in chain, or EOC/BAD)."""
    fat_offset   = geo['reserved_sectors'] * geo['bytes_per_sector']
    entry_offset = fat_offset + cluster * 4
    sector_num   = entry_offset // geo['bytes_per_sector']
    byte_in_sec  = entry_offset  % geo['bytes_per_sector']

    raw = read_sector(drive_path, sector_num, geo['bytes_per_sector'])
    return struct.unpack_from('<I', raw, byte_in_sec)[0] & 0x0FFFFFFF


def cluster_to_sector(cluster: int, geo: dict) -> int:
    """Convert a FAT32 cluster number to its first sector number."""
    return geo['data_area_start'] + (cluster - 2) * geo['sectors_per_cluster']


def read_cluster_chain(drive_path: str, start_cluster: int, geo: dict) -> bytes:
    """
    Walk the FAT chain starting at `start_cluster` and return all raw bytes.
    Stops at EOC (>= 0x0FFFFFF8) or cluster 0/1 (invalid).
    """
    data    = b''
    cluster = start_cluster
    visited = set()

    while cluster >= 2 and cluster < 0x0FFFFFF8:
        if cluster in visited:          # loop guard
            break
        visited.add(cluster)

        sector = cluster_to_sector(cluster, geo)
        for s in range(geo['sectors_per_cluster']):
            data += read_sector(drive_path, sector + s, geo['bytes_per_sector'])

        cluster = read_fat_entry(drive_path, cluster, geo)

    return data


# ── 4. Directory entry parser ─────────────────────────────────────────────────

def parse_directory_entries(raw: bytes) -> list:
    """
    Parse 32-byte FAT directory entries from a raw directory cluster buffer.
    Returns a list of dicts, one per valid entry.
    """
    entries = []
    for offset in range(0, len(raw), 32):
        entry = raw[offset: offset + 32]
        if len(entry) < 32:
            break

        first_byte = entry[0]

        # 0x00 → remaining entries are free (no more entries follow)
        if first_byte == 0x00:
            break

        attributes = entry[11]

        # Skip LFN (Long File Name) and Volume-Label entries
        if attributes == ATTR_LFN or (attributes & ATTR_VOLUME_LABEL):
            continue

        name_raw  = entry[0:8]
        ext_raw   = entry[8:11]
        hi_cluster= struct.unpack_from('<H', entry, 20)[0]
        lo_cluster= struct.unpack_from('<H', entry, 26)[0]
        file_size = struct.unpack_from('<I', entry, 28)[0]
        start_cls = (hi_cluster << 16) | lo_cluster

        is_deleted   = (first_byte == DELETED_MARKER)
        is_directory = bool(attributes & ATTR_DIRECTORY)

        # Decode the 8.3 name; replace the deleted marker with '?' for display
        if is_deleted:
            name_bytes = b'?' + name_raw[1:]
        else:
            name_bytes = name_raw

        name = name_bytes.decode('ascii', errors='replace').strip()
        ext  = ext_raw.decode('ascii', errors='replace').strip()

        entries.append({
            'name'      : name,
            'ext'       : ext,
            'attributes': attributes,
            'start_cls' : start_cls,
            'file_size' : file_size,
            'is_deleted': is_deleted,
            'is_dir'    : is_directory,
        })

    return entries


# ── 5. Recursive directory scanner ───────────────────────────────────────────

def scan_directory(drive_path: str, cluster: int, geo: dict,
                   deleted_files: list, depth: int = 0) -> None:
    """
    Recursively walk a FAT32 directory tree rooted at `cluster`.
    Appends deleted-file dicts to `deleted_files`.
    """
    if depth > 20:          # safety: don't recurse infinitely
        return

    raw     = read_cluster_chain(drive_path, cluster, geo)
    entries = parse_directory_entries(raw)

    for e in entries:
        # Skip dot / dot-dot entries
        if e['name'].strip('.') == '':
            continue

        if e['is_deleted'] and not e['is_dir']:
            deleted_files.append(e)

        elif e['is_dir'] and not e['is_deleted'] and e['start_cls'] >= 2:
            # Recurse into live sub-directories only
            scan_directory(drive_path, e['start_cls'], geo,
                           deleted_files, depth + 1)


# ── 6. Main entry point ───────────────────────────────────────────────────────

def main():
    drive_path = f'\\\\.\\{DRIVE_LETTER}:'
    print("=" * 60)
    print(f"  FAT32 Deleted File Scanner  —  Drive {DRIVE_LETTER}:")
    print("=" * 60)

    try:
        # Step A – parse the boot sector / BPB
        print("\n[*] Reading boot sector …")
        geo = parse_boot_sector(drive_path)

        print(f"    Bytes per sector    : {geo['bytes_per_sector']}")
        print(f"    Sectors per cluster : {geo['sectors_per_cluster']}")
        print(f"    Reserved sectors    : {geo['reserved_sectors']}")
        print(f"    Number of FATs      : {geo['num_fats']}")
        print(f"    Sectors per FAT     : {geo['sectors_per_fat']}")
        print(f"    Root cluster        : {geo['root_cluster']}")
        print(f"    Data area start     : sector {geo['data_area_start']}")

        # Step B – recursively scan the directory tree
        print("\n[*] Scanning directory entries for deleted files …\n")
        deleted_files = []
        scan_directory(drive_path, geo['root_cluster'], geo, deleted_files)

        # Step C – report results
        if not deleted_files:
            print("  No deleted files found.")
        else:
            print(f"  Found {len(deleted_files)} deleted file(s):\n")
            print(f"  {'#':<5} {'Name':<12} {'Ext':<6} {'Start Cluster':<15} {'Size (bytes)'}")
            print(f"  {'-'*5} {'-'*12} {'-'*6} {'-'*15} {'-'*12}")
            for i, f in enumerate(deleted_files, 1):
                full_name = f"{f['name']}.{f['ext']}" if f['ext'] else f['name']
                print(
                    f"  {i:<5} {full_name:<18} "
                    f"{f['start_cls']:<15} {f['file_size']}"
                )

        print("\n[*] Scan complete.")

    except PermissionError:
        print(
            "\n[ERROR] Permission denied.\n"
            "        Please run this script as Administrator:\n"
            "        Right-click your terminal → 'Run as administrator'\n"
            "        then execute the script again."
        )
    except FileNotFoundError:
        print(
            f"\n[ERROR] Drive '{DRIVE_LETTER}:' not found or not accessible.\n"
            f"        Make sure the USB drive is connected and the letter is correct."
        )
    except Exception as exc:
        print(f"\n[ERROR] Unexpected error: {exc}")


if __name__ == '__main__':
    main()
