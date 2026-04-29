"""WatcherWorker — `data/photos/raw/` üzerinde watchdog Observer.

Yeni `.NEF` dosyası oluştuğunda `file_arrived(str)` sinyali yayınlar.
Dosyanın tam olarak yazılıp yazılmadığını anlamak için kısa bir 'stable size'
kontrolü yapılır (modify event'lerini debounce etmek için).
"""
from __future__ import annotations

import time
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from karotcam.utils.logger import get_logger

_log = get_logger(__name__)

_NEF_SUFFIX = ".nef"
_STABILIZE_POLLS = 5
_STABILIZE_INTERVAL_S = 0.2


class _NEFHandler(FileSystemEventHandler):
    def __init__(self, signal: pyqtSignal) -> None:
        super().__init__()
        self._signal = signal

    def on_created(self, event: FileCreatedEvent) -> None:  # type: ignore[override]
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() != _NEF_SUFFIX:
            return
        if not _wait_until_stable(path):
            _log.warning("NEF stabilize olmadı, atlandı: %s", path)
            return
        _log.info("NEF geldi: %s", path)
        self._signal.emit(str(path))


def _wait_until_stable(path: Path) -> bool:
    """Aynı boyutta `_STABILIZE_POLLS` kez okunana kadar bekle."""
    last = -1
    same = 0
    for _ in range(60):  # max ~12 sn
        try:
            cur = path.stat().st_size
        except FileNotFoundError:
            return False
        if cur == last and cur > 0:
            same += 1
            if same >= _STABILIZE_POLLS:
                return True
        else:
            same = 0
            last = cur
        time.sleep(_STABILIZE_INTERVAL_S)
    return False


class WatcherWorker(QObject):
    file_arrived = pyqtSignal(str)
    watcher_died = pyqtSignal(str)

    def __init__(self, watch_dir: Path) -> None:
        super().__init__()
        self._dir = watch_dir
        self._observer: Observer | None = None

    def start(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._observer = Observer()
        handler = _NEFHandler(self.file_arrived)
        self._observer.schedule(handler, str(self._dir), recursive=False)
        try:
            self._observer.start()
            _log.info("watcher başladı: %s", self._dir)
        except Exception as e:
            _log.exception("watcher başlatılamadı")
            self.watcher_died.emit(str(e))

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None


def make_watcher_thread(watch_dir: Path) -> tuple[QThread, WatcherWorker]:
    thread = QThread()
    worker = WatcherWorker(watch_dir)
    worker.moveToThread(thread)
    thread.started.connect(worker.start)
    return thread, worker
