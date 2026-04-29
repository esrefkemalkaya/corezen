# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — `pyinstaller karotcam.spec` ile çalıştır.

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("karotcam/gui/styles.qss", "karotcam/gui"),
        ("karotcam/gui/i18n/tr.json", "karotcam/gui/i18n"),
    ],
    hiddenimports=[
        "rawpy",
        "watchdog.observers.read_directory_changes",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="KarotCam",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
