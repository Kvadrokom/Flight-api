from pydantic import BaseModel


class City(BaseModel):
    code: str
    name: str
    country: str