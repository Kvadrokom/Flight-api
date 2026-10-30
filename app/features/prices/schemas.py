"""Pydantic-схемы фичи prices: запросы и ответы для всех эндпоинтов цен."""

from datetime import date, datetime

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────
#  /prices/cheap — поиск дешёвых билетов по маршруту
# ─────────────────────────────────────────────────────────────


class PriceSearchRequest(BaseModel):
    """Запрос на поиск дешёвых билетов."""

    origin: str = Field(
        ...,
        min_length=2,
        max_length=3,
        description="IATA-код города вылета, например MOW",
    )
    destination: str = Field(
        ...,
        min_length=2,
        max_length=3,
        description="IATA-код города прилёта, например LED",
    )
    depart_date: str | None = Field(
        None,
        description="Дата вылета: YYYY-MM-DD или YYYY-MM",
    )
    return_date: str | None = Field(
        None,
        description="Дата возврата: YYYY-MM-DD или YYYY-MM",
    )
    one_way: bool | None = Field(
        None,
        description="true — только в одну сторону, false — только туда-обратно, null — без фильтра",
    )


class PriceEntry(BaseModel):
    """Одна запись о цене (используется в /cheap, /popular, /latest)."""

    origin: str
    destination: str
    price: float

    airline: str | None = None
    flight_number: int | None = None

    departure_at: datetime | None = None
    return_at: datetime | None = None
    expires_at: datetime | None = None

    transfers: int | None = None

    # Длительность в минутах
    duration: int | None = None
    duration_to: int | None = None
    duration_back: int | None = None

    link: str | None = None


# ─────────────────────────────────────────────────────────────
#  /prices/popular — популярные направления из города
# ─────────────────────────────────────────────────────────────


class PopularRequest(BaseModel):
    """Запрос на популярные направления из города (без destination)."""

    origin: str = Field(
        ...,
        min_length=2,
        max_length=3,
        description="IATA-код города вылета",
    )
    limit: int = Field(
        30,
        ge=1,
        le=100,
        description="Максимум записей в ответе",
    )


# ─────────────────────────────────────────────────────────────
#  /prices/calendar — календарь минимальных цен на месяц
# ─────────────────────────────────────────────────────────────


class CalendarRequest(BaseModel):
    """Запрос календаря цен на месяц."""

    origin: str = Field(..., min_length=2, max_length=3)
    destination: str = Field(..., min_length=2, max_length=3)
    depart_date: str = Field(
        ...,
        description="Месяц в формате YYYY-MM (например, 2026-12)",
    )
    return_date: str | None = Field(
        None,
        description="Месяц возврата YYYY-MM (для round-trip)",
    )


class CalendarDay(BaseModel):
    """Минимальная цена за конкретный день месяца."""

    day: date
    price: float
    airline: str | None = None
    transfers: int | None = None


# ─────────────────────────────────────────────────────────────
#  /prices/month-matrix — матрица цен на месяц
# ─────────────────────────────────────────────────────────────


class MonthMatrixRequest(BaseModel):
    """Запрос матрицы цен на месяц."""

    origin: str = Field(..., min_length=2, max_length=3)
    destination: str = Field(..., min_length=2, max_length=3)
    month: str = Field(
        ...,
        description="Месяц YYYY-MM или первое число YYYY-MM-01",
    )
    currency: str = Field(
        "rub",
        description="Валюта цен: rub, usd, eur",
    )
    show_to_affiliates: bool = Field(
        True,
        description="true — показывать цены партнёра, false — цены обычного пользователя",
    )


class MatrixDay(BaseModel):
    """Одна строка матрицы цен: день, цена, пересадки."""

    day: date
    price: float
    airline: str | None = None
    transfers: int | None = None
    flight_number: int | None = None


# ─────────────────────────────────────────────────────────────
#  /prices/latest — последние найденные цены
# ─────────────────────────────────────────────────────────────


class LatestRequest(BaseModel):
    """Запрос последних найденных цен (без обязательного маршрута)."""

    origin: str | None = Field(
        None,
        min_length=2,
        max_length=3,
        description="Если указан — только вылеты из этого города",
    )
    destination: str | None = Field(
        None,
        min_length=2,
        max_length=3,
        description="Если указан — только прилёты в этот город",
    )
    limit: int = Field(
        30,
        ge=1,
        le=100,
        description="Максимум записей",
    )