# CoreZen / KarotCam

Açık kaynaklı, saha-odaklı **maden karot kutusu fotoğraflama uygulaması**. Ticari Imago Petcore ürününe alternatif. Türkiye (ESAN Eczacıbaşı Balya) ve ileride Fas (JEMAS Maroc) saha ekipleri için günlük kullanılmak üzere geliştirilmektedir.

> **Not:** Bu repository şu anda **tasarım ve plan** aşamasındadır. Henüz çalışan kod yoktur — implementasyon bekleniyor.

## Mevcut Durum

| Aşama | Durum |
|---|---|
| İlk gereksinim dokümanı | ✅ [`karotcam_prompt.md`](karotcam_prompt.md) |
| Sub-project 1 tasarım dokümanı | ✅ [`docs/superpowers/specs/2026-04-29-karotcam-foundation-design.md`](docs/superpowers/specs/2026-04-29-karotcam-foundation-design.md) |
| Sub-project 1 implementasyon planı (24 task, TDD) | ✅ [`docs/superpowers/plans/2026-04-29-karotcam-foundation.md`](docs/superpowers/plans/2026-04-29-karotcam-foundation.md) |
| Sub-project 1 kod | ⏳ Bekliyor |
| Sub-project 2 (Kalibrasyon + geometrik düzeltme) | ⏳ Tasarım bekliyor |
| Sub-project 3 (Wet/dry, panorama, gallery, export) | ⏳ Tasarım bekliyor |

## Özet

KarotCam, sondaj operasyonu sırasında karot kutularının fotoğraflama iş akışını uçtan uca otomatize eder:

- **Kamera tetikleme** — Nikon Z5, USB-C tethering, [digiCamControl](https://digicamcontrol.com) HTTP API üzerinden
- **Otomatik dosya transferi** — SD karta gerek yok
- **Otomatik isimlendirme** — Kuyu / kutu / derinlik bilgisiyle (ör. `BLY-2024-156_K0023_145.20-148.50_KURU_20260429-1430.NEF`)
- **Geometrik düzeltme** — Perspektif + lens distortion (Sub-project 2)
- **Ölçek kalibrasyonu** — mm/pixel (Sub-project 2)
- **Kuru/ıslak fotoğraf eşleştirme** (Sub-project 3)
- **Multi-shot panorama stitching** (Sub-project 3)
- **Galeri ve dışa aktarma** (Sub-project 3)

## Mimari Özeti (Sub-project 1)

- **Dil / GUI:** Python 3.11+, PyQt6
- **Kamera:** digiCamControl HTTP API (`localhost:5513`), Nikon Z5
- **Veritabanı:** SQLite (WAL modu)
- **Görüntü işleme:** rawpy (NEF preview), OpenCV (Sub-project 2'de)
- **Eşzamanlılık:** Thread-per-concern (GUI / capture worker / watcher worker / heartbeat) Qt signal/slot üzerinden
- **Paketleme:** PyInstaller tek dosya `.exe` (Windows)

Detaylı tasarım için bkz. [`docs/superpowers/specs/2026-04-29-karotcam-foundation-design.md`](docs/superpowers/specs/2026-04-29-karotcam-foundation-design.md).

## Geliştirme Yol Haritası

Bu repo üç sub-project'e ayrılmıştır. Her biri kendi spec → plan → implementasyon döngüsüne sahiptir:

1. **Foundation + Capture Loop** (mevcut planlanan sub-project) — DB, digiCam wrapper, proje/kuyu/kutu CRUD, capture → save → name → store, Türkçe arayüz, PyInstaller exe.
2. **Calibration & Geometric Correction** — Satranç tahtası kalibrasyon sihirbazı, perspektif + distortion düzeltme, mm/pixel ölçek.
3. **Advanced Imaging & Export** — Kuru/ıslak eşleştirme, panorama stitching, gallery cilalama, Excel/CSV dışa aktarma.

## Implementasyona Başlamak İçin

Sub-project 1'in implementasyon planı **24 küçük task** halinde, TDD-uyumlu, her adımda tam kod ve komut içerir:

[`docs/superpowers/plans/2026-04-29-karotcam-foundation.md`](docs/superpowers/plans/2026-04-29-karotcam-foundation.md)

Plan, Claude Code / superpowers framework ile otonom subagent çalıştırması için tasarlanmıştır ama insan geliştirici tarafından da sırayla uygulanabilir.

## Lisans

Henüz lisans atanmadı.

## İletişim

Esref Kemal Kaya — esref.kemal.kaya@gmail.com
