"""Pydantic-схемы фичи prices: запросы и ответы для всех эндпоинтов цен."""

import re
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────
#  /prices/cheap
# ─────────────────────────────────────────────────────────────


class PriceSearchRequest(BaseModel):
    origin: str = Field(..., min_length=2, max_length=3)
    destination: str = Field(..., min_length=2, max_length=3)
    depart_date: str | None = Field(None, description="Дата вылета: YYYY-MM-DD или YYYY-MM")
    return_date: str | None = Field(None, description="Дата возврата: YYYY-MM-DD или YYYY-MM")
    one_way: bool | None = Field(
        None,
        description="true — только в одну сторону, false — только туда-обратно, null — без фильтра",
    )


class PriceEntry(BaseModel):
    origin: str
    destination: str
    price: float

    airline: str | None = None
    flight_number: int | None = None

    departure_at: datetime | None = None
    return_at: datetime | None = None
    expires_at: datetime | None = None

    transfers: int | None = None

    duration: int | None = None
    duration_to: int | None = None
    duration_back: int | None = None

    link: str | None = None


# ─────────────────────────────────────────────────────────────
#  /prices/popular
# ─────────────────────────────────────────────────────────────


class PopularRequest(BaseModel):
    origin: str = Field(..., min_length=2, max_length=3)
    limit: int = Field(30, ge=1, le=100)


# ─────────────────────────────────────────────────────────────
#  /prices/calendar
# ─────────────────────────────────────────────────────────────


class CalendarRequest(BaseModel):
    origin: str = Field(..., min_length=2, max_length=3)
    destination: str = Field(..., min_length=2, max_length=3)
    depart_date: str = Field(..., description="Месяц вылета в формате YYYY-MM")
    return_date: str | None = Field(None, description="Месяц возврата YYYY-MM (для round-trip)")

    @field_validator("depart_date", "return_date")
    @classmethod
    def _validate_month(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not re.fullmatch(r"\d{4}-\d{2}", v):
            raise ValueError("Ожидается формат YYYY-MM, например 2026-12")
        return v


class CalendarDay(BaseModel):
    day: date
    price: float
    airline: str | None = None
    transfers: int | None = None
    # Заполнен, если у записи есть дата возврата (round-trip)
    return_at: datetime | None = None


# ─────────────────────────────────────────────────────────────
#  /prices/month-matrix
# ─────────────────────────────────────────────────────────────


class MonthMatrixRequest(BaseModel):
    origin: str = Field(..., min_length=2, max_length=3)
    destination: str = Field(..., min_length=2, max_length=3)
    month: str = Field(..., description="Месяц YYYY-MM или первое число YYYY-MM-01")
    currency: str = Field("rub")
    show_to_affiliates: bool = Field(True)


class MatrixDay(BaseModel):
    day: date
    price: float
    airline: str | None = None
    transfers: int | None = None
    flight_number: int | None = None


# ─────────────────────────────────────────────────────────────
#  /prices/latest
# ─────────────────────────────────────────────────────────────


class LatestRequest(BaseModel):
    origin: str | None = Field(None, min_length=2, max_length=3)
    destination: str | None = Field(None, min_length=2, max_length=3)
    limit: int = Field(30, ge=1, le=100)