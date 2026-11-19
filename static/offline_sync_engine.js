/**
 * Samagam Offline Resiliency & IndexedDB Sync Engine
 * Queues station demands, check-ins, and GPS pings when network drops.
 */
const DB_NAME = 'SamagamOfflineQueueDB';
const STORE_NAME = 'pending_requests';

function openQueueDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'idempotency_key' });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function enqueueOfflineAction(endpoint, payload, meta = {}) {
  const db = await openQueueDB();
  const tx = db.transaction(STORE_NAME, 'readwrite');
  const item = {
    idempotency_key: 'OFF-' + Date.now() + '-' + Math.random().toString(36).substring(2, 8),
    endpoint,
    method: 'POST',
    payload,
    client_timestamp: new Date().toISOString(),
    volunteer_name: meta.volunteer_name || 'Field Sevadar',
    station_hub: meta.station_hub || null
  };
  tx.objectStore(STORE_NAME).put(item);
  return item.idempotency_key;
}

async function flushOfflineQueue() {
  if (!navigator.onLine) return;
  const db = await openQueueDB();
  const tx = db.transaction(STORE_NAME, 'readonly');
  const allReq = tx.objectStore(STORE_NAME).getAll();

  allReq.onsuccess = async () => {
    const items = allReq.result;
    if (!items || items.length === 0) return;

    try {
      const res = await fetch('/api/operations/offline-sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items })
      });
      if (res.ok) {
        const clearTx = db.transaction(STORE_NAME, 'readwrite');
        clearTx.objectStore(STORE_NAME).clear();
        console.log(`✅ Synced ${items.length} offline queued records.`);
      }
    } catch (err) {
      console.warn('⏳ Offline sync deferred until connection stabilizes.');
    }
  };
}

window.addEventListener('online', flushOfflineQueue);
setInterval(flushOfflineQueue, 30000);