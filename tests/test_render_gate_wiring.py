# -*- coding: utf-8 -*-
"""render.main() 이 실제로 0이 아닌 종료 코드를 돌려주는지.

평가서 §4.3 의 지적은 "시각 검수가 실패해도 CLI 가 0으로 끝난다"였다.
게이트 로직이 옳아도 배선이 끊겨 있으면 무의미하므로, 여기서는 배선만 본다.
PowerPoint/LibreOffice 없이 돌리기 위해 export() 를 대체한다.
"""
import os, sys, json
import numpy as np, cv2
import pytest

import render as render_mod
import quality


def _run(work, pptx, fake_slides, extra_argv=()):
    """export() 를 가짜 렌더 결과로 대체하고 render.main() 을 돌린다."""
    def fake_export(_pptx, outdir, W, H):
        os.makedirs(outdir, exist_ok=True)
        for k, img in enumerate(fake_slides, start=1):
            cv2.imwrite(os.path.join(outdir, f"s{k}.png"), img)
        return len(fake_slides), "fake"

    argv, real = sys.argv, render_mod.export
    sys.argv = ["render", pptx, work] + list(extra_argv)
    render_mod.export = fake_export
    try:
        return render_mod.main()
    finally:
        sys.argv, render_mod.export = argv, real


@pytest.fixture
def built(work, tmp_path):
    import build as build_mod
    out = str(tmp_path / "out.pptx")
    argv = sys.argv
    sys.argv = ["build", work, out]
    try:
        build_mod.main()
    finally:
        sys.argv = argv
    return out


def test_faithful_render_exits_zero_and_writes_report(work, built, page_img):
    rc = _run(work, built, [page_img.copy()])
    assert rc == quality.EXIT_OK
    rep = json.load(open(os.path.join(work, "report.json"), encoding="utf-8"))
    assert rep["status"] == "pass" and rep["renderer"] == "fake"
    assert rep["pages"][0]["ssim"] > 0.99


def test_blank_render_exits_non_zero(work, built, page_img):
    """가장 중요한 회귀: 빈 슬라이드가 나왔는데 0을 돌려주면 fail-open 으로 되돌아간 것이다."""
    rc = _run(work, built, [np.full_like(page_img, 255)])
    assert rc == quality.EXIT_VISUAL
    rep = json.load(open(os.path.join(work, "report.json"), encoding="utf-8"))
    assert rep["status"] == "fail" and rep["failures"]


def test_missing_renderer_exits_with_renderer_code(work, built, page_img):
    def no_renderer(_pptx, outdir, W, H):
        os.makedirs(outdir, exist_ok=True)
        return 0, None
    argv, real = sys.argv, render_mod.export
    sys.argv = ["render", built, work]
    render_mod.export = no_renderer
    try:
        rc = render_mod.main()
    finally:
        sys.argv, render_mod.export = argv, real
    assert rc == quality.EXIT_RENDERER, "렌더러가 없으면 조용히 건너뛰지 말고 실패해야 한다"


def test_allow_degraded_flag_exits_zero_but_marks_degraded(work, built, page_img):
    rc = _run(work, built, [np.full_like(page_img, 255)], extra_argv=["--allow-degraded"])
    assert rc == quality.EXIT_OK
    rep = json.load(open(os.path.join(work, "report.json"), encoding="utf-8"))
    assert rep["status"] == "degraded", "성공(pass)과 반드시 구분되어야 한다"
    assert rep["failures"]


def test_worst_tile_is_marked_on_overlay_image(work, built, page_img):
    broken = page_img.copy()
    broken[420:700, 60:340] = 255
    _run(work, built, [broken], extra_argv=["--allow-degraded"])
    assert os.path.exists(os.path.join(work, "compare", "o1.png"))
    rep = json.load(open(os.path.join(work, "report.json"), encoding="utf-8"))
    assert rep["pages"][0]["worst_tile_bbox"] is not None
