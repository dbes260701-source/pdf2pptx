@echo off
REM PDF2PPTX 단일 실행파일 빌드 (AGPL 라이브러리 제외: PyMuPDF 대신 pypdfium2 사용)
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name PDF2PPTX ^
  --paths . ^
  --add-data "winocr.ps1;." ^
  --add-data "THIRD-PARTY-NOTICES.md;." ^
  --add-data "licenses;licenses" ^
  --collect-data pptx ^
  --collect-all pypdfium2 ^
  --hidden-import pdfio --hidden-import tables --hidden-import extract --hidden-import build --hidden-import render ^
  --hidden-import quality --hidden-import native ^
  --hidden-import win32com.client --hidden-import pythoncom ^
  --exclude-module pymupdf --exclude-module fitz ^
  --exclude-module matplotlib --exclude-module scipy --exclude-module pandas ^
  --exclude-module IPython --exclude-module notebook --exclude-module PySide6 --exclude-module PyQt5 ^
  app.py
echo.
echo 완료: %~dp0dist\PDF2PPTX.exe
pause
