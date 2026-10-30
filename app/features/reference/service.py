import json
from pathlib import Path

from . import schemas

_CITIES_PATH = Path(__file__).parent.parent.parent / "data" / "cities.json"
_cities_cache: list[schemas.City] | None = None


def get_cities() -> list[schemas.City]:
    """Возвращает список городов, отсортированный по названию. Кэширует в памяти."""
    global _cities_cache
    if _cities_cache is None:
        with _CITIES_PATH.open(encoding="utf-8") as f:
            raw = json.load(f)
        cities = [schemas.City(**item) for item in raw]
        # Сортировка по русскому названию (локаль 'ru')
        cities.sort(key=lambda c: c.name)
        _cities_cache = cities
    return _cities_cache