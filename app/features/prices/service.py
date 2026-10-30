"""Бизнес-логика фичи prices: вызовы avia-api и нормализация ответов."""
import httpx

from app.core.config import settings
import logging
from datetime import date, datetime
from typing import Any

from avia_api import AviaApiClient

from . import schemas

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
#  Утилиты нормализации
# ─────────────────────────────────────────────────────────────


def _to_dict(obj: Any) -> dict:
    """Приводит Pydantic-модель (SimplePrice) или dict к plain dict."""
    if hasattr(obj, "model_dump"):       # Pydantic v2
        return obj.model_dump()
    if hasattr(obj, "dict"):             # Pydantic v1
        return obj.dict()
    if isinstance(obj, dict):
        return obj
    return {}


def _unwrap(raw: Any) -> Any:
    """Если API вернул полный ответ с обёрткой {"data": ...} — достаём data."""
    if isinstance(raw, dict) and "data" in raw:
        inner = raw["data"]
        # Если внутри data — только служебные поля, оставляем как есть
        if isinstance(inner, (dict, list)):
            return inner
    return raw


def _parse_date(value: Any) -> date | None:
    """Парсит дату из строки, datetime или date. Возвращает None при неудаче."""
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


def _entry_from_dict(
    data: dict,
    origin: str,
    destination: str,
) -> schemas.PriceEntry:
    """Собирает PriceEntry из plain dict, безопасно извлекая поля."""
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
    """
    Итерирует по структуре, похожей на /prices/cheap:
        {destination_code: {index: SimplePrice | dict}}
    Yields (destination_code, entry_dict).
    """
    if not isinstance(raw, dict):
        return
    for dest_code, by_index in raw.items():
        if not isinstance(by_index, dict):
            continue
        for entry in by_index.values():
            yield dest_code, _to_dict(entry)


# ─────────────────────────────────────────────────────────────
#  /prices/cheap — дешёвые билеты по маршруту
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

    results: list[schemas.PriceEntry] = []
    for dest_code, entry_dict in _iter_cheap_like(raw):
        results.append(_entry_from_dict(entry_dict, request.origin, dest_code))

    results.sort(key=lambda e: e.price)
    logger.info("Найдено %d записей", len(results))
    return results


# ─────────────────────────────────────────────────────────────
#  /prices/popular — популярные направления из города
# ─────────────────────────────────────────────────────────────


async def get_popular_destinations(
    client: AviaApiClient,
    request: schemas.PopularRequest,
) -> list[schemas.PriceEntry]:
    """Популярные направления из города — запрос без destination.

    avia-api не позволяет опустить destination (обязательный позиционный аргумент),
    поэтому обращаемся к Travelpayouts напрямую через httpx.
    """
    logger.info("Популярные из %s (limit=%d)", request.origin, request.limit)

    async with httpx.AsyncClient(timeout=15.0) as http:
        response = await http.get(
            "https://api.travelpayouts.com/v1/prices/cheap",
            params={"origin": request.origin},
            headers={"X-Access-Token": settings.travelpayouts_token},
        )
        response.raise_for_status()
        payload = response.json()

    data = payload.get("data", {}) if isinstance(payload, dict) else {}

    results: list[schemas.PriceEntry] = []
    for dest_code, entry_dict in _iter_cheap_like(data):
        results.append(_entry_from_dict(entry_dict, request.origin, dest_code))

    results.sort(key=lambda e: e.price)
    logger.info("Популярных направлений: %d", len(results))
    return results[: request.limit]


# ─────────────────────────────────────────────────────────────
#  /prices/calendar — календарь минимальных цен на месяц
# ─────────────────────────────────────────────────────────────


async def get_price_calendar(
    client: AviaApiClient,
    request: schemas.CalendarRequest,
) -> list[schemas.CalendarDay]:
    logger.info(
        "Календарь цен: %s → %s, месяц %s",
        request.origin, request.destination, request.depart_date,
    )

    kwargs: dict = {
        "origin": request.origin,
        "destination": request.destination,
        "depart_date": request.depart_date,
    }
    if request.return_date:
        kwargs["return_date"] = request.return_date

    raw = await client.prices.calendar(**kwargs)
    raw = _unwrap(raw)

    results: list[schemas.CalendarDay] = []

    # calendar обычно возвращает {YYYY-MM-DD: SimplePrice | dict}
    if isinstance(raw, dict):
        for day_str, entry in raw.items():
            day = _parse_date(day_str)
            if day is None:
                continue
            entry_dict = _to_dict(entry)
            results.append(
                schemas.CalendarDay(
                    day=day,
                    price=float(entry_dict.get("price") or 0),
                    airline=entry_dict.get("airline"),
                    transfers=entry_dict.get("transfers"),
                )
            )
    # На случай, если API вернёт список
    elif isinstance(raw, list):
        for item in raw:
            entry_dict = _to_dict(item)
            day = _parse_date(entry_dict.get("depart_date") or entry_dict.get("day"))
            if day is None:
                continue
            results.append(
                schemas.CalendarDay(
                    day=day,
                    price=float(entry_dict.get("price") or 0),
                    airline=entry_dict.get("airline"),
                    transfers=entry_dict.get("transfers"),
                )
            )

    results.sort(key=lambda d: d.day)
    logger.info("Календарь: %d дней", len(results))
    return results


# ─────────────────────────────────────────────────────────────
#  /prices/month-matrix — матрица цен на месяц
# ─────────────────────────────────────────────────────────────


async def get_month_matrix(
    client: AviaApiClient,
    request: schemas.MonthMatrixRequest,
) -> list[schemas.MatrixDay]:
    logger.info(
        "Матрица цен: %s → %s, месяц %s",
        request.origin, request.destination, request.month,
    )

    raw = await client.prices.month_matrix(
        origin=request.origin,
        destination=request.destination,
        month=request.month,
    )
    raw = _unwrap(raw)

    results: list[schemas.MatrixDay] = []

    # month-matrix обычно возвращает список словарей
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        items = list(raw.values())
    else:
        items = []

    for item in items:
        entry_dict = _to_dict(item)
        day = _parse_date(entry_dict.get("depart_date") or entry_dict.get("day"))
        if day is None:
            continue
        results.append(
            schemas.MatrixDay(
                day=day,
                price=float(entry_dict.get("price") or 0),
                airline=entry_dict.get("airline"),
                transfers=entry_dict.get("transfers"),
                flight_number=entry_dict.get("flight_number"),
            )
        )

    results.sort(key=lambda d: d.day)
    logger.info("Матрица: %d дней", len(results))
    return results


# ─────────────────────────────────────────────────────────────
#  /prices/latest — последние найденные цены
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

    # Структура как cheap: {dest_code: {idx: entry}}
    if isinstance(raw, dict) and raw and not isinstance(next(iter(raw.values())), list):
        for dest_code, entry_dict in _iter_cheap_like(raw):
            results.append(
                _entry_from_dict(
                    entry_dict,
                    origin=request.origin or "—",
                    destination=dest_code,
                )
            )
    # Структура как список: [{origin, destination, price, ...}]
    elif isinstance(raw, list):
        for item in raw:
            entry_dict = _to_dict(item)
            results.append(
                _entry_from_dict(
                    entry_dict,
                    origin=entry_dict.get("origin") or request.origin or "—",
                    destination=entry_dict.get("destination") or request.destination or "—",
                )
            )

    results.sort(key=lambda e: e.price)
    logger.info("Последние: %d записей", len(results))
    return results