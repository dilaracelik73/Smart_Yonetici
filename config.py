

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLITE_PATH = os.getenv("SQLITE_PATH", os.path.join(BASE_DIR, "app.db"))
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{SQLITE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
