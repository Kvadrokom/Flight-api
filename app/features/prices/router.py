"""HTTP-эндпоинты фичи prices."""

from fastapi import APIRouter, Depends
from avia_api import AviaApiClient

from . import schemas, service
from .dependencies import get_avia_client

router = APIRouter()


# ─────────────────────────────────────────────────────────────
#  /prices/cheap — дешёвые билеты по маршруту
# ─────────────────────────────────────────────────────────────


@router.post(
    "/cheap",
    response_model=list[schemas.PriceEntry],
    summary="Дешёвые билеты по направлению",
    description="Возвращает кэшированные цены Travelpayouts по маршруту.",
)
async def find_cheap_prices(
    search: schemas.PriceSearchRequest,
    client: AviaApiClient = Depends(get_avia_client),
) -> list[schemas.PriceEntry]:
    return await service.get_cheapest_prices(client, search)


# ─────────────────────────────────────────────────────────────
#  /prices/popular — популярные направления из города
# ─────────────────────────────────────────────────────────────


@router.post(
    "/popular",
    response_model=list[schemas.PriceEntry],
    summary="Популярные направления из города",
    description="30 самых дешёвых билетов из указанного города без указания направления.",
)
async def popular_destinations(
    search: schemas.PopularRequest,
    client: AviaApiClient = Depends(get_avia_client),
) -> list[schemas.PriceEntry]:
    return await service.get_popular_destinations(client, search)


# ─────────────────────────────────────────────────────────────
#  /prices/calendar — календарь цен на месяц
# ─────────────────────────────────────────────────────────────


@router.post(
    "/calendar",
    response_model=list[schemas.CalendarDay],
    summary="Календарь цен на месяц",
    description="Минимальная цена за каждый день месяца по маршруту.",
)
async def price_calendar(
    search: schemas.CalendarRequest,
    client: AviaApiClient = Depends(get_avia_client),
) -> list[schemas.CalendarDay]:
    return await service.get_price_calendar(client, search)


# ─────────────────────────────────────────────────────────────
#  /prices/month-matrix — матрица цен на месяц
# ─────────────────────────────────────────────────────────────


@router.post(
    "/month-matrix",
    response_model=list[schemas.MatrixDay],
    summary="Матрица цен на месяц",
    description="Цены по дням месяца с разбивкой по пересадкам и авиакомпаниям.",
)
async def month_matrix(
    search: schemas.MonthMatrixRequest,
    client: AviaApiClient = Depends(get_avia_client),
) -> list[schemas.MatrixDay]:
    return await service.get_month_matrix(client, search)


# ─────────────────────────────────────────────────────────────
#  /prices/latest — последние найденные цены
# ─────────────────────────────────────────────────────────────


@router.post(
    "/latest",
    response_model=list[schemas.PriceEntry],
    summary="Последние найденные цены",
    description="Последние цены по всем направлениям (или с фильтром по origin/destination).",
)
async def latest_prices(
    search: schemas.LatestRequest,
    client: AviaApiClient = Depends(get_avia_client),
) -> list[schemas.PriceEntry]:
    return await service.get_latest_prices(client, search)