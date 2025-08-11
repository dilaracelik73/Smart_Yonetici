import os
from dotenv import load_dotenv

load_dotenv()

import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
    SQLITE_PATH = os.getenv("SQLITE_PATH", "app.db")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.abspath(SQLITE_PATH)}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
