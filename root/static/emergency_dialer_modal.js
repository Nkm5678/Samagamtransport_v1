/**
 * Floating 1-Click SOS Helpline, MSRTC Depot & Traffic Control Dialer
 */
(function injectEmergencySOS() {
  const contacts = [
    { label: 'Central Transport Control Room', phone: '+919820000101', tag: '24x7 HQ' },
    { label: 'MSRTC Thane Divisional Controller', phone: '+912225332361', tag: 'State Bus' },
    { label: 'Mumbai Traffic Police Helpline', phone: '103', tag: 'Traffic SOS' },
    { label: 'Medical & Ambulance Desk (Ground 1)', phone: '+919820000108', tag: 'Medical' }
  ];

  const btn = document.createElement('button');
  btn.innerHTML = '🚨 SOS';
  btn.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;background:#dc2626;color:#fff;font-weight:800;padding:12px 16px;border-radius:9999px;box-shadow:0 10px 25px rgba(220,38,38,0.45);border:2px solid #fecaca;cursor:pointer;font-size:13px;';
  
  const modal = document.createElement('div');
  modal.style.cssText = 'display:none;position:fixed;inset:0;background:rgba(15,23,42,0.75);z-index:10000;align-items:center;justify-content:center;padding:16px;';
  modal.innerHTML = `
    <div style="background:#fff;color:#0f172a;max-width:400px;width:100%;border-radius:16px;padding:20px;box-shadow:0 20px 40px rgba(0,0,0,0.3);">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h3 style="margin:0;font-size:16px;font-weight:800;color:#b91c1c;">🚨 Emergency & MSRTC Rapid Dialer</h3>
        <button id="close-sos-btn" style="background:none;border:none;font-size:18px;font-weight:bold;cursor:pointer;">✕</button>
      </div>
      <div style="display:flex;flex-direction:column;gap:10px;">
        ${contacts.map(c => `
          <a href="tel:${c.phone}" style="display:flex;justify-content:space-between;align-items:center;padding:12px;border:1px solid #e2e8f0;border-radius:10px;text-decoration:none;color:#0f172a;background:#f8fafc;">
            <div>
              <div style="font-weight:700;font-size:13px;">${c.label}</div>
              <div style="font-size:11px;color:#64748b;">${c.phone}</div>
            </div>
            <span style="background:#dc2626;color:#fff;font-size:11px;font-weight:700;padding:6px 10px;border-radius:8px;">📞 Call</span>
          </a>
        `).join('')}
      </div>
    </div>
  `;

  document.body.appendChild(btn);
  document.body.appendChild(modal);

  btn.onclick = () => { modal.style.display = 'flex'; };
  modal.querySelector('#close-sos-btn').onclick = () => { modal.style.display = 'none'; };
})();