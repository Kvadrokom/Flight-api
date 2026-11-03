"""Бизнес-логика фичи prices: вызовы API и нормализация ответов."""

import logging
from datetime import date, datetime
from typing import Any

import httpx
from avia_api import AviaApiClient

from app.core.config import settings
from . import schemas

logger = logging.getLogger(__name__)

TRAVELPAYOUTS_BASE = "https://api.travelpayouts.com"


# ─────────────────────────────────────────────────────────────
#  Утилиты нормализации
# ─────────────────────────────────────────────────────────────


def _to_dict(obj: Any) -> dict:
    """Pydantic-модель (SimplePrice) или dict → plain dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if isinstance(obj, dict):
        return obj
    return {}


def _unwrap(raw: Any) -> Any:
    """Если API вернул {"data": ...} — достаём data."""
    if isinstance(raw, dict) and "data" in raw:
        inner = raw["data"]
        if isinstance(inner, (dict, list)):
            return inner
    return raw


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _entry_from_dict(data: dict, origin: str, destination: str) -> schemas.PriceEntry:
    return schemas.PriceEntry(
        origin=origin,
        destination=destination,
        price=float(data.get("price") or 0),
        airline=data.get("airline"),
        flight_number=data.get("flight_number"),
        departure_at=data.get("departure_at"),
        return_at=data.get("return_at"),
        expires_at=data.get("expires_at"),
        transfers=data.get("transfers"),
        duration=data.get("duration"),
        duration_to=data.get("duration_to"),
        duration_back=data.get("duration_back"),
        link=data.get("link"),
    )


def _iter_cheap_like(raw: Any):
    """Генератор по структуре {dest: {idx: entry}}."""
    if not isinstance(raw, dict):
        return
    for dest_code, by_index in raw.items():
        if not isinstance(by_index, dict):
            continue
        for entry in by_index.values():
            yield dest_code, _to_dict(entry)


# ─────────────────────────────────────────────────────────────
#  /prices/cheap
# ─────────────────────────────────────────────────────────────


async def get_cheapest_prices(
    client: AviaApiClient,
    request: schemas.PriceSearchRequest,
) -> list[schemas.PriceEntry]:
    logger.info(
        "Запрос цен: %s → %s (depart=%s, return=%s, one_way=%s)",
        request.origin, request.destination,
        request.depart_date, request.return_date, request.one_way,
    )

    kwargs: dict = {"origin": request.origin, "destination": request.destination}
    if request.depart_date:
        kwargs["depart_date"] = request.depart_date
    if request.return_date:
        kwargs["return_date"] = request.return_date
    if request.one_way is not None:
        kwargs["one_way"] = request.one_way

    raw = await client.prices.cheap(**kwargs)
    raw = _unwrap(raw)

    results = [
        _entry_from_dict(d, request.origin, dest)
        for dest, d in _iter_cheap_like(raw)
    ]
    results.sort(key=lambda e: e.price)
    logger.info("Найдено %d записей", len(results))
    return results


# ─────────────────────────────────────────────────────────────
#  /prices/popular — через httpx (avia-api требует destination)
# ─────────────────────────────────────────────────────────────


async def get_popular_destinations(
    client: AviaApiClient,
    request: schemas.PopularRequest,
) -> list[schemas.PriceEntry]:
    logger.info("Популярные из %s (limit=%d)", request.origin, request.limit)

    async with httpx.AsyncClient(timeout=15.0) as http:
        response = await http.get(
            f"{TRAVELPAYOUTS_BASE}/v1/prices/cheap",
            params={"origin": request.origin},
            headers={"X-Access-Token": settings.travelpayouts_token},
        )
        response.raise_for_status()
        payload = response.json()

    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    results = [
        _entry_from_dict(d, request.origin, dest)
        for dest, d in _iter_cheap_like(data)
    ]
    results.sort(key=lambda e: e.price)
    logger.info("Популярных направлений: %d", len(results))
    return results[: request.limit]


# ─────────────────────────────────────────────────────────────
#  /prices/calendar — через httpx (для calendar_type)
# ─────────────────────────────────────────────────────────────


async def get_price_calendar(
    client: AviaApiClient,
    request: schemas.CalendarRequest,
) -> list[schemas.CalendarDay]:
    logger.info(
        "Календарь: %s → %s, месяц %s%s",
        request.origin, request.destination, request.depart_date,
        f", return={request.return_date}" if request.return_date else " (one-way)",
    )

    params: dict = {
        "origin": request.origin,
        "destination": request.destination,
        "depart_date": request.depart_date,
        "calendar_type": "departure_date",
    }
    if request.return_date:
        params["return_date"] = request.return_date

    async with httpx.AsyncClient(timeout=15.0) as http:
        response = await http.get(
            f"{TRAVELPAYOUTS_BASE}/v1/prices/calendar",
            params=params,
            headers={"X-Access-Token": settings.travelpayouts_token},
        )
        response.raise_for_status()
        payload = response.json()

    data = payload.get("data", {}) if isinstance(payload, dict) else {}

    results: list[schemas.CalendarDay] = []

    if isinstance(data, dict):
        for day_str, entry in data.items():
            day = _parse_date(day_str)
            if day is None:
                continue
            ed = _to_dict(entry)
            results.append(
                schemas.CalendarDay(
                    day=day,
                    price=float(ed.get("price") or 0),
                    airline=ed.get("airline"),
                    transfers=ed.get("transfers"),
                    return_at=ed.get("return_at"),
                )
            )
    elif isinstance(data, list):
        for item in data:
            ed = _to_dict(item)
            day = _parse_date(ed.get("depart_date") or ed.get("day"))
            if day is None:
                continue
            results.append(
                schemas.CalendarDay(
                    day=day,
                    price=float(ed.get("price") or 0),
                    airline=ed.get("airline"),
                    transfers=ed.get("transfers"),
                    return_at=ed.get("return_at"),
                )
            )

    results.sort(key=lambda d: d.day)
    logger.info("Календарь: %d дней", len(results))
    return results


# ─────────────────────────────────────────────────────────────
#  /prices/month-matrix
# ─────────────────────────────────────────────────────────────


async def get_month_matrix(
    client: AviaApiClient,
    request: schemas.MonthMatrixRequest,
) -> list[schemas.MatrixDay]:
    logger.info(
        "Матрица: %s → %s, месяц %s",
        request.origin, request.destination, request.month,
    )

    raw = await client.prices.month_matrix(
        origin=request.origin,
        destination=request.destination,
        month=request.month,
    )
    raw = _unwrap(raw)

    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        items = list(raw.values())
    else:
        items = []

    results: list[schemas.MatrixDay] = []
    for item in items:
        ed = _to_dict(item)
        day = _parse_date(ed.get("depart_date") or ed.get("day"))
        if day is None:
            continue
        results.append(
            schemas.MatrixDay(
                day=day,
                price=float(ed.get("price") or 0),
                airline=ed.get("airline"),
                transfers=ed.get("transfers"),
                flight_number=ed.get("flight_number"),
            )
        )

    results.sort(key=lambda d: d.day)
    logger.info("Матрица: %d дней", len(results))
    return results


# ─────────────────────────────────────────────────────────────
#  /prices/latest
# ─────────────────────────────────────────────────────────────


async def get_latest_prices(
    client: AviaApiClient,
    request: schemas.LatestRequest,
) -> list[schemas.PriceEntry]:
    logger.info(
        "Последние цены (origin=%s, destination=%s, limit=%d)",
        request.origin, request.destination, request.limit,
    )

    kwargs: dict = {"limit": request.limit}
    if request.origin:
        kwargs["origin"] = request.origin
    if request.destination:
        kwargs["destination"] = request.destination

    raw = await client.prices.latest(**kwargs)
    raw = _unwrap(raw)

    results: list[schemas.PriceEntry] = []

    if isinstance(raw, dict) and raw and not isinstance(next(iter(raw.values())), list):
        for dest, d in _iter_cheap_like(raw):
            results.append(_entry_from_dict(d, request.origin or "—", dest))
    elif isinstance(raw, list):
        for item in raw:
            ed = _to_dict(item)
            results.append(
                _entry_from_dict(
                    ed,
                    origin=ed.get("origin") or request.origin or "—",
                    destination=ed.get("destination") or request.destination or "—",
                )
            )

    results.sort(key=lambda e: e.price)
    logger.info("Последних: %d", len(results))
    return results