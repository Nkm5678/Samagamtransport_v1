"""
Samagam Transport Platform (49-File Enterprise Architecture)
Automated Directory Tree Builder & GitHub Repository Initializer.
Run: python setup_and_push_github.py
"""

import os
import subprocess

PROJECT_DIR = "samagamtransport"

DIRECTORIES = [
    "",
    "app",
    "app/services",
    "app/routers",
    "static",
    ".github/workflows",
]

INIT_FILES = {
    "app/__init__.py": "",
    "app/services/__init__.py": "",
    "app/routers/__init__.py": "",
    ".gitignore": """__pycache__/
*.py[cod]
*.db
*.sqlite3
.env
.venv/
venv/
.DS_Store
dist/
build/
""",
}


def build_enterprise_tree():
    for d in DIRECTORIES:
        target = os.path.join(PROJECT_DIR, d) if d else PROJECT_DIR
        os.makedirs(target, exist_ok=True)
        print(f"📁 Verified folder: {target}/")

    for rel_path, content in INIT_FILES.items():
        full_path = os.path.join(PROJECT_DIR, rel_path)
        if not os.path.exists(full_path):
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ Created {full_path}")

    try:
        subprocess.run(["git", "init"], cwd=PROJECT_DIR, check=True)
        subprocess.run(["git", "branch", "-M", "main"], cwd=PROJECT_DIR, check=True)
        print("\n🚀 Git repository initialized in ./samagamtransport/ on branch 'main'.")
        print("Next: Place all 49 files into their folders, then run:")
        print("  cd samagamtransport")
        print("  git add . && git commit -m 'Upload all 49 files'")
        print("  git remote add origin https://github.com/narendrakmali/Samagamtransport_v1.git")
        print("  git push -u origin main")
    except Exception as e:
        print(f"⚠️ Git initialization note: {e}")


if __name__ == "__main__":
    build_enterprise_tree()