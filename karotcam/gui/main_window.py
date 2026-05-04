"""KarotCam ana penceresi.

Üç ekran (project picker / hole picker / capture) bir QStackedWidget içinde.
Worker'lar ve sinyal kabloları burada kurulur. Ana penceredeki tüm yazma
işlemleri bu thread üzerinde olur (DB single-writer kuralı).
"""
from __future__ import annotations

import shutil
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QEvent, QObject, Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import config
from karotcam.camera.capture_worker import make_capture_thread
from karotcam.camera.digicam_client import (
    CameraConnectionError,
    DigiCamHTTPClient,
)
from karotcam.camera.heartbeat import Heartbeat
from karotcam.camera.watcher_worker import make_watcher_thread
from karotcam.db.models import Box, Hole, Project
from karotcam.db.repository import (
    BoxRepository,
    HoleRepository,
    PhotoRepository,
    ProjectRepository,
)
from karotcam.gui.widgets.box_form import BoxForm, NextBox
from karotcam.gui.widgets.hole_picker import HolePicker
from karotcam.gui.widgets.live_view import LiveView
from karotcam.gui.widgets.project_picker import ProjectPicker
from karotcam.gui.widgets.recent_shots import RecentShots
from karotcam.gui.widgets.shortcut_hints import ShortcutHints
from karotcam.gui.widgets.status_bar import TopStatusBar
from karotcam.utils.filename import PhotoNameInputs, build_photo_filename
from karotcam.utils.logger import get_logger
from karotcam.utils.session_state import SessionContext, save_session

_log = get_logger(__name__)

_SCREEN_PROJECT = 0
_SCREEN_HOLE = 1
_SCREEN_CAPTURE = 2


class MainWindow(QMainWindow):
    request_capture = pyqtSignal()  # → CaptureWorker

    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self.setWindowTitle(f"{config.APP_NAME} {config.APP_VERSION}")
        self.resize(1400, 900)

        self._conn = conn
        self._project_repo = ProjectRepository(conn)
        self._hole_repo = HoleRepository(conn)
        self._box_repo = BoxRepository(conn)
        self._photo_repo = PhotoRepository(conn)

        self._current_project: Project | None = None
        self._current_hole: Hole | None = None
        self._next_box: NextBox | None = None
        self._connected: bool = False

        # --- camera client + workers ---
        self._client = DigiCamHTTPClient(
            base_url=config.DIGICAM_BASE_URL,
            timeout_s=config.DIGICAM_HTTP_TIMEOUT_S,
            liveview_url=config.DIGICAM_LIVEVIEW_URL,
        )
        # Heartbeat uses its own client with a short timeout for fast-fail
        self._heartbeat_client = DigiCamHTTPClient(
            base_url=config.DIGICAM_BASE_URL,
            timeout_s=config.DIGICAM_HEARTBEAT_TIMEOUT_S,
            ping_timeout_s=config.DIGICAM_HEARTBEAT_TIMEOUT_S,
        )
        self._heartbeat = Heartbeat(
            client=self._heartbeat_client,
            interval_ms=config.DIGICAM_HEARTBEAT_MS,
            parent=self,
        )

        self._capture_thread, self._capture_worker = make_capture_thread(self._client)
        self._watcher_thread, self._watcher_worker = make_watcher_thread(
            config.PHOTOS_RAW_DIR
        )

        # --- UI shell ---
        central = QWidget(self)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.setCentralWidget(central)

        self._status_bar = TopStatusBar(self)
        outer.addWidget(self._status_bar)

        self._banner = QLabel("", self)
        self._banner.setObjectName("WarningBanner")
        self._banner.setVisible(False)
        outer.addWidget(self._banner)

        self._stack = QStackedWidget(self)
        outer.addWidget(self._stack, 1)

        self._project_picker = ProjectPicker(self._project_repo, self)
        self._hole_picker = HolePicker(self._hole_repo, self)
        self._capture_screen = self._build_capture_screen()
        self._stack.addWidget(self._project_picker)  # 0
        self._stack.addWidget(self._hole_picker)     # 1
        self._stack.addWidget(self._capture_screen)  # 2

        # --- signal wiring ---
        self._project_picker.project_chosen.connect(self._on_project_chosen)
        self._hole_picker.hole_chosen.connect(self._on_hole_chosen)
        self._hole_picker.back_requested.connect(
            lambda: self._goto(_SCREEN_PROJECT)
        )
        self._heartbeat.connection_changed.connect(self._on_connection_changed)
        self.request_capture.connect(self._capture_worker.request_capture)
        self._capture_worker.capture_failed.connect(self._on_capture_failed)
        self._capture_worker.capture_dispatched.connect(self._on_capture_dispatched)
        self._watcher_worker.file_arrived.connect(self._on_file_arrived)
        self._watcher_worker.watcher_died.connect(self._on_watcher_died)
        self._box_form.edited.connect(self._on_box_edited)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    def _build_capture_screen(self) -> QWidget:
        screen = QWidget(self)
        layout = QVBoxLayout(screen)
        layout.setContentsMargins(8, 8, 8, 8)

        self._live_view = LiveView(
            client=self._client,
            poll_ms=config.DIGICAM_LIVEVIEW_POLL_MS,
            parent=screen,
        )
        layout.addWidget(self._live_view, 1)

        self._box_form = BoxForm(screen)
        layout.addWidget(self._box_form)

        layout.addWidget(QLabel("Son Çekimler:", screen))
        self._recent = RecentShots(max_count=config.RECENT_SHOTS_COUNT, parent=screen)
        layout.addWidget(self._recent)

        hints_row_widget = QWidget(screen)
        hints_row = QVBoxLayout(hints_row_widget)
        hints_row.setContentsMargins(0, 0, 0, 0)
        hints_row.setSpacing(4)

        self._hints = ShortcutHints(
            "[SPACE] Çek  [R] Yeniden  [ENTER] Sıradaki  "
            "[D] Düzenle  [H] Kuyu Değiştir  [ESC] Geri",
            parent=hints_row_widget,
        )
        hints_row.addWidget(self._hints)

        self._open_folder_btn = QPushButton("📁 Fotoğraf Klasörünü Aç", hints_row_widget)
        self._open_folder_btn.clicked.connect(self._open_photos_folder)
        hints_row.addWidget(self._open_folder_btn)

        layout.addWidget(hints_row_widget)

        # eventFilter: capture ekranındaki tüm child'lardan gelen key event'ları yakala
        screen.installEventFilter(self)
        for child in screen.findChildren(QWidget):
            child.installEventFilter(self)

        return screen

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self, restored: SessionContext | None) -> None:
        self._capture_thread.start()
        self._watcher_thread.start()
        self._heartbeat.start()
        # İlk bağlantı denemesi; başarısız olursa _on_connection_changed(True) geldiğinde tekrar denenecek
        self._apply_session_folder()

        if restored is not None and restored.project_id is not None:
            project = self._project_repo.get(restored.project_id)
            if project is not None:
                self._current_project = project
                if restored.hole_id is not None:
                    hole = self._hole_repo.get(restored.hole_id)
                    if hole is not None:
                        self._current_hole = hole
                        self._enter_capture_screen()
                        return
                self._enter_hole_picker()
                return
        self._enter_project_picker()

    def closeEvent(self, e) -> None:  # type: ignore[override]
        try:
            self._heartbeat.stop()   # stops timer + joins heartbeat thread
            self._live_view.stop()   # stops timer + joins fetch thread
            self._watcher_worker.stop()
            self._capture_thread.quit()
            self._capture_thread.wait(2000)
            self._watcher_thread.quit()
            self._watcher_thread.wait(2000)
        finally:
            super().closeEvent(e)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def _goto(self, index: int) -> None:
        if index == _SCREEN_CAPTURE:
            self._live_view.start()
        else:
            self._live_view.stop()
        self._stack.setCurrentIndex(index)
        self._stack.currentWidget().setFocus()

    def _enter_project_picker(self) -> None:
        self._project_picker.refresh()
        self._goto(_SCREEN_PROJECT)
        self._status_bar.set_context(project=None, hole=None)

    def _enter_hole_picker(self) -> None:
        assert self._current_project is not None
        self._hole_picker.load_for_project(self._current_project.id)
        self._goto(_SCREEN_HOLE)
        self._status_bar.set_context(
            project=self._current_project.ad, hole=None
        )

    def _enter_capture_screen(self) -> None:
        assert self._current_project is not None
        assert self._current_hole is not None
        self._refresh_next_box()
        self._refresh_recent_strip()
        self._goto(_SCREEN_CAPTURE)
        self._status_bar.set_context(
            project=self._current_project.ad,
            hole=self._current_hole.kuyu_adi,
        )
        self._persist_session()

    def _persist_session(self) -> None:
        save_session(
            self._conn,
            SessionContext(
                project_id=(self._current_project.id if self._current_project else 0),
                hole_id=(self._current_hole.id if self._current_hole else None),
                box_id=None,
            ),
        )

    # ------------------------------------------------------------------
    # Picker handlers
    # ------------------------------------------------------------------
    @pyqtSlot(int)
    def _on_project_chosen(self, project_id: int) -> None:
        project = self._project_repo.get(project_id)
        if project is None:
            return
        self._current_project = project
        self._current_hole = None
        self._enter_hole_picker()

    @pyqtSlot(int)
    def _on_hole_chosen(self, hole_id: int) -> None:
        hole = self._hole_repo.get(hole_id)
        if hole is None:
            return
        self._current_hole = hole
        self._enter_capture_screen()

    # ------------------------------------------------------------------
    # Capture logic
    # ------------------------------------------------------------------
    def _refresh_next_box(self) -> None:
        assert self._current_hole is not None
        kutu_no, der_bas = self._box_repo.next_box_for(self._current_hole.id)
        # Default span: 3.0 m; operatör D ile düzenleyebilir.
        suggestion = NextBox(
            kutu_no=kutu_no,
            derinlik_baslangic=der_bas,
            derinlik_bitis=der_bas + 3.0,
        )
        self._next_box = suggestion
        self._box_form.set_suggestion(suggestion)

    def _refresh_recent_strip(self) -> None:
        assert self._current_hole is not None
        photos = self._photo_repo.list_recent_for_hole(
            hole_id=self._current_hole.id, limit=config.RECENT_SHOTS_COUNT
        )
        self._recent.set_thumbnails([Path(p.dosya_yolu) for p in photos])

    def _on_box_edited(self, edited: NextBox) -> None:
        self._next_box = edited
        self._box_form.set_suggestion(edited)

    def _on_capture_dispatched(self) -> None:
        # Tetik başarılı; artık WatcherWorker'dan file_arrived bekliyoruz.
        pass

    def _on_capture_failed(self, msg: str) -> None:
        QMessageBox.warning(self, "Çekim başarısız", msg)

    @pyqtSlot(str)
    def _on_file_arrived(self, raw_path_str: str) -> None:
        if self._current_hole is None or self._next_box is None:
            _log.warning("file_arrived ama bağlam eksik: %s", raw_path_str)
            return
        raw_path = Path(raw_path_str)
        try:
            box_id = self._ensure_box_for_next()
            target_name = build_photo_filename(
                PhotoNameInputs(
                    kuyu_adi=self._current_hole.kuyu_adi,
                    kutu_no=self._next_box.kutu_no,
                    derinlik_baslangic=self._next_box.derinlik_baslangic,
                    derinlik_bitis=self._next_box.derinlik_bitis,
                    tip="KURU",
                    when=datetime.now(),
                )
            )
            target = _resolve_unique(raw_path.parent / target_name)
            raw_path.rename(target)
            self._photo_repo.create(
                box_id=box_id, dosya_yolu=str(target), foto_tipi="KURU"
            )
            _log.info("kayıt edildi: %s", target.name)
        except OSError as e:
            _log.error("dosya adı değiştirilemedi: %s → %s | %s", raw_path, target, e)
            # WinError 32 = digiCamControl henüz kilidi bırakmadı — kullanıcıya yol göster
            err_no = getattr(e, "winerror", None) or getattr(e, "errno", None)
            if err_no == 32:
                msg = (
                    f"Fotoğraf henüz hazır değil — digiCamControl dosyayı aktarıyor.\n\n"
                    f"Birkaç saniye bekleyin, ardından [SPACE] ile tekrar çekin."
                )
            else:
                msg = f"Dosya kaydedilemedi:\n{e}"
            _log.error(msg)
            mb = QMessageBox(QMessageBox.Icon.Warning, "Kayıt hatası", msg, parent=self)
            mb.addButton("Tamam", QMessageBox.ButtonRole.AcceptRole)
            open_btn = mb.addButton("Klasörü Aç", QMessageBox.ButtonRole.ActionRole)
            mb.exec()
            if mb.clickedButton() == open_btn:
                subprocess.Popen(["explorer", str(raw_path.parent)])
            return
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Hata", f"Veritabanı yazılamadı: {e}")
            return
        self._refresh_recent_strip()
        self._refresh_next_box()

    def _ensure_box_for_next(self) -> int:
        assert self._current_hole is not None
        assert self._next_box is not None
        # Aynı kutu zaten var mı?
        for b in self._box_repo.list_for_hole(self._current_hole.id):
            if b.kutu_no == self._next_box.kutu_no:
                return b.id
        return self._box_repo.create(
            hole_id=self._current_hole.id,
            kutu_no=self._next_box.kutu_no,
            derinlik_baslangic=self._next_box.derinlik_baslangic,
            derinlik_bitis=self._next_box.derinlik_bitis,
        )

    def _advance_box(self) -> None:
        """ENTER: sıradaki kutu önerisini bir artır (çekim yapmadan)."""
        if self._next_box is None:
            return
        span = self._next_box.derinlik_bitis - self._next_box.derinlik_baslangic
        new_box = NextBox(
            kutu_no=self._next_box.kutu_no + 1,
            derinlik_baslangic=self._next_box.derinlik_bitis,
            derinlik_bitis=self._next_box.derinlik_bitis + span,
        )
        self._next_box = new_box
        self._box_form.set_suggestion(new_box)

    def _trigger_capture(self) -> None:
        if not self._connected:
            return  # banner zaten görünür
        if not _has_min_free_disk():
            self._show_banner("Disk alanı yetersiz — devam etmeden temizlik yapın.")
            return
        self.request_capture.emit()

    def _reshoot(self) -> None:
        if self._current_hole is None or self._next_box is None:
            return
        # En son aktif foto'yu bul ve iptal et
        for b in self._box_repo.list_for_hole(self._current_hole.id):
            if b.kutu_no == self._next_box.kutu_no - 1 or b.kutu_no == self._next_box.kutu_no:
                latest = self._photo_repo.latest_active_for_box(b.id)
                if latest is not None:
                    self._photo_repo.soft_delete(latest.id, sebep="yeniden çekim")
                    # Kutuyu geri sıraya al
                    self._next_box = NextBox(
                        kutu_no=b.kutu_no,
                        derinlik_baslangic=b.derinlik_baslangic,
                        derinlik_bitis=b.derinlik_bitis,
                    )
                    self._box_form.set_suggestion(self._next_box)
                    self._refresh_recent_strip()
                    return

    # ------------------------------------------------------------------
    # Connection / banners
    # ------------------------------------------------------------------
    @pyqtSlot(bool)
    def _on_connection_changed(self, connected: bool) -> None:
        self._connected = connected
        self._status_bar.set_connection(connected)
        if connected:
            self._hide_banner()
            self._apply_session_folder()
        else:
            self._show_banner(
                "Kamera bağlantısı yok — kabloyu ve digiCamControl'u kontrol edin."
            )

    def _apply_session_folder(self) -> None:
        """digiCamControl'a çekim klasörünü arka planda bildir.

        HTTP çağrıları (set + get) GUI thread'ini bloklamamak için ayrı
        bir QThread'de yapılır. Çift çağrıları önlemek için in-flight guard var.
        """
        if getattr(self, "_session_folder_busy", False):
            return
        self._session_folder_busy = True

        target = str(config.PHOTOS_RAW_DIR)
        client = self._client
        watcher = self._watcher_worker

        def _worker() -> None:
            try:
                try:
                    client.set_session_folder(target)
                    _log.info("session.folder ayarlandı: %s", target)
                except CameraConnectionError as e:
                    _log.warning("session.folder ayarlanamadı: %s", e)

                # get → digiCamControl'un gerçekte yazdığı yolu öğren
                # Bu yol set'ten farklı olabilir (encoding, aktif oturum kilidi)
                # Her zaman watcher'ı bu yola yönlendir
                actual = client.get_session_folder()
                _log.info("digiCamControl aktif klasör: %s", actual)
                if actual:
                    actual_path = Path(actual)
                    if actual_path.exists():
                        watcher.update_watch_dir(actual_path)
                        _log.info("watcher yönlendirildi: %s", actual_path)
                    else:
                        _log.warning("digiCamControl klasörü bulunamadı: %s", actual_path)
                        # Fallback: hedef klasörü izle
                        watcher.update_watch_dir(Path(target))
            finally:
                self._session_folder_busy = False

        t = QThread(self)
        t.run = _worker  # type: ignore[method-assign]
        t.finished.connect(t.deleteLater)
        t.start()

    def _open_photos_folder(self) -> None:
        """Windows Explorer'da fotoğraf klasörünü aç."""
        folder = self._watcher_worker.current_dir()
        subprocess.Popen(["explorer", str(folder)])

    def _on_watcher_died(self, msg: str) -> None:
        self._show_banner(f"Dosya izleyici çöktü: {msg}")

    def _show_banner(self, text: str) -> None:
        self._banner.setText(text)
        self._banner.setVisible(True)

    def _hide_banner(self) -> None:
        self._banner.setVisible(False)

    # ------------------------------------------------------------------
    # Key handling — eventFilter captures keys from all capture screen children
    # ------------------------------------------------------------------
    def eventFilter(self, obj: QObject, e: QEvent) -> bool:  # type: ignore[override]
        if (
            e.type() == QEvent.Type.KeyPress
            and self._stack.currentIndex() == _SCREEN_CAPTURE
        ):
            key = e.key()  # type: ignore[attr-defined]
            if key == Qt.Key.Key_Space:
                self._trigger_capture()
                return True
            if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                # ENTER: edit modundaysa onayla, değilse sıradaki kutuya geç
                if self._box_form.is_editing():
                    self._box_form.confirm_edit()
                else:
                    self._advance_box()
                return True
            if key == Qt.Key.Key_R:
                self._reshoot()
                return True
            if key == Qt.Key.Key_D:
                self._box_form.enter_edit_mode()
                return True
            if key == Qt.Key.Key_H:
                self._enter_hole_picker()
                return True
            if key == Qt.Key.Key_Escape:
                # ESC: edit modundaysa iptal, değilse kuyu seçimine dön (çıkış yok)
                if self._box_form.is_editing():
                    self._box_form.cancel_edit()
                else:
                    self._enter_hole_picker()
                return True
        return super().eventFilter(obj, e)

    def keyPressEvent(self, e: QKeyEvent) -> None:  # type: ignore[override]
        # eventFilter capture ekranını hallediyor; burada sadece diğer ekranlar için
        super().keyPressEvent(e)


def _resolve_unique(target: Path) -> Path:
    """Hedef varsa _002, _003 ... ekle."""
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    n = 2
    while True:
        candidate = target.with_name(f"{stem}_{n:03d}{suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def _has_min_free_disk() -> bool:
    try:
        free_mb = shutil.disk_usage(config.DATA_DIR).free // (1024 * 1024)
        return free_mb >= config.MIN_FREE_DISK_MB
    except OSError:
        return True  # fallback: don't block on stat failure
