from fastapi import FastAPI
from .routes import places
from .database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(places.router)
