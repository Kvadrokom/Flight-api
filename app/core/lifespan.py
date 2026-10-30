import logging
from contextlib import asynccontextmanager

from avia_api import AviaApiClient
from fastapi import FastAPI

from app.core.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управляет жизненным циклом общих ресурсов: старт и остановка."""
    logger.info("Создаём AviaApiClient...")
    app.state.avia_client = AviaApiClient(token=settings.travelpayouts_token)

    try:
        yield
    finally:
        logger.info("Закрываем AviaApiClient...")
        await app.state.avia_client.close()
