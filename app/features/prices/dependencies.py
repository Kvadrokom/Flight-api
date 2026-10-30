from fastapi import Request
from avia_api import AviaApiClient


def get_avia_client(request: Request) -> AviaApiClient:
    """Достаёт общий клиент из app.state (создан в lifespan)."""
    return request.app.state.avia_client