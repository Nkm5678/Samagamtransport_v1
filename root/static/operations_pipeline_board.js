/**
 * Samagam Transport — Interactive 6-Stage Operations Pipeline & Sequence Board
 * Renders the chronological workflow across Control Room, Ground Team & Station Team:
 *   1. Request Intake -> 2. Ready Fleet -> 3. In-Transit GPS -> 4. Gate Unload -> 5. Fuel/Safety -> 6. Exit & Accounts
 */
(function initOperationsPipelineBoard() {
    window.renderOperationsPipelineWidget = async function (containerId, actorLabel = "Operations Controller") {
        const hostEl = document.getElementById(containerId);
        if (!hostEl) return;

        hostEl.innerHTML = `<div class="p-4 rounded-2xl bg-slate-900 border border-slate-700 text-xs text-slate-300">Loading 6-Stage Operations Pipeline...</div>`;

        try {
            const res = await fetch("/api/operations/pipeline/live-board");
            if (!res.ok) throw new Error("Pipeline endpoint unavailable");
            const data = await res.json();
            const st = data.stages;
            const readyBuses = st.stage_2_ready_fleet.vehicles || [];

            const busOptionsHtml = readyBuses.length
                ? readyBuses.map(b => `<option value="${b.id}">${b.reg} (${b.capacity}s • ${b.hub})</option>`).join("")
                : `<option value="">No Empty Bus Ready</option>`;

            hostEl.innerHTML = `
                <div class="bg-slate-900/95 border border-slate-700 rounded-3xl p-4 sm:p-5 space-y-4 shadow-xl text-xs text-slate-100">
                    <div class="flex flex-wrap justify-between items-center gap-2 border-b border-slate-800 pb-3">
                        <div>
                            <span class="text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                                Chronological Activity Sequence
                            </span>
                            <h3 class="text-sm sm:text-base font-extrabold text-white mt-1">🔄 Live 6-Stage Transport Pipeline</h3>
                        </div>
                        <button onclick="renderOperationsPipelineWidget('${containerId}', '${actorLabel}')" class="bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-xl font-bold text-emerald-300 border border-slate-700">
                            ↻ Sync Sequence
                        </button>
                    </div>

                    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
                        <div class="p-2.5 rounded-xl bg-amber-950/60 border border-amber-600/50">
                            <div class="text-[10px] font-bold text-amber-300">STEP 1 • INTAKE</div>
                            <div class="text-lg font-black text-white">${st.stage_1_intake.count}</div>
                            <div class="text-[10px] text-amber-200/80">Pending Requests</div>
                        </div>
                        <div class="p-2.5 rounded-xl bg-emerald-950/60 border border-emerald-600/50">
                            <div class="text-[10px] font-bold text-emerald-300">STEP 2 • STAGED</div>
                            <div class="text-lg font-black text-white">${st.stage_2_ready_fleet.count}</div>
                            <div class="text-[10px] text-emerald-200/80">Ready Buses</div>
                        </div>
                        <div class="p-2.5 rounded-xl bg-blue-950/60 border border-blue-600/50">
                            <div class="text-[10px] font-bold text-blue-300">STEP 3 • TRANSIT</div>
                            <div class="text-lg font-black text-white">${st.stage_3_in_transit.count}</div>
                            <div class="text-[10px] text-blue-200/80">Live GPS Moving</div>
                        </div>
                        <div class="p-2.5 rounded-xl bg-teal-950/60 border border-teal-600/50">
                            <div class="text-[10px] font-bold text-teal-300">STEP 4 • UNLOAD</div>
                            <div class="text-lg font-black text-white">${st.stage_4_gate_unload_audit.count}</div>
                            <div class="text-[10px] text-teal-200/80">At Gate / MSRTC</div>
                        </div>
                        <div class="p-2.5 rounded-xl bg-rose-950/60 border border-rose-600/50">
                            <div class="text-[10px] font-bold text-rose-300">STEP 5 • SAFETY</div>
                            <div class="text-lg font-black text-white">${st.stage_5_fuel_and_safety.count}</div>
                            <div class="text-[10px] text-rose-200/80">Maint / Fuel Hold</div>
                        </div>
                        <div class="p-2.5 rounded-xl bg-purple-950/60 border border-purple-600/50">
                            <div class="text-[10px] font-bold text-purple-300">STEP 6 • BILLING</div>
                            <div class="text-lg font-black text-white">${st.stage_6_contracts_settlement.active_rolling_count}</div>
                            <div class="text-[10px] text-purple-200/80">Active 24h Contracts</div>
                        </div>
                    </div>

                    <div class="grid grid-cols-1 lg:grid-cols-3 gap-3">
                        <div class="bg-slate-950/90 border border-slate-800 rounded-2xl p-3 space-y-2">
                            <div class="font-extrabold text-amber-300">1 → 2. Pending Demands (Assign & Dispatch)</div>
                            ${st.stage_1_intake.demands.length ? st.stage_1_intake.demands.map(d => `
                                <div class="p-2.5 rounded-xl bg-slate-900 border border-slate-800 space-y-1.5">
                                    <div class="flex justify-between font-bold">
                                        <span class="text-white">${d.code} • ${d.hub}</span>
                                        <span class="text-amber-300">${d.pax} Pax</span>
                                    </div>
                                    <div class="text-[11px] text-slate-400">Mix: ${d.mix || "1x Bus"}</div>
                                    <div class="flex gap-1.5 pt-1">
                                        <select id="pipe-bus-${d.id}" class="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-2 py-1 text-[11px] text-white font-bold">
                                            ${busOptionsHtml}
                                        </select>
                                        <button onclick="triggerPipelineStep('ASSIGN_AND_DISPATCH', document.getElementById('pipe-bus-${d.id}').value, ${d.id}, 'Ground 1 (Main Hall)', ${d.pax}, '${containerId}', '${actorLabel}')" class="bg-emerald-600 hover:bg-emerald-500 text-white font-extrabold px-2.5 py-1 rounded-lg text-[11px]">
                                            Dispatch →
                                        </button>
                                    </div>
                                </div>
                            `).join("") : `<div class="text-slate-500 py-2">All demands dispatched!</div>`}
                        </div>

                        <div class="bg-slate-950/90 border border-slate-800 rounded-2xl p-3 space-y-2">
                            <div class="font-extrabold text-blue-300">3 → 4. Active Transit (Confirm Gate Arrival)</div>
                            ${st.stage_3_in_transit.vehicles.length ? st.stage_3_in_transit.vehicles.map(v => `
                                <div class="p-2.5 rounded-xl bg-slate-900 border border-slate-800 space-y-1.5">
                                    <div class="flex justify-between font-bold">
                                        <span class="text-white">${v.reg}</span>
                                        <span class="text-blue-300">${v.status} (${v.pax}/${v.capacity})</span>
                                    </div>
                                    <div class="text-[11px] text-slate-400">${v.hub} → ${v.destination}</div>
                                    <button onclick="triggerPipelineStep('${v.status === "EMPTY_OUT" ? "MARK_READY_AT_HUB" : "GATE_ARRIVE_UNLOAD"}', ${v.id}, null, '${v.destination}', 0, '${containerId}', '${actorLabel}')" class="w-full bg-teal-600 hover:bg-teal-500 text-white font-extrabold py-1.5 rounded-lg text-[11px]">
                                        ${v.status === "EMPTY_OUT" ? "✓ Arrived Empty at Station (Ready)" : "⬇ Confirm Gate Unload (Step 4)"}
                                    </button>
                                </div>
                            `).join("") : `<div class="text-slate-500 py-2">No buses currently in transit.</div>`}
                        </div>

                        <div class="bg-slate-950/90 border border-slate-800 rounded-2xl p-3 space-y-2">
                            <div class="font-extrabold text-teal-300">4 → 5. Unloaded at Gate (Return Loop)</div>
                            ${st.stage_4_gate_unload_audit.unloaded_vehicles.length ? st.stage_4_gate_unload_audit.unloaded_vehicles.map(v => `
                                <div class="p-2.5 rounded-xl bg-slate-900 border border-slate-800 space-y-1.5">
                                    <div class="flex justify-between font-bold">
                                        <span class="text-white">${v.reg}</span>
                                        <span class="text-emerald-400">UNLOADED_IN</span>
                                    </div>
                                    <div class="text-[11px] text-slate-400">At: ${v.hub} • Driver: ${v.driver}</div>
                                    <button onclick="triggerPipelineStep('RELEASE_EMPTY_LOOP', ${v.id}, null, 'Thane Railway Station', 0, '${containerId}', '${actorLabel}')" class="w-full bg-amber-600 hover:bg-amber-500 text-slate-950 font-extrabold py-1.5 rounded-lg text-[11px]">
                                        ↻ Release Empty for Next Loop
                                    </button>
                                </div>
                            `).join("") : `<div class="text-slate-500 py-2">No unloaded buses waiting at gate.</div>`}
                        </div>
                    </div>
                </div>
            `;
        } catch (err) {
            hostEl.innerHTML = `<div class="p-3 rounded-xl bg-rose-950 text-rose-200 text-xs">Could not load sequence pipeline: ${err.message}</div>`;
        }
    };

    window.triggerPipelineStep = async function (action, vehicleId, demandId, destHub, pax, containerId, actorLabel) {
        if (!vehicleId) {
            alert("Please select an available vehicle first.");
            return;
        }
        const res = await fetch("/api/operations/pipeline/advance-step", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                action,
                vehicle_id: parseInt(vehicleId),
                demand_id: demandId ? parseInt(demandId) : null,
                destination_hub: destHub,
                passenger_count: pax,
                actor_name: actorLabel
            })
        });
        const data = await res.json();
        if (res.ok) {
            renderOperationsPipelineWidget(containerId, actorLabel);
            if (typeof loadAdminSummary === "function") loadAdminSummary();
        } else {
            alert(data.detail || "Unable to advance sequence step.");
        }
    };
})();
