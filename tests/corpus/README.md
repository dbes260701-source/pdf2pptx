# 회귀 코퍼스

평가서 §8.5 / §11 대응. **사내 PDF 원본은 이 저장소에 커밋하지 않는다.**
여기에는 매니페스트(해시·분류·기대 동작·임계값)만 두고, PDF 실물은
로컬 또는 사내 공유 경로에 두고 `PDF2PPTX_CORPUS` 환경변수로 가리킨다.

    set PDF2PPTX_CORPUS=D:\pdf2pptx-corpus
    python -m pytest tests -m slow

`manifest.example.json` 을 `manifest.json` 으로 복사해 채운다(`manifest.json` 은 .gitignore 대상).

## 목표 구성 (30~50건)

| 분류 | 최소 건수 | 확인 목적 |
|---|---:|---|
| `text_only`   | 5 | 기본 텍스트 복원율·글꼴 크기 |
| `table`       | 6 | 괘선 있음/없음/부분/병합/불규칙 |
| `photo`       | 4 | 원본 이미지 품질·해상도 보존 |
| `vector`      | 4 | 도형·곡선·아이콘 (현재 미지원 범위 확인용) |
| `scanned`     | 5 | OCR 경로 |
| `mixed`       | 6 | 한/영 혼용, 다단, 회전 텍스트 |
| `chart`       | 4 | 차트 격자를 표로 오인하지 않는지 |
| `complex`     | 4 | 투명도·클리핑·마스크 |
| `multi_size`  | 2 | 페이지 크기가 섞인 문서 |
