import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.services.seed_service import seed_initial_operations_data
from app.routers import auth, saints, fleet, operations, reports

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

_RATE_BUCKETS = defaultdict(deque)
GENERAL_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "180"))
AUTH_LIMIT_PER_MIN = int(os.environ.get("AUTH_RATE_LIMIT_PER_MIN", "25"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_initial_operations_data(db)
    finally:
        db.close()
    yield


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def ddos_rate_limit_and_security_headers(request: Request, call_next):
    path = request.url.path
    if path != "/health" and not path.startswith("/static/"):
        forwarded = request.headers.get("x-forwarded-for", "")
        client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
        is_auth_route = path.startswith("/api/auth/")
        bucket_key = f"{client_ip}:{'auth' if is_auth_route else 'gen'}"
        limit = AUTH_LIMIT_PER_MIN if is_auth_route else GENERAL_LIMIT_PER_MIN

        now = time.time()
        window = _RATE_BUCKETS[bucket_key]
        while window and window[0] < now - 60.0:
            window.popleft()

        if len(window) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests from this IP. Please wait 60 seconds before retrying."}
            )
        window.append(now)

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if path == "/" or path.endswith(".html") or path.endswith(".js"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


app.include_router(auth.router)
app.include_router(saints.router)
app.include_router(fleet.router)
app.include_router(operations.router)
app.include_router(reports.router)

static_dir = os.path.join(ROOT_DIR, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


def _serve_html(filename: str):
    path = os.path.join(ROOT_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path)
    return {"detail": f"{filename} not found in project root."}


@app.get("/")
def home(request: Request):
    host = (request.headers.get("host") or "").lower()
    if host.startswith("parking."):
        p = os.path.join(ROOT_DIR, "parking_portal.html")
        if os.path.exists(p):
            return FileResponse(p)
    if host.startswith("advancesewa."):
        a = os.path.join(ROOT_DIR, "advance_sewa_portal.html")
        if os.path.exists(a):
            return FileResponse(a)
    welcome_path = os.path.join(ROOT_DIR, "welcome.html")
    if os.path.exists(welcome_path):
        return FileResponse(welcome_path)
    return _serve_html("admin_dashboard.html")


@app.get("/sw.js")
def service_worker():
    sw_path = os.path.join(ROOT_DIR, "sw.js")
    if os.path.exists(sw_path):
        return FileResponse(sw_path, media_type="application/javascript")
    return {"status": "ok"}


@app.get("/{page_name}.html")
def serve_html_page(page_name: str):
    return _serve_html(f"{page_name}.html")


@app.get("/health")
def health():
    return {"status": "healthy", "version": settings.APP_VERSION}
