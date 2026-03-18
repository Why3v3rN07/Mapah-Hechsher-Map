from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import models, schemas, database
from . import crud
router = APIRouter(prefix="/places")


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.Restaurant)
def create_place(place: schemas.RestaurantCreate, db: Session = Depends(get_db)):
    db_restaurant = models.Restaurant(
        name=place.name,
        lat=place.lat,
        lng=place.lng,
        hechsher=place.hechsher,
        type=place.type
    )
    db.add(db_restaurant)
    db.commit()
    db.refresh(db_restaurant)
    return db_restaurant

@router.get("/", response_model=list[schemas.Restaurant])
def get_places():
    db = database.SessionLocal()
    return db.query(models.Restaurant).all()
