# Run inside C:\narendra\SamagamtransportV1:
# .\push_and_deploy_all.ps1

$ErrorActionPreference = "Stop"

Write-Host "1. Writing missing Field Web Apps, Proper 'जागृति' Logo & Fixing app/main.py..." -ForegroundColor Cyan

$pyCode = @'
import os, re, shutil

ROOT = os.getcwd()

# A. Ensure all field web app HTML files exist in BOTH project root and ./root/
FIELD_APPS = {
    "station_team_app.html": ("STATION TEAM FIELD APP", "Platform Crowd, MSRTC Cash & Intercom", "rose"),
    "ground_team_app.html": ("GROUND TEAM FIELD APP", "Central Park Dispatch & Seva Allocation", "sky"),
    "gate_keeper_app.html": ("GATE KEEPER MARSHALL APP", "Inward/Outward Turnaround & 24h Odometer", "teal"),
    "diesel_team_app.html": ("DIESEL & FUEL TEAM APP", "Fuel Fill-Up Slips & Safety Audits", "amber"),
    "accounts_team_app.html": ("ACCOUNTS & TREASURY APP", "Petty Cash Floats, MSRTC & 24h Billing", "blue"),
}

for fname, (title, subtitle, color) in FIELD_APPS.items():
    fpath = os.path.join(ROOT, fname)
    rpath = os.path.join(ROOT, "root", fname)
    if not os.path.isfile(fpath) and os.path.isfile(rpath):
        shutil.copy2(rpath, fpath)
    elif not os.path.isfile(fpath):
        html_stub = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | Samagam Transport</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="min-h-screen bg-slate-900 text-slate-100 max-w-md mx-auto border-x border-slate-800 flex flex-col justify-between">
    <header class="bg-{color}-950 border-b border-{color}-800 px-4 py-3.5 flex items-center justify-between">
        <div>
            <h1 class="font-extrabold text-sm text-white">{title}</h1>
            <p class="text-[11px] text-{color}-300">{subtitle}</p>
        </div>
        <a href="/" class="text-xs bg-slate-800 px-2.5 py-1.5 rounded-lg font-bold">Home</a>
    </header>
    <main class="p-4 space-y-4 flex-1">
        <div class="bg-slate-800 border border-slate-700 rounded-2xl p-4 space-y-2 text-xs">
            <div class="font-extrabold text-emerald-400">● Active Field Terminal</div>
            <p class="text-slate-300">Connected to Central Samagam Transport Database. Use the top bar to switch hubs, log movements, or message Control Room.</p>
        </div>
        <div id="live-hubs-box" class="bg-slate-800 border border-slate-700 rounded-2xl p-4 space-y-2 text-xs">
            <div class="font-bold text-amber-300">Active Hubs & Fleet Status</div>
            <div id="hubs-list" class="text-slate-300">Loading live data...</div>
        </div>
    </main>
    <script src="/static/samagam_app_shell.js"></script>
    <script>
        fetch('/api/operations/hubs').then(r => r.json()).then(hubs => {{
            document.getElementById('hubs-list').innerHTML = hubs.map(h =>
                `<div class="py-1 border-b border-slate-700/60 flex justify-between"><span>${{h.hub_name}}</span><span class="text-emerald-400">${{h.hub_code}}</span></div>`
            ).join('');
        }}).catch(() => {{}});
    </script>
</body>
</html>"""
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(html_stub)
    os.makedirs(os.path.join(ROOT, "root"), exist_ok=True)
    shutil.copy2(fpath, rpath)
    print("Verified field HTML:", fname)

# B. Ensure samagam_app_shell.js is attached to every field HTML page so Login/Register opens automatically
for fname in list(FIELD_APPS.keys()) + ["driver_rider_companion.html", "radar_map_console.html", "bus_onboarding_form.html"]:
    for base_dir in [ROOT, os.path.join(ROOT, "root")]:
        p = os.path.join(base_dir, fname)
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as f:
                c = f.read()
            if "samagam_app_shell.js" not in c:
                c = c.replace("</body>", '    <script src="/static/samagam_app_shell.js"></script>\n</body>')
                with open(p, "w", encoding="utf-8") as f:
                    f.write(c)

# C. Patch app/main.py _serve_html so it checks ROOT_DIR, ROOT_DIR/root, and os.getcwd()
main_py = os.path.join(ROOT, "app", "main.py")
if os.path.isfile(main_py):
    with open(main_py, "r", encoding="utf-8") as f:
        mcode = f.read()
    new_serve = '''def _serve_html(filename: str):
    for d in [ROOT_DIR, os.path.join(ROOT_DIR, "root"), os.getcwd(), os.path.join(os.getcwd(), "root")]:
        path = os.path.join(d, filename)
        if os.path.isfile(path):
            return FileResponse(path)
    return JSONResponse(status_code=404, content={"detail": f"{filename} not found in project root."})'''
    mcode, cnt = re.subn(
        r'def _serve_html\(filename: str\):.*?return \{"detail": f"\{filename\} not found in project root\."\}',
        new_serve,
        mcode,
        count=1,
        flags=re.DOTALL
    )
    if cnt > 0:
        with open(main_py, "w", encoding="utf-8") as f:
            f.write(mcode)
        print("Patched _serve_html in app/main.py")

# D. Apply proper 'जागृति — The Awakening' SVG logo and remove dark-blue '60' banner
SVG_CODE = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" width="1600" height="900">
  <defs>
    <radialGradient id="jagritiAuraGlow" cx="43%" cy="46%" r="34%" fx="43%" fy="46%">
      <stop offset="0%" stop-color="#FDE047" stop-opacity="0.72"/>
      <stop offset="42%" stop-color="#F59E0B" stop-opacity="0.52"/>
      <stop offset="72%" stop-color="#FBBF24" stop-opacity="0.18"/>
      <stop offset="100%" stop-color="#FFFFFF" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="jagritiSunDisc" cx="52%" cy="46%" r="55%">
      <stop offset="0%" stop-color="#FFFFFF"/>
      <stop offset="78%" stop-color="#FFFFFF"/>
      <stop offset="94%" stop-color="#FFFBEB"/>
      <stop offset="100%" stop-color="#FDE68A"/>
    </radialGradient>
    <linearGradient id="jagritiNavyFill" x1="15%" y1="15%" x2="85%" y2="90%">
      <stop offset="0%" stop-color="#0B3B78"/>
      <stop offset="45%" stop-color="#062856"/>
      <stop offset="100%" stop-color="#031736"/>
    </linearGradient>
    <linearGradient id="jagritiGoldEdge" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FEF08A"/>
      <stop offset="35%" stop-color="#EAB308"/>
      <stop offset="75%" stop-color="#CA8A04"/>
      <stop offset="100%" stop-color="#FDE047"/>
    </linearGradient>
    <linearGradient id="jagritiSheen" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#38BDF8" stop-opacity="0.28"/>
      <stop offset="50%" stop-color="#FFFFFF" stop-opacity="0.06"/>
      <stop offset="100%" stop-color="#021024" stop-opacity="0.35"/>
    </linearGradient>
  </defs>
  <rect x="0" y="0" width="1600" height="900" rx="48" fill="#FFFFFF"/>
  <circle cx="670" cy="410" r="355" fill="url(#jagritiAuraGlow)"/>
  <circle cx="685" cy="408" r="245" fill="url(#jagritiSunDisc)"/>
  <g id="jagriti-calligraphy-group">
    <path d="M 480 302 L 1245 302 C 1254 302, 1258 308, 1254 316 L 1222 366 C 1217 374, 1208 376, 1198 370 C 1184 361, 1166 355, 1144 352 L 526 352 C 514 352, 502 345, 492 332 Z" fill="url(#jagritiNavyFill)" stroke="url(#jagritiGoldEdge)" stroke-width="5.5" stroke-linejoin="round"/>
    <path d="M 488 307 L 1246 307 L 1218 354 L 524 354 Z" fill="url(#jagritiSheen)" opacity="0.65"/>
    <path d="M 656 352 L 656 498 C 656 544, 628 572, 582 572 C 534 572, 496 534, 472 486 C 452 448, 426 426, 396 426 C 368 426, 352 446, 354 472 C 356 494, 372 508, 392 508 C 362 518, 332 496, 330 462 C 328 424, 356 398, 396 398 C 440 398, 474 432, 502 478 C 524 514, 550 532, 578 532 C 602 532, 616 516, 616 490 L 616 446 L 534 406 L 538 398 L 616 426 L 616 352 Z" fill="url(#jagritiNavyFill)" stroke="url(#jagritiGoldEdge)" stroke-width="5.5" stroke-linejoin="round"/>
    <path d="M 702 352 L 744 352 L 744 552 L 723 576 L 702 552 Z" fill="url(#jagritiNavyFill)" stroke="url(#jagritiGoldEdge)" stroke-width="5.5" stroke-linejoin="round"/>
    <path d="M 852 352 L 894 352 L 894 532 C 918 524, 944 534, 954 556 C 966 582, 952 616, 922 628 C 892 640, 856 632, 838 608 C 826 592, 826 572, 838 558 C 844 574, 856 586, 874 592 C 898 600, 922 590, 924 570 C 926 554, 912 544, 894 548 L 894 606 L 873 624 L 852 606 L 852 468 L 764 416 L 770 406 L 852 444 Z" fill="url(#jagritiNavyFill)" stroke="url(#jagritiGoldEdge)" stroke-width="5.5" stroke-linejoin="round"/>
    <path d="M 784 434 L 840 468 L 840 538 L 784 434 Z" fill="url(#jagritiNavyFill)" stroke="url(#jagritiGoldEdge)" stroke-width="4.5" stroke-linejoin="round"/>
    <path d="M 1094 352 L 1136 352 L 1136 552 L 1115 576 L 1094 552 L 1094 456 C 1068 446, 1036 456, 1016 482 C 998 506, 996 538, 1006 566 C 980 544, 974 498, 994 462 C 1016 424, 1058 412, 1094 426 Z" fill="url(#jagritiNavyFill)" stroke="url(#jagritiGoldEdge)" stroke-width="5.5" stroke-linejoin="round"/>
    <path d="M 1115 302 C 1115 224, 1152 172, 1196 172 C 1236 172, 1262 214, 1272 284 C 1276 312, 1292 324, 1312 314 C 1296 340, 1260 338, 1244 294 C 1230 254, 1212 222, 1190 222 C 1164 222, 1146 254, 1142 302 Z" fill="url(#jagritiNavyFill)" stroke="url(#jagritiGoldEdge)" stroke-width="5.5" stroke-linejoin="round"/>
  </g>
  <text x="720" y="616" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-style="italic" font-weight="700" font-size="46" letter-spacing="1.2" fill="#082A5B" stroke="#FACC15" stroke-width="0.9" paint-order="stroke fill">The Awakening</text>
</svg>"""

for sub in ["static", os.path.join("root", "static")]:
    if sub == "static" or os.path.isdir(os.path.join(ROOT, "root")):
        os.makedirs(os.path.join(ROOT, sub), exist_ok=True)
        for fn in ["jagriti_proper_logo.svg", "samagam_79_logo.svg", "samagam_79_crest.svg"]:
            with open(os.path.join(ROOT, sub, fn), "w", encoding="utf-8") as f:
                f.write(SVG_CODE)

for wpath in [os.path.join(ROOT, "welcome.html"), os.path.join(ROOT, "root", "welcome.html")]:
    if os.path.isfile(wpath):
        with open(wpath, "r", encoding="utf-8") as f:
            html = f.read()
        html = re.sub(r'<!-- OFFICIAL (?:60TH|79) SAMAGAM LOGO.*?-->.*?</section>\s*', '', html, flags=re.DOTALL)
        html = re.sub(r'<section class="max-w-5xl mx-auto">\s*<div class="bg-\[#0b2447\].*?</section>\s*', '', html, flags=re.DOTALL)
        logo_tag = '<div class="mx-auto max-w-sm sm:max-w-md my-2"><img src="/static/jagriti_proper_logo.svg?v=2026" alt="जागृति — The Awakening" class="w-full h-auto rounded-3xl shadow-md border border-amber-200 bg-white mx-auto"></div>'
        if "jagriti-sun-glow" in html:
            html = re.sub(r'<div class="relative mx-auto w-64 h-36.*?</div>\s*</div>', logo_tag, html, count=1, flags=re.DOTALL)
        with open(wpath, "w", encoding="utf-8") as f:
            f.write(html)
        print("Updated logo in:", wpath)
'@

$tmpPy = ".\_apply_proper_logo_tmp.py"
Set-Content -Path $tmpPy -Value $pyCode -Encoding UTF8
python $tmpPy
Remove-Item $tmpPy -Force

Write-Host "`n2. Committing & Pushing ALL HTML files, Logo & app/main.py to GitHub..." -ForegroundColor Cyan
git add -f *.html root/*.html static/* app/main.py 2>$null
git add .
git commit -m "Include field web app HTML files, compulsory login shell & proper Jagriti logo" 2>$null
git push origin main

Write-Host "`n3. NOW RUN THIS IN GOOGLE CLOUD SHELL TO UPDATE LIVE CLOUD RUN:" -ForegroundColor Yellow
Write-Host "cd ~/Samagamtransport_v1 && git fetch --all && git reset --hard origin/main && gcloud run deploy samagamtransport --source . --region asia-southeast1 --platform managed --allow-unauthenticated --port 8080" -ForegroundColor Green