from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from .models import Kullanici, Sikayet, Aidat, Daire, Sakin,Duyurular,AISorgu,AidatDonem,Aidat,Sakin,GiderKategori,Gider,Gelir
from . import db
from ai_helpers import generate_announcement,analyze_complaint_with_ai,kaydet_ai_sorgu,akilli_cevap_uret
from flask_login import login_required
from sqlalchemy.sql import func
from sqlalchemy import text

main = Blueprint('main', __name__)


# Anasayfa yönlendirme
@main.route('/')
def home():
    return redirect(url_for('main.login'))


# Kayıt olma işlemi
@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        ad_soyad = request.form.get('ad_soyad')
        email = request.form.get('email')
        sifre_raw = request.form.get('sifre')
        sifre_tekrar = request.form.get('sifre_tekrar')
        rol = request.form.get('rol')
        telefon = request.form.get('telefon')

        if sifre_raw != sifre_tekrar:
            flash("❌ Şifreler uyuşmuyor.", "danger")
            return redirect(url_for('main.register'))

        var_mi = Kullanici.query.filter_by(email=email).first()
        if var_mi:
            flash("❌ Bu e-posta zaten kayıtlı.", "danger")
            return redirect(url_for('main.register'))

        hashed_password = generate_password_hash(sifre_raw)

        yeni = Kullanici(
            ad_soyad=ad_soyad,
            email=email,
            sifre=hashed_password,
            rol=rol,
            telefon=telefon,
            aktif=True,
            olusturma_tarihi=datetime.now(),
            guncelleme_tarihi=datetime.now()
        )
        db.session.add(yeni)
        db.session.commit()

        flash("✅ Başarıyla kayıt olundu. Şimdi giriş yapabilirsiniz.", "success")
        return redirect(url_for('main.login'))

    return render_template('register.html')


# Giriş işlemi
@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        sifre = request.form['sifre']

        kullanici = Kullanici.query.filter_by(email=email).first()

        if kullanici and check_password_hash(kullanici.sifre, sifre):
            session['kullanici_id'] = kullanici.id
            session['kullanici_adi'] = kullanici.ad_soyad
            session['rol'] = kullanici.rol

            if kullanici.rol == 'yonetici':
                return redirect(url_for('main.dashboard_yonetici'))
            elif kullanici.rol == 'sakin':
                return redirect(url_for('main.dashboard_sakin'))
            else:
                flash("⚠️ Bilinmeyen rol: " + kullanici.rol, "warning")
                return redirect(url_for('main.login'))
        else:
            flash('❌ E-posta veya şifre yanlış.', 'danger')

    return render_template('login.html')


# Çıkış işlemi
@main.route('/logout')
def logout():
    session.clear()
    flash("🚪 Oturum başarıyla kapatıldı.", "info")
    return redirect(url_for('main.login'))


# Genel dashboard yönlendirme
@main.route('/dashboard')
def dashboard():
    if 'kullanici_id' not in session:
        return redirect(url_for('main.login'))

    if session.get('rol') == 'yonetici':
        return redirect(url_for('main.dashboard_yonetici'))
    elif session.get('rol') == 'sakin':
        return redirect(url_for('main.dashboard_sakin'))
    else:
        flash("⚠️ Tanımsız rol.", "danger")
        return redirect(url_for('main.login'))


# Yönetici paneli
@main.route('/dashboard/yonetici')
def dashboard_yonetici():
    if 'kullanici_id' not in session or session.get('rol') != 'yonetici':
        flash("🔒 Bu sayfaya erişiminiz yok.", "warning")
        return redirect(url_for('main.dashboard_sakin'))

    toplam_kullanici = Kullanici.query.count()
    sikayet_sayisi = Sikayet.query.count()
    tahsilat = db.session.query(db.func.sum(Aidat.tutar)).filter_by(odendi=True).scalar() or 0
    aktif_daire = Daire.query.filter_by(aktif=True).count()

    kartlar = [
        {"baslik": "Toplam Kullanıcı", "deger": toplam_kullanici, "renk": "primary", "ikon": "fa-users"},
        {"baslik": "Şikayet Sayısı", "deger": sikayet_sayisi, "renk": "danger", "ikon": "fa-comments"},
        {"baslik": "Toplam Tahsilat", "deger": f"{tahsilat:,.2f}₺", "renk": "success", "ikon": "fa-coins"},
        {"baslik": "Aktif Daire", "deger": aktif_daire, "renk": "info", "ikon": "fa-building"}
    ]

    return render_template("base_dashboard.html", kullanici_adi=session.get('kullanici_adi'), kartlar=kartlar)


# Sakin paneli
@main.route('/dashboard/sakin')
def dashboard_sakin():
    if 'kullanici_id' not in session or session.get('rol') != 'sakin':
        flash("🔒 Bu sayfaya erişiminiz yok.", "warning")
        return redirect(url_for('main.login'))

    kullanici_id = session.get('kullanici_id')

    sakinlik = Sakin.query.filter_by(kullanici_id=kullanici_id, aktif=True).first()
    daire_id = sakinlik.daire_id if sakinlik else None
    daire_no = "-"
    if daire_id:
        daire = Daire.query.get(daire_id)
        if daire:
            daire_no = daire.daire_no

    toplam_sikayet = Sikayet.query.filter_by(sikayetci_id=kullanici_id).count()
    toplam_borc = db.session.query(db.func.sum(Aidat.tutar))\
        .filter_by(daire_id=daire_id, odendi=False).scalar() or 0

    kartlar = [
        {"baslik": "Şikayet Sayım", "deger": toplam_sikayet, "renk": "warning", "ikon": "fa-exclamation-circle"},
        {"baslik": "Ödenmemiş Aidat", "deger": f"{toplam_borc:,.2f}₺", "renk": "danger", "ikon": "fa-money-bill-wave"},
        {"baslik": "Dairem", "deger": daire_no, "renk": "info", "ikon": "fa-door-open"},
        {"baslik": "Son Ödeme", "deger": "2025-07", "renk": "success", "ikon": "fa-calendar-check"}  # örnek veri
    ]

    return render_template("base_dashboard.html", kullanici_adi=session.get('kullanici_adi'), kartlar=kartlar)


# Şifremi unuttum
@main.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        kullanici = Kullanici.query.filter_by(email=email).first()

        if not kullanici:
            flash("❌ Bu e-posta sistemde bulunamadı.", "danger")
            return redirect(url_for('main.forgot_password'))

        flash("✅ Şifre sıfırlama bağlantısı gönderildi (demo).", "success")
        return redirect(url_for('main.reset_password', user_id=kullanici.id))

    return render_template('forgot_password.html')


# Şifre sıfırlama
@main.route('/reset-password/<int:user_id>', methods=['GET', 'POST'])
def reset_password(user_id):
    kullanici = Kullanici.query.get(user_id)
    if not kullanici:
        flash("❌ Geçersiz kullanıcı.", "danger")
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        yeni_sifre = request.form.get('sifre')
        yeni_sifre_tekrar = request.form.get('sifre_tekrar')

        if yeni_sifre != yeni_sifre_tekrar:
            flash("❌ Şifreler uyuşmuyor.", "danger")
            return redirect(url_for('main.reset_password', user_id=user_id))

        kullanici.sifre = generate_password_hash(yeni_sifre)
        kullanici.guncelleme_tarihi = datetime.now()
        db.session.commit()

        flash("✅ Şifreniz başarıyla güncellendi. Şimdi giriş yapabilirsiniz.", "success")
        return redirect(url_for('main.login'))

    return render_template('reset_password.html', kullanici=kullanici)


# Profil bilgileri
@main.route('/profil', methods=['GET', 'POST'])
def profil():
    if 'kullanici_id' not in session:
        return redirect(url_for('main.login'))

    kullanici = Kullanici.query.get(session['kullanici_id'])

    if request.method == 'POST':
        kullanici.ad_soyad = request.form.get('ad_soyad')
        kullanici.telefon = request.form.get('telefon')
        kullanici.guncelleme_tarihi = datetime.now()
        db.session.commit()
        flash("✅ Bilgiler başarıyla güncellendi.", "success")
        return redirect(url_for('main.profil'))

    return render_template('profil.html', kullanici=kullanici)


# Şifre güncelleme
@main.route('/sifre-guncelle', methods=['GET', 'POST'])
def sifre_guncelle():
    if 'kullanici_id' not in session:
        return redirect(url_for('main.login'))

    kullanici = Kullanici.query.get(session['kullanici_id'])

    if request.method == 'POST':
        mevcut_sifre = request.form.get('mevcut_sifre')
        yeni_sifre = request.form.get('yeni_sifre')
        yeni_sifre_tekrar = request.form.get('yeni_sifre_tekrar')

        if not check_password_hash(kullanici.sifre, mevcut_sifre):
            flash("❌ Mevcut şifre yanlış.", "danger")
            return redirect(url_for('main.sifre_guncelle'))

        if yeni_sifre != yeni_sifre_tekrar:
            flash("❌ Yeni şifreler uyuşmuyor.", "danger")
            return redirect(url_for('main.sifre_guncelle'))

        kullanici.sifre = generate_password_hash(yeni_sifre)
        kullanici.guncelleme_tarihi = datetime.now()
        db.session.commit()
        flash("✅ Şifre başarıyla güncellendi.", "success")
        return redirect(url_for('main.profil'))

    return render_template('sifre_guncelle.html')


# Duyurular
@main.route('/ai_duyuru_olustur', methods=['GET', 'POST'])
def ai_duyuru_olustur():
    # Sadece yönetici erişebilir
    if session.get("rol") != "yonetici":
        flash("Bu sayfaya erişim yetkiniz yok.", "danger")
        return redirect(url_for('main.dashboard_sakin'))

    if request.method == 'POST':
        kategori = request.form.get('kategori')
        kisa_aciklama = request.form.get('kisa_aciklama')
        ton = request.form.get('ton')
        ozur = 'Evet' if request.form.get('ozur') else 'Hayır'
        tesekkur = 'Evet' if request.form.get('tesekkur') else 'Hayır'
        action = request.form.get('action')

        # Prompt oluşturma
        prompt = (
            f"Aşağıdaki bilgilerle {kategori} kategorisinde, {ton} tonunda, "
            f"profesyonel bir Türkçe duyuru yaz:\n\n"
            f"- Kısa Açıklama: {kisa_aciklama}\n"
            f"- Özür ifadesi: {ozur}\n"
            f"- Teşekkür ifadesi: {tesekkur}\n\n"
            f"Lütfen sadece Türkçe yaz. Cümle sonlarında veya metin sonunda '[Your Name]', '[Contact Info]', "
            f"'Thanks', 'Best regards' gibi ifadeler kullanma. Düz ve sade bir duyuru metni üret."
        )

        icerik = generate_announcement(prompt).strip()

        if action == 'publish':
            # Veritabanına kaydet
            yeni_duyuru = Duyurular(
                baslik=f"{kategori.capitalize()} Duyurusu",
                icerik=icerik,
                kategori=kategori,
                yazar_id=session.get("kullanici_id"),
                ai_olusturuldu=True,
                goruntulenme_sayisi=0,
                aktif=True,
                yayinlanma_tarihi=datetime.now()
            )
            db.session.add(yeni_duyuru)
            db.session.commit()
            flash("Duyuru başarıyla yayınlandı.", "success")
            return redirect(url_for('main.ai_duyuru_olustur'))

        # Eğer sadece oluşturulmuşsa, göster
        return render_template(
            'duyuru.html',
            duyuru=icerik,
            kategori=kategori,
            kisa_aciklama=kisa_aciklama,
            ton=ton,
            ozur=ozur,
            tesekkur=tesekkur
        )

    return render_template('duyuru.html')

# ✅ Duyuru Listeleme (Her kullanıcı görebilir – login kontrolü var)
@main.route("/duyurular")
def duyurular():
    if 'kullanici_id' not in session:
        flash("🔒 Lütfen giriş yapınız.", "warning")
        return redirect(url_for('main.login'))

    duyurular = Duyurular.query.filter_by(aktif=True).order_by(Duyurular.yayinlanma_tarihi.desc()).all()

    toplam_duyuru = len(duyurular)
    ai_duyuru_sayisi = sum(1 for d in duyurular if d.ai_olusturuldu)
    toplam_goruntulenme = sum(d.goruntulenme_sayisi for d in duyurular)
    bu_ay_eklenen = sum(1 for d in duyurular if d.yayinlanma_tarihi.month == datetime.now().month)

    return render_template("duyurular_liste_sakin.html", 
        duyurular=duyurular,
        toplam_duyuru=toplam_duyuru,
        ai_duyuru_sayisi=ai_duyuru_sayisi,
        toplam_goruntulenme=toplam_goruntulenme,
        bu_ay_eklenen=bu_ay_eklenen,
        rol=session.get('rol'),
        kullanici_adi=session.get('kullanici_adi')
    )


@main.route("/duyuru/<int:id>")
def duyuru_goruntule(id):
    if 'kullanici_id' not in session:
        flash("🔒 Lütfen giriş yapınız.", "warning")
        return redirect(url_for('main.login'))

    duyuru = Duyurular.query.get_or_404(id)
    duyuru.goruntulenme_sayisi += 1
    db.session.commit()

    return render_template("duyuru_detay.html", duyuru=duyuru)

@main.route("/duyuru/duzenle/<int:id>", methods=['GET', 'POST'])
def duyuru_duzenle(id):
    if 'kullanici_id' not in session or session.get('rol') != 'yonetici':
        flash("🚫 Bu işlemi yapma yetkiniz yok.", "danger")
        return redirect(url_for('main.login'))

    duyuru = Duyurular.query.get_or_404(id)

    if request.method == 'POST':
        kategori = request.form.get('kategori', '').strip().lower().replace("ı", "i")

        # Veritabanıyla uyumlu değerler
        GECERLI_KATEGORILER = ['acil', 'guvenlik', 'etkinlik', 'bakim', 'aidat', 'genel']
        if kategori not in GECERLI_KATEGORILER:
            flash("⚠️ Geçersiz kategori seçimi.", "danger")
            return redirect(url_for('main.duyuru_duzenle', id=duyuru.id))

        duyuru.baslik = request.form.get('baslik')
        duyuru.icerik = request.form.get('icerik')
        duyuru.kategori = kategori
        duyuru.guncelleme_tarihi = datetime.now()

        try:
            db.session.commit()
            flash("✅ Duyuru başarıyla güncellendi.", "success")
        except Exception as e:
            db.session.rollback()
            flash("❌ Bir hata oluştu: " + str(e), "danger")

        return redirect(url_for('main.duyurular'))

    return render_template("duyuru_düzenle.html", duyuru=duyuru)

@main.route("/duyuru/sil/<int:id>")
def duyuru_sil(id):
    if 'kullanici_id' not in session or session.get('rol') != 'yonetici':
        flash("🚫 Bu işlemi yapma yetkiniz yok.", "danger")
        return redirect(url_for('main.login'))

    duyuru = Duyurular.query.get_or_404(id)
    db.session.delete(duyuru)
    db.session.commit()
    flash("🗑️ Duyuru silindi.", "success")
    return redirect(url_for('main.duyurular'))

#Şikayet 

@main.route('/sikayet/olustur', methods=['GET', 'POST'])
def sikayet_olustur():
    if 'kullanici_id' not in session or session.get('rol') != 'sakin':
        flash("Sadece sakinler şikayet oluşturabilir.", "danger")
        return redirect(url_for('main.dashboard_yonetici'))

    if request.method == 'POST':
        metin = request.form.get('metin')
        daire_id = request.form.get('daire_id')  # Eğer formda varsa

        if not metin or metin.strip() == "":
            flash("Şikayet metni boş bırakılamaz.", "warning")
            return redirect(url_for('main.sikayet_olustur'))

        # AI ANALİZİ
        ai_sonuc = analyze_complaint_with_ai(metin)
        print("AI Çıktısı:", ai_sonuc)

        # Geçerli değerler
        gecerli_kategoriler = ['diger', 'yonetim', 'guvenlik', 'gurultu', 'temizlik', 'teknik']
        gecerli_oncelikler = ['dusuk', 'orta', 'yuksek']
        gecerli_durumlar = ['bekliyor', 'inceleniyor', 'cozuldu', 'iptal']

        kategori = ai_sonuc.get("kategori", "diger")
        if kategori not in gecerli_kategoriler:
            kategori = "diger"

        oncelik = ai_sonuc.get("oncelik", "orta")
        if oncelik not in gecerli_oncelikler:
            oncelik = "orta"

        durum = ai_sonuc.get("durum", "bekliyor")
        if durum not in gecerli_durumlar:
            durum = "bekliyor"

        # Veritabanına kaydet
        yeni_sikayet = Sikayet(
            sikayetci_id=session['kullanici_id'],
            daire_id=daire_id if daire_id else None,
            metin=metin,
            kategori=kategori,
            oncelik=oncelik,
            durum=durum,
            ai_siniflandirma=True,
            ai_guven_skoru=ai_sonuc.get("guven_skoru", 80),
            cozum_onerisi=ai_sonuc.get("cozum_onerisi", ""),
            olusturma_tarihi=datetime.now(),
            guncelleme_tarihi=datetime.now()
        )
        db.session.add(yeni_sikayet)
        db.session.commit()

        flash("✅ Şikayetiniz yapay zeka tarafından analiz edilip kaydedildi.", "success")
        return redirect(url_for('main.sikayet_grafik'))

    # 📊 Sağ taraftaki kartlar için istatistikler
    toplam_sikayet = Sikayet.query.filter_by(sikayetci_id=session['kullanici_id']).count()
    bekleyen_sikayet = Sikayet.query.filter_by(sikayetci_id=session['kullanici_id'], durum='bekliyor').count()
    cozulen_sikayet = Sikayet.query.filter_by(sikayetci_id=session['kullanici_id'], durum='cozuldu').count()

    return render_template(
        "sikayet_olustur.html",
        toplam_sikayet=toplam_sikayet,
        bekleyen_sikayet=bekleyen_sikayet,
        cozulen_sikayet=cozulen_sikayet
    )


@main.route("/sikayetler")
def sikayetler():
    if 'kullanici_id' not in session or session.get('rol') != 'yonetici':
        flash("🚫 Bu sayfaya erişim izniniz yok.", "danger")
        return redirect(url_for('main.dashboard_sakin'))

    tum_sikayetler = Sikayet.query.order_by(Sikayet.olusturma_tarihi.desc()).all()
    return render_template("sikayetler.html", sikayetler=tum_sikayetler)

@main.route("/sikayet-grafik")
def sikayet_grafik():
    if 'kullanici_id' not in session:
        flash("Lütfen giriş yapın.", "warning")
        return redirect(url_for("main.login"))

    from collections import Counter
    sikayetler = Sikayet.query.all()

    # Kategori ve öncelik dağılımı
    kategoriler = [s.kategori for s in sikayetler]
    oncelikler = [s.oncelik for s in sikayetler]

    kategori_sayilari = dict(Counter(kategoriler))
    oncelik_sayilari = dict(Counter(oncelikler))

    return render_template(
        "sikayet_grafik.html",
        kategori_sayilari=kategori_sayilari,
        oncelik_sayilari=oncelik_sayilari
    )

@main.route("/sikayet/sil/<int:id>", methods=["POST"])
def sikayet_sil(id):
    if 'kullanici_id' not in session or session.get('rol') != 'yonetici':
        flash("🚫 Bu işlem için yetkiniz yok.", "danger")
        return redirect(url_for('main.login'))

    sikayet = Sikayet.query.get_or_404(id)
    db.session.delete(sikayet)
    db.session.commit()
    flash("🗑️ Şikayet başarıyla silindi.", "success")
    return redirect(url_for('main.sikayetler'))

@main.route("/sikayet/guncelle/<int:id>", methods=["GET", "POST"])
def sikayet_guncelle(id):
    if 'kullanici_id' not in session or session.get('rol') != 'yonetici':
        flash("🚫 Bu işlem için yetkiniz yok.", "danger")
        return redirect(url_for('main.login'))

    sikayet = Sikayet.query.get_or_404(id)

    if request.method == 'POST':
        sikayet.durum = request.form.get('durum')
        sikayet.cozum_onerisi = request.form.get('cozum_onerisi')
        sikayet.admin_notu = request.form.get('admin_notu')
        sikayet.guncelleme_tarihi = datetime.now()

        db.session.commit()
        flash("🛠️ Şikayet başarıyla güncellendi.", "success")
        return redirect(url_for('main.sikayetler'))

    return render_template("sikayet_guncelle.html", sikayet=sikayet)

#Akıllı Sorgu

@main.route("/akilli-sorgu", methods=["GET", "POST"])
def akilli_sorgu():
    if "kullanici_id" not in session:
        flash("Bu özelliği kullanmak için lütfen giriş yapın.", "warning")
        return redirect(url_for("main.login"))

    cevap = None
    kullanici_id = session["kullanici_id"]

    if request.method == "POST":
        kullanici_sorusu = request.form.get("soru")
        if kullanici_sorusu:
            try:
                cevap = akilli_cevap_uret(kullanici_sorusu, kullanici_id)
            except Exception as e:
                flash(f"AI Sorgu Hatası: {str(e)}", "danger")

    # SQL üzerinden istatistikleri al
    toplam_sorgu = db.session.query(func.count(AISorgu.id)).scalar() or 0
    ortalama_sure = db.session.query(func.avg(AISorgu.yanitlanma_suresi)).scalar() or 0
    ortalama_memnuniyet = db.session.query(func.avg(AISorgu.kullanici_memnuniyeti)).scalar() or 0
    dogruluk_orani = 94  # Sabit bırakılmış, dinamikleştirilebilir

    return render_template("akilli_sorgu.html",
                           cevap=cevap,
                           toplam_sorgu=toplam_sorgu,
                           ortalama_sure=round(ortalama_sure, 2),
                           ortalama_memnuniyet=round(ortalama_memnuniyet, 1),
                           dogruluk_orani=dogruluk_orani)


#Aidatlar
# routes.py (veya ilgili blueprint dosyan)
from flask import request, session, flash, redirect, url_for, render_template
from sqlalchemy import func, and_
from app import db  # senin proje yapına göre import yolu değişebilir
from app.models import Aidat, AidatDonem, Daire, Kullanici, Sakin  # model yollarını kendi yapına göre düzelt

@main.route("/aidat_takip", methods=["GET"])
def aidat_takip():
    if "kullanici_id" not in session:
        flash("Bu sayfaya erişmek için giriş yapmanız gerekmektedir.", "warning")
        return redirect(url_for("main.login"))

    # Rol kontrolü
    if session.get("rol") != "yonetici":
        flash("Bu sayfaya yalnızca yöneticiler erişebilir.", "danger")
        return redirect(url_for("main.dashboard_yonetici" if session.get("rol") == "yonetici" else "main.dashboard_sakin"))

    secili_donem = request.args.get("donem")

    # Dönem listesi
    donemler = (
        db.session.query(AidatDonem.donem_adi)
        .distinct()
        .order_by(AidatDonem.donem_adi.desc())
        .all()
    )
    donemler = [d[0] for d in donemler]

    # ---- EN GÜNCEL AKTİF SAKİN SUBQUERY ----
    latest_sakin = (
        db.session.query(
            Sakin.daire_id.label("daire_id"),
            func.max(Sakin.baslangic_tarihi).label("max_baslangic")
        )
        .filter(Sakin.aktif == True)
        .group_by(Sakin.daire_id)
        .subquery()
    )

    # ---- ANA SORGU (DOĞRU JOIN ZİNCİRİ) ----
    query = (
        db.session.query(
            Daire.daire_no,
            Kullanici.ad_soyad.label("sakin_adi"),
            Aidat.tutar,
            Aidat.vade_tarihi.label("vade"),
            Aidat.odendi,
            Aidat.odeme_tarihi,
            Aidat.risk_skoru.label("risk"),
            AidatDonem.donem_adi.label("donem")
        )
        .join(Daire, Aidat.daire_id == Daire.id)
        .join(AidatDonem, Aidat.aidat_donem_id == AidatDonem.id)
        # en güncel aktif sakin -> Sakin
        .join(latest_sakin, latest_sakin.c.daire_id == Daire.id)
        .join(
            Sakin,
            and_(
                Sakin.daire_id == latest_sakin.c.daire_id,
                Sakin.baslangic_tarihi == latest_sakin.c.max_baslangic
            )
        )
        # sakin -> kullanıcı
        .join(Kullanici, Kullanici.id == Sakin.kullanici_id)
    )

    if secili_donem:
        query = query.filter(AidatDonem.donem_adi == secili_donem)

    aidatlar = query.order_by(Aidat.vade_tarihi.desc()).all()

    # ---- Özet kartlar ----
    toplam_tutar = sum(a.tutar for a in aidatlar)
    toplam_sayi = len(aidatlar)
    odeme_sayisi = sum(1 for a in aidatlar if a.odendi)
    oran = round((odeme_sayisi / toplam_sayi) * 100, 1) if toplam_sayi else 0

    # ---- Grafik verileri (sadece ödenenler) ----
    chart_query = (
        db.session.query(AidatDonem.donem_adi, func.count().label("adet"))
        .join(Aidat, Aidat.aidat_donem_id == AidatDonem.id)
        .filter(Aidat.odendi == True)
        .group_by(AidatDonem.donem_adi)
        .order_by(AidatDonem.donem_adi)
        .all()
    )
    chart_labels = [x[0] for x in chart_query]
    chart_values = [x[1] for x in chart_query]

    return render_template(
        "aidat_takip.html",
        donemler=donemler,
        secili_donem=secili_donem,
        aidatlar=aidatlar,
        toplam_tutar=toplam_tutar,
        toplam_sayi=toplam_sayi,
        odeme_sayisi=odeme_sayisi,
        oran=oran,
        chart_labels=chart_labels,
        chart_values=chart_values
    )

# Aidat Ödeme

@main.route("/aidat_odeme", methods=["GET", "POST"])
def aidat_odeme():
    if "kullanici_id" not in session:
        flash("Giriş yapmanız gerekiyor.", "warning")
        return redirect(url_for("main.login"))

    if session.get("rol") != "sakin":
        flash("Bu sayfaya yalnızca sakinler erişebilir.", "danger")
        return redirect(url_for("main.dashboard_yonetici"))

    kullanici_id = session["kullanici_id"]

    # Kullanıcının aktif sakin kaydını al
    sakin_kaydi = Sakin.query.filter_by(kullanici_id=kullanici_id, aktif=True).first()
    if not sakin_kaydi:
        flash("Sistemde aktif daire kaydınız bulunamadı.", "danger")
        return redirect(url_for("main.dashboard_sakin"))

    daire = sakin_kaydi.daire
   
    
    # Bu daireye ait ödenmemiş aidatları listele
    odenmemis_aidatlar = Aidat.query.filter_by(daire_id=daire.id, odendi=False).all()

    if request.method == "POST":
        aidat_id = request.form.get("aidat_id")
        aidat = Aidat.query.get(aidat_id)

        if aidat and aidat.daire_id == daire.id:
            aidat.odendi = True
            aidat.odeme_tarihi = datetime.now()
            db.session.commit()
            flash("Aidat ödemeniz başarıyla kaydedildi.", "success")
            return redirect(url_for("main.aidat_odeme"))
        else:
            flash("Geçersiz aidat işlemi.", "danger")

    return render_template("aidat_ödeme.html", aidatlar=odenmemis_aidatlar)

@main.route("/aidat/mail_goster")
def mail_goster():
    odemeyenler = db.session.query(Kullanici.email, Kullanici.ad_soyad, Aidat.tutar, Aidat.vade_tarihi)\
        .join(Sakin, Sakin.kullanici_id == Kullanici.id)\
        .join(Aidat, Aidat.daire_id == Sakin.daire_id)\
        .filter(Aidat.odendi == False).all()

    if not odemeyenler:
        flash("📭 Ödenmemiş aidat bulunamadı.", "info")
    else:
        for email, ad_soyad, tutar, vade in odemeyenler:
            mesaj = f"📧 {ad_soyad} ({email}) kişisine {vade.strftime('%Y-%m-%d')} son ödemeli {tutar}₺ aidat hatırlatma maili gönderildi (simülasyon)."
            flash(mesaj, "success")

    return redirect(url_for("main.aidat_odeme"))  # bu fonksiyonun ismine göre ayarla

#Gelir Gider
from sqlalchemy import text

from collections import defaultdict
from datetime import datetime

@main.route("/gelir_gider")
def gelir_gider():
    # Kayıtları çek (kendi model adlarını kullan)
    gelirler = Gelir.query.order_by(Gelir.tarih.asc()).all()
    giderler = Gider.query.order_by(Gider.tarih.asc()).all()

    # Aylık toplama: YYYY-MM anahtar
    gelir_ay_toplam = defaultdict(float)
    gider_ay_toplam = defaultdict(float)
    aylar_set = set()

    def key_for(dt):
        # dt datetime/date olabilir; string ise parse et
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt)
            except Exception:
                # Son çare: ilk 7 karakter YYYY-MM biçiminde bekleniyorsa:
                return dt[:7]
        return dt.strftime("%Y-%m")

    for g in gelirler:
        k = key_for(g.tarih)
        gelir_ay_toplam[k] += float(g.tutar or 0)
        aylar_set.add(k)

    for gd in giderler:
        k = key_for(gd.tarih)
        gider_ay_toplam[k] += float(gd.tutar or 0)
        aylar_set.add(k)

    # Tüm ayları birleşik ve sıralı (kronolojik)
    aylar = sorted(aylar_set)  # "YYYY-MM" sıralaması kronolojiktir

    # Grafiğe giden diziler (aylar ile aynı sırada)
    gelir_seri = [round(gelir_ay_toplam.get(a, 0), 2) for a in aylar]
    gider_seri = [round(gider_ay_toplam.get(a, 0), 2) for a in aylar]

    # Kartlar vs. için toplamlar
    toplam_gelir = round(sum(gelir_seri), 2)
    toplam_gider = round(sum(gider_seri), 2)
    net_bakiye = round(toplam_gelir - toplam_gider, 2)

    # Tablo verilerinizi zaten template’e kommunike ediyorsunuz:
    return render_template(
        "gelir_gider.html",
        aylar=aylar,
        gelir_seri=gelir_seri,
        gider_seri=gider_seri,
        toplam_gelir=toplam_gelir,
        toplam_gider=toplam_gider,
        net_bakiye=net_bakiye,
        gelirler=gelirler,
        giderler=giderler
    )


@main.route("/gelir_gider/ekle", methods=["GET", "POST"])
def gider_ekle():
    if "kullanici_id" not in session:
        flash("Giriş yapmanız gerekiyor.", "warning")
        return redirect(url_for("main.login"))

    if session.get("rol") != "yonetici":
        flash("Bu işlem için yetkiniz yok!", "danger")
        return redirect(url_for("main.gelir_gider"))

    kullanici_id = session["kullanici_id"]
    ai_risk_skoru = request.form.get("ai_risk_skoru") or None

    if request.method == "POST":
        gider = Gider(
        kategori_id=request.form["kategori_id"],
        aciklama=request.form["aciklama"],
        tutar=request.form["tutar"],
        tarih=request.form["tarih"],
        fatura_no=request.form.get("fatura_no"),
        tedarikci=request.form.get("tedarikci"),
        ai_risk_skoru=request.form.get("ai_risk_skoru"),  # 'Yüksek', 'Normal', 'Düşük' olmalı
        onay_durumu="onaylandi",  # küçük harfli olmalı
        onayi_veren_id=kullanici_id
    )

        db.session.add(gider)
        db.session.commit()
        flash("✅ Gider başarıyla eklendi.", "success")
        return redirect(url_for("main.gelir_gider"))

    kategoriler = GiderKategori.query.filter_by(aktif=True).all()
    return render_template("gider_ekle.html", kategoriler=kategoriler)

@main.route("/gelir/ekle", methods=["GET", "POST"])
def gelir_ekle():
    if session.get("rol") != "yonetici":
        flash("Bu işlem için yetkiniz yok!", "danger")
        return redirect(url_for("main.gelir_gider"))

    kullanici_id = session["kullanici_id"]

    if request.method == "POST":
        gelir = Gelir(
            aciklama=request.form["aciklama"],
            tutar=request.form["tutar"],
            tarih=request.form["tarih"],
            gelir_kaynak=request.form["gelir_kaynak"],
            onay_durumu="Onaylandı",
            onayi_veren_id=kullanici_id
        )
        db.session.add(gelir)
        db.session.commit()
        flash("Gelir başarıyla eklendi.", "success")
        return redirect(url_for("main.gelir_gider"))

    return render_template("gelir_ekle.html")

@main.route("/gider/sil/<int:id>")
def gider_sil(id):
    if session.get("rol") != "yonetici":
        flash("Bu işlem için yetkiniz yok!", "danger")
        return redirect(url_for("main.gelir_gider"))

    gider = Gider.query.get_or_404(id)
    db.session.delete(gider)
    db.session.commit()
    flash("Gider başarıyla silindi.", "success")
    return redirect(url_for("main.gelir_gider"))

@main.route("/gelir/sil/<int:id>")
def gelir_sil(id):
    if session.get("rol") != "yonetici":
        flash("Bu işlem için yetkiniz yok!", "danger")
        return redirect(url_for("main.gelir_gider"))

    gelir = Gelir.query.get_or_404(id)
    db.session.delete(gelir)
    db.session.commit()
    flash("Gelir başarıyla silindi.", "success")
    return redirect(url_for("main.gelir_gider"))

@main.route("/gider/duzenle/<int:id>", methods=["GET", "POST"])
def gider_duzenle(id):
    if session.get("rol") != "yonetici":
        flash("Bu işlem için yetkiniz yok!", "danger")
        return redirect(url_for("main.gelir_gider"))

    gider = Gider.query.get_or_404(id)
    kategoriler = GiderKategori.query.filter_by(aktif=True).all()
    

    if request.method == "POST":
        gider.kategori_id = request.form["kategori_id"]
        gider.aciklama = request.form["aciklama"]
        gider.tutar = request.form["tutar"]
        gider.tarih = request.form["tarih"]
        gider.fatura_no = request.form.get("fatura_no")
        gider.tedarikci = request.form.get("tedarikci")
        gider.ai_risk_skoru = request.form.get("ai_risk_skoru") or None

        db.session.commit()
        flash("✅ Gider başarıyla güncellendi.", "success")
        return redirect(url_for("main.gelir_gider"))

    return render_template("gider_duzenle.html", gider=gider, kategoriler=kategoriler)

@main.route("/gelir/duzenle/<int:id>", methods=["GET", "POST"])
def gelir_duzenle(id):
    if session.get("rol") != "yonetici":
        flash("Bu işlem için yetkiniz yok!", "danger")
        return redirect(url_for("main.gelir_gider"))

    gelir = Gelir.query.get_or_404(id)

    if request.method == "POST":
        gelir.aciklama = request.form["aciklama"]
        gelir.tutar = request.form["tutar"]
        gelir.tarih = request.form["tarih"]
        gelir.gelir_kaynak = request.form["gelir_kaynak"]
        gelir.onay_durumu = "onayli"  # veritabanına uygun olacak şekilde küçük harf

        db.session.commit()
        flash("✅ Gelir başarıyla güncellendi.", "success")
        return redirect(url_for("main.gelir_gider"))

    return render_template("gelir_duzenle.html", gelir=gelir)
