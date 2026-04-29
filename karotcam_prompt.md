# KarotCam MVP — Claude Code Master Prompt

Sen bir mineral exploration drilling operations için karot fotoğraflama uygulaması geliştireceksin. Bu, ticari **Imago Petcore** ürününe açık kaynak ve özelleştirilmiş bir alternatiftir. Saha jeoloji ekibi tarafından Türkiye ve Fas'taki maden sahalarında günlük olarak kullanılacak.

## Proje Adı
CoreZen

## Kullanıcı Bağlamı
- **Birincil kullanıcı:** Saha operatörü (driller veya jeolog asistanı)
- **Saha:** ESAN Eczacıbaşı Balya Kurşun-Çinko Madeni (Türkiye), ileride Drillon JEMAS Maroc operasyonları
- **Dil:** Türkçe arayüz (sonradan EN/FR eklenecek, i18n hazır olsun)
- **Donanım:** Saha laptopu (Windows 10/11, 8-16GB RAM), Nikon Z5 + 24-70mm lens, sabit fotoğraf ünitesi (sehpa+aydınlatma), USB 3.0 kablo
- **Mevcut durum:** Operatörler şu an SD karttan manuel transfer + manuel isimlendirme yapıyor — bu çok yavaş ve hata yapıyor

## Hedef
Karot kutusu fotoğraflama iş akışını uçtan uca otomatize etmek:
1. Kamera tetikleme (uzaktan, klavye kısayolu)
2. Otomatik dosya transferi (SD karta gerek yok)
3. Kuyu/kutu/derinlik bilgisiyle otomatik isimlendirme
4. Geometrik düzeltme (perspektif + lens distortion)
5. Ölçek kalibrasyonu (mm/pixel)
6. Kuru/ıslak fotoğraf eşleştirme
7. Multi-shot panorama stitching
8. Galeri ve dışa aktarma

## Teknoloji Yığını (KESİN, değiştirme)
- **Dil:** Python 3.11+
- **GUI:** PyQt6
- **Kamera kontrolü:** digiCamControl (Windows servisi, HTTP REST API üzerinden)
  - Base URL: `http://localhost:5513`
  - Komut formatı: `GET /?slc=<command>&param1=<p1>&param2=<p2>`
  - Anahtar komutlar: `capture`, `set` (iso/shutter/aperture/session.folder/session.filenametemplate), `get` (status), `liveview`
- **Veritabanı:** SQLite (lokal, `karotcam.db` dosyası)
- **Görüntü işleme:** OpenCV (cv2), Pillow, scikit-image (stitching için)
- **HTTP:** requests
- **Paketleme:** PyInstaller (tek .exe çıktısı için, ileride)

## Teknoloji Yığını Notları
- digiCamControl Z5'i destekler ama kullanıcının makinesinde HENÜZ KURULU DEĞİL — README'de kurulum talimatı ver
- libgphoto2 Windows'ta resmi destek vermiyor, KULLANMA
- Nikon NMSDK NDA gerektiriyor, KULLANMA
- Sadece digiCamControl HTTP API ile ilerle

## Mimari Katmanlar

```
┌─────────────────────────────────────────────┐
│  PyQt6 GUI (TR arayüz, i18n hazır)          │
├─────────────────────────────────────────────┤
│  İş Mantığı (Python sınıfları)              │
│  - ProjectManager, HoleManager, BoxManager  │
│  - CaptureService, ImageProcessor           │
│  - CalibrationManager                        │
├─────────────────────────────────────────────┤
│  Veri Katmanı (SQLite + dosya sistemi)      │
├─────────────────────────────────────────────┤
│  Entegrasyonlar:                             │
│  - DigiCamControl HTTP wrapper               │
│  - OpenCV görüntü işleme                     │
└─────────────────────────────────────────────┘
```

## Veri Modeli (SQLite şeması)

```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    ad TEXT NOT NULL,
    sirket TEXT,           -- ESAN, Drillon, JEMAS Maroc...
    konum TEXT,
    baslangic_tarihi DATE,
    olusturma DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE holes (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    kuyu_adi TEXT NOT NULL,         -- BLY-2024-156
    tip TEXT,                        -- DDH/RC/Sonic
    planlanan_uzunluk REAL,
    durum TEXT DEFAULT 'aktif',
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE boxes (
    id INTEGER PRIMARY KEY,
    hole_id INTEGER NOT NULL,
    kutu_no INTEGER NOT NULL,
    derinlik_baslangic REAL NOT NULL,
    derinlik_bitis REAL NOT NULL,
    kutu_tipi TEXT,                  -- HQ/NQ/PQ
    foto_durumu TEXT DEFAULT 'beklemede',
    olusturma DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hole_id) REFERENCES holes(id),
    UNIQUE(hole_id, kutu_no)
);

CREATE TABLE photos (
    id INTEGER PRIMARY KEY,
    box_id INTEGER NOT NULL,
    dosya_yolu TEXT NOT NULL,
    foto_tipi TEXT NOT NULL,         -- kuru/islak/panorama
    cekim_tarihi DATETIME,
    kamera_ayarlari_json TEXT,       -- ISO, shutter, aperture
    duzeltme_uygulandi INTEGER DEFAULT 0,
    duzeltilmis_yol TEXT,
    olcek_mm_per_pixel REAL,
    FOREIGN KEY (box_id) REFERENCES boxes(id)
);

CREATE TABLE calibrations (
    id INTEGER PRIMARY KEY,
    ad TEXT NOT NULL,
    kamera_modeli TEXT,
    lens_modeli TEXT,
    mesafe_cm REAL,
    perspektif_matrisi_json TEXT,    -- 3x3 homography
    distortion_coefs_json TEXT,      -- k1,k2,p1,p2,k3
    camera_matrix_json TEXT,         -- 3x3 intrinsic
    olcek_mm_per_pixel REAL,
    olusturma DATETIME DEFAULT CURRENT_TIMESTAMP,
    aktif INTEGER DEFAULT 0
);
```

## Klasör Yapısı

```
karotcam/
├── main.py                    # Giriş noktası
├── config.py                  # Sabitler, yollar
├── requirements.txt
├── README.md                  # Kurulum talimatı (digiCamControl dahil)
├── karotcam.db               # SQLite (runtime'da oluşur)
├── data/
│   ├── photos/
│   │   ├── raw/              # digiCamControl'den gelen ham
│   │   ├── corrected/        # Geometrik düzeltme sonrası
│   │   └── panoramas/        # Stitching çıktıları
│   └── calibrations/         # Kalibrasyon referans fotoğrafları
├── karotcam/
│   ├── __init__.py
│   ├── camera/
│   │   ├── __init__.py
│   │   ├── digicam_client.py     # HTTP API wrapper
│   │   └── capture_service.py    # Çekim iş mantığı
│   ├── db/
│   │   ├── __init__.py
│   │   ├── schema.py             # CREATE TABLE
│   │   ├── models.py             # Project, Hole, Box, Photo dataclass
│   │   └── repository.py         # CRUD operasyonları
│   ├── imaging/
│   │   ├── __init__.py
│   │   ├── calibration.py        # Satranç tahtası tabanlı kalibrasyon
│   │   ├── corrections.py        # Perspektif + distortion
│   │   ├── stitching.py          # Multi-shot panorama
│   │   └── scale.py              # mm/pixel hesaplama
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   ├── widgets/
│   │   │   ├── live_view.py
│   │   │   ├── hole_selector.py
│   │   │   ├── box_form.py
│   │   │   ├── gallery.py
│   │   │   └── calibration_dialog.py
│   │   └── i18n/
│   │       ├── tr.json
│   │       └── en.json
│   └── utils/
│       ├── filename.py           # İsim üretici
│       └── logger.py
└── tests/
    ├── test_filename.py
    ├── test_calibration.py
    └── test_repository.py
```

## Saha İş Akışı (UX)

1. **Uygulama açılır** → digiCamControl bağlantısı kontrol edilir, Z5 tanınır mı?
2. **Proje seç** → mevcut projelerden seç veya yeni oluştur
3. **Kuyu seç** → mevcut aktif kuyulardan seç veya yeni gir (BLY-2024-156 formatı)
4. **Kalibrasyon kontrolü** → bu kamera+lens için aktif kalibrasyon var mı? Yoksa kullanıcıyı kalibrasyon sihirbazına yönlendir (satranç tahtası + cetvel ile)
5. **Sıradaki kutu öneriş** → son kutudan +1, derinlik aralığı son bitiş+0
6. **Live view** → operatör çerçeveler, fotoğraf ünitesini ayarlar
7. **Çekim** → SPACE tuşu = kuru fotoğraf, sonra ISLAK tuşu = ıslatılmış fotoğraf
8. **Otomatik isim:** `BLY-2024-156_K0023_145.20-148.50_KURU_20260429-1430.jpg`
9. **Otomatik düzeltme** → arka planda perspektif + distortion düzeltilir
10. **Galeride önizleme** → operatör onaylar veya yeniden çeker
11. **Sıradaki kutu** → süreç tekrarlanır

## Kritik UX Detayları

- Klavye kısayolları (saha operatörü mouse kullanmaz):
  - `SPACE` = Kuru fotoğraf çek
  - `W` = Islak fotoğraf çek
  - `ENTER` = Sıradaki kutuya geç
  - `R` = Son fotoğrafı sil ve yeniden çek
  - `S` = Stitching modu (multi-shot başlat)
- Büyük yazı tipi (saha gözlüklü/eldivenli kullanım)
- Yüksek kontrast tema (dış ışık altında okunabilirlik)
- Her aksiyondan sonra büyük yeşil/kırmızı ikon ile geribildirim
- Hata durumunda Türkçe net mesaj (stack trace gizle)

## İsimlendirme Şablonu

`{KUYU_ADI}_K{KUTU_NO_4DIGIT}_{DER_BAS}-{DER_BIT}_{TIP}_{TARIH}-{SAAT}.jpg`

Örnek: `BLY-2024-156_K0023_145.20-148.50_KURU_20260429-1430.jpg`

- KUYU_ADI: harfler+sayılar+tire
- KUTU_NO: 4 haneli (0001, 0023, 0156)
- DER_BAS / DER_BIT: 2 ondalık (145.20)
- TIP: KURU / ISLAK / PANO
- TARIH-SAAT: YYYYMMDD-HHMM

## Geometrik Düzeltme Akışı

1. **Kalibrasyon (1 kez, kurulum sonrası):**
   - Operatör 9x6 satranç tahtası + cetvel referansını fotoğraflar (5-10 kare farklı açı)
   - OpenCV `cv2.calibrateCamera` ile intrinsic matrix + distortion coefs
   - Sonra düz bir referans (kalibrasyon levhası) fotoğrafı çekilir
   - 4 köşesi tıklanarak perspektif homography çıkarılır
   - Cetvelin bilinen mesafesi tıklanarak mm/pixel ölçeği bulunur
   - Tüm bu profil `calibrations` tablosuna kaydedilir, "aktif" işaretlenir

2. **Her çekim sonrası (otomatik):**
   - `cv2.undistort` → lens distortion düzelt
   - `cv2.warpPerspective` → perspektifi düzelt (kuş bakışı)
   - Düzeltilmiş fotoğraf `data/photos/corrected/` altına yazılır
   - DB'de `duzeltme_uygulandi=1`, `duzeltilmis_yol`, `olcek_mm_per_pixel` doldurulur

## MVP Kapsamı (Faz 1 — bu prompt için)

✅ Yapılacaklar:
- digiCamControl bağlantı kontrolü ve Z5 tetikleme
- Live view streaming (MJPEG)
- Proje/kuyu/kutu CRUD
- Otomatik isimlendirme
- Kalibrasyon sihirbazı (satranç tahtası tabanlı)
- Otomatik perspektif + distortion düzeltme
- Kuru/ıslak çift çekim ve eşleştirme
- Galeri (kutu bazlı, küçük resim ızgarası)
- Multi-shot panorama stitching (OpenCV Stitcher)
- Excel/CSV dışa aktarma (kuyu özeti)

❌ Bu fazda YAPMA (v2'ye bırak):
- Bulut sync (Supabase)
- Çok kullanıcı desteği
- AI tabanlı RQD/TCR tespiti
- Mobil görüntüleme
- SAP entegrasyonu

## Kalite Beklentileri

- **Test kapsamı:** İsim üretici, kalibrasyon math, repository CRUD için pytest
- **Loglama:** `logging` modülü, `data/logs/` altına gün bazlı dosya
- **Hata yönetimi:** Try/except + kullanıcıya Türkçe hata mesajı, asla traceback gösterme
- **Offline güvenilirlik:** Hiçbir kritik özellik internete bağımlı olmasın
- **Yeniden başlatma:** Çekim sırasında kapatılırsa hangi kutuda kaldığını hatırlasın
- **Performans:** Live view en az 15 fps, çekimden galeride önizlemeye kadar <3 saniye

## Güvenlik / Veri Bütünlüğü

- SQLite WAL modu aktif olsun (eşzamanlı okuma için)
- Her gece SQLite dosyası `data/backups/` altına kopyalansın (uygulama açılışında)
- Fotoğraflar SADECE `data/photos/` altına yazılsın, başka yere asla
- Dosya silme YOK (sadece "iptal" işareti DB'de)

## README.md İçeriği (oluştururken yaz)

1. KarotCam nedir, ne yapar
2. Donanım gereksinimleri (Z5, USB kablo, laptop, fotoğraf ünitesi)
3. Yazılım kurulumu adım adım:
   - digiCamControl indir + kur + webserver enable (PORT 5513)
   - Python 3.11+ kur
   - `pip install -r requirements.txt`
   - `python main.py`
4. İlk kalibrasyon nasıl yapılır
5. Saha kullanım kılavuzu (klavye kısayolları)
6. Sorun giderme

## Geliştirme Sırası (önerilen)

1. **İskeleti kur:** klasör yapısı, requirements, README, boş main.py
2. **DB katmanı:** schema + models + repository + testler
3. **digiCamControl wrapper:** HTTP client + bağlantı testi
4. **PyQt6 ana pencere:** menu + status bar + boş tab'lar
5. **Proje/kuyu/kutu CRUD ekranları**
6. **Live view widget'ı**
7. **Çekim akışı:** SPACE → tetikle → indir → DB kaydet → galeri yenile
8. **Kalibrasyon sihirbazı**
9. **Otomatik düzeltme entegrasyonu**
10. **Galeri ve dışa aktarma**
11. **Stitching özelliği**
12. **Genel cilalama, hata mesajları, loglama**

## İlk Adım

Lütfen önce:
1. Proje klasör yapısını oluştur
2. `requirements.txt` ve `README.md` yaz (kurulum dahil)
3. SQLite şemasını ve repository katmanını yaz + temel pytest testleri
4. digiCamControl HTTP wrapper'ı yaz (ama mock modu da olsun, kamera olmadan da test edilebilsin)
5. Boş PyQt6 ana penceresi (proje seç ekranı ile)

Bu kadar yapınca DUR ve bana göster. Sonraki adımlar için onay bekle. Tüm uygulamayı tek seferde yazmaya kalkma — adım adım, her adımda test edilmiş, çalışır kod istiyorum.

## Kod Stili

- Type hints kullan (mypy uyumlu)
- Docstring'ler Türkçe
- Değişken/fonksiyon isimleri İngilizce
- Black formatter, satır 100 karakter
- pathlib.Path kullan, os.path KULLANMA
- f-string kullan, %-format KULLANMA
- async/await GEREKMEZ (saha aracı, basit tut)

---

**Hazır olduğunda başla. Sorun varsa bana sor, varsayım yapma.**
