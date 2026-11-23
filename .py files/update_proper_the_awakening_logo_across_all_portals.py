"""
Samagam Transport Platform — Update Proper 'जागृति — The Awakening' Logo
Writes the exact high-definition vector artwork (matching image_2303ef.png) to:
  - static/jagriti_proper_logo.svg
  - static/samagam_79_logo.svg (overwrites any old '60' badge SVG)
And updates welcome.html + sub-portals so the exact 'जागृति — The Awakening'
logo is displayed cleanly everywhere.

Run inside C:\\narendra\\SamagamtransportV1:
    python update_proper_jagriti_logo.py
"""

import os
import re
import shutil

TARGET_DIR = r"C:\narendra\SamagamtransportV1"
if not os.path.isdir(TARGET_DIR):
    TARGET_DIR = os.path.dirname(os.path.abspath(__file__))

EXACT_JAGRITI_LOGO_SVG = '''<?xml version="1.0" encoding="UTF-8"?>
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

  <!-- Soft Warm Golden Crescent Halo & White Sun Disc -->
  <circle cx="670" cy="410" r="355" fill="url(#jagritiAuraGlow)"/>
  <circle cx="685" cy="408" r="245" fill="url(#jagritiSunDisc)"/>

  <!-- Calligraphic 'जागृति' Emblem -->
  <g id="jagriti-calligraphy-group">
    <!-- Top Shirorekha Bar -->
    <path d="M 480 302
             L 1245 302
             C 1254 302, 1258 308, 1254 316
             L 1222 366
             C 1217 374, 1208 376, 1198 370
             C 1184 361, 1166 355, 1144 352
             L 526 352
             C 514 352, 502 345, 492 332
             Z"
          fill="url(#jagritiNavyFill)" stroke="url(#jagritiGoldEdge)" stroke-width="5.5" stroke-linejoin="round"/>
    <path d="M 488 307 L 1246 307 L 1218 354 L 524 354 Z" fill="url(#jagritiSheen)" opacity="0.65"/>

    <!-- Left Swirl & 'ज' (Ja) -->
    <path d="M 656 352
             L 656 498
             C 656 544, 628 572, 582 572
             C 534 572, 496 534, 472 486
             C 452 448, 426 426, 396 426
             C 368 426, 352 446, 354 472
             C 356 494, 372 508, 392 508
             C 362 518, 332 496, 330 462
             C 328 424, 356 398, 396 398
             C 440 398, 474 432, 502 478
             C 524 514, 550 532, 578 532
             C 602 532, 616 516, 616 490
             L 616 446
             L 534 406
             L 538 398
             L 616 426
             L 616 352
             Z"
          fill="url(#jagritiNavyFill)" stroke="url(#jagritiGoldEdge)" stroke-width="5.5" stroke-linejoin="round"/>

    <!-- Vertical Kana / Danda of 'जा' -->
    <path d="M 702 352
             L 744 352
             L 744 552
             L 723 576
             L 702 552
             Z"
          fill="url(#jagritiNavyFill)" stroke="url(#jagritiGoldEdge)" stroke-width="5.5" stroke-linejoin="round"/>

    <!-- Central 'गृ' (Gri) -->
    <path d="M 852 352
             L 894 352
             L 894 532
             C 918 524, 944 534, 954 556
             C 966 582, 952 616, 922 628
             C 892 640, 856 632, 838 608
             C 826 592, 826 572, 838 558
             C 844 574, 856 586, 874 592
             C 898 600, 922 590, 924 570
             C 926 554, 912 544, 894 548
             L 894 606
             L 873 624
             L 852 606
             L 852 468
             L 764 416
             L 770 406
             L 852 444
             Z"
          fill="url(#jagritiNavyFill)" stroke="url(#jagritiGoldEdge)" stroke-width="5.5" stroke-linejoin="round"/>

    <path d="M 784 434 L 840 468 L 840 538 L 784 434 Z" fill="url(#jagritiNavyFill)" stroke="url(#jagritiGoldEdge)" stroke-width="4.5" stroke-linejoin="round"/>

    <!-- Right 'ति' (Ti) -->
    <path d="M 1094 352
             L 1136 352
             L 1136 552
             L 1115 576
             L 1094 552
             L 1094 456
             C 1068 446, 1036 456, 1016 482
             C 998 506, 996 538, 1006 566
             C 980 544, 974 498, 994 462
             C 1016 424, 1058 412, 1094 426
             Z"
          fill="url(#jagritiNavyFill)" stroke="url(#jagritiGoldEdge)" stroke-width="5.5" stroke-linejoin="round"/>

    <!-- Top Sweeping Matra Arch Above 'ति' -->
    <path d="M 1115 302
             C 1115 224, 1152 172, 1196 172
             C 1236 172, 1262 214, 1272 284
             C 1276 312, 1292 324, 1312 314
             C 1296 340, 1260 338, 1244 294
             C 1230 254, 1212 222, 1190 222
             C 1164 222, 1146 254, 1142 302
             Z"
          fill="url(#jagritiNavyFill)" stroke="url(#jagritiGoldEdge)" stroke-width="5.5" stroke-linejoin="round"/>
  </g>

  <!-- Subtitle: The Awakening -->
  <text x="720" y="616"
        text-anchor="middle"
        font-family="Georgia, 'Times New Roman', serif"
        font-style="italic"
        font-weight="700"
        font-size="46"
        letter-spacing="1.2"
        fill="#082A5B"
        stroke="#FACC15"
        stroke-width="0.9"
        paint-order="stroke fill">
    The Awakening
  </text>
</svg>
'''


def write_proper_logo_svgs():
    static_dir = os.path.join(TARGET_DIR, "static")
    os.makedirs(static_dir, exist_ok=True)

    for fname in ["jagriti_proper_logo.svg", "samagam_79_logo.svg", "samagam_79_crest.svg"]:
        fpath = os.path.join(static_dir, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(EXACT_JAGRITI_LOGO_SVG)
        print(f"✅ Wrote proper logo SVG: {fpath}")


def update_welcome_html():
    welcome_path = os.path.join(TARGET_DIR, "welcome.html")
    if not os.path.isfile(welcome_path):
        print(f"⚠️ {welcome_path} not found.")
        return

    with open(welcome_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Remove any old dark-blue '60' or '79' banner section at top
    html = re.sub(
        r'<!-- OFFICIAL (?:60TH|79) SAMAGAM LOGO.*?-->.*?</section>\s*',
        "",
        html,
        flags=re.DOTALL,
    )

    # Replace text-only or sun-glow hero logo block with the crisp SVG image
    new_logo_block = '''<div class="mx-auto max-w-sm sm:max-w-md my-2">
                <img src="/static/jagriti_proper_logo.svg" alt="जागृति — The Awakening" class="w-full h-auto rounded-3xl shadow-md border border-amber-200/80 bg-white mx-auto">
            </div>'''

    if "jagriti-sun-glow" in html:
        html = re.sub(
            r'<div class="relative mx-auto w-64 h-36.*?</div>\s*</div>',
            new_logo_block,
            html,
            count=1,
            flags=re.DOTALL,
        )
    elif "samagam-hero-canvas" in html:
        html = re.sub(
            r'<section class="samagam-hero-canvas.*?</section>',
            f'''<section class="text-center max-w-3xl mx-auto space-y-3 pt-2">
            <div class="inline-block px-4 py-1 rounded-full bg-sky-100 text-[#0f2c59] text-xs font-extrabold tracking-wide">
                धन निरंकार जी 🙏 • SANT NIRANKARI MANDAL
            </div>
            {new_logo_block}
            <h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#0f2c59]">
                निरंकारी सन्त समागम — परिवहन सेवा पोर्टल
            </h1>
            <p class="text-xs sm:text-sm font-bold text-slate-600">
                60th Maharashtra Annual Nirankari Sant Samagam • Kharghar, Navi Mumbai (Central Park) • 23–26 January 2027
            </p>
            <p class="text-xs sm:text-sm text-slate-500 max-w-2xl mx-auto leading-relaxed" data-i18n="hero_desc">
                Select your transport requirement below. All vehicle requests are connected directly to the Central Transport Database so our team can allocate vehicles and update your request status live within 24 hours.
            </p>
        </section>''',
            html,
            count=1,
            flags=re.DOTALL,
        )

    with open(welcome_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Updated {welcome_path} with the exact 'जागृति — The Awakening' logo")


def sync_root_copy():
    root_sub = os.path.join(TARGET_DIR, "root")
    if os.path.isdir(root_sub):
        src = os.path.join(TARGET_DIR, "welcome.html")
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(root_sub, "welcome.html"))
        root_static = os.path.join(root_sub, "static")
        os.makedirs(root_static, exist_ok=True)
        for fname in ["jagriti_proper_logo.svg", "samagam_79_logo.svg", "samagam_79_crest.svg"]:
            s = os.path.join(TARGET_DIR, "static", fname)
            if os.path.isfile(s):
                shutil.copy2(s, os.path.join(root_static, fname))
        print("✅ Synced updated logo & welcome.html to ./root/")


if __name__ == "__main__":
    print(f"🎨 Updating proper 'जागृति — The Awakening' logo in: {TARGET_DIR}\n")
    write_proper_logo_svgs()
    update_welcome_html()
    sync_root_copy()
    print("\n🎉 Done! Run these commands to push & redeploy:")
    print("  1. git add .")
    print('  2. git commit -m "Update proper Jagriti - The Awakening logo across portals"')
    print("  3. git push origin main")
    print("  4. Deploy Cloud Run: gcloud run deploy samagamtransport --source . --region asia-southeast1 --platform managed --allow-unauthenticated --port 8080")