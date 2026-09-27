# -*- mode: python ; coding: utf-8 -*-
# Chess Analyzer Pro -- PyInstaller spec fayli.
# Windows'da ishlatish: pyinstaller chess_analyzer.spec
import sys
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = (
    collect_submodules('chess')
    + collect_submodules('pyqtgraph', filter=lambda name: 'examples' not in name and 'opengl' not in name)
    + ['PyQt5.sip']
)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
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
    name='ChessAnalyzerPro',
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
    icon=None,
)
