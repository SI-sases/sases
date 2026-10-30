# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['launcher/launcher.py'],
    pathex=['C:\\Users\\xiaomai\\sases'],
    binaries=[],
    datas=[('C:\\Users\\xiaomai\\sases\\launcher\\launcher_config.py', 'launcher'), ('C:\\Users\\xiaomai\\sases\\launcher\\icon.ico', 'launcher')],
    hiddenimports=['PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebEngineCore', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SASES启动器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='C:\\Users\\xiaomai\\sases\\launcher\\icon.ico',
)