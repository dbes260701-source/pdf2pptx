# -*- mode: python ; coding: utf-8 -*-
"""
PDF2PPTX 단일 실행파일 빌드 스펙
  - AGPL(PyMuPDF) 제외: PDF 렌더링은 pypdfium2(BSD/Apache)
  - LGPL(FFmpeg) 제외: 영상 기능을 쓰지 않으므로 opencv의 FFmpeg DLL을 번들에서 제거
  빌드:  python -m PyInstaller --noconfirm --clean PDF2PPTX.spec
"""

EXCLUDE_BINARY_PATTERNS = ("ffmpeg",)      # LGPL 구성요소 제거

from PyInstaller.utils.hooks import collect_data_files, collect_all
_extra_datas = collect_data_files('pptx')
_pd, _pb, _ph = collect_all('pypdfium2')
_extra_datas += _pd

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=_pb,
    datas=[
        ('winocr.ps1', '.'),
        ('THIRD-PARTY-NOTICES.md', '.'),
        ('licenses', 'licenses'),
    ] + _extra_datas,
    hiddenimports=[
        'pdfio', 'tables', 'extract', 'build', 'render', 'quality', 'native', 'ppt_validate',
        'win32com.client', 'pythoncom',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pymupdf', 'fitz',
        'matplotlib', 'scipy', 'pandas', 'IPython', 'notebook', 'PySide6', 'PyQt5',
    ],
    noarchive=False,
)

# LGPL 바이너리 제외
a.binaries = [entry for entry in a.binaries
              if not any(p in str(entry[0]).lower() for p in EXCLUDE_BINARY_PATTERNS)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PDF2PPTX',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
