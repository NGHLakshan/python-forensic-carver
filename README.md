# 🔎 Python Forensic Recovery Tool

A professional, standalone Windows forensic data carving tool built in Python.  
Recovers deleted files from raw drives using signature-based carving.

## Features

- **23 file types** — JPG, PNG, BMP, GIF, MP3, WAV, MP4, AVI, MOV, MKV, PDF, DOCX, XLSX, PPTX, ZIP, RAR, 7z, ISO, PST, SQLite, XML, HTML, EXE
- **Modern dark UI** — Real-time live log streaming via Server-Sent Events
- **Native app window** — Opens as a desktop app (no browser needed) via pywebview
- **🔒 Secure by design:**
  - Binds to `127.0.0.1` only — no remote/network access possible
  - One-time random session token — fresh every launch
  - Zero external resource loading — fully offline

## Requirements

```
pip install flask pywebview
```

> Must be run as **Administrator** for raw drive access.

## Run (Development)

```powershell
python api_server.py
```

## Build Standalone EXE

```powershell
python build_exe.py
```

Output: `dist\PythonForensicTool.exe`

## Supported File Types

| Category   | Types |
|------------|-------|
| Images     | JPG, PNG, BMP, GIF |
| Audio      | MP3, WAV |
| Video      | MP4, AVI, MOV, MKV |
| Documents  | PDF, DOCX, XLSX, PPTX, XML, HTML |
| Archives   | ZIP, RAR, 7z, ISO |
| Other      | PST/OST Email, SQLite, EXE |

## Security

- Server binds to `127.0.0.1` (loopback only)
- 64-character hex token generated at each startup
- Token verified on every HTTP request (`403 Forbidden` on mismatch)
- No external network requests — fonts and assets are all local

## License

For educational and lawful forensic use only.
