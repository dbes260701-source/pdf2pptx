# 예제

## `overrides_35-40.py`

`work/make_overrides.py` 를 옮긴 것. 특정 문서(`35-40.pdf`)에 대해 손으로 작성한
overrides 생성 스크립트이며, **overrides 워크플로의 유일한 실제 예제**라서 남겨 두었다.

OCR 오타 교정, 누락 요소 추가(`add`), 오검출 제거(`delete`), 색·굵기·정렬 지정이
어떤 형태로 들어가는지 보여준다. 실행하면 현재 디렉터리에 `overrides/pN.json` 을 쓴다.

    cd work_35-40 && python ../examples/overrides_35-40.py
    python run.py "35-40.pdf" --no-extract

좌표는 그 문서의 200dpi 렌더링 픽셀 기준이므로 다른 문서에 그대로 쓸 수 없다.
형식만 참고할 것. overrides 스키마는 [../README.md](../README.md) 참조.
