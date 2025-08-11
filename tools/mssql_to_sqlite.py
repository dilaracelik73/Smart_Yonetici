# tools/mssql_to_sqlite.py
import os
from datetime import datetime, date
from decimal import Decimal


from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table, select, text,func
from sqlalchemy.orm import sessionmaker

# ------------- AYARLAR -------------
# Büyük verilerde RAM'i korumak için satırları parçalar halinde taşır.
CHUNK = 5_000
# Taşıma sırası (FK hatası olmasın diye ebeveynler önce):
TABLES_IN_ORDER = [
    "kullanicilar",
    "daireler",
    "aidat_donemleri",
    "gider_kategorileri",
    "duyurular",
    "sakinler",
    "gelirler",
    "giderler",
    "sikayetler",
    "aidatlar",
    "ai_sorgulari",
]

# ------------- YARDIMCI -------------
def normalize_val(v):
    # SQLite için Decimal, datetime vb. tipleri uyumlu hale getir
    if isinstance(v, Decimal):
        # Parasal alanlarda istersen float yerine str de kullanabilirsin
        return float(v)
    if isinstance(v, (datetime, date)):
        return v  # sqlite3 datetime'ı destekler (SQLAlchemy dönüştürür)
    return v

def row_to_dict(row):
    d = dict(row._mapping)
    return {k: normalize_val(v) for k, v in d.items()}

# ------------- ANA AKIŞ -------------
def main():
    load_dotenv()

    mssql_host = os.getenv("MSSQL_HOST")
    mssql_db   = os.getenv("MSSQL_DB")
    mssql_drv  = os.getenv("MSSQL_DRIVER", "ODBC Driver 17 for SQL Server").replace(" ", "+")
    sqlite_path = os.getenv("SQLITE_PATH", "app.db")

    if not (mssql_host and mssql_db):
        raise SystemExit("MSSQL_HOST ve MSSQL_DB .env'de tanımlı olmalı.")

    mssql_uri  = f"mssql+pyodbc://@{mssql_host}/{mssql_db}?driver={mssql_drv}&Trusted_Connection=yes&TrustServerCertificate=yes"
    sqlite_uri = f"sqlite:///{os.path.abspath(sqlite_path)}"

    print(f"Kaynak MSSQL: {mssql_host}/{mssql_db}")
    print(f"Hedef SQLite: {sqlite_path}")

    # Kaynak/Hedef engine'ler
    src_engine = create_engine(mssql_uri, future=True)
    dst_engine = create_engine(sqlite_uri, future=True)

    # Hedef veritabanında tablolar yoksa oluştur (uygulama modellerinize göre)
    # Projeniz Flask app ile create_all yapıyorsa onu çağırmak en doğrusu:
    try:
        from app import create_app, db as flask_db
        app = create_app()
        with app.app_context():
            flask_db.create_all()
            print("-> SQLite şeması (create_all) hazır.")
    except Exception as e:
        print(f"Uyarı: Flask create_all çalışmadı ({e}). Var olan şemayla devam edilecek.")

    src_md = MetaData()
    dst_md = MetaData()

    src_md.reflect(bind=src_engine)
    dst_md.reflect(bind=dst_engine)

    # Hız için ve FK sırayı biz yönettiğimiz için SQLite FK kontrolünü kapat
    with dst_engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys = OFF;"))
    print("-> SQLite foreign_keys=OFF")

    # Kopyalama
    total_rows = 0
    for tname in TABLES_IN_ORDER:
        if tname not in src_md.tables:
            print(f"Atlanıyor (kaynakta yok): {tname}")
            continue
        if tname not in dst_md.tables:
            # hedefte eksikse oluştur (kaynak şemasını kopyalayarak)
            src_table = src_md.tables[tname]
            Table(tname, dst_md, *[c.copy() for c in src_table.columns])
            dst_md.create_all(bind=dst_engine)
            dst_md.reflect(bind=dst_engine)

        src_table = src_md.tables[tname]
        dst_table = dst_md.tables[tname]

        print(f"-> Taşınıyor: {tname}")

        # Toplam satır sayısı
        with src_engine.connect() as conn:
            count_ = conn.execute(
    select(func.count()).select_from(src_table)
).scalar() or 0
        print(f"   MSSQL rows: {count_}")

        if not count_:
            continue

        # CHUNK halinde çek
        offset = 0
        while offset < count_:
            with src_engine.connect() as sconn:
                # MSSQL: OFFSET/FETCH kullanımı
                
                pk_cols = list(src_table.primary_key.columns)
                order_col = pk_cols[0] if pk_cols else list(src_table.columns)[0]
                stmt = (
                    select(src_table)
                    .order_by(order_col)
                    .offset(offset)
                    .limit(CHUNK)   # SQLAlchemy MSSQL'de OFFSET/FETCH'e çevirir
                )
                chunk_rows = sconn.execute(stmt).fetchall()
            if not chunk_rows:
                break

            payload = [row_to_dict(r) for r in chunk_rows]

            # Hedefe bas
            with dst_engine.begin() as dconn:
                # Aynı PK varsa üzerine yazmak istemiyorsan INSERT OR IGNORE da kullanabilirsin.
                dconn.execute(dst_table.insert(), payload)

            offset += len(chunk_rows)
            total_rows += len(chunk_rows)
            print(f"   +{len(chunk_rows)} (toplam {offset}/{count_})")

    # FK kontrolünü geri aç
    with dst_engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON;"))
    print("-> SQLite foreign_keys=ON")

    print(f"TAMAM ✅  Toplam taşınan satır: {total_rows}")
    print(f"Hedef dosya: {sqlite_path}")

if __name__ == "__main__":
    main()
