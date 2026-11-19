"""
[File 05] One-Click Project ZIP Archive Builder
Packages the entire samagamtransport/ directory into a clean distributable ZIP.
Run: python create_final_zip_bundle.py
"""

import os
import zipfile
from datetime import datetime

EXCLUDE_DIRS = {"__pycache__", ".git", ".venv", "venv", "node_modules", "android"}
EXCLUDE_EXTS = {".pyc", ".pyo", ".db", ".sqlite3", ".zip"}

def build_zip_bundle():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_filename = f"samagamtransport_release_{timestamp}.zip"
    root_dir = os.path.dirname(os.path.abspath(__file__))

    file_count = 0
    with zipfile.ZipFile(output_filename, "w", zipfile.ZIP_DEFLATED) as zf:
        for foldername, subfolders, filenames in os.walk(root_dir):
            subfolders[:] = [d for d in subfolders if d not in EXCLUDE_DIRS]
            for filename in filenames:
                if any(filename.endswith(ext) for ext in EXCLUDE_EXTS):
                    continue
                filepath = os.path.join(foldername, filename)
                arcname = os.path.relpath(filepath, root_dir)
                zf.write(filepath, arcname)
                file_count += 1

    print(f"📦 Created {output_filename} containing {file_count} files.")

if __name__ == "__main__":
    build_zip_bundle()