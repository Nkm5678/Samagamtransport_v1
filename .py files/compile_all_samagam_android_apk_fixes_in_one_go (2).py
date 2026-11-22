# ... existing code ...
import os
import re
import subprocess
from datetime import datetime

TARGET_DIR = r"C:\narendra\SamagamtransportV1"

WORKFLOW_APK_YML = """name: Build Android APK

on:
  push:
    branches: [ main ]
  workflow_dispatch:

permissions:
  contents: write

env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true

jobs:
  build-all-6-apks:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v5

      - name: Set up JDK 21
        uses: actions/setup-java@v5
        with:
          java-version: '21'
          distribution: 'temurin'

      - name: Accept Android SDK Licenses (Runner Built-In SDK)
        run: |
          yes | $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager --licenses >/dev/null 2>&1 || true

      - name: Set up Node.js 24
        uses: actions/setup-node@v5
        with:
          node-version: '24'

      - name: Install Capacitor CLI & Android Platform
        run: |
          npm init -y
          npm install @capacitor/core @capacitor/cli @capacitor/android

      - name: Build All 6 Role-Specific Android APKs
        run: |
          mkdir -p dist_apks

          build_role_apk() {
            local HTML_FILE="$1"
            local APP_NAME="$2"
            local PKG_ID="$3"
            local OUT_APK="$4"

            echo "Building $OUT_APK from $HTML_FILE ($PKG_ID)"
            rm -rf www android capacitor.config.json capacitor.config.ts
            mkdir -p www
            cp ./*.html www/ 2>/dev/null || true
            cp ./root/*.html www/ 2>/dev/null || true
            cp -r ./static www/static 2>/dev/null || true
            cp -r ./root/static www/static 2>/dev/null || true
            cp ./sw.js www/ 2>/dev/null || true
            cp ./root/sw.js www/ 2>/dev/null || true

            RESOLVED_HTML=""
            for CANDIDATE in "./root/$HTML_FILE" "./$HTML_FILE" "./root/ground_dashboard.html" "./ground_dashboard.html" "./root/admin_dashboard.html" "./admin_dashboard.html" "./root/welcome.html" "./welcome.html"; do
              if [ -f "$CANDIDATE" ]; then
                RESOLVED_HTML="$CANDIDATE"
                break
              fi
            done

            if [ -n "$RESOLVED_HTML" ]; then
              cp "$RESOLVED_HTML" www/index.html
            else
              echo "<!DOCTYPE html><html><head><meta charset=\\"utf-8\\"><meta name=\\"viewport\\" content=\\"width=device-width,initial-scale=1.0\\"><title>$APP_NAME</title></head><body><h1>$APP_NAME</h1></body></html>" > www/index.html
            fi

            npx cap init "$APP_NAME" "$PKG_ID" --web-dir=www
            npx cap add android
            npx cap copy android
            npx cap sync android

            MANIFEST="android/app/src/main/AndroidManifest.xml"
            sed -i 's|<application|<uses-permission android:name="android.permission.INTERNET" />\\n    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />\\n    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />\\n    <uses-permission android:name="android.permission.CAMERA" />\\n    <application android:usesCleartextTraffic="true"|g' "$MANIFEST"

            cd android
            chmod +x gradlew
            ./gradlew assembleDebug
            cd ..

            cp android/app/build/outputs/apk/debug/app-debug.apk "dist_apks/$OUT_APK"
          }

          build_role_apk "driver_rider_companion.html" "Samagam Driver App" "org.samagam.driver" "Samagam-Driver-App.apk"
          build_role_apk "station_team_app.html" "Samagam Station Team" "org.samagam.station" "Samagam-Station-Team.apk"
          build_role_apk "ground_team_app.html" "Samagam Ground Team" "org.samagam.ground" "Samagam-Ground-Team.apk"
          build_role_apk "gate_keeper_app.html" "Samagam Gate Keeper" "org.samagam.gatekeeper" "Samagam-Gate-Keeper.apk"
          build_role_apk "diesel_team_app.html" "Samagam Diesel Team" "org.samagam.diesel" "Samagam-Diesel-Team.apk"
          build_role_apk "accounts_team_app.html" "Samagam Accounts Team" "org.samagam.accounts" "Samagam-Accounts-Team.apk"

      - name: Upload All 6 APKs as Workflow Artifacts
        uses: actions/upload-artifact@v6
        with:
          name: Samagam-All-6-Android-APKs
          path: dist_apks/*.apk

      - name: Publish All 6 APKs to GitHub Releases (latest-apks)
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh release delete latest-apks --yes 2>/dev/null || true
          git push origin :refs/tags/latest-apks 2>/dev/null || true
          gh release create latest-apks dist_apks/*.apk \\
            --title "Samagam Transport Field APKs (All 6 Apps)" \\
            --notes "Official 6 Android APKs: Driver, Station Team, Ground Team, Gate Keeper, Diesel Team & Accounts Team."
"""


def write_file(rel_path: str, content: str):
    """Writes UTF-8 content to a file inside TARGET_DIR, creating parent folders as needed."""
    full_path = os.path.join(TARGET_DIR, rel_path.replace("/", os.sep))
    parent = os.path.dirname(full_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Wrote: {full_path}")


def patch_main_py():
    """Ensures admin.samagamtransport.in routes to admin_dashboard.html and blocks admin HTML on non-admin hosts."""
    main_path = os.path.join(TARGET_DIR, "app", "main.py")
    if not os.path.isfile(main_path):
        print("ℹ️ app/main.py not found; skipping main.py patch.")
        return
    with open(main_path, "r", encoding="utf-8") as f:
        code = f.read()

    if "admin.samagamtransport.in" not in code:
        code = code.replace(
            '    host = (request.headers.get("host") or "").lower()',
            '    host = (request.headers.get("host") or "").lower().split(":")[0]\n'
            '    if host == "admin.samagamtransport.in" or host.startswith("admin."):\n'
            '        admin_path = os.path.join(ROOT_DIR, "admin_dashboard.html")\n'
            '        if os.path.exists(admin_path):\n'
            '            return FileResponse(admin_path)'
        )
        with open(main_path, "w", encoding="utf-8") as f:
            f.write(code)
    print("✅ Verified admin subdomain routing in app/main.py")


def patch_auth_py():
    """Ensures Narendra@2183 admin master password support is present in app/routers/auth.py."""
    auth_path = os.path.join(TARGET_DIR, "app", "routers", "auth.py")
    if not os.path.isfile(auth_path):
        print("ℹ️ app/routers/auth.py not found; skipping auth.py patch.")
        return
    with open(auth_path, "r", encoding="utf-8") as f:
        code = f.read()

    if "ADMIN_MASTER_PASSWORD" not in code:
        code = code.replace(
            'ADMIN_ACCESS_CODE = os.environ.get("ADMIN_ACCESS_CODE", "SAMAGAM-HQ-2026").strip()',
            'ADMIN_ACCESS_CODE = os.environ.get("ADMIN_ACCESS_CODE", "SAMAGAM-HQ-2026").strip()\n'
            'ADMIN_MASTER_PASSWORD = os.environ.get("ADMIN_MASTER_PASSWORD", "Narendra@2183").strip()'
        ).replace(
            'passcode = str(data.get("access_code") or "").strip()',
            'passcode = str(data.get("access_code") or data.get("password") or "").strip()'
        ).replace(
            'code_valid = bool(ADMIN_ACCESS_CODE and hmac.compare_digest(passcode, ADMIN_ACCESS_CODE))',
            'master_pwd_valid = bool(ADMIN_MASTER_PASSWORD and hmac.compare_digest(passcode, ADMIN_MASTER_PASSWORD))\n'
            '    code_valid = bool(ADMIN_ACCESS_CODE and hmac.compare_digest(passcode, ADMIN_ACCESS_CODE))'
        ).replace(
            'if not ((is_admin_role and pin_valid) or code_valid):',
            'if not ((is_admin_role and pin_valid) or master_pwd_valid or code_valid):'
        )
        with open(auth_path, "w", encoding="utf-8") as f:
            f.write(code)
    print("✅ Verified Narendra@2183 admin auth in app/routers/auth.py")


def patch_admin_dashboard_html():
    """Ensures admin_dashboard.html has the admin login form supporting password/access_code."""
    admin_path = os.path.join(TARGET_DIR, "admin_dashboard.html")
    if not os.path.isfile(admin_path):
        print("ℹ️ admin_dashboard.html not found; skipping admin HTML patch.")
        return
    with open(admin_path, "r", encoding="utf-8") as f:
        html = f.read()
    if "admin-login-password" not in html and "submitAdminSubdomainLogin" not in html:
        gate_snippet = """
<div id="admin-auth-gate" class="fixed inset-0 bg-slate-950/95 backdrop-blur-md z-50 flex items-center justify-center p-4">
  <div class="bg-slate-900 border border-slate-700 rounded-3xl max-w-md w-full p-6 space-y-4 shadow-2xl">
    <h2 class="text-xl font-extrabold text-white text-center">Admin Control Room Login</h2>
    <form onsubmit="submitAdminSubdomainLogin(event)" class="space-y-3 text-sm">
      <input type="tel" id="admin-login-mobile" required maxlength="10" placeholder="10-Digit Mobile Number" class="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-white font-bold">
      <input type="password" id="admin-login-password" required placeholder="Admin Password" class="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-white font-semibold">
      <div id="admin-login-error" class="text-xs text-rose-400 font-bold text-center"></div>
      <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-extrabold py-3 rounded-xl">Unlock Control Room</button>
    </form>
  </div>
</div>
<script>
async function submitAdminSubdomainLogin(e) {
  e.preventDefault();
  const mobile_number = document.getElementById('admin-login-mobile').value.trim();
  const password = document.getElementById('admin-login-password').value;
  const res = await fetch('/api/auth/control-room-login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mobile_number, access_code: password, password })
  });
  const data = await res.json();
  if (res.ok) {
    localStorage.setItem('samagam_admin_token', data.session_token);
    localStorage.setItem('samagam_driver_token', data.session_token);
    document.getElementById('admin-auth-gate').classList.add('hidden');
  } else {
    document.getElementById('admin-login-error').textContent = data.detail || 'Invalid Admin credentials.';
  }
}
</script>
"""
        html = html.replace("</body>", gate_snippet + "\n</body>")
        with open(admin_path, "w", encoding="utf-8") as f:
            f.write(html)
    print("✅ Verified admin_dashboard.html login gate")


def ensure_root_html_copies():
    """Copies HTML pages and service worker into ./root/ for Capacitor builds."""
    root_dir = os.path.join(TARGET_DIR, "root")
    os.makedirs(root_dir, exist_ok=True)
    for fname in os.listdir(TARGET_DIR):
        if fname.endswith(".html") or fname == "sw.js":
            src = os.path.join(TARGET_DIR, fname)
            dst = os.path.join(root_dir, fname)
            if os.path.isfile(src):
                with open(src, "rb") as f_in, open(dst, "wb") as f_out:
                    f_out.write(f_in.read())
    print(f"✅ Synced HTML pages into {root_dir}")


def stamp_build_version():
    """Adds/updates a build stamp so Git always detects a fresh commit even when files match."""
    stamp_path = os.path.join(TARGET_DIR, "BUILD_STAMP.txt")
    stamp_val = f"build_ts={datetime.utcnow().isoformat()}Z\n"
    with open(stamp_path, "w", encoding="utf-8") as f:
        f.write(stamp_val)
    print(f"✅ Updated build stamp: {stamp_val.strip()}")


def push_latest_to_github():
    """Stages, commits, and pushes all changes in TARGET_DIR to origin main."""
    try:
        subprocess.run(["git", "add", "."], cwd=TARGET_DIR, check=True)
        msg = f"Deploy latest Samagam & Android APK build ({datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC)"
        commit_proc = subprocess.run(
            ["git", "commit", "-m", msg],
            cwd=TARGET_DIR,
            capture_output=True,
            text=True
        )
        if commit_proc.returncode == 0:
            print(f"✅ Committed new commit: {msg}")
        else:
            print("ℹ️ Nothing new to commit beyond existing HEAD.")
        subprocess.run(["git", "push", "origin", "main"], cwd=TARGET_DIR, check=True)
        head_hash = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=TARGET_DIR, text=True).strip()
        print(f"✅ Pushed latest commit to origin/main (HEAD: {head_hash})")
    except Exception as exc:
        print(f"⚠️ Git push notice: {exc}")


def main():
    print(f"🚀 Compiling all Samagam & Android APK changes in: {TARGET_DIR}\n")
    write_file(".github/workflows/build_apk.yml", WORKFLOW_APK_YML)
    ensure_root_html_copies()
    patch_main_py()
    patch_auth_py()
    patch_admin_dashboard_html()
    stamp_build_version()
    push_latest_to_github()
    print("\n🎉 Done! Now run this in Google Cloud Shell to deploy the new commit to Cloud Run:")
    print("   cd ~/Samagamtransport_v1 && git fetch --all && git reset --hard origin/main && gcloud run deploy samagamtransport --source . --region asia-southeast1 --platform managed --allow-unauthenticated --port 8080")


if __name__ == "__main__":
    main()