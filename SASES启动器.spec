# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:/Users/xiaomai/sases/launcher/launcher.py'],
    pathex=['C:/Users/xiaomai/sases/launcher'],
    binaries=[],
    datas=[('C:/Users/xiaomai/sases/launcher/ui', 'ui'), ('C:/Users/xiaomai/sases/launcher/launcher_config.py', '.'), ('C:/Users/xiaomai/sases/launcher/icon.ico', '.')],
    hiddenimports=['urllib.request', 'urllib.error', 'urllib.parse', 'http.client', 'webbrowser', 'subprocess', 'socket', 'json', 'ui.main_window', 'launcher_config'],
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
    icon=['C:/Users/xiaomai/sases/launcher/icon.ico'],
)
