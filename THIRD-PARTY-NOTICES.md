# 서드파티 고지 (THIRD-PARTY NOTICES)

PDF2PPTX 실행 파일에는 아래 오픈소스 구성요소가 포함되어 있습니다.
각 구성요소의 전체 라이선스 원문은 배포 패키지의 `licenses/` 폴더에 있습니다.

| 구성요소 | 버전 | 라이선스 | 상용 배포 |
|---|---|---|---|
| pypdfium2 + PDFium | 5.13.0 | BSD-3-Clause / Apache-2.0 | 가능 (고지 필요) |
| python-pptx | 1.0.2 | MIT | 가능 (고지 필요) |
| OpenCV (opencv-python-headless) | 5.0.0 | Apache-2.0 | 가능 (고지 필요) |
| NumPy | 2.4.6 | BSD-3-Clause 외 | 가능 (고지 필요) |
| Pillow | 12.3.0 | MIT-CMU | 가능 (고지 필요) |
| lxml + libxml2/libxslt | 6.1.2 | BSD-3-Clause / MIT | 가능 (고지 필요) |
| pywin32 | 312 | PSF | 가능 (고지 필요) |
| CPython 런타임 | 3.12 | PSF License | 가능 (고지 필요) |
| PyInstaller 부트로더 | 6.22.2 | GPL-2.0+ with linking exception | 가능. 예외 조항이 비공개·상용 앱 배포를 명시적으로 허용 |

PDFium에는 FreeType, libjpeg-turbo, libpng, zlib, ICU, Abseil, LCMS, OpenJPEG, libtiff 등의
하위 구성요소가 포함되며 해당 원문 역시 `licenses/` 폴더에 있습니다.

## 의도적으로 제외한 구성요소

- **PyMuPDF (fitz)** — AGPL-3.0 또는 Artifex 상용 라이선스 이중 라이선스입니다.
  비공개 상용 배포 시 AGPL 의무(전체 소스 공개)가 발생할 수 있어 배포본에서 제외했고,
  동일 기능을 BSD/Apache 라이선스인 pypdfium2로 대체했습니다.
  개발 환경에서는 `PDF2PPTX_BACKEND=pymupdf` 로 전환할 수 있으나, 그 상태의 빌드는 배포하지 마십시오.

## 재배포하지 않는 외부 요소

- **글꼴** — 배포본은 글꼴 파일을 포함하지 않습니다. 텍스트 폭 측정과 결과 PPTX의 글꼴 지정에
  사용자 PC에 이미 설치된 글꼴(기본값: Windows 기본 제공 맑은 고딕)을 사용합니다.
- **Windows OCR** — Windows에 내장된 기능을 API로 호출합니다. 별도 재배포가 없습니다.
- **Microsoft PowerPoint** — 렌더링 검수 단계에서 사용자 PC에 설치된 PowerPoint를 자동화합니다.
  최종 사용자가 정품 Office 라이선스를 보유해야 하며, 서버 환경의 무인 자동화는
  Microsoft가 지원하지 않습니다. PowerPoint가 없으면 LibreOffice로 대체하거나 이 단계를 건너뜁니다.
