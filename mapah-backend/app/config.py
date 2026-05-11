import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # In production, override these with environment variables or a .env file
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
