# -*- coding: utf-8 -*-
"""테스트 공용 픽스처.

원칙(평가서 §8.5): 사내 PDF 원본은 저장소에 커밋하지 않는다.
여기 픽스처는 전부 코드로 합성하므로 커밋해도 안전하다.
실제 문서군 회귀는 tests/corpus/manifest.example.json 참조.
"""
import os, sys, json
import numpy as np
import cv2
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def page_img():
    """텍스트 줄 · 색 띠 · 사진 블록이 있는 합성 페이지 (200dpi A4 비율 축소)."""
    h, w = 800, 600
    img = np.full((h, w, 3), 255, np.uint8)
    cv2.rectangle(img, (40, 40), (560, 100), (200, 120, 40), -1)        # 머리말 색 띠
    for i, y in enumerate(range(160, 320, 40)):                          # 본문 줄
        cv2.rectangle(img, (60, y), (60 + 380 - i * 30, y + 22), (30, 30, 30), -1)
    cv2.line(img, (40, 360), (560, 360), (120, 120, 120), 2)             # 가로 괘선
    rng = np.random.default_rng(0)                                       # 사진 블록
    img[420:700, 60:340] = rng.integers(0, 255, (280, 280, 3), dtype=np.uint8)
    cv2.rectangle(img, (380, 420), (560, 700), (60, 180, 90), -1)        # 단색 도형
    return img


@pytest.fixture
def work(tmp_path, page_img):
    """extract 산출물 형태를 흉내낸 최소 작업 디렉터리."""
    w = tmp_path / "work"
    for d in ("pages", "hires", "layout", "ocr", "render", "compare"):
        (w / d).mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(w / "pages" / "p1.png"), page_img)
    cv2.imwrite(str(w / "hires" / "p1.png"),
                cv2.resize(page_img, (page_img.shape[1] * 2, page_img.shape[0] * 2)))
    layout = dict(
        page=1, width=page_img.shape[1], height=page_img.shape[0],
        pt_w=page_img.shape[1] * 72 / 200, pt_h=page_img.shape[0] * 72 / 200, dpi=200,
        elements=[
            dict(id="r0", type="rect", bbox=[40, 40, 560, 100], fill="#2878C8"),
            dict(id="t0", type="text", text="보고서 제목", bbox=[60, 55, 400, 90],
                 font_px=28.0, color="#FFFFFF", bold=True, align="left", pitch_px=None, bg="#2878C8"),
            dict(id="t1", type="text", text="첫째 줄\n둘째 줄", bbox=[60, 160, 440, 300],
                 font_px=22.0, color="#1E1E1E", bold=False, align="left", pitch_px=40.0, bg="#FFFFFF"),
            dict(id="l0", type="line", bbox=[40, 359, 560, 362], color="#787878", width_px=2),
            dict(id="i0", type="image", bbox=[60, 420, 340, 700], photo=True),
        ])
    json.dump(layout, open(w / "layout" / "p1.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump({"lines": [{"text": "보고서 제목", "words": [{"x": 60, "y": 55, "w": 340, "h": 35}]},
                         {"text": "첫째 줄", "words": [{"x": 60, "y": 160, "w": 380, "h": 24}]},
                         {"text": "둘째 줄", "words": [{"x": 60, "y": 200, "w": 350, "h": 24}]}]},
              open(w / "ocr" / "p1.json", "w", encoding="utf-8"), ensure_ascii=False)
    return str(w)
