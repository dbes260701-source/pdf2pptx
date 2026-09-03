# -*- coding: utf-8 -*-
"""detect_lines() 두께 임계값 회귀.

실제로 있었던 버그: 200dpi 렌더에서 높이 10px 인 가로 괘선이
detect_lines(h<=6) 에도 detect_rects(h>=12) 에도 걸리지 않고 조용히 사라졌다.
두 검출기의 임계값 사이에 사각지대가 있었고, 값이 200dpi 절대 픽셀이라
300dpi 로 올리면 사각지대가 더 넓어졌다.
"""
import numpy as np
import cv2
import pytest

import extract


def _page_with_hline(thickness, dpi_scale=1.0, color=150, W=1654, H=1200):
    """흰 배경에 가로 괘선 하나만 있는 페이지."""
    W, H = int(W * dpi_scale), int(H * dpi_scale)
    img = np.full((H, W, 3), 255, np.uint8)
    y = H // 2
    img[y:y + thickness, int(120 * dpi_scale):int(1534 * dpi_scale)] = color
    return img


def _page_with_vline(thickness, color=150, W=1200, H=1654):
    img = np.full((H, W, 3), 255, np.uint8)
    x = W // 2
    img[int(120):int(1534), x:x + thickness] = color
    return img


# --------------------------------------------------------------- 사각지대
@pytest.mark.parametrize("thickness", [1, 2, 3, 5, 6, 7, 8, 9, 10, 11])
def test_horizontal_lines_up_to_gap_are_detected(thickness):
    """1~11px 두께는 전부 선으로 잡혀야 한다. 12px 부터는 detect_rects 영역이다."""
    img = _page_with_hline(thickness)
    lines = extract.detect_lines(img, np.zeros(img.shape[:2], np.uint8), dpi=200)
    assert len(lines) == 1, f"{thickness}px 가로 괘선을 놓쳤다 (검출 {len(lines)}개)"
    x0, y0, x1, y1 = lines[0]["bbox"]
    assert y1 - y0 == thickness
    assert x1 - x0 > 1000


def test_regression_10px_line_from_real_render():
    """버그 재현 케이스: 실제 PDF 렌더에서 나온 10px 괘선."""
    img = _page_with_hline(10, color=213)
    lines = extract.detect_lines(img, np.zeros(img.shape[:2], np.uint8), dpi=200)
    assert len(lines) == 1, "10px 괘선이 line 과 rect 사이 사각지대로 사라졌다"


def test_thick_band_is_not_a_line():
    """detect_rects 가 맡을 두께(12px 이상)는 선으로 잡지 않는다 — 중복 검출 방지."""
    img = _page_with_hline(14)
    lines = extract.detect_lines(img, np.zeros(img.shape[:2], np.uint8), dpi=200)
    assert lines == []


def test_stubby_block_is_not_a_line():
    """길이/두께 비가 낮으면 선이 아니라 덩어리다."""
    img = np.full((400, 400, 3), 255, np.uint8)
    img[200:210, 100:170] = 150          # 70x10 -> 비율 7:1
    lines = extract.detect_lines(img, np.zeros(img.shape[:2], np.uint8), dpi=200)
    assert lines == []


# --------------------------------------------------------------- DPI 비례
@pytest.mark.parametrize("dpi,scale", [(150, 0.75), (200, 1.0), (300, 1.5)])
def test_threshold_scales_with_dpi(dpi, scale):
    """같은 물리적 굵기의 선은 dpi 가 올라가도 계속 잡혀야 한다.

    임계값이 200dpi 절대 픽셀이면 300dpi 에서 같은 선이 탈락한다.
    """
    thickness = max(1, int(round(9 * scale)))     # 200dpi 에서 9px 인 선
    img = _page_with_hline(thickness, dpi_scale=scale)
    lines = extract.detect_lines(img, np.zeros(img.shape[:2], np.uint8), dpi=dpi)
    assert len(lines) == 1, f"{dpi}dpi 에서 {thickness}px 괘선을 놓쳤다"


def test_dpi_scaling_helper():
    assert extract._scale(6, 200) == 6
    assert extract._scale(6, 300) == 9
    assert extract._scale(6, 100) == 3
    assert extract._scale(1, 50) >= 1        # 0 으로 무너지지 않는다


# --------------------------------------------------------------- 세로선
@pytest.mark.parametrize("thickness", [2, 6, 10, 11])
def test_vertical_lines_are_detected(thickness):
    img = _page_with_vline(thickness)
    lines = extract.detect_lines(img, np.zeros(img.shape[:2], np.uint8), dpi=200)
    assert len(lines) == 1, f"{thickness}px 세로 괘선을 놓쳤다"
    x0, y0, x1, y1 = lines[0]["bbox"]
    assert x1 - x0 == thickness


# --------------------------------------------------------------- 기존 동작 유지
def test_textmask_still_suppresses_lines():
    img = _page_with_hline(3)
    tm = np.zeros(img.shape[:2], np.uint8)
    tm[:] = 255
    assert extract.detect_lines(img, tm, dpi=200) == []


def test_low_contrast_line_is_ignored():
    """배경과 거의 같은 밝기면 선으로 보지 않는다(기존 대비 조건)."""
    img = _page_with_hline(3, color=250)
    assert extract.detect_lines(img, np.zeros(img.shape[:2], np.uint8), dpi=200) == []
