import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.admin import router as admin_router
from backend.app.api.analytics import router as analytics_router
from backend.app.api.auth import router as auth_router
from backend.app.api.endpoints import router as ops_router
from backend.app.config.config import settings
from backend.app.database.postgres import check_database_connection, create_tables
from backend.app.database.seed_tarot import seed_tarot_cards

_log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(level=_log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("aetheria")
telemetry = {
    "requests": 0,
    "errors": 0,
    "client_errors": 0,
    "latency_total_ms": 0.0,
    "started_at": time.time(),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ENVIRONMENT.lower() == "production" and (not settings.JWT_SECRET or len(settings.JWT_SECRET) < 32):
        raise RuntimeError("JWT_SECRET must be configured in production.")
    os.makedirs("static/palm_images", exist_ok=True)
    create_tables()
    seed_tarot_cards()
    logger.info("Aetheria backend started in %s environment", settings.ENVIRONMENT)
    yield
    logger.info("Aetheria backend stopped")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-assisted Palmistry and Tarot intelligence platform for symbolic self-reflection.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"], allow_headers=["Authorization", "Content-Type"])


@app.middleware("http")
async def request_telemetry(request: Request, call_next):
    start = time.perf_counter()
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    try:
        response = await call_next(request)
    except Exception:
        elapsed = (time.perf_counter() - start) * 1000
        telemetry["errors"] += 1
        telemetry["requests"] += 1
        telemetry["latency_total_ms"] += elapsed
        logger.exception(
            "request_failed request_id=%s method=%s path=%s status=500 latency_ms=%.2f",
            request_id, request.method, request.url.path, elapsed,
        )
        response = JSONResponse({"detail": "Internal server error"}, status_code=500)
    else:
        elapsed = (time.perf_counter() - start) * 1000
        telemetry["requests"] += 1
        telemetry["latency_total_ms"] += elapsed
        if response.status_code >= 500:
            telemetry["errors"] += 1
        elif response.status_code >= 400:
            telemetry["client_errors"] += 1
        logger.info(
            "request_completed request_id=%s method=%s path=%s status=%s latency_ms=%.2f",
            request_id, request.method, request.url.path, response.status_code, elapsed,
        )

    response.headers["X-Process-Time-Ms"] = f"{elapsed:.2f}"
    response.headers["X-Request-ID"] = request_id
    return response


app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(ops_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health"])
def read_root():
    return {"status": "ok", "platform": settings.PROJECT_NAME, "version": app.version}


@app.get("/health/live", tags=["Health"])
def health_live():
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
def health_ready():
    if not check_database_connection():
        return JSONResponse({"status": "not_ready", "database": "unavailable"}, status_code=503)
    return {"status": "ready", "database": "ok"}


@app.get("/metrics", response_class=PlainTextResponse, tags=["Monitoring"])
def metrics():
    avg = telemetry["latency_total_ms"] / telemetry["requests"] if telemetry["requests"] else 0.0
    uptime = max(0.0, time.time() - telemetry["started_at"])
    return "\n".join([
        "# HELP aetheria_http_requests_total Total HTTP requests handled by this process.",
        "# TYPE aetheria_http_requests_total counter",
        f"aetheria_http_requests_total {telemetry['requests']}",
        "# HELP aetheria_http_errors_total Total HTTP 5xx responses handled by this process.",
        "# TYPE aetheria_http_errors_total counter",
        f"aetheria_http_errors_total {telemetry['errors']}",
        "# HELP aetheria_http_client_errors_total Total HTTP 4xx responses handled by this process.",
        "# TYPE aetheria_http_client_errors_total counter",
        f"aetheria_http_client_errors_total {telemetry['client_errors']}",
        "# HELP aetheria_http_latency_average_ms Average request latency in milliseconds for this process.",
        "# TYPE aetheria_http_latency_average_ms gauge",
        f"aetheria_http_latency_average_ms {avg:.2f}",
        "# HELP aetheria_process_uptime_seconds Process uptime in seconds.",
        "# TYPE aetheria_process_uptime_seconds gauge",
        f"aetheria_process_uptime_seconds {uptime:.2f}",
    ])


if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000)
