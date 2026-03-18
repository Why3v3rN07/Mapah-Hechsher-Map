from sqlalchemy import Column, Integer, String, Float
from .database import Base

class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    lat = Column(Float)
    lng = Column(Float)
    hechsher = Column(String, index=True)
    type = Column(String)
