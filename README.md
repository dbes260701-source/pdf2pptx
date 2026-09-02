# pdf2pptx — 스캔/이미지형 PDF → 편집 가능한 PPTX 복원 파이프라인

## 실행
    python C:\PTEP\pdf2pptx\run.py "<pdf 경로>"            # 추출 → 빌드 → PowerPoint 렌더링 → 비교 이미지
    python C:\PTEP\pdf2pptx\run.py "<pdf>" --no-extract    # overrides 수정 후 재빌드/재렌더링만
    python C:\PTEP\pdf2pptx\run.py "<pdf>" --pages 1,2     # 일부 페이지만

## 산출물 (work_<이름>/)
- pages/pN.png, hires/pN.png : 200/400dpi 렌더링
- ocr/pN.json                : Windows OCR 원본 (한국어)
- layout/pN.json             : 구조화 레이아웃 (text/rect/line/image + bbox, 색, 굵기, 정렬, 행간)
- debug/pN_boxes.png         : 감지 결과 오버레이
- overrides/pN.json          : 수동 교정 (delete / set / add) — OCR 오타, 병합 열 분리, 누락 요소 추가
- assets/                    : 잘라낸 이미지 (텍스트 영역은 자동 마스킹/인페인팅)
- render/sN.png, compare/cN.png(원본|결과), compare/oN.png(오버레이)

## overrides 형식
{ "delete": ["t3","i2"],
  "set": {"t5": {"text": "교정문구", "bold": true, "color": "#FFFFFF", "bbox": [x0,y0,x1,y1], "font_pt": 11,
                 "align": "center", "pitch_px": 40, "mask": "inpaint|fill", "bg": "#RRGGBB"}},
  "add": [ {"type":"text","text":"..","bbox":[..],"rotation":315,"runs":[{"text":"0","color":"#.."}]},
           {"type":"line","bbox":[..],"color":"#..","width_px":2,"dash":"dot","arrow_end":true},
           {"type":"rect","bbox":[..],"fill":"#..","line":"#..","line_px":2,"rounded":true,"gradient":["#a","#b"]},
           {"type":"image","bbox":[..],"inpaint":[[..]],"transparent":false,"photo":true} ] }
좌표는 pages/pN.png 픽셀(200dpi) 기준. 텍스트 id(tN)는 OCR 결과가 같으면 재추출해도 유지된다.

## 의존성
python 3.12: pymupdf, python-pptx, opencv-python-headless, numpy, pillow, pywin32 / PowerPoint 설치 / Windows OCR 한국어 팩
폰트: fonts/NanumGothic.ttf, NanumGothicBold.ttf (폭 측정용)

## 표 인식 (tables.py)

괘선이 뚜렷한 표는 자동으로 **편집 가능한 PowerPoint 표 개체**로 복원한다.
행 경계는 가로 괘선, 열 경계는 세로 괘선(없으면 모든 행을 관통하는 공백 통로)에서 얻고,
OCR 줄을 셀에 배정한다. 셀 배경색·글자색·굵기·정렬·글자 크기를 각각 추정하며,
글자가 없는 행/열은 병합하고, 셀을 덮는 사진은 표 위에 그대로 얹는다.

- 자동 검출 끄기: `extract.py ... --no-tables`
- 검출되지 않은 표를 수동 지정: overrides에 영역만 넣으면 셀 구조는 자동 복원
      {"add": [{"type": "table", "bbox": [x0, y0, x1, y1], "name": "my-table"}]}
- 행/열 경계 직접 지정: `"xs": [...], "ys": [...]` 를 함께 넣는다
- 셀 글자 교정: `"fix": {"1,2": "교정문구"}`  (행,열은 0부터)

한계: 괘선이 매우 흐린 스캔(예: 본 샘플 2페이지 지도 위 표)이나 병합 셀이 많은 표는
자동 검출되지 않거나 행이 합쳐질 수 있다. 이 경우 위의 수동 지정 경로를 쓴다.

---

# 배포용 실행 파일 (PDF2PPTX.exe)

## 빌드
    build_exe.bat        →  dist\PDF2PPTX.exe  (약 84MB, 단일 파일)

## 사용
- GUI: exe를 더블클릭 → PDF 선택 → 변환 시작
- CLI: `PDF2PPTX.exe "파일.pdf" [--out 결과.pptx] [--pages 1,3] [--dpi 200] [--font "맑은 고딕"] [--no-render]`

## 배포본 구성 원칙
- PDF 렌더링 백엔드는 **pypdfium2(BSD/Apache)** 를 사용한다. AGPL인 PyMuPDF는 빌드에서 제외한다.
  개발 환경에서는 `PDF2PPTX_BACKEND=pymupdf|pypdfium2` 로 전환 가능하나, PyMuPDF 포함 빌드는 배포 금지.
- 글꼴 파일은 재배포하지 않는다. 사용자 PC의 설치 글꼴(기본: 맑은 고딕)을 사용하며,
  없으면 `build.font_file()`이 자동으로 대체 글꼴을 찾는다.
- 배포 시 `THIRD-PARTY-NOTICES.md` 와 `licenses/` 폴더를 반드시 동봉한다(exe 내부에도 포함됨).

## 최종 사용자 환경 요구사항
- Windows 10/11, 한국어 OCR 언어 팩 (설정 > 시간 및 언어 > 언어 > 한국어 > 선택적 기능)
- 렌더링 검수 단계에만: Microsoft PowerPoint 또는 LibreOffice (없으면 자동으로 건너뜀)
