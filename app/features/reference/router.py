from fastapi import APIRouter

from . import schemas, service

router = APIRouter()


@router.get(
    "/cities",
    response_model=list[schemas.City],
    summary="Список городов",
)
async def list_cities() -> list[schemas.City]:
    return service.get_cities()