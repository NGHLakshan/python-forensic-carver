import os
import subprocess
import sys

# Carver modules (dynamically loaded via importlib)
hidden_imports = [
    "jpg_carver", "png_carver", "bmp_carver", "gif_carver",
    "mp3_carver", "wav_carver", "mp4_carver", "avi_carver",
    "mov_carver", "mkv_carver", "pdf_carver", "docx_carver",
    "xlsx_carver", "pptx_carver", "zip_carver", "rar_carver",
    "7z_carver", "iso_carver", "pst_carver", "sqlite_carver",
    "xml_carver", "html_carver", "exe_carver", "fat32_deleted_files",
    "file_validator", "output_organizer", "report_generator",
    "chain_of_custody",
    # pywebview & its Windows backend (Edge WebView2)
    "webview",
    "webview.platforms.winforms",
    "clr",
    "pythonnet",
]

add_data_path = f"web_ui{os.pathsep}web_ui"

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--name", "PythonForensicTool",
    "--add-data", add_data_path,
    "--onefile",        # Single standalone EXE
    "--uac-admin",      # Request Administrator on launch
    "--noconfirm",
    "--clean",
    "--windowed",       # No console window — pure native app appearance
]

for mod in hidden_imports:
    cmd.extend(["--hidden-import", mod])

cmd.append("api_server.py")

print("=" * 55)
print("  Building SECURE NATIVE APP EXE...")
print("=" * 55)
print(f"Command:\n{' '.join(cmd)}\n")

try:
    subprocess.run(cmd, check=True)
    print("\n" + "=" * 55)
    print("  SUCCESS: Native App EXE created!")
    print(f"  Location: {os.path.join(os.getcwd(), 'dist', 'PythonForensicTool.exe')}")
    print("=" * 55)
except subprocess.CalledProcessError as e:
    print(f"\nERROR: Build failed with return code {e.returncode}")
    sys.exit(1)
