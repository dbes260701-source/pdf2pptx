# pdf2pptx — 스캔/이미지형 PDF → 편집 가능한 PPTX 복원 파이프라인

Windows 로컬에서 도는 **문서 레이아웃 복원 도구**다.
페이지를 통째로 그림으로 넣지 않고 텍스트 상자·기본 도형·개별 이미지·PowerPoint 표로 재구성한다.
born-digital PDF 는 PDF 객체를 직접 읽고, 스캔본은 OCR/CV 로 복원한다.

## 범위 (무엇이 아닌지 먼저)

- **대상**: 스캔/이미지형 PDF, 그리고 사내에서 반복되는 보고서·회의자료처럼
  서식이 일정한 문서군. 이 범위에서 가장 잘 동작한다.
- **아직 아닌 것**: 임의의 PDF 를 완전한 시각 충실도로 보존하는 범용 변환기가 아니다.
- **미지원**: 베지어 곡선·임의 다각형·그라디언트·투명도 그룹·클리핑 경로, 세로쓰기·RTL.
  이런 객체를 만나면 조용히 버리지 않고 미지원으로 보고하며, 기본 설정에서는
  품질 게이트가 실패한다(→ [docs/ROADMAP.md](docs/ROADMAP.md) R9).
- 결과물은 **사람이 검수한 뒤** 쓰는 것을 전제로 한다. 무인 배치 실행 승인 기준은
  [docs/ROADMAP.md](docs/ROADMAP.md) 마지막 절에 있다.

외부 평가 두 건에 대한 항목별 대응은 [docs/EVALUATION-RESPONSE.md](docs/EVALUATION-RESPONSE.md) 참조.
기여자와 AI 도구 사용 내역은 [CONTRIBUTORS.md](CONTRIBUTORS.md) 참조.

## 실행
    python run.py "<pdf 경로>"            # 추출 → 빌드 → PowerPoint 렌더링 → 비교 + 품질 게이트
    python run.py "<pdf>" --no-extract    # overrides 수정 후 재빌드/재렌더링만
    python run.py "<pdf>" --pages 1,2     # 일부 페이지만
    python run.py "<pdf>" --allow-degraded  # 품질 미달이어도 0으로 종료(사유는 보고서에 남음)

## 두 가지 추출 경로

페이지마다 자동으로 고른다.

| | 네이티브 경로 (기본) | OCR/CV 경로 |
|---|---|---|
| 대상 | PDF 안에 텍스트 객체가 있는 born-digital 문서 | 스캔/이미지형 문서 |
| 글자 | PDF 원본 문자열 — **OCR 오타가 없다** | Windows OCR 인식 |
| 글꼴 크기·굵기 | 원본 값 (글꼴 이름으로 굵기 판별) | 글자 높이·획 두께로 추정 |
| 색 | 원본 값 | 픽셀에서 추정 |
| 겹침 순서 | **원본 그리기 순서 복원** | 타입 기준 근사 |
| 이미지 | **임베디드 JPEG 원본 바이트 통과** (재인코딩 없음) | 렌더 이미지에서 잘라내기 |
| 표 | 렌더 이미지에서 괘선 검출 | 렌더 이미지에서 괘선 검출 |

페이지에 텍스트 객체가 있고 글자 수가 `pdfio.NATIVE_MIN_CHARS`(기본 20자) 이상이면
네이티브 경로를 쓴다. 스캔 페이지처럼 글자가 거의 없으면 OCR 경로로 넘어간다.
`--no-native` 로 항상 OCR 경로를 강제할 수 있다.

같은 PDF 를 두 경로로 변환해 비교한 예:

| 경로 | SSIM | 최악 타일 | MAE | 결과 |
|---|---:|---:|---:|---|
| OCR/CV | 0.886 | 0.289 | 3.734 | 게이트 실패 (사진 질감 손실) |
| 네이티브 | **0.944** | **0.583** | **3.123** | 통과 |

복원할 수 없는 객체(복잡한 벡터 경로, shading, form)는 버리지 않고
`layout/pN.json` 의 `unsupported` 에 사유와 함께 남으며, 기본 설정에서는
품질 게이트가 이를 실패로 처리한다.

## 품질 게이트

변환이 끝나면 원본 페이지와 PowerPoint 렌더 결과를 비교해 `work_<이름>/report.json` 을 쓰고,
기준에 못 미치면 **0이 아닌 종료 코드로 끝난다.** 배치 스크립트가 부실한 변환을
성공으로 집계하지 않게 하기 위한 것이다.

측정 항목:

| 지표 | 기본 임계값 | 잡아내는 것 |
|---|---:|---|
| 페이지 SSIM | ≥ 0.75 | 전반적인 레이아웃 붕괴 |
| **최악 타일 SSIM** (8×8 격자) | ≥ 0.35 | 큰 개체 하나가 통째로 빠진 경우 — 페이지 평균만 보면 놓친다 |
| MAE | ≤ 28.0 | 색·명도 전반의 어긋남 |
| 텍스트 복원율 | ≥ 0.90 | 원본 줄이 조용히 사라진 경우 |
| 미지원 객체 | 0개 | 복원하지 못한 객체가 보고서에만 남고 넘어가는 경우 |

최악 타일 위치는 `compare/oN.png` 에 빨간 상자로 표시된다.
임계값은 문서군마다 다르므로 `PDF2PPTX_THRESHOLDS=<json 경로>` 로 덮어쓸 수 있다.

종료 코드:

| 코드 | 의미 |
|---:|---|
| 0 | 품질 게이트 통과 (또는 `--allow-degraded` 로 완화) |
| 2 | 잘못된 입력 또는 옵션 |
| 3 | PDF 파싱/추출 실패 |
| 4 | PPTX 패키지 검증 실패 |
| 5 | 시각 품질 임계값 미달 |
| 6 | 원본 요소 누락 감지 |
| 7 | PowerPoint 열기/저장/재개봉 실패 (미구현 — ROADMAP R4) |
| 8 | 필수 렌더러/외부 의존성 없음 |

`--allow-degraded` 는 시각·누락 실패만 완화한다. 패키지 검증 실패(4)와 렌더러 부재(8)는
품질을 확인조차 못 한 상태이므로 완화되지 않는다. 완화된 결과는 보고서에
`"status": "degraded"` 로 남아 정상 통과(`pass`)와 구분된다.

## 산출물 (work_<이름>/)
- pages/pN.png, hires/pN.png : 200/400dpi 렌더링
- ocr/pN.json                : Windows OCR 원본 (한국어) — OCR 경로에서만 생성
- report.json                : 품질 지표와 pass/degraded/fail 판정
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

## 설치와 개발

    pip install -r requirements.txt          # 실행에 필요한 것만
    pip install -r requirements-dev.txt      # 테스트 · exe 빌드 포함
    pip install -e .                         # pdf2pptx 명령으로 설치
    pytest                                   # 회귀 테스트 (OCR/PowerPoint 없이 동작)

Python 3.12 / Windows 10·11. 별도로 필요한 것: Windows OCR 한국어 언어 팩,
렌더링 검수 단계에 한해 PowerPoint 또는 LibreOffice.
폰트 `fonts/NanumGothic*.ttf` 는 글자 폭 측정용이며 배포 exe 에는 포함하지 않는다.

PDF 렌더링 백엔드는 **pypdfium2**(BSD-3-Clause / Apache-2.0)를 쓴다.
AGPL 인 PyMuPDF 는 런타임 의존성이 아니며, 백엔드 대조가 필요할 때만
`pip install -e ".[pymupdf]"` 로 넣고 `PDF2PPTX_BACKEND=pymupdf` 로 전환한다.
**PyMuPDF 가 포함된 환경에서 만든 exe 는 배포하지 않는다.**

## 테스트

    pytest                      # 전체 (65건, 수 초)
    pytest -m "not slow"        # OCR/렌더러가 필요 없는 것만

핵심은 통과 사례가 아니라 **음성 대조군**이다. 고의로 망가뜨린 출력
(빈 슬라이드, 개체 하나가 빠진 페이지, 깨진 XML, 잘린 zip)이 반드시 거부되는지 확인한다.
이 테스트가 깨졌다면 품질 게이트가 무력화된 것이다.

사내 문서 회귀 코퍼스는 [tests/corpus/](tests/corpus/) 참조 —
**PDF 원본은 커밋하지 않고** 매니페스트(해시·분류·기대 임계값)만 둔다.

## 표 인식 (tables.py)

괘선이 뚜렷한 표는 자동으로 **편집 가능한 PowerPoint 표 개체**로 복원한다.
행 경계는 가로 괘선, 열 경계는 세로 괘선(없으면 모든 행을 관통하는 공백 통로)에서 얻고,
OCR 줄을 셀에 배정한다. 셀 배경색·글자색·굵기·정렬·글자 크기를 각각 추정하며,
글자가 없는 행/열은 병합하고, 셀을 덮는 사진은 표 위에 그대로 얹는다.

- 자동 검출 끄기: `--no-tables` (run.py / extract.py 공통)
- 검출되지 않은 표를 수동 지정: overrides에 영역만 넣으면 셀 구조는 자동 복원
      {"add": [{"type": "table", "bbox": [x0, y0, x1, y1], "name": "my-table"}]}
- 행/열 경계 직접 지정: `"xs": [...], "ys": [...]` 를 함께 넣는다
- 셀 글자 교정: `"fix": {"1,2": "교정문구"}`  (행,열은 0부터)

한계: 괘선이 매우 흐린 스캔(예: 본 샘플 2페이지 지도 위 표)이나 병합 셀이 많은 표는
자동 검출되지 않거나 행이 합쳐질 수 있다. 이 경우 위의 수동 지정 경로를 쓴다.

---

# 배포용 실행 파일 (PDF2PPTX.exe)

## 빌드
    build_exe.bat        →  dist\PDF2PPTX.exe  (약 68MB, 단일 파일)

## 사용
- GUI: exe를 더블클릭 → PDF 선택 → 변환 시작
- CLI: `PDF2PPTX.exe "파일.pdf" [--out 결과.pptx] [--pages 1,3] [--dpi 200] [--font "맑은 고딕"]
        [--no-render] [--allow-degraded] [--no-native]`
  품질 게이트를 통과하지 못하면 0이 아닌 종료 코드로 끝난다(위 표 참조).

## 배포본 구성 원칙
- PDF 렌더링 백엔드는 **pypdfium2(BSD/Apache)** 를 사용한다. AGPL인 PyMuPDF는 빌드에서 제외한다.
  개발 환경에서는 `PDF2PPTX_BACKEND=pymupdf|pypdfium2` 로 전환 가능하나, PyMuPDF 포함 빌드는 배포 금지.
- 글꼴 파일은 재배포하지 않는다. 사용자 PC의 설치 글꼴(기본: 맑은 고딕)을 사용하며,
  없으면 `build.font_file()`이 자동으로 대체 글꼴을 찾는다.
- 배포 시 `THIRD-PARTY-NOTICES.md` 와 `licenses/` 폴더를 반드시 동봉한다(exe 내부에도 포함됨).

## 최종 사용자 환경 요구사항
- Windows 10/11, 한국어 OCR 언어 팩 (설정 > 시간 및 언어 > 언어 > 한국어 > 선택적 기능)
- 렌더링 검수 단계에만: Microsoft PowerPoint 또는 LibreOffice (없으면 자동으로 건너뜀)
