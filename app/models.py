from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Kullanici(db.Model):
    __tablename__ = 'kullanicilar'
    id = db.Column(db.Integer, primary_key=True)
    ad_soyad = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    sifre = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False)
    telefon = db.Column(db.String(20), nullable=True)
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now)

class Daire(db.Model):
    __tablename__ = 'daireler'
    id = db.Column(db.Integer, primary_key=True)
    daire_no = db.Column(db.String(10), unique=True, nullable=False)
    blok = db.Column(db.String(5))
    kat = db.Column(db.Integer)
    daire_tipi = db.Column(db.String(20))
    metrekare = db.Column(db.Numeric(8, 2))
    aidat_katsayisi = db.Column(db.Numeric(4, 2), default=1.0)
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)


class Sikayet(db.Model):
    __tablename__ = 'sikayetler'
    id = db.Column(db.Integer, primary_key=True)
    sikayetci_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'))
    daire_id = db.Column(db.Integer, db.ForeignKey('daireler.id'))  # FK bağlantısı

    metin = db.Column(db.Text, nullable=False)
    kategori = db.Column(db.String(20), nullable=False, default="diger")
    oncelik = db.Column(db.String(10), nullable=False, default="orta")
    durum = db.Column(db.String(20), nullable=False, default="bekliyor")

    ai_siniflandirma = db.Column(db.Boolean, default=False)
    ai_guven_skoru = db.Column(db.Integer, nullable=True)
    cozum_onerisi = db.Column(db.Text, nullable=True)
    admin_notu = db.Column(db.Text, nullable=True)

    cozum_tarihi = db.Column(db.Date, nullable=True)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    kullanici = db.relationship('Kullanici', backref='sikayetler', foreign_keys=[sikayetci_id])
    daire = db.relationship('Daire', backref='sikayetler')

class Aidat(db.Model):
    __tablename__ = 'aidatlar'

    id = db.Column(db.Integer, primary_key=True)
    daire_id = db.Column(db.Integer, db.ForeignKey('daireler.id'), nullable=False)
    aidat_donem_id = db.Column(db.Integer, db.ForeignKey('aidat_donemleri.id'), nullable=False)
    tutar = db.Column(db.Float, nullable=False)
    vade_tarihi = db.Column(db.Date, nullable=False)
    odendi = db.Column(db.Boolean, default=False)
    odeme_tarihi = db.Column(db.Date, nullable=True)
    risk_skoru = db.Column(db.String(10), nullable=True)
    aciklama = db.Column(db.String(10), nullable=True)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    # İlişkiler
    daire = db.relationship('Daire', backref='aidatlar')
    donem = db.relationship('AidatDonem', backref='aidatlar')


class Duyurular(db.Model):
    __tablename__ = 'duyurular'
    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(200), nullable=False)
    icerik = db.Column(db.Text, nullable=False)
    kategori = db.Column(db.String(20), nullable=False)
    yazar_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'), nullable=False)
    ai_olusturuldu = db.Column(db.Boolean, default=False)
    goruntulenme_sayisi = db.Column(db.Integer, default=0)
    yayinlanma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.utcnow)
    aktif = db.Column(db.Boolean, default=True)

class AISorgu(db.Model):
    __tablename__ = 'ai_sorgulari'

    id = db.Column(db.Integer, primary_key=True)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'), nullable=False)
    sorgu_metni = db.Column(db.Text, nullable=False)
    cevap_metni = db.Column(db.Text)
    sorgu_kategori = db.Column(db.String(50))
    yanitlanma_suresi = db.Column(db.Numeric(5, 2))  # Örnek: 1.25 saniye
    kullanici_memnuniyeti = db.Column(db.Integer)     # 1-5 arası puanlama
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)

class AidatDonem(db.Model):
    __tablename__ = "aidat_donemleri"

    id = db.Column(db.Integer, primary_key=True)
    yil = db.Column(db.Integer, nullable=False)
    ay = db.Column(db.Integer, nullable=False)
    donem_adi = db.Column(db.String(20), nullable=False)  # Örn: "2024-07"
    temel_aidat = db.Column(db.Numeric(10, 2), nullable=False)
    son_odeme_tarihi = db.Column(db.Date, nullable=False)
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime)

class Sakin(db.Model):
    __tablename__ = 'sakinler'

    id = db.Column(db.Integer, primary_key=True)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'), nullable=False)
    daire_id = db.Column(db.Integer, db.ForeignKey('daireler.id'), nullable=False)
    baslangic_tarihi = db.Column(db.Date)
    bitis_tarihi = db.Column(db.Date)
    sahip_mi = db.Column(db.Boolean)
    aktif = db.Column(db.Boolean)

    daire = db.relationship("Daire", backref="sakinlikler")
    kullanici = db.relationship("Kullanici", backref="sakinlikler")

class GiderKategori(db.Model):
    __tablename__ = "gider_kategorileri"
    id = db.Column(db.Integer, primary_key=True)
    kod = db.Column(db.String(20), nullable=False)
    ad = db.Column(db.String(50), nullable=False)
    aciklama = db.Column(db.Text)
    aktif = db.Column(db.Boolean)

    giderler = db.relationship('Gider', backref='kategori', lazy=True)


class Gider(db.Model):
    __tablename__ = "giderler"
    id = db.Column(db.Integer, primary_key=True)
    kategori_id = db.Column(db.Integer, db.ForeignKey('gider_kategorileri.id'), nullable=False)
    aciklama = db.Column(db.String(200), nullable=False)
    tutar = db.Column(db.Numeric(12, 2), nullable=False)
    tarih = db.Column(db.Date, nullable=False)
    fatura_no = db.Column(db.String(50))
    tedarikci = db.Column(db.String(100))
    ai_risk_skoru = db.Column(db.String(10))
    onay_durumu = db.Column(db.String(20))
    onayi_veren_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'))
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Gelir(db.Model):
    __tablename__ = 'gelirler'

    id = db.Column(db.Integer, primary_key=True)
    aciklama = db.Column(db.String(200), nullable=False)
    tutar = db.Column(db.Numeric(12, 2), nullable=False)
    tarih = db.Column(db.Date, nullable=False)
    gelir_kaynak = db.Column(db.String(100))
    onay_durumu = db.Column(db.String(20))
    onayi_veren_id = db.Column(db.Integer, db.ForeignKey("kullanicilar.id"))
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.now)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.now)

    onaylayan = db.relationship("Kullanici", foreign_keys=[onayi_veren_id])
