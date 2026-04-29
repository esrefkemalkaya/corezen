# KarotCam (CoreZen) — Sub-project 1: Foundation + Capture Loop

**Status:** Design approved (2026-04-29)
**Owner:** Esref Kaya
**Sub-project:** 1 of 3 (Foundation → Calibration & Correction → Advanced Imaging & Export)

## Context

KarotCam is a Python/PyQt6 desktop application for mineral exploration drilling core box photography. It is an open-source alternative to the commercial Imago Petcore product, used daily by field geology teams at ESAN Eczacıbaşı Balya (Turkey) and (later) Drillon JEMAS Maroc sites.

Field operators currently transfer photos manually from SD cards and rename them by hand — slow and error-prone. KarotCam automates the entire capture loop end-to-end via a tethered Nikon Z5 driven by digiCamControl over its HTTP webserver.

The full product (defined in `karotcam_prompt.md` at the repo root) covers capture, calibration, geometric correction, wet/dry pairing, panorama stitching, gallery, and export. That is too large for a single design. This document covers **Sub-project 1 only**: the foundation and the core capture loop. Subsequent sub-projects build on this:

- **Sub-project 2:** Calibration wizard + perspective and lens distortion correction + scale (mm/pixel)
- **Sub-project 3:** Wet/dry pairing UX, panorama stitching, gallery polish, Excel/CSV export

## Goals

1. Operator at the rig can take a sequence of identified, named, persisted core-box photos using only the keyboard, with zero manual file management.
2. App is robust to USB unplugs, digiCamControl crashes, and disk pressure — never silently loses a photo, never freezes.
3. App restarts to exactly where the operator left off (last project + hole + box).
4. Ships as a single `KarotCam.exe` requiring no Python install on the field laptop.
5. Foundation is clean enough that Sub-projects 2 and 3 can extend it without rework of this sub-project's modules.

## Non-Goals (Out of Scope)

- Calibration, perspective/distortion correction, mm/pixel scale (Sub-project 2)
- Wet/dry pairing UX semantics, panorama stitching, full gallery, Excel/CSV export (Sub-project 3)
- i18n language switching (Turkish only in v1, structure ready)
- MJPEG streaming live view (HTTP polling only in v1)
- Cloud sync, multi-user, AI defect detection, mobile, SAP integration (v2+)
- User-editable runtime configuration (config baked into exe in v1)
- Installer / auto-update (portable folder distribution in v1)

## Confirmed Constraints

- **Camera:** Nikon Z5, USB-C tethered, already verified working with digiCamControl GUI (capture + live view + auto-transfer to PC). HTTP webserver API at `localhost:5513` to be exercised during build.
- **Capture format:** RAW only (Nikon NEF). No JPEG sidecar. Live view and gallery thumbnails use the JPEG preview embedded inside the NEF (extracted via `rawpy.thumb_data`) — no separate JPEG file on disk.
- **File delivery:** digiCamControl writes NEFs to a configured `session.folder` (`data/photos/raw/`); KarotCam uses a `watchdog` filesystem observer to detect arrivals.
- **Mock client:** stub `DigiCamClient` Protocol implementation for pytest only. Interactive development uses the real Z5.
- **Persistence:** full session resume — last project + hole + box restored on launch.
- **Re-shoot:** soft-delete (`iptal=1`); files always preserved.
- **Live view:** HTTP polling at ~15 fps via `QTimer` (66 ms interval). MJPEG streaming deferred to v2 if polling proves inadequate.
- **Connection loss:** soft warning banner — capture disabled, rest of app remains usable.
- **Heartbeat:** 5 s `QTimer` calling digiCam `get`, drives green/red status indicator.
- **GUI:** keyboard-primary. Every action has a shortcut, persistent legend at the bottom of the capture screen, large fonts (≥16 pt) and large buttons (≥48 px) for glove use, high-contrast field theme.
- **Testing:** pragmatic pytest — filename, repository, HTTP client (with `requests-mock`). No GUI unit tests. Manual smoke checklist for releases.
- **Packaging:** PyInstaller single-file `.exe` from day one.

## Architecture: Thread-per-Concern with Qt Signals

The capture loop coordinates four concerns: GUI rendering, HTTP-based camera control, filesystem watching, and SQLite writes. To keep the UI responsive under HTTP latency spikes (e.g., the camera writing a 40 MB NEF), each concern lives on its own thread, communicating via Qt signals/slots:

| Thread | Owns | Responsibility |
|---|---|---|
| **Main (GUI)** | All `QWidget`s, `HeartbeatTimer`, `LiveViewTimer`, all DB writes | Render, route signals, persist |
| **CaptureWorker** (`QThread`) | `DigiCamClient` instance | Receives `capture_requested` signal, fires HTTP `capture`, returns immediately |
| **WatcherWorker** (`QThread`) | `watchdog.Observer` on `data/photos/raw/` | Emits `file_arrived(path)` on new NEF |
| **HeartbeatTimer** (main-thread `QTimer`, 5 s) | `DigiCamClient` (separate instance) | Emits `connection_changed(bool)` |

**SQLite concurrency rule:** WAL mode is enabled, but **all writes happen on the main thread** through a `RepositoryWriter` facade. Worker threads never touch the database. This keeps the concurrency model trivial (no locking, no race conditions) at the cost of a tiny GUI-thread cost per insert (microseconds for a single row — irrelevant).

**Capture happy-path sequence:**

1. Operator presses `SPACE`
2. `MainWindow` shows yellow flash overlay "ÇEKİLİYOR..." on the live view
3. `MainWindow` emits `capture_requested` → `CaptureWorker.trigger_capture()` slot
4. `CaptureWorker` POSTs to digiCam `capture`; HTTP returns within ~100 ms (camera queues internally)
5. NEF arrives in `data/photos/raw/` (typically <2 s on confirmed setup)
6. `WatcherWorker` emits `file_arrived(raw_path)`
7. Main thread: resolves current Project/Hole/Box context → renames file via `utils/filename.py` → INSERTs `photos` row → updates `app_state.last_box_id` → emits `photo_added(photo_id)`
8. Flash overlay turns green ✓ "Kayıt edildi: K0023" for 1 s
9. `recent_shots` widget prepends new thumbnail (decoded from NEF embedded JPEG)
10. Box auto-advances: `kutu_no += 1`, `derinlik_baslangic = previous derinlik_bitis`, `app_state` updated. Operator can immediately press `SPACE` again.

**Re-shoot path (`R` key):**
- Most recent active photo for current box marked `iptal = 1, iptal_sebep = "yeniden çekim"`
- File on disk is left untouched (soft-delete only)
- Thumbnail in `recent_shots` is greyed-out
- Current box stays selected (no auto-advance)
- Capture flow ready again

## Module Layout

```
karotcam/
├── main.py                          # Entry point, splash, qApp setup
├── config.py                        # Constants: paths, digiCam URL, polling rates
├── requirements.txt                 # Dev deps
├── karotcam.spec                    # PyInstaller build spec
├── README.md
├── data/                            # Created on first run
│   ├── photos/raw/
│   ├── backups/
│   └── logs/
├── karotcam/
│   ├── camera/
│   │   ├── digicam_client.py        # HTTPClient + MockClient (same Protocol)
│   │   ├── capture_worker.py        # QThread
│   │   ├── watcher_worker.py        # QThread (watchdog Observer)
│   │   └── heartbeat.py             # Main-thread QTimer
│   ├── db/
│   │   ├── schema.py                # CREATE TABLE + migrations
│   │   ├── models.py                # @dataclass: Project, Hole, Box, Photo, AppState
│   │   ├── repository.py            # Per-entity Repository classes
│   │   └── backup.py                # Startup nightly-backup logic
│   ├── gui/
│   │   ├── main_window.py           # QMainWindow; owns workers, wires signals
│   │   ├── widgets/
│   │   │   ├── project_picker.py
│   │   │   ├── hole_picker.py
│   │   │   ├── box_form.py          # Inline edit of next-box suggestion
│   │   │   ├── live_view.py         # QLabel + 66 ms QTimer polling
│   │   │   ├── status_bar.py        # Connection dot + current context
│   │   │   ├── shortcut_hints.py    # Always-visible keyboard legend
│   │   │   └── recent_shots.py      # Strip of last N captures
│   │   ├── styles.qss               # Big-font, high-contrast field theme
│   │   └── i18n/tr.json
│   └── utils/
│       ├── filename.py              # Template engine + sanitization
│       ├── session_state.py         # Read/write app_state row
│       ├── nef_preview.py           # Extract embedded JPEG via rawpy
│       └── logger.py                # Per-day RotatingFileHandler setup
└── tests/
    ├── test_filename.py
    ├── test_repository.py
    ├── test_digicam_client.py       # Uses requests-mock
    ├── test_session_state.py
    └── MANUAL_SMOKE.md
```

## Data Model

Schema follows `karotcam_prompt.md` for `projects`, `holes`, `boxes`, `photos`, `calibrations` (the latter empty in v1 — populated in Sub-project 2). Additions:

```sql
CREATE TABLE app_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_project_id INTEGER,
    last_hole_id INTEGER,
    last_box_id INTEGER,
    updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (last_project_id) REFERENCES projects(id),
    FOREIGN KEY (last_hole_id) REFERENCES holes(id),
    FOREIGN KEY (last_box_id) REFERENCES boxes(id)
);

ALTER TABLE photos ADD COLUMN iptal INTEGER DEFAULT 0;
ALTER TABLE photos ADD COLUMN iptal_sebep TEXT;

CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

Notes:
- `app_state` is a single-row table enforced by `CHECK (id = 1)`.
- All "active" queries on `photos` filter by `WHERE iptal = 0`. An "audit" path (Sub-project 3) can show all rows.
- For Sub-project 1, `photos.foto_tipi` is always `KURU`. Wet/dry semantics arrive in Sub-project 3.
- `schema_version` enables idempotent migrations from v1 onward.

**Repository pattern:** one `Repository` class per entity, each method opens/closes its own SQLite connection, returns `@dataclass` instances. `next_box_for(hole_id)` helper computes suggested `kutu_no = max + 1` and `derinlik_baslangic = previous derinlik_bitis`.

## Filename Generation

Template: `{KUYU_ADI}_K{KUTU_NO_4DIGIT}_{DER_BAS}-{DER_BIT}_{TIP}_{YYYYMMDD-HHMM}.NEF`
Example: `BLY-2024-156_K0023_145.20-148.50_KURU_20260429-1430.NEF`

- `KUYU_ADI` allowed chars: `[A-Za-z0-9-]`. Anything else replaced with `_` and logged at WARN.
- `KUTU_NO`: zero-padded to 4 digits (0001, 0023, 0156).
- Depths: 2 decimal places.
- `TIP`: `KURU` in v1.
- Path length capped at Windows MAX_PATH (260). If exceeded, `KUYU_ADI` is truncated and a short hash suffix appended.
- Collisions (same box, same minute) resolved by appending `_002`, `_003`, etc. — guaranteed by the `UNIQUE(hole_id, kutu_no)` invariant on `boxes` plus the suffix logic on `photos`.

## User Flow

**Startup:**
1. Splash for ≥500 ms while `data/` tree is created, DB opened/migrated, WAL enabled, nightly backup taken if today's not present, logger initialized, workers started.
2. `app_state` read. If `last_project_id` exists → jump to **Capture screen** with full context. Otherwise → **Project picker**.

**Three primary screens** (no modal dialogs, no wizards):

- **Project picker:** large keyboard-navigable list. `↑/↓` to move, `ENTER` opens, `N` creates new (inline form: ad / şirket / konum).
- **Hole picker:** same shape, scoped to current project. `ENTER` opens, `N` creates new, `ESC` returns.
- **Capture screen:** main workspace, layout:

```
┌──────────────────────────────────────────────────────────┐
│ STATUS BAR: ●Bağlı  Proje: ESAN-Balya  Kuyu: BLY-156   │
├──────────────────────────────────────────────────────────┤
│              LIVE VIEW (large, ~70% height)              │
├──────────────────────────────────────────────────────────┤
│ Sıradaki Kutu: K0024  Derinlik: 148.50 - 151.80         │
│ [düzenle: D]                                             │
├──────────────────────────────────────────────────────────┤
│ Son Çekimler: [thumb] [thumb] [thumb] [thumb] [thumb]   │
├──────────────────────────────────────────────────────────┤
│ SHORTCUTS: [SPACE] Çek  [R] Yeniden  [ENTER] Sıradaki   │
│            [D] Düzenle  [H] Kuyu Değiştir  [ESC] Çıkış  │
└──────────────────────────────────────────────────────────┘
```

**Visual / accessibility:**
- Base font 16 pt, shortcut hints 14 pt, status bar 18 pt
- Dark theme: bg `#1e1e1e`, fg `#ffffff`, accent green `#00c853`, error red `#d50000`, warning amber `#ffd600`
- All clickable elements ≥48 px tall (glove fallback)
- All shortcuts shown in persistent legend — no hidden bindings

## Error Handling

Three severity tiers, distinct UI treatments:

| Severity | Example | UI treatment |
|---|---|---|
| Info | "Kayıt edildi: K0023" | Green toast, 1 s, top of live view |
| Warning | "Kamera bağlantısı yok" | Persistent banner under status bar |
| Error | "Veritabanı yazılamadı" | Modal block with [Tamam] + [Logu Aç] |

| Failure | Detection | Response |
|---|---|---|
| digiCam unreachable on startup | First heartbeat fails | Red banner, capture disabled, app still launches |
| digiCam dies mid-session | Heartbeat fails | Banner appears; in-flight capture (if any) timed out and discarded; no DB row written |
| HTTP `capture` returns error | `CaptureWorker` catches | Toast "Çekim başarısız: <kısa neden>"; no DB row |
| NEF doesn't arrive within `DIGICAM_CAPTURE_TIMEOUT_S` | Watcher timeout | Toast "Fotoğraf alınamadı — tekrar deneyin"; no DB row |
| Two NEFs arrive close together | Watcher debounce | Each processed independently; rename collisions resolved by `_NNN` suffix |
| File rename fails (locked / disk full) | `try`/`except` around `Path.rename` | Error modal; file stays under digiCam's name; logged |
| DB write fails | `try`/`except` around INSERT | Error modal; file already on disk under correct name preserved; logged; operator notified to retry |
| `watchdog` observer dies | Worker catches, emits `watcher_died` | Banner "Dosya izleyici çöktü — uygulamayı yeniden başlatın"; capture disabled |
| Free disk < `MIN_FREE_DISK_MB` | Pre-capture check on `SPACE` | Block capture; banner "Disk alanı yetersiz" |

User-facing messages are Turkish. Stack traces go only to log files. No telemetry, no log uploads — fully local.

## Configuration

`config.py` is the single source of truth for tunables. No environment variables, no JSON config file in v1 — anything that needs changing requires a rebuild. Defaults:

| Setting | Default | Purpose |
|---|---|---|
| `DIGICAM_BASE_URL` | `http://localhost:5513` | digiCamControl webserver |
| `DIGICAM_HEARTBEAT_MS` | 5000 | Connection check interval |
| `DIGICAM_LIVEVIEW_POLL_MS` | 66 | ~15 fps live view polling |
| `DIGICAM_CAPTURE_TIMEOUT_S` | 10 | Max wait for NEF on disk |
| `DIGICAM_HTTP_TIMEOUT_S` | 3 | Single HTTP request timeout |
| `BACKUP_RETENTION_DAYS` | 14 | Days of nightly DB backups kept |
| `MIN_FREE_DISK_MB` | 500 | Minimum free space before capture |
| `UI_FONT_SIZE_PT` | 16 | Base UI font size |
| `UI_LANGUAGE` | `"tr"` | Active i18n bundle |

## Logging

- `logging` module, `RotatingFileHandler` per day to `data/logs/YYYY-MM-DD.log`
- Format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- DEBUG to file, INFO to console (dev mode only — silenced in PyInstaller build)
- Every capture logged at INFO with full context (project/hole/box/filename/elapsed-ms)
- All caught exceptions logged at ERROR with `exc_info=True`

## Testing Strategy

| Module | Test type | Coverage target |
|---|---|---|
| `utils/filename.py` | Pure unit, parametrized | 100% — boundary cases, sanitization, collisions |
| `db/repository.py` | Integration with `:memory:` SQLite | All CRUD + edge cases |
| `db/schema.py` | Migration test on empty + populated DBs | All migration paths |
| `camera/digicam_client.py` | Mocked `requests` via `requests-mock` | All endpoints, all documented error codes |
| `utils/session_state.py` | Integration with `:memory:` SQLite | All read/write paths |
| `utils/nef_preview.py` | Skipped in CI — needs real NEF fixtures | Manual verification only |
| All GUI code | Not unit tested in v1 | Manual smoke checklist before release |

CI runs `pytest`, `mypy karotcam/`, `black --check karotcam/`. PyInstaller build runs only on release tags.

**Manual smoke test checklist** (`tests/MANUAL_SMOKE.md`):
1. Launch from clean state → project picker appears
2. Create project → hole → land on capture screen
3. Press `SPACE` with camera connected → photo lands in DB and on disk with correct name within 3 s
4. Press `R` → previous photo marked `iptal=1`, thumbnail greyed
5. Unplug USB → red banner within 5 s, `SPACE` does nothing
6. Replug USB → banner clears within 10 s
7. Close + reopen → restored to same project/hole/box

## Packaging & Distribution

**Dependencies (`requirements.txt`):**

```
PyQt6==6.7.*
requests==2.32.*
watchdog==4.*
rawpy==0.21.*
# Dev only
pytest==8.*
pytest-cov==5.*
requests-mock==1.12.*
black==24.*
mypy==1.11.*
PyInstaller==6.*
```

`pyproject.toml` enforces `requires-python = ">=3.11"`.

**PyInstaller (`karotcam.spec`):**
- One-file exe: `pyinstaller karotcam.spec` → `dist/KarotCam.exe`
- Includes: `karotcam/gui/i18n/tr.json`, `karotcam/gui/styles.qss`, app icon
- Hidden imports for `rawpy`, `watchdog.observers.read_directory_changes`
- `data/` and `karotcam.db` NOT bundled — created on first run beside the exe

**Field laptop layout:**

```
C:\KarotCam\
├── KarotCam.exe
├── karotcam.db           # Created on first run
└── data\                 # Created on first run
    ├── photos\raw\
    ├── backups\
    └── logs\
```

Operator runs `KarotCam.exe`. No installer, no registry, no admin rights. Fully portable — copying `C:\KarotCam` backs up everything.

**digiCamControl side-by-side configuration** (documented in README, not enforced by code):
- digiCamControl `session.folder` set to `C:\KarotCam\data\photos\raw\`
- digiCamControl webserver enabled on port 5513
- digiCamControl set to "Use original filename" off (KarotCam handles naming via post-capture rename)

**Build & release flow:**
1. `pytest` passes
2. `mypy karotcam/` passes
3. `black --check karotcam/` passes
4. `pyinstaller karotcam.spec` from a clean venv on a Windows 10 build machine
5. Manual smoke checklist passes on a clean Win10/11 VM with the real Z5
6. `dist/KarotCam.exe` shipped (~80–120 MB, single file)

## Open Questions

None. All design decisions confirmed during the brainstorm session on 2026-04-29.

## Decisions Log

| Topic | Decision | Notes |
|---|---|---|
| Sub-project scope | Foundation + capture loop only | Q1 → A |
| Camera readiness | digiCam + Z5 confirmed working via GUI; HTTP API to be exercised during build | Q2 (revised) → B |
| Capture format | RAW (NEF) only, embedded JPEG used for previews | User reversed earlier RAW+JPEG choice |
| Mock client | Test-only stub; real camera for interactive dev | Q4 → B |
| File delivery | digiCam `session.folder` + `watchdog` observer | Q5 → A |
| Persistence | Full session resume (project + hole + box) | Q6 → A |
| Re-shoot | Soft-delete (`iptal=1`); files preserved | Q7 → A |
| Live view | HTTP polling at ~15 fps in v1; streaming deferred | Q8 → C |
| GUI style | Keyboard-primary, large fonts, high-contrast, glove-friendly buttons | Q9 → A |
| Connection loss | Soft warning banner; rest of app stays usable | Q10 → B |
| Heartbeat | 5 s `QTimer` with green/red status indicator | Q11 → A |
| Testing | Pragmatic pytest, no GUI tests, manual smoke checklist | Q12 → A |
| Packaging | PyInstaller single-file `.exe` from day one | Q13 → B |
| Architecture | Thread-per-concern with Qt signals (Approach 1) | Approaches → 1 |
