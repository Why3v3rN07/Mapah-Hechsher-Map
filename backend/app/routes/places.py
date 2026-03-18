from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, database
router = APIRouter(prefix="/places")

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create
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

# Read
@router.get("/", response_model=list[schemas.Restaurant])
def get_places():
    db = database.SessionLocal()
    return db.query(models.Restaurant).all()

# Update
@router.patch("/{restaurant_id}", response_model=schemas.Restaurant)
def update_place(restaurant_id: int, updates: schemas.RestaurantUpdate, db: Session = Depends(get_db)):
    db_restaurant = db.query(models.Restaurant).filter(models.Restaurant.id == restaurant_id).first()
    if not db_restaurant: raise HTTPException(status_code=404, detail="Restaurant not found")
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_restaurant, key, value)
    db.commit()
    db.refresh(db_restaurant)
    return db_restaurant

# Delete
@router.delete("/{restaurant_id}")
def delete_place(restaurant_id: int, db: Session = Depends(get_db)):
    db_restaurant = db.query(models.Restaurant).filter(models.Restaurant.id == restaurant_id).first()
    if not db_restaurant: raise HTTPException(status_code=404, detail="Restaurant not found")
    db.delete(db_restaurant)
    db.commit()
    return {"detail": "Restaurant deleted"}
