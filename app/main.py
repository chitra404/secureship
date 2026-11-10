from pathlib import Path

from fastapi import FastAPI, HTTPException, Path as PathParam, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.schemas import Shipment, ShipmentCreate
from app.store import AlreadyDelivered, ShipmentNotFound, ShipmentStore, StoreFull

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
CODE_PATTERN = r"^SS-[0-9A-F]{8}$"

app = FastAPI(
    title="SecureShip",
    description="A small shipment tracker used to demonstrate the SecureShip security pipeline.",
    version=__version__,
)
store = ShipmentStore()

# The interactive API docs load scripts from a CDN, so the strict CSP skips them.
DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    """Attach low-risk hardening headers to every response."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cache-Control", "no-store")
    if not request.url.path.startswith(DOCS_PATHS):
        response.headers.setdefault(
            "Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'"
        )
    return response


# ----------------------------- Frontend ------------------------------------
@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    """Serve the single-page web interface."""
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ------------------------------ Health -------------------------------------
@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Lightweight health check (used by the Docker HEALTHCHECK)."""
    return {"status": "healthy"}


@app.get("/api/v1/status", tags=["api"])
def api_status() -> dict[str, str | int]:
    """Return service status and how many shipments are stored."""
    return {
        "service": "secureship-api",
        "version": app.version,
        "status": "operational",
        "shipments": store.count(),
    }


# ----------------------------- Shipments -----------------------------------
@app.get("/api/v1/shipments", response_model=list[Shipment], tags=["shipments"])
def list_shipments() -> list[Shipment]:
    """List all shipments, newest first."""
    return store.list()


@app.post("/api/v1/shipments", response_model=Shipment, status_code=201, tags=["shipments"])
def create_shipment(data: ShipmentCreate) -> Shipment:
    """Create a new shipment with a generated tracking code."""
    try:
        return store.create(data)
    except StoreFull:
        raise HTTPException(status_code=429, detail="Shipment limit reached. Try again later.")


@app.get("/api/v1/shipments/{code}", response_model=Shipment, tags=["shipments"])
def get_shipment(code: str = PathParam(pattern=CODE_PATTERN)) -> Shipment:
    """Track one shipment by its tracking code."""
    try:
        return store.get(code)
    except ShipmentNotFound:
        raise HTTPException(status_code=404, detail="Shipment not found.")


@app.post("/api/v1/shipments/{code}/advance", response_model=Shipment, tags=["shipments"])
def advance_shipment(code: str = PathParam(pattern=CODE_PATTERN)) -> Shipment:
    """Move a shipment to its next status."""
    try:
        return store.advance(code)
    except ShipmentNotFound:
        raise HTTPException(status_code=404, detail="Shipment not found.")
    except AlreadyDelivered:
        raise HTTPException(status_code=409, detail="Shipment is already delivered.")
