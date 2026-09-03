# -*- coding: utf-8 -*-
"""detect_lines() 두께 임계값 회귀.

여기서 지키는 것은 두 가지다.

1. **임계값이 DPI 에 비례할 것.** 값이 200dpi 절대 픽셀이면 300dpi 에서
   같은 물리적 굵기의 선이 탈락한다. GUI 가 300dpi 를 제공하므로 실제 문제였다.

2. **두께 상한을 함부로 넓히지 말 것.** 두께 7~11 이 line(<=6) 에도
   rect(>=12) 에도 안 잡히는 사각지대라 한때 상한을 11 로 올렸다가,
   실제 스캔 문서에서 선 검출이 8 -> 15 로 늘며 글자·그래픽을 오인해
   SSIM 이 0.8189 -> 0.8072 로 나빠졌다. 합성 픽스처만 보고 넓힌 탓이다.
   아래 test_widening_the_cap_is_a_deliberate_decision 이 그 회귀를 막는다.
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
@pytest.mark.parametrize("thickness", [1, 2, 3, 4, 5, 6])
def test_horizontal_lines_are_detected(thickness):
    """상한(200dpi 기준 6px) 이하 두께는 전부 선으로 잡혀야 한다."""
    img = _page_with_hline(thickness)
    lines = extract.detect_lines(img, np.zeros(img.shape[:2], np.uint8), dpi=200)
    assert len(lines) == 1, f"{thickness}px 가로 괘선을 놓쳤다 (검출 {len(lines)}개)"
    x0, y0, x1, y1 = lines[0]["bbox"]
    assert y1 - y0 == thickness
    assert x1 - x0 > 1000


def test_widening_the_cap_is_a_deliberate_decision():
    """두께 상한을 실제 문서군 검증 없이 올리지 못하게 막는다.

    한때 11 로 올렸다가 스캔 보고서에서 선 검출이 8 -> 15 로 늘고
    SSIM 이 0.8189 -> 0.8072 로 나빠졌다. 넓히려면 합성 픽스처가 아니라
    tests/corpus/ 의 실제 문서로 오검출이 늘지 않음을 먼저 확인할 것.
    """
    assert extract.LINE_MAX_THICK_200DPI == 6, (
        "두께 상한을 바꿨다면 실제 문서 코퍼스로 SSIM 이 나빠지지 않는지 "
        "확인했는지 먼저 답할 것")


@pytest.mark.parametrize("thickness", [7, 10, 12, 14])
def test_thick_band_is_not_a_line(thickness):
    """상한을 넘는 두께는 선으로 잡지 않는다.

    7~11 은 detect_rects(>=12) 도 안 맡는 알려진 사각지대다. 지금은 의도적으로
    비워 둔다 — 넓혔더니 실제 문서에서 더 나빠졌기 때문이다.
    """
    img = _page_with_hline(thickness)
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
    thickness = max(1, int(round(4 * scale)))     # 200dpi 에서 4px 인 선
    img = _page_with_hline(thickness, dpi_scale=scale)
    lines = extract.detect_lines(img, np.zeros(img.shape[:2], np.uint8), dpi=dpi)
    assert len(lines) == 1, f"{dpi}dpi 에서 {thickness}px 괘선을 놓쳤다"


def test_dpi_scaling_helper():
    assert extract._scale(6, 200) == 6
    assert extract._scale(6, 300) == 9
    assert extract._scale(6, 100) == 3
    assert extract._scale(1, 50) >= 1        # 0 으로 무너지지 않는다


# --------------------------------------------------------------- 세로선
@pytest.mark.parametrize("thickness", [2, 4, 6])
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
