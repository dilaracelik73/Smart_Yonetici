# 🧠🏢 SmartYönetici — Bina Yönetim Sistemi (Flask)

**SmartYönetici**, apartman/site yönetimleri için geliştirilmiş **Flask tabanlı** bir web uygulamasıdır.  
Aidat takibi, duyuru yönetimi, şikayet yönetimi, gelir-gider ve **AI destekli** akıllı modüller içerir.  
Roller: **Yönetici** ve **Sakin**


## ✨ Özellikler
- 🔐 Rol bazlı giriş: Yönetici / Sakin
- 💸 Aidat takibi: ödeme geçmişi, yönetici için toplu görünüm
- 📣 Duyurular: AI destekli duyuru üretimi, sakin yorumları (onaylı)
- 🧾 Gelir-Gider: yönetici ekler/düzenler, herkes görüntüler
- 📮 Şikayetler: sakin oluşturur, AI ile sınıflandırma, yönetici yönetir
- 🔎 Akıllı Sorgu: doğal dille SQL verilerinden özet
- 🌙 Kalıcı dark mode, modern arayüz
- 🗃️ Veritabanı: SQLite (lokal), opsiyonel PostgreSQL


## 📂 Dizin Yapısı
```
Smart_Yonetici/
├─ app/ # Uygulama modülleri, blueprint, templates, static
├─ tools/ # Yardımcı scriptler
├─ ai_helpers.py # AI entegrasyonu
├─ config.py # Konfigürasyon
├─ run.py # Başlatma dosyası
├─ requirements.txt
├─ .env.example
└─ app.db
```


## ⚙️ Kurulum
```bash
git clone https://github.com/dilaracelik73/Smart_Yonetici.git
cd Smart_Yonetici
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

🔐 .env Örneği
FLASK_ENV=development
SECRET_KEY=super_secret_key
DATABASE_URL=sqlite:///app.db
# AI entegrasyonu (opsiyonel)
OPENROUTER_API_KEY=...
GEMINI_API_KEY=...

▶️ Çalıştırma
# Flask CLI
export FLASK_APP=run.py
flask run --port 5000

# veya
python run.py
```
## 🔗 Örnek Rotalar

### 👤 Kimlik & Yetki
| Metot | Yol              | Açıklama             |
|-------|------------------|----------------------|
| POST  | `/auth/login`    | Kullanıcı girişi     |
| POST  | `/auth/register` | Yeni kullanıcı kaydı |
| GET   | `/auth/logout`   | Oturum kapatma       |

### 📊 Dashboard
| Metot | Yol                   | Açıklama             |
|-------|-----------------------|----------------------|
| GET   | `/dashboard/yonetici` | Yönetici paneli      |
| GET   | `/dashboard/sakin`    | Sakin paneli         |

### 💸 Aidat
| Metot | Yol                | Açıklama                      |
|-------|--------------------|-------------------------------|
| GET   | `/aidat/mine`      | Sakin – kendi ödemelerini gör |
| GET   | `/aidat/all`       | Yönetici – tüm ödemeler       |
| GET   | `/aidat/export.csv`| CSV dışa aktarım              |

### 📣 Duyurular
| Metot  | Yol                     | Açıklama                          |
|--------|-------------------------|-----------------------------------|
| GET    | `/duyurular`            | Duyuruları listele                 |
| POST   | `/duyurular`            | Yeni duyuru (Yönetici)             |
| PUT    | `/duyurular/:id`        | Duyuru güncelle (Yönetici)         |
| DELETE | `/duyurular/:id`        | Duyuru sil (Yönetici)              |
| POST   | `/duyurular/:id/yorum`  | Sakin yorumu (onaylı yayına alınır)|

### 📮 Şikayetler
| Metot | Yol             | Açıklama                    |
|-------|-----------------|-----------------------------|
| GET   | `/sikayet`      | Şikayetleri listele         |
| POST  | `/sikayet`      | Yeni şikayet oluştur (Sakin)|
| PUT   | `/sikayet/:id`  | Durum/etiket güncelle       |

### 🧾 Gelir-Gider
| Metot | Yol               | Açıklama                         |
|-------|-------------------|----------------------------------|
| GET   | `/gelir-gider`    | Gelir-giderleri listele           |
| POST  | `/gelir-gider`    | Yeni gelir/gider (Yönetici)       |
| PUT   | `/gelir-gider/:id`| Güncelle (Yönetici)              |

### 🤖 Akıllı Sorgu
| Metot | Yol         | Açıklama                           |
|-------|-------------|------------------------------------|
| POST  | `/ai/query` | Doğal dil → SQL verisinden özet    |



## 🤝 Katkı

Katkılar memnuniyetle kabul edilir!
- Fork’la
- Branch aç: feature/isim
- Değişikliklerini yap + test et
- PR aç: değişiklik özetini ve nedenini yaz

## 📜 Lisans
MIT © 2025 Dilara Çelik
