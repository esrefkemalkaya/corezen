# KarotCam — Manuel Smoke Test Listesi

Her sürümden önce bu listeyi `dist/KarotCam.exe` üzerinde çalıştır.
Kamera (Z5) bağlı, digiCamControl webserver port 5513 açık olmalı.

## Hazırlık

- [ ] `C:\KarotCamTest\` klasörüne `KarotCam.exe`'yi kopyala (temiz dizin)
- [ ] digiCamControl session folder = `C:\KarotCamTest\data\photos\raw\`
- [ ] digiCamControl webserver enabled, port 5513
- [ ] Z5 USB ile bağlı, açık

## Senaryolar

- [ ] **Temiz başlatma:** İlk açılışta Proje Seç ekranı görünür, üstte yeşil bağlantı noktası 5 sn içinde.
- [ ] **Yeni proje + kuyu:** `N` ile proje oluştur, sonra kuyu oluştur, capture ekranına in.
- [ ] **İlk çekim:** `SPACE` bas → 3 sn içinde Son Çekimler şeridinde yeni thumb belirir, dosya `data/photos/raw/<KUYU>_K0001_*.NEF` olarak görülür, sıradaki kutu önerisi K0002'ye geçer.
- [ ] **Yeniden çekim:** `R` bas → son thumb soluk gri olur, kutu önerisi geri K0001'e döner; `SPACE` ile tekrar çek → yeni thumb gelir.
- [ ] **Kutu düzenle:** `D` bas → kutu_no/derinlik alanları görünür, değiştir, `Enter` ile onayla, sıradaki çekim yeni değerlerle isimlendirilir.
- [ ] **USB çıkar:** kabloyu çek → 5 sn içinde kırmızı banner + kırmızı nokta, `SPACE` hiçbir şey yapmaz, sessizdir.
- [ ] **USB tak:** kabloyu yeniden tak → 10 sn içinde banner kaybolur, nokta yeşile döner.
- [ ] **Kuyu değiştir:** `H` bas → Kuyu Seç ekranı, başka bir kuyu seç → capture ekranı yeni bağlamla açılır.
- [ ] **Kapat + aç:** Pencereyi kapat, exe'yi tekrar çalıştır → aynı proje/kuyu/capture ekranıyla açılır.
- [ ] **Loglar:** `data/logs/<bugün>.log` her çekim için bir INFO satırı içerir.
- [ ] **Yedek:** `data/backups/karotcam-<bugün>.db` mevcut.

## Sonuç

Tarih: ____________________
Sürüm: ____________________
Yapan: ____________________
Notlar: ___________________
