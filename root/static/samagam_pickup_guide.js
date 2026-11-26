
// Samagam Station / Airport / Bus Depot Visual Schematic Map & On-Duty Sewadar Widget
(function () {
  function renderSchematicSVG(guide) {
    return `
      <svg viewBox="0 0 560 175" class="w-full rounded-xl border border-amber-400/40 bg-slate-950 shadow-inner" xmlns="http://www.w3.org/2000/svg">
        <rect x="8" y="8" width="544" height="159" rx="12" fill="#0f172a" stroke="#334155" stroke-width="1.5"/>
        <!-- Platform / Terminal -->
        <rect x="24" y="34" width="145" height="106" rx="8" fill="#1e293b" stroke="#64748b" stroke-width="1.5"/>
        <text x="96" y="64" fill="#94a3b8" font-size="10" font-weight="bold" text-anchor="middle">ARRIVAL PLATFORM /</text>
        <text x="96" y="79" fill="#94a3b8" font-size="10" font-weight="bold" text-anchor="middle">TERMINAL GATE</text>
        <text x="96" y="108" fill="#fbbf24" font-size="11" font-weight="bold" text-anchor="middle">${guide.gate_label || "MAIN EXIT"}</text>

        <!-- Walkway Arrow -->
        <line x1="175" y1="87" x2="245" y2="87" stroke="#38bdf8" stroke-width="3" stroke-dasharray="6,4"/>
        <polygon points="245,81 258,87 245,93" fill="#38bdf8"/>
        <text x="214" y="74" fill="#38bdf8" font-size="9" font-weight="bold" text-anchor="middle">WALK 50-80m</text>

        <!-- Waiting Canopy -->
        <rect x="262" y="34" width="135" height="106" rx="8" fill="#14532d" stroke="#22c55e" stroke-width="2"/>
        <text x="329" y="62" fill="#bbf7d0" font-size="10" font-weight="bold" text-anchor="middle">GROUP WAITING POINT</text>
        <text x="329" y="82" fill="#ffffff" font-size="11" font-weight="bold" text-anchor="middle">SAMAGAM HELPDESK</text>
        <text x="329" y="102" fill="#86efac" font-size="9.5" text-anchor="middle">Sewadars On-Duty Here</text>
        <circle cx="329" cy="121" r="7" fill="#22c55e"/>

        <!-- Bus Boarding Bay -->
        <line x1="402" y1="87" x2="424" y2="87" stroke="#fbbf24" stroke-width="3"/>
        <rect x="426" y="34" width="112" height="106" rx="8" fill="#78350f" stroke="#f59e0b" stroke-width="2"/>
        <text x="482" y="64" fill="#fde68a" font-size="10" font-weight="bold" text-anchor="middle">SHUTTLE BOARDING</text>
        <text x="482" y="86" fill="#ffffff" font-size="11" font-weight="bold" text-anchor="middle">${guide.bay_label || "BUS BAY 1"}</text>
        <text x="482" y="108" fill="#fcd34d" font-size="9" text-anchor="middle">To Samagam Ground</text>
      </svg>`;
  }

  window.loadSamagamPickupGuide = async function (locationName, containerId) {
    const box = document.getElementById(containerId || "samagam-pickup-guide-box");
    if (!box || !locationName) return;
    box.innerHTML = `<div class="p-3 text-xs text-amber-300">Loading schematic pickup map & on-duty Sewadars for ${locationName}...</div>`;
    try {
      const res = await fetch(`/api/operations/pickup-guide?location=${encodeURIComponent(locationName)}`);
      const data = await res.json();
      const g = data.guide || {};
      const sewadars = data.on_duty_sewadars || [];
      const sewHtml = sewadars.map(s => `
        <div class="flex items-center justify-between bg-slate-900/90 border border-slate-700 rounded-lg px-3 py-2 text-xs">
          <div>
            <div class="font-bold text-white">${s.sewadar_name} <span class="text-amber-300">(${s.unit_no || "Station Unit"})</span></div>
            <div class="text-slate-400">${s.duty_role || "Station Guide"} ? ${s.shift_timing || "On-Duty"}</div>
          </div>
          <div class="flex gap-1.5">
            <a href="tel:${s.primary_mobile}" class="px-2.5 py-1 rounded bg-emerald-600 text-white font-bold">Call ${s.primary_mobile}</a>
            ${s.alt_mobile ? `<a href="tel:${s.alt_mobile}" class="px-2 py-1 rounded bg-slate-700 text-slate-200">Alt</a>` : ""}
          </div>
        </div>
      `).join("");

      box.innerHTML = `
        <div class="rounded-2xl border border-amber-500/40 bg-slate-900/95 p-4 space-y-3 text-slate-100">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="text-sm font-extrabold text-amber-300">${g.title || locationName}</div>
            <span class="text-[11px] px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">Helpline: 18001232005 | Bot: 9266629848</span>
          </div>
          ${renderSchematicSVG(g)}
          <div class="bg-amber-950/40 border border-amber-500/30 rounded-xl p-3 text-xs space-y-1">
            <div class="font-bold text-amber-200">Exact Waiting Point:</div>
            <div class="text-slate-200">${g.waiting_point || ""}</div>
            <div class="text-slate-400">Landmark: ${g.landmark || ""}</div>
          </div>
          <div class="space-y-1.5">
            <div class="text-xs font-bold text-emerald-300">Station Sewadars Currently On Duty Here:</div>
            ${sewHtml}
          </div>
        </div>
      `;
    } catch (e) {
      box.innerHTML = `<div class="text-xs text-rose-400 p-2">Could not load pickup guide: ${e}</div>`;
    }
  };
})();
