from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import places
from .database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(places.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # during development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
