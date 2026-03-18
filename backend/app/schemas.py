from pydantic import BaseModel

class RestaurantBase(BaseModel):
    name: str
    lat: float
    lng: float
    hechsher: str
    type: str

class Restaurant(RestaurantBase):
    id: int

    class Config:
        orm_mode = True
