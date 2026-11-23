"""
Samagam Transport Platform — End-to-End Operations Pipeline & Sequence Engine
Implements the strict chronological sequence of activities across all 6 teams:
  STAGE 1: REQUEST / ARRIVAL INTAKE
    - Devotee Pickup/Drop, Advance Sewa, or Dept. Requisition raises a Demand
    - OR Bus arrives at Gate/Station -> First-Time Onboarding + 24h Clock / MSRTC Cash
  STAGE 2: CONTROL ROOM & GROUND ALLOCATION
    - Optimal Bus Mix calculated (50-seat / 35-seat / 20-seat)
    - Bus + Driver assigned -> Vehicle moves from EMPTY_IN -> ASSIGNED_DISPATCH
  STAGE 3: STATION BOARDING & IN-TRANSIT GPS (180s)
    - Station Team loads pilgrims -> Driver taps START TRIP (LOADED_OUT)
    - Live 180-second GPS telemetry streams to Radar Map
  STAGE 4: VENUE GATE INWARD UNLOAD & AUDIT
    - Gate Keeper logs UNLOADED_IN -> Pilgrims checked in at Ground/Tent
    - MSRTC Spot Cash ETM voucher verified at Gate
  STAGE 5: TURNAROUND, FUEL & SAFETY CHECK
    - Diesel Team logs fuel slip & pre-trip tire/brake health check
    - Vehicle either returns EMPTY_OUT for next shuttle loop OR exits Gate
  STAGE 6: OUTWARD GATE EXIT & ACCOUNTS SETTLEMENT
    - 24-Hour Hired Bus exit odometer logged -> Auto-calculates 300km/day quota & bill
    - Accounts Team closes & settles voucher

Run inside C:\\narendra\\SamagamtransportV1:
    python install_operations_pipeline.py
"""

import os
import re

TARGET_DIR = r"C:\narendra\SamagamtransportV1"
if not os.path.isdir(TARGET_DIR):
    TARGET_DIR = os.path.dirname(os.path.abspath(__file__))

PIPELINE_API_CODE = r'''

# ==============================================================================
# END-TO-END OPERATIONS PIPELINE & CHRONOLOGICAL SEQUENCE ENGINE
# ==============================================================================

SEQUENCE_STAGES = [
    {
        "step": 1,
        "key": "INTAKE_DEMAND",
        "title": "1. Request & Demand Intake",
        "owner_team": "Devotee / Station / Dept",
        "description": "Pickup/Drop, Advance Sewa, or Station Crowd Demand logged into Central Queue."
    },
    {
        "step": 2,
        "key": "DISPATCH_ASSIGNED",
        "title": "2. Fleet Allocation & Dispatch",
        "owner_team": "Control Room / Ground Team",
        "description": "Bus & Driver assigned; vehicle dispatched empty or staged for boarding."
    },
    {
        "step": 3,
        "key": "IN_TRANSIT_LOADED",
        "title": "3. Boarding & Live GPS Transit",
        "owner_team": "Station Team & Driver App",
        "description": "Pilgrims boarded; Driver started trip with 180s live GPS telemetry."
    },
    {
        "step": 4,
        "key": "GATE_UNLOADED_VERIFIED",
        "title": "4. Venue Gate Unload & Audit",
        "owner_team": "Gate Keeper & Ground Team",
        "description": "Bus arrived at Samagam Gate, pilgrims unloaded, MSRTC ETM voucher verified."
    },
    {
        "step": 5,
        "key": "TURNAROUND_FUEL_SAFETY",
        "title": "5. Fuel, Safety & Loop Return",
        "owner_team": "Diesel & Workshop Marshall",
        "description": "Pre-trip tire/brake check & diesel refill before next shuttle loop."
    },
    {
        "step": 6,
        "key": "EXIT_AND_SETTLEMENT",
        "title": "6. Outward Exit & Accounts Billing",
        "owner_team": "Gate Keeper & Accounts Cell",
        "description": "24h Rolling Contract exit odometer logged & final bill settled."
    }
]


@router.get("/pipeline/live-board")
def get_live_operations_pipeline(db: Session = Depends(get_db)):
    """Returns the complete 6-stage chronological sequence with live counts, items & next-action triggers."""
    from app.models import (
        PickupDropVehicleRequest, AdvanceSewaVehicleRequest,
        DepartmentVehicleRequisition, MSRTCSpotCashVoucher,
        HiredRollingContract
    )

    pending_demands = db.query(StationDemand).filter(StationDemand.status == "PENDING").order_by(StationDemand.id.desc()).all()
    pending_adv = db.query(AdvanceSewaVehicleRequest).filter(AdvanceSewaVehicleRequest.status == "PENDING_ALLOCATION").all()
    pending_dept = db.query(DepartmentVehicleRequisition).filter(DepartmentVehicleRequisition.status == "PENDING_ALLOCATION").all()

    vehicles = db.query(Vehicle).order_by(Vehicle.last_updated.desc()).all()
    stage2_ready = [v for v in vehicles if v.status == "EMPTY_IN" and not v.is_maintenance_flagged]
    stage3_transit = [v for v in vehicles if v.status in ("LOADED_OUT", "EMPTY_OUT")]
    stage4_unloaded = [v for v in vehicles if v.status == "UNLOADED_IN"]
    stage5_maint = [v for v in vehicles if v.is_maintenance_flagged or v.status == "MAINTENANCE_HOLD"]

    unverified_msrtc = db.query(MSRTCSpotCashVoucher).filter(MSRTCSpotCashVoucher.is_verified_at_gate == False).all()
    active_contracts = db.query(HiredRollingContract).filter(HiredRollingContract.status == "ACTIVE_ROLLING").all()
    settled_contracts = db.query(HiredRollingContract).filter(HiredRollingContract.status == "SETTLED_AND_EXITED").order_by(HiredRollingContract.id.desc()).limit(10).all()

    return {
        "sequence_definition": SEQUENCE_STAGES,
        "stages": {
            "stage_1_intake": {
                "count": len(pending_demands) + len(pending_adv) + len(pending_dept),
                "demands": [
                    {
                        "id": d.id,
                        "code": d.demand_code,
                        "hub": d.hub_name,
                        "pax": d.waiting_passenger_count,
                        "mix": d.recommended_buses,
                        "requested_by": d.requested_by,
                        "notes": d.notes or ""
                    }
                    for d in pending_demands
                ],
                "advance_sewa": [
                    {
                        "id": a.id,
                        "code": a.request_code,
                        "name": a.requester_name,
                        "phone": a.contact_number,
                        "branch": f"{a.branch_name} (Unit {a.unit_number})",
                        "station": a.nearest_railway_station,
                        "schedule": f"{a.date_of_sewa} {a.start_journey_time}-{a.return_time}",
                        "pax": a.passenger_count
                    }
                    for a in pending_adv
                ]
            },
            "stage_2_ready_fleet": {
                "count": len(stage2_ready),
                "vehicles": [
                    {
                        "id": v.id,
                        "reg": v.vehicle_reg_number,
                        "type": v.vehicle_type,
                        "capacity": v.capacity,
                        "hub": v.current_hub,
                        "driver": f"{v.driver_name} ({v.driver_phone})",
                        "ownership": v.ownership_type
                    }
                    for v in stage2_ready
                ]
            },
            "stage_3_in_transit": {
                "count": len(stage3_transit),
                "vehicles": [
                    {
                        "id": v.id,
                        "reg": v.vehicle_reg_number,
                        "status": v.status,
                        "hub": v.current_hub,
                        "destination": v.current_destination or "Samagam Ground",
                        "pax": v.current_passengers,
                        "capacity": v.capacity,
                        "speed_kmh": v.current_speed_kmh,
                        "driver": f"{v.driver_name} ({v.driver_phone})"
                    }
                    for v in stage3_transit
                ]
            },
            "stage_4_gate_unload_audit": {
                "count": len(stage4_unloaded) + len(unverified_msrtc),
                "unloaded_vehicles": [
                    {
                        "id": v.id,
                        "reg": v.vehicle_reg_number,
                        "hub": v.current_hub,
                        "driver": v.driver_name,
                        "ownership": v.ownership_type
                    }
                    for v in stage4_unloaded
                ],
                "pending_msrtc_gate_checks": [
                    {
                        "id": m.id,
                        "voucher": m.voucher_number,
                        "station": m.station_hub,
                        "etm": m.etm_receipt_number,
                        "amount": m.cash_amount_paid_inr,
                        "pax": m.passenger_headcount
                    }
                    for m in unverified_msrtc
                ]
            },
            "stage_5_fuel_and_safety": {
                "count": len(stage5_maint),
                "maintenance_holds": [
                    {
                        "id": v.id,
                        "reg": v.vehicle_reg_number,
                        "health": v.health_score_pct,
                        "reason": v.maintenance_reason or "Workshop Hold"
                    }
                    for v in stage5_maint
                ]
            },
            "stage_6_contracts_settlement": {
                "active_rolling_count": len(active_contracts),
                "settled_count": len(settled_contracts),
                "active_contracts": [
                    {
                        "id": c.id,
                        "code": c.contract_code,
                        "reg": c.vehicle.vehicle_reg_number if c.vehicle else "",
                        "vendor": c.vendor_agency_name,
                        "entry_odo": c.entry_odometer_km
                    }
                    for c in active_contracts
                ]
            }
        }
    }


@router.post("/pipeline/advance-step")
def advance_vehicle_sequence_step(data: dict, db: Session = Depends(get_db)):
    """Moves a vehicle or demand cleanly to the next valid step in the 6-stage sequence."""
    action = str(data.get("action") or "").upper().strip()
    vehicle_id = data.get("vehicle_id")
    demand_id = data.get("demand_id")
    actor = str(data.get("actor_name") or "Operations Controller").strip()
    destination = str(data.get("destination_hub") or "Ground 1 (Main Hall)").strip()
    pax = int(data.get("passenger_count") or 0)

    veh = db.query(Vehicle).filter(Vehicle.id == int(vehicle_id)).first() if vehicle_id else None

    if action == "ASSIGN_AND_DISPATCH":
        if not veh:
            raise HTTPException(status_code=400, detail="Select an available bus to dispatch.")
        if veh.is_maintenance_flagged:
            raise HTTPException(status_code=409, detail=f"Blocked: {veh.vehicle_reg_number} is on Maintenance Hold.")
        if demand_id:
            dem = db.query(StationDemand).filter(StationDemand.id == int(demand_id)).first()
            if dem:
                dem.status = "DISPATCHED"
                pax = pax or dem.waiting_passenger_count
                from app.models import PickupDropVehicleRequest, AdvanceSewaVehicleRequest
                pd = db.query(PickupDropVehicleRequest).filter(PickupDropVehicleRequest.request_code == dem.demand_code).first()
                if pd:
                    pd.status = "DISPATCHED"
                    pd.assigned_vehicle_reg = veh.vehicle_reg_number
                adv = db.query(AdvanceSewaVehicleRequest).filter(AdvanceSewaVehicleRequest.request_code == dem.demand_code).first()
                if adv:
                    adv.status = "ALLOCATED"
                    adv.assigned_vehicle_reg = veh.vehicle_reg_number
                    adv.assigned_driver_name = veh.driver_name
                    adv.assigned_driver_phone = veh.driver_phone
        record_turnaround_movement(db, veh, "LOADED_OUT", veh.current_hub, actor, min(pax or veh.capacity, veh.capacity), destination)
        db.commit()
        return {"status": "MOVED_TO_STAGE_3_TRANSIT", "vehicle": veh.vehicle_reg_number, "next_step": "Arrival & Unload at Venue Gate"}

    if action == "GATE_ARRIVE_UNLOAD":
        if not veh:
            raise HTTPException(status_code=404, detail="Vehicle not found.")
        record_turnaround_movement(db, veh, "UNLOADED_IN", destination, actor, 0, None)
        db.commit()
        return {"status": "MOVED_TO_STAGE_4_UNLOADED", "vehicle": veh.vehicle_reg_number, "next_step": "Fuel/Safety Check or Return Loop"}

    if action == "RELEASE_EMPTY_LOOP":
        if not veh:
            raise HTTPException(status_code=404, detail="Vehicle not found.")
        if veh.is_maintenance_flagged:
            raise HTTPException(status_code=409, detail="Cannot release bus on Maintenance Hold.")
        record_turnaround_movement(db, veh, "EMPTY_OUT", veh.current_hub, actor, 0, destination)
        db.commit()
        return {"status": "MOVED_TO_STAGE_5_RETURN_LOOP", "vehicle": veh.vehicle_reg_number, "next_step": "Arrive Empty at Station Staging"}

    if action == "MARK_READY_AT_HUB":
        if not veh:
            raise HTTPException(status_code=404, detail="Vehicle not found.")
        record_turnaround_movement(db, veh, "EMPTY_IN", destination, actor, 0, None)
        db.commit()
        return {"status": "MOVED_TO_STAGE_2_READY", "vehicle": veh.vehicle_reg_number, "next_step": "Assign Next Pilgrim Demand"}

    raise HTTPException(status_code=400, detail=f"Unsupported pipeline action: {action}")
'''

PIPELINE_WIDGET_JS = r'''/**
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
'''


def install_pipeline_backend():
    ops_path = os.path.join(TARGET_DIR, "app", "routers", "operations.py")
    if not os.path.isfile(ops_path):
        print(f"Warning: {ops_path} not found.")
        return
    with open(ops_path, "r", encoding="utf-8") as f:
        code = f.read()

    if "/pipeline/live-board" not in code:
        code = code + "\n" + PIPELINE_API_CODE
        with open(ops_path, "w", encoding="utf-8") as f:
            f.write(code)
        print("Added 6-Stage Operations Pipeline API to app/routers/operations.py")
    else:
        print("Pipeline API already present in app/routers/operations.py")


def install_pipeline_frontend():
    static_dir = os.path.join(TARGET_DIR, "static")
    os.makedirs(static_dir, exist_ok=True)
    widget_path = os.path.join(static_dir, "operations_pipeline_board.js")
    with open(widget_path, "w", encoding="utf-8") as f:
        f.write(PIPELINE_WIDGET_JS)
    print(f"Wrote interactive 6-stage pipeline board script: {widget_path}")

    targets = [
        ("admin_dashboard.html", "Control Room HQ"),
        ("ground_team_app.html", "Ground Team"),
        ("station_team_app.html", "Station Team"),
    ]
    for fname, actor in targets:
        for base in [TARGET_DIR, os.path.join(TARGET_DIR, "root")]:
            fpath = os.path.join(base, fname)
            if not os.path.isfile(fpath):
                continue
            with open(fpath, "r", encoding="utf-8") as f:
                html = f.read()
            if "operations_pipeline_board.js" not in html:
                mount_div = '<section id="samagam-live-pipeline-board" class="max-w-6xl mx-auto px-4 pt-4"></section>\n'
                html = re.sub(r'(<main[^>]*>)', r'\1\n' + mount_div, html, count=1)
                boot_script = (
                    '    <script src="/static/operations_pipeline_board.js"></script>\n'
                    f'    <script>window.addEventListener("DOMContentLoaded", () => renderOperationsPipelineWidget("samagam-live-pipeline-board", "{actor}"));</script>\n'
                )
                html = html.replace("</body>", boot_script + "</body>")
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(html)
                print(f"Embedded Live 6-Stage Pipeline Board into: {fpath}")


if __name__ == "__main__":
    print(f"Installing End-to-End Samagam Operations Pipeline & Sequence Engine in: {TARGET_DIR}\n")
    install_pipeline_backend()
    install_pipeline_frontend()
    print("\nPipeline & Sequence of Activities logic installed!")
    print("Next steps:")
    print("  1. git add .")
    print('  2. git commit -m "Add 6-stage chronological operations pipeline and sequence board"')
    print("  3. git push origin main")
    print("  4. Deploy Cloud Run: gcloud run deploy samagamtransport --source . --region asia-southeast1 --platform managed --allow-unauthenticated --port 8080")