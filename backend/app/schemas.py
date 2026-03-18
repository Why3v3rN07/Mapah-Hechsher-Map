from pydantic import BaseModel


class RestaurantBase(BaseModel):
    name: str
    lat: float
    lng: float
    hechsher: str
    type: str | None = None


class RestaurantCreate(RestaurantBase):
    pass

class Restaurant(RestaurantBase):
    id: int

    model_config = {
        "from_attributes": True
    }

class RestaurantUpdate(BaseModel):
    name: str | None = None
    lat: float | None = None
    lng: float | None = None
    hechsher: str | None = None
    type: str | None = None

    model_config = {
        "from_attributes": True
    }
