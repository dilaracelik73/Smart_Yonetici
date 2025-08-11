import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # .env'den oku; yoksa dev için yedek değer
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only")

    MSSQL_HOST = os.getenv("MSSQL_HOST")              # örn: DILARA_CELIK\\SQLEXPRESS
    MSSQL_DB = os.getenv("MSSQL_DB")                  # örn: yonetici_db
    MSSQL_DRIVER = os.getenv("MSSQL_DRIVER", "ODBC Driver 17 for SQL Server")
    MSSQL_TRUST_CERT = os.getenv("MSSQL_TRUST_CERT", "yes")

    # Opsiyonel SQL kullanıcı/parola (prod için genelde bu tercih edilir)
    MSSQL_USER = os.getenv("MSSQL_USER")              # örn: sa
    MSSQL_PASSWORD = os.getenv("MSSQL_PASSWORD")      # örn: Sifre123!

    # --- SQLAlchemy veritabanı bağlantı dizesi ---
    if MSSQL_USER and MSSQL_PASSWORD:
        # SQL Authentication
        SQLALCHEMY_DATABASE_URI = (
            "mssql+pyodbc://"
            f"{MSSQL_USER}:{MSSQL_PASSWORD}@{MSSQL_HOST},1433/{MSSQL_DB}"
            f"?driver={MSSQL_DRIVER.replace(' ', '+')}"
            f"&TrustServerCertificate={MSSQL_TRUST_CERT}"
        )
    else:
        # Windows Integrated Security (lokal geliştirme)
        SQLALCHEMY_DATABASE_URI = (
            "mssql+pyodbc://@"
            f"{MSSQL_HOST}/{MSSQL_DB}"
            f"?driver={MSSQL_DRIVER.replace(' ', '+')}"
            f"&Trusted_Connection=yes"
            f"&TrustServerCertificate={MSSQL_TRUST_CERT}"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

