# ai_helpers.py
import requests
from app import db
from app.models import AISorgu
from datetime import datetime
import time
import os
from dotenv import load_dotenv
from flask import current_app

load_dotenv()




# API sabitleri (geliştirme amaçlı doğrudan yazıldı)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-chat-v3-0324:free"

headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
}


def generate_announcement(prompt):
    data = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(OPENROUTER_BASE_URL, headers=headers, json=data)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print("OpenRouter API hatası:", response.status_code, response.text)
        return "❌ AI yanıtı alınamadı!"


def analyze_complaint_with_ai(text):
    prompt = f"""
Aşağıdaki apartman şikayet metnini analiz etmeni istiyorum.

Metin: \"{text}\"

Şu formatta cevap ver:

Kategori: [teknik, temizlik, gurultu, guvenlik, yonetim, diger]
Öncelik: [dusuk, orta, yuksek]
Durum: [bekliyor] (varsayılan olarak bekliyor yaz)
Çözüm Önerisi: (kısa ve uygulanabilir öneri ver)

Yanıt sadece bu alanları içersin. Başka hiçbir şey yazma.
"""

    data = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(OPENROUTER_BASE_URL, headers=headers, json=data, timeout=30)
    except Exception as e:
        print("OpenRouter API bağlantı hatası:", e)
        return {
            "kategori": "diger",
            "oncelik": "orta",
            "durum": "bekliyor",
            "cozum_onerisi": "AI bağlantı hatası.",
            "guven_skoru": 0
        }

    if response.status_code != 200:
        try:
            err = response.json().get("error", {}).get("message", response.text)
        except Exception:
            err = response.text
        print(f"OpenRouter API hatası: {response.status_code} - {err}")
        return {
            "kategori": "diger",
            "oncelik": "orta",
            "durum": "bekliyor",
            "cozum_onerisi": f"AI yanıt veremedi ({response.status_code}).",
            "guven_skoru": 0
        }

    try:
        resp_json = response.json()
        if "choices" not in resp_json or not resp_json["choices"]:
            print("Beklenen 'choices' alanı yok. Dönen veri:", resp_json)
            return {
                "kategori": "diger",
                "oncelik": "orta",
                "durum": "bekliyor",
                "cozum_onerisi": "AI yanıt formatı hatalı.",
                "guven_skoru": 0
            }

        result_text = resp_json["choices"][0]["message"]["content"]
        return parse_ai_response(result_text)

    except Exception as e:
        print("Yanıt işleme hatası:", e)
        return {
            "kategori": "diger",
            "oncelik": "orta",
            "durum": "bekliyor",
            "cozum_onerisi": "AI yanıt işleme hatası.",
            "guven_skoru": 0
        }


def parse_ai_response(text):
    lines = text.strip().split("\n")
    result = {
        "kategori": "diger",
        "oncelik": "orta",
        "durum": "bekliyor",
        "cozum_onerisi": "",
        "guven_skoru": 80  # varsayılan
    }

    for line in lines:
        line = line.strip().lower()
        if line.startswith("kategori:"):
            result["kategori"] = line.replace("kategori:", "").strip()
        elif line.startswith("öncelik:") or line.startswith("oncelik:"):
            result["oncelik"] = line.replace("öncelik:", "").replace("oncelik:", "").strip()
        elif line.startswith("durum:"):
            result["durum"] = line.replace("durum:", "").strip()
        elif line.startswith("çözüm önerisi:") or line.startswith("cozum onerisi:"):
            result["cozum_onerisi"] = line.replace("çözüm önerisi:", "").replace("cozum onerisi:", "").strip()

    return result

from sqlalchemy import text
from app import db
import os
import unicodedata
from datetime import datetime
import requests
from sqlalchemy import text


# --- Yardımcılar -------------------------------------------------------------

# NOT: Bu listeler normalize edilmiş (ş,ı,ü vs. sadeleştirilmiş) halleriyle tutulur.
FINANS_KW = ("gider", "gelir", "butce", "butceleme", "harcama", "maliyet", "masraf", "fatura", "bilanco", "kasa")
SOHBET_KW = ("sohbet", "konus", "chat", "soru-cevap", "muhabbet", "muhabbet etmek", "lafla", "geyik")

def _tr_normalize(s: str) -> str:
    """Türkçe metni anahtar aramaya uygun normalize eder."""
    if not s:
        return ""
    s = s.lower()
    repl = str.maketrans({
        "ı":"i","İ":"i","ş":"s","Ş":"s","ç":"c","Ç":"c",
        "ö":"o","Ö":"o","ü":"u","Ü":"u","ğ":"g","Ğ":"g"
    })
    s = s.translate(repl)
    return unicodedata.normalize("NFKD", s)

def _safe_ai_call(messages):
    """OpenRouter çağrısı. Hata durumunda RuntimeError raise eder."""
    if not OPENROUTER_API_KEY:
        # Anahtar yoksa erken ve anlamlı hata:
        raise RuntimeError("OpenRouter API key missing")
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"model": MODEL, "messages": messages},
        timeout=30,
    )
    if r.status_code != 200:
        # Hata içeriğini iletelim (429 tespiti için)
        raise RuntimeError(f"OpenRouter {r.status_code}: {r.text[:400]}")
    data = r.json()
    return (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()

def _ai_chat_with_fallback(user_text: str) -> str:
    """Sohbet çağrısı; 429 ve benzeri hatalarda nazik fallback döner."""
    try:
        return _safe_ai_call([{"role": "user", "content": user_text}]) or "Sohbet ediyoruz, devam!"
    except RuntimeError as e:
        msg = str(e)
        # Rate limit ya da anahtar yoksa vb. durumlar
        if "429" in msg:
            return "Şu an sohbet limitim doldu gibi görünüyor, ama buradayım 😊 Başka ne hakkında konuşalım?"
        if "API key" in msg or "key missing" in msg:
            return "Sohbet servisine erişemedim (API anahtarı yok). Yine de buradayım; kısaca ne hakkında konuşmak istersin?"
        # Diğer hatalarda genel fallback:
        return "Sohbet servisine şu an erişemedim ama seninle konuşmaya hazırım. Devam edelim!"

def _rule_based_category(soru_norm: str) -> str:
    """Anahtar kelimelerle hızlı kategori."""
    if any(k in soru_norm for k in FINANS_KW):
        return "finans"
    if "aidat" in soru_norm:
        return "aidat"
    if "sikayet" in soru_norm or "şikayet" in soru_norm:
        return "şikayet"
    return "genel"

from app.models import AISorgu

def _log_ai_sorgu(kullanici_id, soru, cevap, kategori):
    """AI sorgusunu taşınabilir şekilde kaydet (ORM)."""
    kayit = AISorgu(
        kullanici_id=kullanici_id,
        sorgu_metni=soru,
        cevap_metni=cevap,
        sorgu_kategori=kategori,
        yanitlanma_suresi=1.1,
        kullanici_memnuniyeti=None,
        olusturma_tarihi=datetime.utcnow()
    )
    db.session.add(kayit)
    db.session.commit()


def _is_sqlite() -> bool:
    """DB türünü güvenli tespit et (context olsa da olmasa da)."""
    # 1) URI'den anla
    try:
        uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
        if uri:
            return uri.strip().lower().startswith("sqlite")
    except Exception:
        pass
    # 2) Etkin bind üzerinden
    try:
        bind = db.session.get_bind()  # Flask-SQLAlchemy 3.x
        return bool(bind and getattr(bind, "dialect", None) and bind.dialect.name == "sqlite")
    except Exception:
        return False

# --- Ana fonksiyon -----------------------------------------------------------

def akilli_cevap_uret(soru: str, kullanici_id: int):
    """
    Soruya göre (Aidat/Şikayet/Finans/Genel/Sohbet) yanıt üretir.
    Sohbet: '/sohbet:' ile başlarsa veya SOHBET_KW tetiklenirse direkt sohbet.
    """
    kategori = "genel"
    cevap = "Şu an yanıt üretemedim."
    try:
        soru_norm = _tr_normalize(soru).strip()

        # --- 0) Sohbet override (normalize edilmiş kontrol) ------------------
        # '/sohbet:' veya '/sohbet' ile başlayan komutlar
        if soru_norm.startswith("/sohbet"):
            # '/sohbet:' sonrası bölümü al (varsa)
            raw = soru.split(":", 1)
            sohbet_icerigi = raw[1].strip() if len(raw) > 1 else soru
            cevap = _ai_chat_with_fallback(f"Kullanıcı ile serbest sohbet:\n{sohbet_icerigi}")
            kategori = "sohbet"
            _log_ai_sorgu(kullanici_id, soru, cevap, kategori)
            return cevap

        # Sohbet anahtar kelimeleri: 'konuş', 'sohbet', 'chat' vs.
        if any(k in soru_norm for k in SOHBET_KW):
            cevap = _ai_chat_with_fallback(f"Kullanıcı ile serbest sohbet:\n{soru}")
            kategori = "sohbet"
            _log_ai_sorgu(kullanici_id, soru, cevap, kategori)
            return cevap

        # --- 1) Kural tabanlı ön-sınıflandırma ------------------------------
        kategori = _rule_based_category(soru_norm)

        # --- 2) Hâlâ 'genel' ise AI'dan tek kelimelik etiket -----------------
        if kategori == "genel":
            sinif_prompt = (
                "Soru kategorisi: Aidat, Şikayet, Finans, Genel. "
                "SADECE BİRİNİ tek kelime olarak ver.\n"
                "S: Bu ay toplam gider ne kadar? -> Finans\n"
                "S: Aidatımı ödedim mi? -> Aidat\n"
                "S: Komşum gürültü yapıyor. -> Şikayet\n"
                "S: Merhaba. -> Genel\n"
                f"S: {soru}\nCevap:"
            )
            try:
                kat = _safe_ai_call([{"role": "user", "content": sinif_prompt}]).lower().strip().strip(".")
            except RuntimeError:
                # AI etiketleyemezse kural tabanlı sonucu kullan
                kat = "genel"
            if "finans" in kat:
                kategori = "finans"
            elif "aidat" in kat:
                kategori = "aidat"
            elif "şikayet" in kat or "sikayet" in kat:
                kategori = "şikayet"
            else:
                kategori = "genel"

        
        # --- 3) Kategoriye göre yanıt ---------------------------------------
        is_sqlite = _is_sqlite()  # YENİ

        if kategori == "finans":
            # a) "son 3 ay" + "gider" analizi
            if (("son 3 ay" in soru_norm) or ("son uc ay" in soru_norm)) and ("gider" in soru_norm):
                if is_sqlite:
                    sql = text("""
                        SELECT strftime('%Y-%m', tarih) AS ay, SUM(tutar) AS toplam
                        FROM giderler
                        WHERE date(tarih) >= date('now','start of month','-2 months')
                        AND date(tarih) <  date('now','start of month','+1 month')
                        GROUP BY ay
                        ORDER BY ay DESC;
                    """)
                else:
                    sql = text("""
                        WITH son3 AS (
                        SELECT FORMAT(tarih, 'yyyy-MM') AS ay, SUM(tutar) AS toplam
                        FROM dbo.giderler
                        WHERE tarih >= DATEADD(MONTH, -2, DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1))
                            AND tarih <  DATEADD(MONTH,  1, DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1))
                        GROUP BY FORMAT(tarih, 'yyyy-MM')
                        )
                        SELECT ay, toplam FROM son3 ORDER BY ay DESC;
                    """)
                rows = db.session.execute(sql).fetchall() or []
                if not rows:
                    cevap = "Son 3 ay için gider kaydı bulunamadı."
                else:
                    satirlar = "\n".join(f"- {r.ay}: {float(r.toplam or 0):,.2f} TL" for r in rows)
                    cevap = "Son 3 ayın gider analizi:\n" + satirlar

            # b) "bu ay toplam gider ne kadar"
            elif ("bu ay" in soru_norm) and ("gider" in soru_norm) and ("ne kadar" in soru_norm):
                if is_sqlite:
                    sql = text("""
                        SELECT COALESCE(SUM(tutar), 0)
                        FROM giderler
                        WHERE strftime('%Y', tarih) = strftime('%Y', 'now')
                        AND strftime('%m', tarih) = strftime('%m', 'now');
                    """)
                else:
                    sql = text("""
                        SELECT ISNULL(SUM(tutar), 0)
                        FROM dbo.giderler
                        WHERE YEAR(tarih) = YEAR(GETDATE())
                        AND MONTH(tarih) = MONTH(GETDATE());
                    """)
                toplam = db.session.execute(sql).scalar() or 0
                cevap = f"Bu ayın toplam gideri: {float(toplam):,.2f} TL"

            # c) Varsayılan: son 3 ay toplamları
            else:
                if is_sqlite:
                    sql = text("""
                        SELECT strftime('%Y-%m', tarih) AS ay, SUM(tutar) AS toplam
                        FROM giderler
                        GROUP BY ay
                        ORDER BY ay DESC
                        LIMIT 3;
                    """)
                else:
                    sql = text("""
                        SELECT TOP 3 FORMAT(tarih, 'yyyy-MM') AS ay, SUM(tutar) AS toplam
                        FROM dbo.giderler
                        GROUP BY FORMAT(tarih, 'yyyy-MM')
                        ORDER BY ay DESC;
                    """)
                rows = db.session.execute(sql).fetchall() or []
                cevap = ("Finans kaydı bulunamadı." if not rows else
                        "Son 3 ayın gider toplamları:\n" +
                        "\n".join(f"- {r.ay}: {float(r.toplam or 0):,.2f} TL" for r in rows))
                

        elif kategori == "aidat":
            sql = text("SELECT COUNT(*) FROM aidatlar WHERE odendi = 1;") if is_sqlite else \
                text("SELECT COUNT(*) FROM dbo.aidatlar WHERE odendi = 1;")
            sonuc = db.session.execute(sql).scalar() or 0
            cevap = f"Bu ay toplam {sonuc} kişi aidat ödedi."

        elif kategori in ("şikayet", "sikayet"):
            sql = text("SELECT kategori, COUNT(*) AS sayi FROM sikayetler GROUP BY kategori;") if is_sqlite else \
                text("SELECT kategori, COUNT(*) AS sayi FROM dbo.sikayetler GROUP BY kategori;")
            rows = db.session.execute(sql).fetchall() or []
            cevap = ("Kayıtlı şikayet bulunamadı." if not rows
                    else "Şikayet kategorileri:\n" +
                        "\n".join(f"- {r.kategori}: {r.sayi} şikayet" for r in rows))

        else:
            # Genel AI fallback (apartman dışı sorular)
            genel = _ai_chat_with_fallback(f"Kullanıcının serbest sorusu:\n{soru}")
            cevap = genel or "Soruyu aldım, konuşmaya devam edelim!"

        # --- 4) Log ----------------------------------------------------------
        if not cevap:
            cevap = "Şu an yanıt üretemedim."
        _log_ai_sorgu(kullanici_id, soru, cevap, kategori)
        return cevap

    except Exception as e:
        db.session.rollback()
        print("AI Sorgu Hatası:", e)
        print("Soru:", soru)
        print("Gelen kategori:", kategori)
        print("Cevap:", cevap)
        return "❌ Üzgünüm, şu anda akıllı yanıt veremiyorum."




def kaydet_ai_sorgu(kullanici_id, soru, cevap, kategori=None, memnuniyet=None):
    baslangic = time.time()
    # Yapay zekadan cevap alma işlemi burada yapılmış olmalı
    sure = round(time.time() - baslangic, 2)

    yeni_kayit = AISorgu(
        kullanici_id=kullanici_id,
        sorgu_metni=soru,
        cevap_metni=cevap,
        sorgu_kategori=kategori,
        yanitlanma_suresi=sure,
        kullanici_memnuniyeti=memnuniyet,
        olusturma_tarihi=datetime.now()
    )
    db.session.add(yeni_kayit)
    db.session.commit()
