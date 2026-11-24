"""
Samagam Transport Platform — One-Click 'jagriti.jpeg' Logo Sync Across Every Page
1. Ensures static/jagriti.jpeg and root/static/jagriti.jpeg exist (plus .jpg/.png aliases).
2. Scans EVERY .html file in C:\\narendra\\SamagamtransportV1 and ./root/ and:
   - Replaces any old /static/samagam_79_logo.svg, /static/jagriti_proper_logo.svg,
     /static/jagriti.png, or /static/jagriti.jpg with /static/jagriti.jpeg
   - Injects the crisp <img src="/static/jagriti.jpeg"> badge into any page header
     that does not yet display the Jagriti logo.
3. Syncs ./root/ and pushes directly to GitHub (origin/main).

Run inside C:\\narendra\\SamagamtransportV1:
    python sync_jagriti_jpeg_all_pages.py
"""

import glob
import os
import re
import shutil
import subprocess

TARGET_DIR = r"C:\narendra\SamagamtransportV1"
if not os.path.isdir(TARGET_DIR):
    TARGET_DIR = os.path.dirname(os.path.abspath(__file__))

LOGO_IMG_TAG = (
    '<img src="/static/jagriti.jpeg" alt="जागृति — The Awakening" '
    'class="h-10 sm:h-11 w-auto rounded-xl bg-white px-2 py-0.5 shadow border border-amber-300/60 object-contain shrink-0">'
)


def ensure_jagriti_jpeg_files() -> str | None:
    static_dir = os.path.join(TARGET_DIR, "static")
    root_static_dir = os.path.join(TARGET_DIR, "root", "static")
    os.makedirs(static_dir, exist_ok=True)
    if os.path.isdir(os.path.join(TARGET_DIR, "root")):
        os.makedirs(root_static_dir, exist_ok=True)

    master_jpeg = os.path.join(static_dir, "jagriti.jpeg")
    if not os.path.isfile(master_jpeg):
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        candidates = [
            os.path.join(static_dir, "jagriti.jpg"),
            os.path.join(static_dir, "jagriti.png"),
            os.path.join(root_static_dir, "jagriti.jpeg"),
            os.path.join(root_static_dir, "jagriti.jpg"),
        ]
        for pat in ["*jagriti*.jp*g", "*image_ccd68e*.jp*g", "*1001094*.jp*g", "*o9vs4e*.png"]:
            candidates.extend(glob.glob(os.path.join(downloads, pat)))
            candidates.extend(glob.glob(os.path.join(TARGET_DIR, pat)))

        for cand in candidates:
            if os.path.isfile(cand):
                shutil.copy2(cand, master_jpeg)
                print(f"✅ Copied source logo {cand} -> {master_jpeg}")
                break

    if not os.path.isfile(master_jpeg):
        print("❌ Could not locate jagriti.jpeg! Place jagriti.jpeg inside static\\jagriti.jpeg first.")
        return None

    # Copy to .jpg/.png aliases and ./root/static/ so no broken links can ever occur
    for dest_dir in [static_dir, root_static_dir]:
        if os.path.isdir(dest_dir):
            for alias in ["jagriti.jpeg", "jagriti.jpg", "jagriti.png"]:
                dst = os.path.join(dest_dir, alias)
                if os.path.abspath(dst) != os.path.abspath(master_jpeg):
                    shutil.copy2(master_jpeg, dst)
    print("✅ Synced jagriti.jpeg (and .jpg/.png aliases) into static/ and root/static/")
    return master_jpeg


def patch_html_file(fpath: str) -> bool:
    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()

    orig = html
    # Normalize all legacy logo image URLs to /static/jagriti.jpeg
    for old_src in [
        "/static/samagam_79_logo.svg",
        "/static/samagam_79_crest.svg",
        "/static/jagriti_proper_logo.svg",
        "/static/jagriti.png",
        "/static/jagriti.jpg",
    ]:
        html = html.replace(old_src, "/static/jagriti.jpeg")

    # If page has a <header> and still doesn't include /static/jagriti.jpeg, inject the logo badge
    if "/static/jagriti.jpeg" not in html and "<header" in html:
        # Insert inside first flex container inside <header>, or right after <header...>
        patched, count = re.subn(
            r'(<header[^>]*>\s*<div[^>]*>)',
            r'\1\n                ' + LOGO_IMG_TAG,
            html,
            count=1,
            flags=re.DOTALL,
        )
        if count == 0:
            patched = re.sub(
                r'(<header[^>]*>)',
                r'\1\n        <div class="max-w-6xl mx-auto px-4 pt-2">' + LOGO_IMG_TAG + "</div>",
                html,
                count=1,
            )
        html = patched

    if html != orig:
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(html)
        return True
    return False


def main():
    print("=" * 78)
    print(f"🎨 SYNCING /static/jagriti.jpeg LOGO ACROSS ALL PORTALS & APPS: {TARGET_DIR}")
    print("=" * 78)

    if not ensure_jagriti_jpeg_files():
        return

    updated_files = []
    search_dirs = [TARGET_DIR]
    if os.path.isdir(os.path.join(TARGET_DIR, "root")):
        search_dirs.append(os.path.join(TARGET_DIR, "root"))

    for d in search_dirs:
        for fname in os.listdir(d):
            if fname.endswith(".html"):
                fpath = os.path.join(d, fname)
                if os.path.isfile(fpath) and patch_html_file(fpath):
                    updated_files.append(os.path.relpath(fpath, TARGET_DIR))

    for rel in updated_files:
        print(f"✅ Updated logo in: {rel}")

    try:
        subprocess.run(["git", "add", "-f", "static/jagriti.jpeg", "static/jagriti.jpg", "static/jagriti.png"], cwd=TARGET_DIR, check=False)
        if os.path.isdir(os.path.join(TARGET_DIR, "root", "static")):
            subprocess.run(["git", "add", "-f", "root/static/jagriti.jpeg", "root/static/jagriti.jpg", "root/static/jagriti.png"], cwd=TARGET_DIR, check=False)
        subprocess.run(["git", "add", "."], cwd=TARGET_DIR, check=True)
        res = subprocess.run(
            ["git", "commit", "-m", "Add /static/jagriti.jpeg logo across all web portals and field apps"],
            cwd=TARGET_DIR,
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            print("✅ Git committed all updated HTML pages and static/jagriti.jpeg")
        subprocess.run(["git", "push", "origin", "main"], cwd=TARGET_DIR, check=True)
        print("✅ Pushed to GitHub (origin/main)!")
    except Exception as exc:
        print(f"⚠️ Git notice: {exc}")

    print("\n🚀 Next step — run in Google Cloud Shell:")
    print("   cd ~/Samagamtransport_v1 && git fetch --all && git reset --hard origin/main && gcloud run deploy samagamtransport --source . --region asia-southeast1 --platform managed --allow-unauthenticated --port 8080 --timeout=300")


if __name__ == "__main__":
    main()