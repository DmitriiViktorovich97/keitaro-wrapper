from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from app.keitaro_client import KeitaroError
from app.routers import router
from app.services.campaign_service import ServiceError

app = FastAPI(title="Keitaro Wrapper")
app.include_router(router)

STATIC = Path(__file__).parent / "static"


@app.exception_handler(KeitaroError)
async def keitaro_error_handler(_: Request, exc: KeitaroError):
    return JSONResponse(status_code=502, content={"detail": f"Keitaro: {exc}"})


@app.exception_handler(ServiceError)
async def service_error_handler(_: Request, exc: ServiceError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC / "index.html")
