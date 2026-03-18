from fastapi import APIRouter
from .. import models, schemas, database

router = APIRouter(prefix="/places")

@router.get("/", response_model=list[schemas.Restaurant])
def get_places():
    db = database.SessionLocal()
    return db.query(models.Restaurant).all()
