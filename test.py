from sqlalchemy import create_engine
from sqlalchemy.sql import text  # 🟢 Doğru yerden import

# Bağlantı adresin (senin örneğine göre)
engine = create_engine(
    "mssql+pyodbc://DILARA_CELIK\\SQLEXPRESS/yonetici_db?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes&trusted_connection=yes"
)

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))  # ✅ BURADA text() İÇİNDE!
        print("✅ MSSQL bağlantısı başarılı:", result.scalar())
except Exception as e:
    print("❌ Hata:", e)
