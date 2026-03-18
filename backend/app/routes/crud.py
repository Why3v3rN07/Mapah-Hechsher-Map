from .. import models, schemas, database

def create_restaurant(db, restaurant: schemas.RestaurantCreate):
    db_restaurant = models.Restaurant(
        name=restaurant.name,
        lat=restaurant.lat,
        lng=restaurant.lng,
        hechsher=restaurant.hechsher,
        type=restaurant.type
    )
    db.add(db_restaurant)
    db.commit()
    db.refresh(db_restaurant)
    return db_restaurant
