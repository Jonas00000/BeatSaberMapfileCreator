# -*- mode: python ; coding: utf-8 -*-
import os, importlib
ytm_pkg = os.path.dirname(importlib.import_module('ytmusicapi').__file__)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('bin', 'bin'),
        ('THIRD_PARTY_LICENSES', '.'),
        ('LICENSE', '.'),
        (os.path.join(ytm_pkg, 'locales'), os.path.join('ytmusicapi', 'locales')),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BeatSaberMapfileCreator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BeatSaberMapfileCreator',
)
