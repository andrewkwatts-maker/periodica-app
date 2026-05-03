# -*- mode: python ; coding: utf-8 -*-

import importlib
import os

# Find periodica's installed data directory
periodica_pkg = importlib.import_module('periodica')
periodica_data = os.path.join(os.path.dirname(periodica_pkg.__file__), 'data')

a = Analysis(
    ['src/periodica_app/__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        (periodica_data, 'periodica/data'),
        ('src/periodica_app/config', 'periodica_app/config'),
    ],
    hiddenimports=[
        'periodica',
        'periodica.core',
        'periodica.data',
        'periodica.utils',
        'periodica.layout_math',
        'periodica_app',
        'periodica_app.ui',
        'periodica_app.layouts',
        'periodica_app.core',
        'periodica_app.utils',
    ],
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
    [],
    exclude_binaries=True,
    name='PeridicaApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PeridicaApp',
)
