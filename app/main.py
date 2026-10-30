import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.lifespan import lifespan
from app.features.prices.router import router as prices_router
from app.features.reference.router import router as reference_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

app = FastAPI(
    title="Flight Price API",
    version="0.2.0",
    description="Сбор цен на авиабилеты через Travelpayouts Data API",
    lifespan=lifespan,
)

# API-роутеры
app.include_router(prices_router, prefix="/prices", tags=["Prices"])
app.include_router(reference_router, prefix="/reference", tags=["Reference"])

# Статика и главная страница
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", tags=["System"])
async def health() -> dict[str, str]:
    return {"status": "ok"}